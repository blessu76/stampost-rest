import assert from 'node:assert/strict';
import test from 'node:test';
import { readRecord, persistRecord } from '../assets/stampost-play.mjs';

function replaceStorage(t, descriptor) {
  const previous = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  Object.defineProperty(globalThis, 'localStorage', { ...descriptor, configurable: true });
  t.after(() => {
    if (previous) Object.defineProperty(globalThis, 'localStorage', previous);
    else delete globalThis.localStorage;
  });
}

function useStorage(t) {
  const entries = new Map();
  const storage = {
    getItem: key => entries.get(key) ?? null,
    setItem: (key, value) => { entries.set(key, String(value)); },
  };
  replaceStorage(t, { value: storage });
  return storage;
}

test('an empty store starts with zero score and stars', t => {
  useStorage(t);
  assert.deepEqual(readRecord(), { score: 0, stars: 0 });
});

test('legacy scores restore stars at 150, 300, and 450 points', t => {
  const storage = useStorage(t);
  for (const [score, stars] of [[149, 0], [150, 1], [299, 1], [300, 2], [449, 2], [450, 3]]) {
    storage.setItem('stampost.best', score);
    assert.deepEqual(readRecord(), { score, stars });
  }
});

test('a new record is saved under the existing keys and survives lower scores', t => {
  const storage = useStorage(t);
  storage.setItem('stampost.best', 300);
  storage.setItem('stampost.bestStars', 2);

  const record = { score: 470, stars: 3 };
  persistRecord(record);
  assert.equal(storage.getItem('stampost.best'), '470');
  assert.equal(storage.getItem('stampost.bestStars'), '3');
  assert.deepEqual(readRecord(), record);

  persistRecord({ score: 200, stars: 1 });
  assert.deepEqual(readRecord(), record);
});

test('blocked storage leaves reads and writes usable', t => {
  const denied = () => { throw new Error('Storage is blocked'); };
  const storage = useStorage(t);
  storage.getItem = denied;
  storage.setItem = denied;
  const record = { score: 300, stars: 2 };
  assert.deepEqual(readRecord(), { score: 0, stars: 0 });
  assert.doesNotThrow(() => persistRecord(record));

  Object.defineProperty(globalThis, 'localStorage', { get: denied, configurable: true });
  assert.deepEqual(readRecord(), { score: 0, stars: 0 });
  assert.doesNotThrow(() => persistRecord(record));
});
