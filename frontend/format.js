export function escapeHTML(value) {
  return String(value ?? '').replace(/[&<>"']/g, character => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[character]));
}
export function exactTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unknown time';
  const tail = typeof value === 'string' ? (value.match(/\.(\d+)/)?.[1] ?? '').slice(3, 6) : '';
  return date.toISOString().replace('Z', tail + ' UTC').replace('T', ' ');
}
export function relativeTime(value, now = Date.now()) {
  const milliseconds = now - new Date(value).getTime();
  if (!Number.isFinite(milliseconds)) return 'Unknown';
  const seconds = Math.abs(milliseconds) / 1000;
  const units = [[86400, 'd'], [3600, 'h'], [60, 'm'], [1, 's']];
  const [divisor, unit] = units.find(([value]) => seconds >= value) ?? units.at(-1);
  const text = Math.floor(seconds / divisor) + unit;
  return milliseconds < 0 ? 'in ' + text : text + ' ago';
}
export const shortId = value => value ? value.slice(0, 7) + '…' + value.slice(-4) : '—';

export function validEventFilter(value) {
  return value === '' || /^[a-f0-9]{64}$/.test(value);
}
export function workflowElapsed(start, finish) {
  function precise(value) {
    if (typeof value !== 'string') return NaN;
    const milliseconds = Date.parse(value);
    const fraction = value.match(/\.(\d+)/)?.[1] ?? '';
    return milliseconds + Number(fraction.slice(3).padEnd(3, '0').slice(0, 3)) / 1000;
  }
  const elapsed = precise(finish) - precise(start);
  if (!Number.isFinite(elapsed) || elapsed < 0) return 'Not recorded';
  return elapsed < 1000 ? elapsed.toFixed(2) + ' ms' : (elapsed / 1000).toFixed(3) + ' s';
}
