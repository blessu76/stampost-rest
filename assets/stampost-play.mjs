import {
  Round, STAMPS, DURATION, MAX_QUEUE, COMBO_TIMEOUT, FEVER_TARGET, FEVER_DURATION,
  STAR_THRESHOLDS, multiplierFor, starsFor, pointsToNextStar,
} from './stampost-round.mjs';

const BEST_KEY = 'stampost.best';
const STARS_KEY = 'stampost.bestStars';

function storedInt(key) {
  try {
    const value = Number(localStorage.getItem(key));
    return Number.isSafeInteger(value) && value > 0 ? value : 0;
  } catch {
    return 0;
  }
}

export function readRecord() {
  const score = storedInt(BEST_KEY);
  const stars = Math.max(starsFor(score), Math.min(STAR_THRESHOLDS.length, storedInt(STARS_KEY)));
  return { score, stars };
}

export function persistRecord(record) {
  try {
    if (record.score > storedInt(BEST_KEY)) localStorage.setItem(BEST_KEY, record.score);
    if (record.stars > storedInt(STARS_KEY)) localStorage.setItem(STARS_KEY, record.stars);
  } catch {
    // Scoring still works for the current page if persistent storage is unavailable.
  }
}

function setText(node, text) {
  const value = String(text);
  if (node.textContent !== value) node.textContent = value;
}

function gameClock(now, previous, elapsed) {
  // Match the app's per-frame cap so a stalled tab cannot dump mail into the queue.
  return elapsed + Math.max(0, Math.min(now - previous, 250));
}

function initGame(root) {
  const copy = JSON.parse(root.querySelector('[data-play-copy]').textContent);
  const parts = Object.fromEntries(Array.from(root.querySelectorAll('[data-part]'), node => [node.dataset.part, node]));
  const buttons = Object.fromEntries(Array.from(root.querySelectorAll('[data-stamp]'), node => [node.dataset.stamp, node]));
  const stampArt = Object.fromEntries(STAMPS.map(stamp => [stamp, buttons[stamp].querySelector('img').src]));
  const stampNames = Object.fromEntries(STAMPS.map(stamp => [stamp, buttons[stamp].querySelector('span').textContent]));
  const queue = Array.from(parts.queue.children);
  const preview = Array.from(parts.next.querySelector('ol').children);
  const comboSlots = Array.from(parts.comboSlots.children);
  const queueCounts = Array.from(parts.queueCounts.querySelectorAll('b'));
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

  let record = readRecord();
  let round = new Round();
  let phase = 'ready';
  let newBest = false;
  let frame = 0;
  let lastFrame = 0;
  let elapsed = 0;
  let marker = 'intro';
  let markerResult;
  let comboStamps = [];
  let feedback = [];

  function message(key, values = {}) {
    const template = copy[key];
    const text = Array.isArray(template) ? template[values.n === 1 ? 0 : 1] : template;
    return text.replace(/\{(\w+)\}/g, (_, name) => values[name]);
  }

  function stampIcon(stamp, size) {
    const img = document.createElement('img');
    img.src = stampArt[stamp];
    img.width = img.height = size;
    img.alt = '';
    return img;
  }

  function paintParcel(cell, letter, front = false) {
    const parcel = cell.firstElementChild;
    const appearance = letter ?? 'empty';
    if (parcel.dataset.letter === appearance) return;
    parcel.dataset.letter = appearance;
    const stamp = parcel.querySelector('.game-parcel-stamp');
    stamp.hidden = !stampArt[letter];
    if (!stamp.hidden) stamp.src = stampArt[letter];
    const label = letter === 'gold'
      ? copy.goldLetter
      : letter ? message(front ? 'parcelFront' : 'parcel', { stamp: stampNames[letter] }) : copy.parcelEmpty;
    setText(parcel.querySelector('[data-parcel-label]'), label);
  }

  function paintStars(node, count) {
    const limit = STAR_THRESHOLDS.length;
    node.setAttribute('aria-label', `${count}/${limit} ★`);
    node.setAttribute('role', 'img');
    setText(node, '★'.repeat(count) + '☆'.repeat(limit - count));
  }

  function updateMeters() {
    const seconds = Math.ceil((DURATION - round.elapsed) / 1000);
    parts.timeMeter.value = seconds / (DURATION / 1000);
    parts.scoreMeter.value = round.inFever
      ? (round.feverEnd - round.elapsed) / FEVER_DURATION : round.feverGauge / FEVER_TARGET;
    parts.bestMeter.value = record.score ? Math.min(1, round.score / record.score) : 0;
    parts.arrival.value = round.arrivalProgress;
    const countdown = Math.min(1, (COMBO_TIMEOUT - round.stall) / 1000);
    parts.comboTime.hidden = !round.combo || countdown >= 1;
    if (!parts.comboTime.hidden) parts.comboTime.style.transform = `scaleX(${countdown})`;
  }

  function markerMessage() {
    if (marker === 'sent') return message('markerSent', { n: markerResult.count, score: markerResult.points });
    return copy[{
      intro: 'markerIntro', waiting: 'markerWaiting', miss: 'markerMiss',
      resumed: 'markerResumed', fever: 'fever',
    }[marker]];
  }

  function render() {
    const playing = phase === 'playing';
    const ended = phase === 'ended';
    const paused = phase === 'paused';
    const seconds = Math.ceil((DURATION - round.elapsed) / 1000);
    const { count, stamp, points } = round.leading;
    const filled = round.queue.length;

    root.dataset.phase = phase;
    root.toggleAttribute('data-fever', round.inFever);
    setText(parts.time, message('seconds', { n: seconds }));
    parts.time.closest('.game-stat').toggleAttribute('data-warning', seconds <= 8);
    setText(parts.score, round.score);
    parts.scoreMeter.toggleAttribute('data-gold', round.inFever);
    setText(parts.best, record.score);
    parts.bestMeter.toggleAttribute('data-gold', record.score > 0 && round.score >= record.score);
    paintStars(parts.bestStars, record.stars);

    comboSlots.forEach((slot, index) => {
      const style = comboStamps[index];
      if (slot.dataset.stamp === style) return;
      if (style) {
        slot.dataset.stamp = style;
        slot.replaceChildren(stampIcon(style, 12));
      } else {
        delete slot.dataset.stamp;
        slot.replaceChildren();
      }
    });
    const comboLabel = round.inFever ? copy.fever : message('comboCount', { n: round.combo });
    setText(parts.combo, `${comboLabel} · ×${multiplierFor(round.combo)}`);

    const status = round.end === 'overflow' ? copy.endOverflow : copy.endTime;
    let intakeLabel = copy.intakeNow;
    let intakeTitle = stamp ? message('intakeBatch', { stamp: stampNames[stamp], n: count }) : copy.goldLetter;
    let intakeDetail = message('points', { n: points });
    if (ended) {
      intakeLabel = status;
      intakeTitle = message('resultScore', { n: round.score });
      intakeDetail = message('delivered', { n: round.total });
    } else if (paused || count === 0) {
      intakeLabel = '';
      intakeTitle = paused ? copy.pausedTitle : copy.idleTitle;
      intakeDetail = paused ? '' : copy.idleDetail;
    }
    parts.intakeLabel.hidden = !intakeLabel;
    parts.intakeDetail.hidden = !intakeDetail;
    setText(parts.intakeLabel, intakeLabel);
    setText(parts.intakeTitle, intakeTitle);
    setText(parts.intakeDetail, intakeDetail);
    parts.newBest.hidden = !newBest;
    parts.next.hidden = ended;
    preview.forEach((cell, index) => paintParcel(cell, round.upcoming[index]));

    parts.capacity.toggleAttribute('data-warning', filled >= MAX_QUEUE - 1);
    setText(parts.capacity, message(filled === MAX_QUEUE ? 'capacityFull' : 'capacity', { n: filled, max: MAX_QUEUE }));
    queue.forEach((cell, index) => {
      paintParcel(cell, round.queue[index], index === 0);
      cell.toggleAttribute('data-leading', index < count && !ended);
      cell.toggleAttribute('data-danger', filled === MAX_QUEUE - 1 && index === filled);
    });
    STAMPS.forEach((stamp, index) => {
      const button = buttons[stamp];
      const total = round.queue.filter(letter => letter === stamp).length;
      button.disabled = !playing;
      button.setAttribute('aria-label', message('stampButton', { stamp: stampNames[stamp] }));
      const badge = button.querySelector('[data-count]');
      badge.hidden = !total;
      setText(badge, total);
      setText(queueCounts[index], total);
    });

    parts.rating.hidden = !ended;
    if (ended) {
      const next = pointsToNextStar(round.score);
      paintStars(parts.resultStars, starsFor(round.score));
      parts.nextStar.hidden = next === null;
      if (next !== null) setText(parts.nextStar, message('nextStar', { n: next }));
      setText(parts.bestCombo, message('bestCombo', { n: round.bestCombo }));
    }
    setText(parts.instructions, ended ? copy.instructionsEnded : copy.instructions);
    parts.start.hidden = playing;
    parts.start.disabled = playing;
    setText(parts.start, ended ? copy.again : paused ? copy.resumeDelivery : copy.start);
    parts.pause.hidden = !playing;
    parts.marker.hidden = !playing;
    parts.marker.dataset.kind = marker;
    setText(parts.marker, markerMessage());
    setText(parts.delivered, message('delivered', { n: round.total }));
    setText(parts.longest, message('longest', { n: round.bestBatch }));
    updateMeters();
  }

  function finish() {
    const hadFocus = root.contains(document.activeElement);
    phase = 'ended';
    const saved = readRecord();
    newBest = round.score > Math.max(record.score, saved.score);
    record = {
      score: Math.max(record.score, saved.score, round.score),
      stars: Math.max(record.stars, saved.stars, starsFor(round.score)),
    };
    persistRecord(record);
    clearFeedback();
    render();
    announce(`${parts.intakeLabel.textContent}. ${parts.intakeTitle.textContent}. ${parts.bestCombo.textContent}`);
    if (hadFocus) parts.start.focus({ preventScroll: true });
    if (!reducedMotion.matches) {
      parts.start.animate([{ transform: 'scale(1)' }, { transform: 'scale(1.025)' }, { transform: 'scale(1)' }], 220);
    }
  }

  function tick(now) {
    const arrival = round.nextArrival;
    const combo = round.combo;
    const second = Math.floor(round.elapsed / 1000);
    const fever = round.inFever;
    elapsed = gameClock(now, lastFrame, elapsed);
    lastFrame = now;
    round.advance(Math.floor(elapsed));
    if (combo !== round.combo) comboStamps = [];
    if (fever && !round.inFever && marker === 'fever') marker = 'intro';
    if (round.end) {
      finish();
      return;
    }
    if (arrival !== round.nextArrival || combo !== round.combo || fever !== round.inFever ||
        second !== Math.floor(round.elapsed / 1000)) {
      render();
    } else {
      updateMeters();
    }
    frame = requestAnimationFrame(tick);
  }

  function pause(moveFocus) {
    if (phase !== 'playing') return;
    cancelAnimationFrame(frame);
    clearFeedback();
    phase = 'paused';
    render();
    announce(copy.pausedTitle);
    if (moveFocus) parts.start.focus({ preventScroll: true });
  }

  function startOrResume() {
    const resumed = phase === 'paused';
    if (phase === 'ended') {
      round = new Round();
      elapsed = 0;
      comboStamps = [];
    }
    phase = 'playing';
    newBest = false;
    marker = resumed ? 'resumed' : 'intro';
    render();
    announce(markerMessage());
    buttons.flower.focus({ preventScroll: true });
    lastFrame = performance.now();
    frame = requestAnimationFrame(tick);
  }

  function announce(text) {
    setText(parts.announcement, text);
  }

  function clearFeedback() {
    feedback.forEach(animation => animation.cancel());
    feedback = [];
    parts.popup.hidden = true;
    parts.imprint.replaceChildren();
  }

  function playFeedback(stamp, result) {
    if (result.kind === 'waiting') return;
    clearFeedback();
    const miss = result.kind === 'miss';
    const big = result.gold || result.count >= 5;
    const motion = !reducedMotion.matches;
    const button = buttons[stamp];
    if (typeof navigator.vibrate === 'function') {
      const duration = miss || result.feverStarted ? 35 : big ? 24 : result.count >= 3 ? 15 : 8;
      navigator.vibrate(duration);
    }
    if (motion && (miss || big)) {
      const distance = miss ? 4 : 2;
      const cycle = [{ transform: `translateX(-${distance}px)` }, { transform: `translateX(${distance}px)` }];
      const frames = [{ transform: 'none' }, ...cycle, ...cycle, ...(miss ? cycle : []), { transform: 'none' }];
      feedback.push(parts.belt.animate(frames, miss ? 180 : 140));
    }
    if (miss) {
      if (motion) feedback.push(button.animate([{ background: '#f4a5a1' }, { background: 'var(--stamp-bg)' }], 120));
      return;
    }
    if (motion) {
      feedback.push(button.animate([1, .92, 1.06, 1].map(scale => ({ transform: `scale(${scale})` })), 160));
      if (big) {
        parts.imprint.replaceChildren(...Array.from({ length: result.count }, () => stampIcon(stamp, 19)));
        const imprint = parts.imprint.animate([{ opacity: .65 }, { opacity: 0 }], 120);
        imprint.onfinish = () => parts.imprint.replaceChildren();
        feedback.push(imprint);
      }
    }
    parts.popup.replaceChildren(`+${result.points}`);
    if (result.multiplier > 1) {
      const badge = document.createElement('small');
      badge.textContent = `×${result.multiplier}`;
      parts.popup.append(badge);
    }
    parts.popup.hidden = false;
    parts.popup.toggleAttribute('data-gold', result.gold);
    parts.popup.style.fontSize = `${big ? 22.5 : result.count >= 3 ? 18.75 : 15}px`;
    const popup = parts.popup.animate([
      { opacity: 1, transform: 'none' },
      { opacity: 0, transform: motion ? 'translateY(-24px)' : 'none' },
    ], 600);
    popup.onfinish = () => { parts.popup.hidden = true; };
    feedback.push(popup);
  }

  function press(stamp) {
    if (phase !== 'playing') return;
    const result = round.send(stamp);
    if (result.kind === 'sent') {
      comboStamps.push(stamp);
      if (comboStamps.length > comboSlots.length) comboStamps.shift();
    } else if (result.kind === 'miss') {
      comboStamps = [];
    }
    marker = result.feverStarted ? 'fever' : result.kind;
    markerResult = result;
    render();
    playFeedback(stamp, result);
    announce(markerMessage());
  }

  STAMPS.forEach(stamp => {
    const button = buttons[stamp];
    button.addEventListener('pointerdown', event => {
      if (event.isPrimary && event.button === 0) press(stamp);
    });
    button.addEventListener('click', event => {
      // Keyboard and assistive input dispatch click without a pointerdown.
      if (event.detail === 0) press(stamp);
    });
  });
  parts.start.addEventListener('click', startOrResume);
  parts.pause.addEventListener('click', () => pause(true));
  root.querySelector('a[href="#rules"]').addEventListener('click', () => pause(false));
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) pause(false);
  });
  reducedMotion.addEventListener('change', clearFeedback);
  render();
}

if (typeof document !== 'undefined') {
  initGame(document.querySelector('[data-stampost-game]'));
}
