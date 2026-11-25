import assert from 'node:assert/strict';
import test from 'node:test';
import {
  Round, MailStream, DURATION, MAX_QUEUE, FEVER_TARGET, FEVER_DURATION,
  FEVER_INTERVAL, intervalAt, multiplierFor, starsFor, pointsToNextStar,
} from '../assets/stampost-round.mjs';

function randomFrom(seed) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 2 ** 32;
  };
}

function startFever(round) {
  while (round.total < FEVER_TARGET) {
    if (!round.queue.length) round.advance(round.nextArrival);
    round.send(round.leading.stamp ?? 'flower');
  }
}

test('rush starts with three letters, follows the app arrival curve, and ends on overflow or time', () => {
  const round = new Round(randomFrom(1));
  assert.deepEqual(round.queue, ['flower', 'flower', 'moon']);
  assert.equal(round.nextArrival, 1550);
  assert.deepEqual([0, 13999, 14000, 28999, 29000].map(intervalAt), [1450, 1450, 1120, 1120, 900]);
  round.advance(775);
  assert.equal(round.arrivalProgress, 0.5);
  round.advance(5899);
  assert.equal(round.queue.length, MAX_QUEUE);
  assert.equal(round.end, null);
  round.advance(5900);
  assert.equal(round.end, 'overflow');
  assert.equal(round.send('flower').kind, 'waiting');

  const cleared = new Round(randomFrom(2));
  while (cleared.elapsed < DURATION) {
    while (cleared.queue.length) cleared.send(cleared.leading.stamp ?? 'moon');
    cleared.advance(Math.min(DURATION, cleared.nextArrival));
  }
  assert.equal(cleared.end, 'time');
  assert.equal(cleared.inFever, false);
});

test('preview is stable and matches actual mail, with gold after the third normal draw only', () => {
  const first = new MailStream(randomFrom(17));
  const second = new MailStream(randomFrom(17));
  const other = new MailStream(randomFrom(42));
  assert.deepEqual(first.peek(3, false), first.peek(3, false));
  const stream = Array.from({ length: 200 }, () => first.next(false));
  assert.deepEqual(stream, Array.from({ length: 200 }, () => second.next(false)));
  assert.notDeepEqual(stream, Array.from({ length: 200 }, () => other.next(false)));
  assert.ok(stream.slice(0, 3).every(letter => letter !== 'gold'));
  assert.ok(stream.slice(3).includes('gold'));

  const round = new Round(randomFrom(17));
  const upcoming = [...round.upcoming];
  round.advance(round.nextArrival);
  assert.equal(round.queue.at(-1), upcoming[0]);
  assert.deepEqual(round.upcoming.slice(0, 2), upcoming.slice(1));
});

test('normal and Fever run ranges and gold chance match the app', () => {
  for (const [roll, normalLength, feverLength] of [[.19, 1, 3], [.31, 2, 4], [.66, 3, 5], [.9, 4, 6]]) {
    for (const [fever, length] of [[false, normalLength], [true, feverLength]]) {
      const mail = new MailStream(() => roll);
      const run = mail.peek(length + 1, fever);
      assert.equal(new Set(run.slice(0, length)).size, 1);
      assert.notEqual(run[0], run[length]);
      assert.ok(!run.includes('gold'));
    }
  }
  const mail = new MailStream(randomFrom(40));
  let gold = 0;
  for (let i = 0; i < 50_000; i++) {
    if (mail.next(false) === 'gold') gold++;
    assert.notEqual(mail.next(true), 'gold');
  }
  assert.ok(gold / 50_000 > .055 && gold / 50_000 < .065);
});

test('gold joins a matching run, doubles the entire batch, and can be sent alone with any stamp', () => {
  const round = new Round(randomFrom(3));
  round.queue = ['gold', 'flower', 'flower', 'gold', 'flower', 'moon'];
  assert.deepEqual(round.leading, { stamp: 'flower', count: 5, gold: true, points: 30 });
  assert.equal(round.send('moon').kind, 'miss');
  assert.equal(round.score, 0);
  assert.deepEqual(round.send('flower'), {
    kind: 'sent', stamp: 'flower', count: 5, gold: true, points: 30, multiplier: 1, feverStarted: false,
  });
  assert.deepEqual(round.queue, ['moon']);
  round.queue = ['gold', 'gold'];
  assert.equal(round.send('star').points, 6);
});

test('combo uses ×2 at four, ×3 at eight, and only times out while mail waits', () => {
  const round = new Round(randomFrom(4));
  assert.deepEqual([3, 4, 7, 8].map(multiplierFor), [1, 2, 2, 3]);
  for (const expected of [1, 1, 1, 2, 2, 2, 2, 3]) {
    round.queue = ['flower'];
    assert.equal(round.leading.points, expected);
    assert.equal(round.send('flower').points, expected);
  }
  assert.equal(round.bestCombo, 8);
  round.advance(1549);
  assert.equal(round.stall, 0);
  round.advance(1550 + 3499);
  assert.equal(round.combo, 8);
  round.advance(1550 + 3500);
  assert.equal(round.combo, 0);
  round.send(round.leading.stamp ?? 'flower');
  round.queue = ['moon'];
  const score = round.score;
  assert.equal(round.send('star').kind, 'miss');
  assert.equal(round.combo, 0);
  assert.equal(round.score, score - 2);
  assert.equal(round.bestCombo, 8);
});

test('Fever lasts six seconds, skips overflow, and grants a full normal interval afterwards', () => {
  const round = new Round(randomFrom(8));
  startFever(round);
  const started = round.elapsed;
  assert.equal(round.total, 18);
  assert.equal(round.feverEnd, started + FEVER_DURATION);
  assert.equal(round.nextArrival, started + FEVER_INTERVAL);
  const preview = [...round.upcoming];
  round.advance(round.nextArrival);
  assert.equal(round.queue.at(-1), preview[0]);
  assert.deepEqual(round.upcoming.slice(0, 2), preview.slice(1));
  assert.equal(round.nextArrival, started + FEVER_INTERVAL * 2);

  round.queue = ['moon', 'gold', 'moon'];
  assert.equal(round.send('moon').points, 6 * 2 * 3 * 2);
  assert.equal(round.feverGauge, 18);
  round.advance(started + 5999);
  assert.equal(round.inFever, true);
  assert.equal(round.queue.length, MAX_QUEUE);
  assert.equal(round.end, null);
  round.advance(started + 6000);
  assert.equal(round.inFever, false);
  assert.equal(round.feverGauge, 0);
  assert.equal(round.arrivalProgress, 0);
  assert.equal(round.nextArrival, round.elapsed + intervalAt(round.elapsed));
  round.advance(round.nextArrival - 1);
  assert.equal(round.end, null);
  round.advance(round.nextArrival);
  assert.equal(round.end, 'overflow');
});

test('record stars and the next star use the app thresholds', () => {
  assert.deepEqual([0, 149, 150, 299, 300, 449, 450, 1000].map(starsFor), [0, 0, 1, 1, 2, 2, 3, 3]);
  assert.deepEqual([0, 150, 420, 450].map(pointsToNextStar), [150, 150, 30, null]);
});
