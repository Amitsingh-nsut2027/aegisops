// The public demo reads only build-generated fixtures. It has no backend credentials.
export function createDataClient({mode, fetcher = fetch}) {
  if (!['local', 'portfolio'].includes(mode)) throw new Error('Unknown runtime mode');
  let snapshot;
  const fail = status => {const error = new Error('Data request failed'); error.status = status; throw error;};
  async function loadSnapshot() {
    if (!snapshot) snapshot = fetcher('/demo-data.json', {cache: 'no-store'})
      .then(response => response.ok ? response.json() : fail(response.status))
      .then(data => {
        if (data.kind !== 'aegisops-portfolio-v1' || !Array.isArray(data.events) || !Array.isArray(data.runs)) fail(503);
        return data;
      }).catch(error => {snapshot = null; throw error;});
    return snapshot;
  }
  return async function api(path) {
    if (mode === 'local') {
      const response = await fetcher('/api' + path, {cache: 'no-store', signal: AbortSignal.timeout(10000)});
      if (!response.ok) fail(response.status);
      return response.json();
    }
    const url = new URL(path, 'https://portfolio.invalid');
    const match = /^\/(events|investigations)(?:\/([a-f0-9]+))?$/.exec(url.pathname);
    if (!match) fail(404);
    const data = await loadSnapshot();
    const isEvent = match[1] === 'events';
    let rows = [...(isEvent ? data.events : data.runs)];
    if (match[2]) {
      const row = rows.find(row => row[isEvent ? 'event_id' : 'run_id'] === match[2]);
      if (!row) fail(404);
      return structuredClone(row);
    }
    const source = url.searchParams.get('source');
    if (isEvent && source) rows = rows.filter(row => row.source === source);
    const eventId = url.searchParams.get('event_id');
    if (!isEvent && eventId) rows = rows.filter(row => row.event_id === eventId);
    const limit = Number(url.searchParams.get('limit') ?? 50);
    const offset = Number(url.searchParams.get('offset') ?? 0);
    if (!Number.isInteger(limit) || limit < 1 || limit > 100 || !Number.isInteger(offset) || offset < 0 || offset > 10000) fail(422);
    rows.sort((a, b) => (isEvent ? b.received_at.localeCompare(a.received_at) : b.started_at.localeCompare(a.started_at)) ||
      a[isEvent ? 'event_id' : 'run_id'].localeCompare(b[isEvent ? 'event_id' : 'run_id']));
    const items = rows.slice(offset, offset + limit);
    return structuredClone({items, limit, offset, returned: items.length, has_more: rows.length > offset + limit});
  };
}
