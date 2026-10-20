import test from 'node:test';
import assert from 'node:assert/strict';
import { escapeHTML, exactTime, relativeTime, shortId, validEventFilter, workflowElapsed } from '../format.js';

test('untrusted source text cannot introduce markup or attributes', () => {
  assert.equal(escapeHTML('<img src=x onerror="bad">&\''), '&lt;img src=x onerror=&quot;bad&quot;&gt;&amp;&#39;');
});
test('relative timestamps handle synthetic past, future and malformed values', () => {
  const now = Date.parse('2026-10-19T00:00:00Z');
  assert.equal(relativeTime('2026-10-18T22:00:00Z', now), '2h ago');
  assert.equal(relativeTime('2026-10-20T00:00:00Z', now), 'in 1d');
  assert.equal(relativeTime('bad', now), 'Unknown');
});
test('exact time is UTC and copied identifiers remain distinguishable', () => {
  assert.equal(exactTime('2026-01-01T05:38:00+05:30'), '2026-01-01 00:08:00.000 UTC');
  assert.equal(shortId('a1234567890ffff'), 'a123456…ffff');
});

test('exact event filter accepts empty or full lowercase IDs only', () => {
  assert.equal(validEventFilter(''), true);
  assert.equal(validEventFilter('a'.repeat(64)), true);
  for (const value of ['a'.repeat(63), 'A'.repeat(64), 'bad', ' a'.repeat(32)]) assert.equal(validEventFilter(value), false);
});
test('elapsed workflow time preserves sub-millisecond report timing and rejects missing/negative intervals', () => {
  assert.equal(workflowElapsed('2026-01-01T00:00:00.000000Z', '2026-01-01T00:00:00.000410Z'), '0.41 ms');
  assert.equal(workflowElapsed('2026-01-01T00:00:00Z', '2026-01-01T00:00:01.234Z'), '1.234 s');
  assert.equal(workflowElapsed(undefined, undefined), 'Not recorded');
  assert.equal(workflowElapsed('2026-01-02T00:00:00Z', '2026-01-01T00:00:00Z'), 'Not recorded');
});
test('exact run timestamps retain their recorded microsecond fraction', () => {
  assert.equal(exactTime('2026-01-01T05:30:00.026878+05:30'), '2026-01-01 00:00:00.026878 UTC');
});
