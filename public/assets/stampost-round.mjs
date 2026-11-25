export const STAMPS = ['flower', 'moon', 'star'];
export const DURATION = 45_000;
export const MAX_QUEUE = 6;
export const COMBO_TIMEOUT = 3_500;
export const FEVER_TARGET = 18;
export const FEVER_DURATION = 6_000;
export const FEVER_INTERVAL = 450;
export const STAR_THRESHOLDS = [150, 300, 450];
const MISS_PENALTY = 2;

export const batchPoints = count => count * (count + 1) / 2;
export const multiplierFor = combo => combo >= 8 ? 3 : combo >= 4 ? 2 : 1;
export const intervalAt = time => time < 14_000 ? 1450 : time < 29_000 ? 1120 : 900;
export const starsFor = score => STAR_THRESHOLDS.filter(threshold => score >= threshold).length;
export const pointsToNextStar = score => {
  const threshold = STAR_THRESHOLDS[starsFor(score)];
  return threshold === undefined ? null : threshold - score;
};

function newRun() {
  return { stampIndex: null, remaining: 0, buffer: [] };
}

export class MailStream {
  constructor(random = Math.random) {
    this.random = random;
    this.normal = newRun();
    this.fever = newRun();
    this.normalDraws = 0;
  }

  startFever() {
    this.fever = newRun();
  }

  next(inFever) {
    this.peek(1, inFever);
    return (inFever ? this.fever : this.normal).buffer.shift();
  }

  peek(count, inFever) {
    const run = inFever ? this.fever : this.normal;
    while (run.buffer.length < count) {
      if (run.remaining === 0) {
        run.stampIndex = run.stampIndex === null
          ? Math.floor(this.random() * STAMPS.length)
          : (run.stampIndex + 1 + Math.floor(this.random() * 2)) % STAMPS.length;
        const cutoffs = inFever ? [20, 55, 90] : [30, 65, 90];
        const roll = Math.floor(this.random() * 100);
        run.remaining = (inFever ? 3 : 1) + cutoffs.filter(cutoff => roll >= cutoff).length;
      }
      run.remaining--;
      const gold = !inFever && ++this.normalDraws > 3 && this.random() < 0.06;
      run.buffer.push(gold ? 'gold' : STAMPS[run.stampIndex]);
    }
    return run.buffer.slice(0, count);
  }
}

export class Round {
  constructor(random) {
    this.mail = new MailStream(random);
    this.queue = ['flower', 'flower', 'moon'];
    this.elapsed = 0;
    this.arrivalBase = 0;
    this.nextArrival = 1550;
    this.combo = 0;
    this.bestCombo = 0;
    this.stall = 0;
    this.feverGauge = 0;
    this.feverEnd = null;
    this.score = 0;
    this.total = 0;
    this.bestBatch = 0;
    this.end = null;
    this.refreshUpcoming();
  }

  get inFever() { return this.feverEnd !== null; }
  get arrivalProgress() {
    return Math.min(1, (this.elapsed - this.arrivalBase) / (this.nextArrival - this.arrivalBase));
  }

  get leading() {
    const stamp = this.queue.find(letter => letter !== 'gold');
    const firstMismatch = this.queue.findIndex(letter => letter !== 'gold' && letter !== stamp);
    const count = firstMismatch === -1 ? this.queue.length : firstMismatch;
    const gold = this.queue.slice(0, count).includes('gold');
    return { stamp, count, gold, points: this.batchScore(count, gold, multiplierFor(this.combo + 1)) };
  }

  batchScore(count, gold, multiplier) {
    return batchPoints(count) * (gold ? 2 : 1) * multiplier * (this.inFever ? 2 : 1);
  }

  refreshUpcoming() {
    const feverCount = this.inFever
      ? Math.max(0, Math.min(3, Math.ceil((this.feverEnd - this.nextArrival) / FEVER_INTERVAL)))
      : 0;
    this.upcoming = [...this.mail.peek(feverCount, true), ...this.mail.peek(3 - feverCount, false)];
  }

  advance(now) {
    if (this.end || now < this.elapsed) return;
    const target = Math.min(now, DURATION);
    while (true) {
      if (this.inFever && this.feverEnd <= target && this.feverEnd <= this.nextArrival) {
        this.advanceClock(this.feverEnd);
        this.endFever();
        this.refreshUpcoming();
      } else if (this.nextArrival <= target && this.nextArrival < DURATION) {
        this.advanceClock(this.nextArrival);
        if (this.queue.length === MAX_QUEUE && !this.inFever) {
          this.end = 'overflow';
          break;
        }
        const letter = this.mail.next(this.inFever);
        if (this.queue.length < MAX_QUEUE) this.queue.push(letter);
        this.arrivalBase = this.nextArrival;
        this.nextArrival += this.inFever ? FEVER_INTERVAL : intervalAt(this.nextArrival);
        this.refreshUpcoming();
      } else {
        break;
      }
    }
    this.advanceClock(target);
    if (!this.end && target === DURATION) {
      this.end = 'time';
      if (this.inFever) this.endFever();
    }
  }

  advanceClock(time) {
    if (this.combo && this.queue.length) {
      this.stall = Math.min(COMBO_TIMEOUT, this.stall + time - this.elapsed);
      if (this.stall === COMBO_TIMEOUT) this.combo = 0;
    }
    this.elapsed = time;
  }

  endFever() {
    this.feverEnd = null;
    this.feverGauge = 0;
    this.arrivalBase = this.elapsed;
    this.nextArrival = this.elapsed + intervalAt(this.elapsed);
  }

  send(stamp) {
    if (this.end || !this.queue.length) return { kind: 'waiting' };
    const leading = this.leading;
    if (leading.stamp && leading.stamp !== stamp) {
      this.score = Math.max(0, this.score - MISS_PENALTY);
      this.combo = 0;
      this.stall = 0;
      return { kind: 'miss' };
    }
    this.combo++;
    this.bestCombo = Math.max(this.bestCombo, this.combo);
    this.stall = 0;
    this.queue.splice(0, leading.count);
    this.score += leading.points;
    this.total += leading.count;
    this.bestBatch = Math.max(this.bestBatch, leading.count);

    let feverStarted = false;
    if (!this.inFever) {
      this.feverGauge = Math.min(FEVER_TARGET, this.feverGauge + leading.count);
      if (this.feverGauge === FEVER_TARGET) {
        feverStarted = true;
        this.feverEnd = this.elapsed + FEVER_DURATION;
        this.arrivalBase = this.elapsed;
        this.nextArrival = this.elapsed + FEVER_INTERVAL;
        this.mail.startFever();
        this.refreshUpcoming();
      }
    }
    return { kind: 'sent', ...leading, multiplier: multiplierFor(this.combo), feverStarted };
  }
}
