import { escapeHTML as e, relativeTime, exactTime, shortId } from './format.js';
import {time, copy, panelState, evidenceContent, traceContent, docsContent} from './report-view.js';
import {createHistoryScreen} from './history.js';
import {runtime} from './runtime-config.js';
import {createDataClient} from './data-client.js';

const api = createDataClient(runtime);
const environmentLabel = runtime.mode === 'portfolio' ? 'PORTFOLIO / SIMULATION' : 'LOCAL / SIMULATION';
if (runtime.mode === 'portfolio') {
  document.body.classList.add('portfolio-mode');
  document.querySelector('#deployment-notice').hidden = false;
}

const app = document.querySelector('#app');
const palette = document.querySelector('#palette');
const pageSize = 25;
let storedWidth;
try { storedWidth = Number(localStorage.getItem('aegis-inspector-width')); } catch { /* Private mode */ }
const state = {
  events: [], histories: new Map(), historyErrors: new Set(), selected: null, runId: null,
  tab: 'evidence', filter: '', offset: 0, hasMore: false, loading: true, refreshing: false,
  error: null, lastRefresh: null, mobileOpen: false, loadedOffset: 0,
  width: storedWidth >= 400 && storedWidth <= 640 ? storedWidth : 456,
};
let requestSequence = 0;
let toastTimer;
let view = location.hash === '#investigations' ? 'investigations' : 'incidents';
const historyScreen = createHistoryScreen({app, api, environmentLabel, announce: message => announce(message), toast: message => toast(message), clipboard: (value, name) => clipboard(value, name), getWidth: () => state.width, bindResize: () => bindResize(), navigate: next => switchView(next), openPalette: () => openPalette(), onRender: () => updateNavigation(), isActive: () => view === 'investigations'});
const tabs = ['evidence', 'trace', 'docs'];
const label = key => ({evidence: 'Evidence', trace: 'Trace', docs: 'Runbooks'}[key]);
const visibleEvents = () => state.events.filter(event => [event.resource_id, event.event_id, event.payload?.scenario_id, event.event_type].some(value => String(value ?? '').toLowerCase().includes(state.filter.toLowerCase())));
const selectedEvent = () => state.events.find(event => event.event_id === state.selected);
const runs = () => state.histories.get(state.selected)?.items ?? [];
const currentRun = () => runs().find(run => run.run_id === state.runId) ?? runs()[0];
const announce = message => { document.querySelector('#announcement').textContent = message; };

function errorKind(error) { return error.status === 401 ? 'session' : error.status === 403 ? 'forbidden' : 'offline'; }

async function loadEvents() {
  const sequence = ++requestSequence;
  state.refreshing = true;
  if (!state.events.length) state.loading = true;
  render();
  try {
    const page = await api(`/events?limit=${pageSize}&offset=${state.offset}&source=simulator`);
    // Fetch one bounded history page per displayed event. Keep this explicit; no guessed run states.
    const results = await Promise.allSettled(page.items.map(event => api(`/investigations?event_id=${event.event_id}&limit=100`)));
    if (sequence !== requestSequence) return;
    const authFailure = results.find(result => result.status === 'rejected' && [401, 403].includes(result.reason.status));
    if (authFailure) throw authFailure.reason;
    state.events = page.items; state.loadedOffset = state.offset;
    state.hasMore = page.has_more;
    state.histories = new Map(); state.historyErrors = new Set();
    results.forEach((result, index) => {
      const id = page.items[index].event_id;
      if (result.status === 'fulfilled') state.histories.set(id, result.value);
      else state.historyErrors.add(id);
    });
    state.error = null; state.lastRefresh = new Date().toISOString();
    const visible = visibleEvents();
    if (!visible.some(event => event.event_id === state.selected)) { state.selected = visible[0]?.event_id ?? null; state.runId = null; }
    announce(`${page.returned} events loaded. ${state.historyErrors.size ? 'Some histories are unavailable.' : 'Snapshot refreshed.'}`);
  } catch (error) {
    if (sequence !== requestSequence) return;
    state.error = errorKind(error); state.offset = state.loadedOffset;
    if (state.error === 'session' || state.error === 'forbidden') {
      state.events = []; state.histories.clear(); state.selected = null;
    }
    announce(state.error === 'session' ? 'Viewer session expired.' : 'API unavailable.');
  } finally {
    if (sequence === requestSequence) { state.loading = false; state.refreshing = false; render(); }
  }
}
function selectEvent(id, open = false) {
  state.selected = id; state.runId = null;
  if (open) state.mobileOpen = true;
  render();
  if (open) document.querySelector('#tab-' + state.tab)?.focus({preventScroll: true});
  announce('Selected ' + (selectedEvent()?.resource_id ?? 'event') + '. ' + rowState(id) + '.');
}
function showTab(tab) {
  if (view === 'investigations') return historyScreen.showTab(tab);
  state.tab = tab;
  if (selectedEvent()) state.mobileOpen = true;
  render();
  document.querySelector('#tab-' + state.tab)?.focus({preventScroll: true});
}
async function clipboard(value, name = 'Value') {
  try { await navigator.clipboard.writeText(value); toast(`${name} copied`); }
  catch { toast('Copy failed. Select and copy the visible value.'); }
}
function toast(message) {
  const element = document.querySelector('#toast'); element.textContent = message; element.hidden = false;
  clearTimeout(toastTimer); toastTimer = setTimeout(() => {element.hidden = true;}, 3200);
}
function errorBanner() {
  if (!state.error) return '';
  const text = {
    session: ['Session expired', 'Renew the local viewer session, then retry.'],
    forbidden: ['Read access denied', 'The active viewer cannot read this workspace.'],
    offline: [state.events.length ? 'Snapshot is stale' : 'API unavailable', state.events.length ? 'Refresh failed. Previously loaded records are still visible.' : 'The local API did not respond. Start the API and retry.'],
  }[state.error];
  return `<div class="error-banner" role="alert"><div><strong>${text[0]}</strong><span>${text[1]}</span>${state.error === 'session' ? '<code>python3 scripts/create_viewer_token.py</code>' : ''}</div><button data-action="refresh" ${state.refreshing ? 'disabled' : ''}>Retry</button></div>`;
}
function skeleton() {
  return `<div class="table-skeleton" aria-label="Loading saved incidents" aria-busy="true">${Array.from({length: 5}, (_, i) => `<div class="skeleton-row"><span class="skeleton stub"></span><span class="skeleton line-${i % 3}"></span><span class="skeleton stub"></span></div>`).join('')}</div>`;
}
function rowState(id) {
  if (state.historyErrors.has(id)) return 'History unavailable';
  const history = state.histories.get(id)?.items ?? [];
  return history.length ? 'Needs evidence' : 'No saved run';
}
function eventRows() {
  return visibleEvents().map(event => {
    const active = event.event_id === state.selected;
    return `<tr class="event-row ${active ? 'selected' : ''}" data-event="${event.event_id}" aria-selected="${active}">
      <td class="sev-cell"><span class="untriaged" title="Source warning has no assessed SEV classification">—</span><span class="sr-only">Untriaged</span></td>
      <td class="resource-cell"><button class="row-select data" data-select="${event.event_id}" tabindex="${active ? 0 : -1}" aria-label="Inspect ${e(event.resource_id)}, ${shortId(event.event_id)}">${e(event.resource_id.split('/').at(-1))}<span class="event-source">${e(event.payload?.scenario_id ?? 'simulator')} · ${shortId(event.event_id)}</span></button></td>
      <td class="identity-cell data">${shortId(event.event_id)}</td>
      <td class="time-cell">${time(event.observed_at, 'Observed ')}<span class="observed-clock data">${e(new Date(event.observed_at).toISOString().slice(11, 16))} UTC</span></td>
      <td class="state-cell"><span class="row-state ${active ? 'row-state-active' : ''}">${rowState(event.event_id)}</span></td>
      <td class="row-arrow" aria-hidden="true">${active ? '↗' : '→'}</td>
    </tr>`;
  }).join('');
}
function chart(event, compact = false) {
  const samples = event?.payload?.cpu_evidence ?? [];
  if (!samples.length) return panelState('No CPU samples', 'The saved event does not contain a trigger window.');
  const values = samples.map(Number).filter(Number.isFinite);
  if (!values.length) return panelState('Invalid CPU samples', 'Inspect the saved event payload.');
  const threshold = Number(event.payload.threshold ?? 90);
  const low = Math.max(0, Math.floor(Math.min(threshold, ...values) / 10) * 10 - 10);
  const high = Math.min(100, Math.max(low + 20, Math.ceil(Math.max(...values) / 10) * 10));
  const start = 45, end = 465, height = compact ? 90 : 150, top = 24;
  const y = value => top + (high - value) / (high - low || 1) * height;
  const x = index => values.length === 1 ? (start + end) / 2 : start + index * (end - start) / (values.length - 1);
  const date = new Date(event.observed_at);
  const sampleTime = index => new Date(date.getTime() - (values.length - 1 - index) * 60000).toISOString();
  const markers = values.map((value, index) => `<g class="sample-point" tabindex="0" role="img" aria-label="${value}% CPU at ${e(exactTime(sampleTime(index)))}"><title>${e(exactTime(sampleTime(index)))} · ${value}% CPU</title><circle cx="${x(index)}" cy="${y(value)}" r="4"/><text x="${x(index)}" y="${y(value) - 14}" text-anchor="middle">${value}%</text></g>`).join('');
  const grid = [high, threshold, low].filter((v, i, a) => a.indexOf(v) === i).map(value => `<text class="chart-axis" x="0" y="${y(value) + 4}">${value}%</text><line class="${value === threshold ? 'threshold-line' : 'grid-line'}" x1="${start}" x2="${end}" y1="${y(value)}" y2="${y(value)}"/>`).join('');
  return `<div class="cpu-chart ${compact ? 'compact' : ''}"><svg viewBox="0 0 510 ${height + 62}" aria-label="CPU trigger samples. ${values.join(', ')} percent. Threshold above ${threshold} percent." role="img">${grid}<polyline class="cpu-line" points="${values.map((v, i) => x(i) + ',' + y(v)).join(' ')}"/>${markers}${values.map((v, i) => `<text class="chart-axis" x="${x(i)}" y="${height + 51}" text-anchor="middle">${new Date(sampleTime(i)).toISOString().slice(11, 16)}</text>`).join('')}</svg><span class="chart-note data">UTC · synthetic observation time · ${low}–${high}% axis</span></div>`;
}
function observation(event) {
  if (!event) return '';
  const values = event.payload?.cpu_evidence ?? [];
  return `<section class="observation" aria-labelledby="observation-heading"><div class="section-top"><div><span class="eyebrow">SELECTED EVENT / OBSERVATION WINDOW</span><h2 id="observation-heading">CPU trigger window</h2><p class="observation-source data">${shortId(event.event_id)} · ${e(event.event_type)}</p></div><span class="data window-tag">${values.length} trigger samples</span></div>
    ${chart(event)}<div class="observation-bottom"><div><span class="eyebrow">DETECTION RULE</span><p class="data">&gt; ${e(event.payload?.threshold ?? '—')}% CPU · ${e(event.payload?.required_samples ?? '—')} consecutive samples</p></div><div class="exact-observation"><span class="eyebrow">OBSERVED AT</span><p class="data">${e(exactTime(event.observed_at))}</p></div></div>
    <div class="scope-note"><span class="scope-marker">SIM</span><p>Fixed sample data. No customer impact or live AWS health has been established.</p></div></section>`;
}
function inspector() {
  const event = selectedEvent();
  if (state.loading) return `<aside class="inspector skeleton-inspector">${skeleton()}</aside>`;
  if (!event) return `<aside class="inspector inspector-empty">${panelState('Select an incident', 'Choose a saved event to inspect its evidence, runs, and source guidance.')}</aside>`;
  const history = state.histories.get(event.event_id);
  const selected = currentRun();
  return `<aside class="inspector" aria-label="Incident inspector"><div class="inspector-title"><button class="mobile-back" data-action="back">← Inbox</button><div class="label-row"><span class="eyebrow">INCIDENT INSPECTOR</span>${copy(event.event_id, 'event ID', 'Copy ID')}</div><h2>${e(event.resource_id.split('/').at(-1))}</h2><div class="inspector-event-id data">${shortId(event.event_id)} · ${e(event.payload?.scenario_id ?? 'simulator')}</div><div class="inspector-subline"><span class="neutral-status">Untriaged</span><span class="data">${e(event.payload?.severity ?? 'unknown')} source</span></div><div class="resource-path"><code>${e(event.resource_id)}</code>${copy(event.resource_id, 'resource identifier')}</div></div>
    <div class="run-picker"><label for="run-select">SAVED RUN</label>${history?.items?.length ? `<select id="run-select" class="data" aria-label="Choose saved investigation run">${history.items.map(run => `<option value="${run.run_id}" ${run.run_id === selected?.run_id ? 'selected' : ''}>${shortId(run.run_id)} · ${relativeTime(run.started_at)}</option>`).join('')}</select>` : `<span class="data">${state.historyErrors.has(event.event_id) ? 'History unavailable' : 'No saved run'}</span>`}${history?.has_more ? '<span class="loaded-limit">Latest 100 runs shown</span>' : ''}</div>
    <div class="inspector-tabs" role="tablist" aria-label="Incident detail">${tabs.map(tab => `<button id="tab-${tab}" role="tab" aria-selected="${state.tab === tab}" aria-controls="detail-panel" tabindex="${state.tab === tab ? 0 : -1}" data-tab="${tab}">${label(tab)}</button>`).join('')}</div>
    <div id="detail-panel" class="detail-panel" role="tabpanel" tabindex="0" aria-labelledby="tab-${state.tab}">${state.historyErrors.has(event.event_id) ? panelState('History unavailable', 'The event loaded, but its investigation history did not.', '<button data-action="refresh">Retry history</button>') : state.tab === 'evidence' ? evidenceContent(event, selected) : state.tab === 'trace' ? traceContent(selected) : docsContent(selected)}</div>
    <div class="inspector-footer"><span class="data">${e(selected?.payload?.analysis?.provider ?? 'No analysis')}</span><span>${selected?.payload?.analysis?.model_called ? 'Model call recorded' : 'No model call'} · read only</span></div></aside>`;
}
function render() {
  if (view === 'investigations') { historyScreen.render(); return; }
  const focus = document.activeElement;
  const id = focus?.id, select = focus?.selectionStart;
  const activeAction = focus?.dataset?.tab;
  const previousContext = app.querySelector('.workbench')?.dataset.detailContext;
  const detailContext = `${state.selected}/${currentRun()?.run_id}/${state.tab}`;
  const scrolls = [...app.querySelectorAll('.detail-panel, .table-scroll, .workspace-scroll')].map(el => [el.className, el.scrollTop]);
  const visible = visibleEvents();
  const event = selectedEvent();
  app.innerHTML = `<div data-detail-context="${e(detailContext)}" class="workbench ${state.mobileOpen ? 'detail-open' : ''}" style="--inspector-width:${state.width}px"><nav class="rail" aria-label="Workspace navigation"><a class="brand" href="/" title="AegisOps incident workbench" aria-label="AegisOps home">A<span class="brand-notch"></span></a><div class="rail-controls"><button class="rail-button active" data-nav="incidents" title="Incident inbox" aria-label="Incident evidence">INC<span>01</span></button><button class="rail-button" data-nav="investigations" title="Investigation history" aria-label="Investigation history">RUN<span>02</span></button><button class="rail-button ${state.tab === 'docs' ? 'active' : ''}" data-nav="docs" title="Selected run — guidance" aria-label="Selected run guidance">DOC<span>03</span></button></div><button class="rail-command" data-action="palette" title="Commands" aria-label="Open command palette">⌘K</button><span class="rail-version data">v0.1</span></nav>
    <main class="workspace"><header class="workspace-header"><div class="workspace-breadcrumb"><span class="small-logo">AEGISOPS</span><span class="slash">/</span><span>OPERATIONS</span></div><div class="header-meta"><span class="simulation-indicator">${environmentLabel}</span><button data-action="palette" class="command-trigger">Commands <kbd>⌘ K</kbd></button></div></header>
    <div class="workspace-scroll"><div class="page-heading"><div><div class="eyebrow">INCIDENT WORKBENCH</div><h1>Incidents<span class="heading-period">.</span></h1><p>Saved CPU events · synthetic observation times</p></div><button class="refresh-button" data-action="refresh" ${state.refreshing ? 'disabled' : ''}>${state.refreshing ? 'Refreshing…' : 'Refresh'}<span aria-hidden="true">↻</span></button></div>
    ${errorBanner()}<div class="table-toolbar"><label class="filter-label" for="incident-filter"><span class="search-symbol" aria-hidden="true"></span><input id="incident-filter" type="search" placeholder="Filter this page…" value="${e(state.filter)}" autocomplete="off"><kbd>/</kbd></label><span class="toolbar-scope data">${state.loading ? 'Loading' : visible.length + ' / ' + state.events.length} <span>on this page</span></span></div>
    <div class="table-scroll" id="incident-table" tabindex="-1"><table><caption class="sr-only">Saved simulated CPU incidents; filter applies to this page only.</caption><thead><tr><th class="sev-cell" scope="col">SEV</th><th class="resource-cell" scope="col">RESOURCE / SCENARIO</th><th class="identity-cell" scope="col">EVENT ID</th><th class="time-cell" scope="col">OBSERVED</th><th class="state-cell" scope="col">INVESTIGATION</th><th><span class="sr-only">Inspect</span></th></tr></thead><tbody>${state.loading ? '' : eventRows()}</tbody></table>${state.loading ? skeleton() : !state.events.length ? panelState(state.error ? 'Records unavailable' : 'No saved incidents', state.error ? 'Restore access to load the event journal.' : 'Publish and consume a simulation to populate this workspace.') : !visible.length ? panelState('No events match this filter', 'Filtering is limited to this loaded page.', '<button data-action="clear-filter">Clear filter</button>') : ''}</div>
    <div class="table-footer"><span class="data">${state.events.length ? state.offset + 1 : 0}–${state.offset + state.events.length} loaded</span><div class="pagination"><button data-action="previous" ${state.offset === 0 || state.refreshing ? 'disabled' : ''} aria-label="Previous event page">←</button><span class="data">Page ${Math.floor(state.offset / pageSize) + 1}</span><button data-action="next" ${!state.hasMore || state.refreshing || state.offset + pageSize > 10000 ? 'disabled' : ''} aria-label="Next event page">→</button></div></div>
    ${!state.loading && visible.length ? observation(event) : ''}
    <footer class="workspace-footer"><span class="snapshot-mark">SNAPSHOT</span><span>${state.lastRefresh ? `Last refreshed ${time(state.lastRefresh)}` : 'Not refreshed'}</span><span class="footer-readonly">Read-only access</span></footer></div></main>
    <div class="pane-separator" role="separator" aria-label="Resize incident inspector" aria-orientation="vertical" aria-valuemin="400" aria-valuemax="640" aria-valuenow="${state.width}" tabindex="0" title="Drag or use arrow keys. Double-click to reset."><span></span></div>${inspector()}</div>`;
  app.querySelectorAll('[data-time]').forEach(element => element.addEventListener('click', () => toast(exactTime(element.dataset.time))));
  app.querySelectorAll('[data-copy]').forEach(element => element.addEventListener('click', () => clipboard(element.dataset.copy, element.getAttribute('aria-label').replace('Copy ', ''))));
  app.querySelectorAll('[data-tab]').forEach(element => element.addEventListener('click', () => {state.tab = element.dataset.tab; render(); document.querySelector('#tab-' + state.tab)?.focus();}));
  app.querySelectorAll('[data-nav]').forEach(element => element.addEventListener('click', () => element.dataset.nav === 'docs' ? showTab('docs') : switchView(element.dataset.nav)));
  app.querySelectorAll('.event-row').forEach(row => row.addEventListener('click', event => {if (!event.target.closest('[data-time]')) selectEvent(row.dataset.event, true);}));
  app.querySelectorAll('[data-select]').forEach(button => button.addEventListener('keydown', event => {if (event.key === 'Enter' || event.key === ' ') {event.preventDefault(); selectEvent(button.dataset.select, true);}}));
  app.querySelectorAll('[data-action]').forEach(element => element.addEventListener('click', () => action(element.dataset.action)));
  document.querySelector('#incident-filter').addEventListener('input', event => {
    state.filter = event.target.value;
    const visible = visibleEvents();
    if (!visible.some(item => item.event_id === state.selected)) {state.selected = visible[0]?.event_id ?? null; state.runId = null;}
    render();
  });
  document.querySelector('#run-select')?.addEventListener('change', event => {state.runId = event.target.value; render();});
  bindResize();
  if (id) {const target = document.getElementById(id); target?.focus({preventScroll: true}); if (typeof select === 'number' && ['text','search'].includes(target?.type)) target.setSelectionRange(select, select);}
  else if (activeAction) document.querySelector('#tab-' + activeAction)?.focus({preventScroll: true});
  updateNavigation();
  for (const [className, scrollTop] of scrolls) [...app.querySelectorAll('.detail-panel, .table-scroll, .workspace-scroll')].find(el => el.className === className)?.scrollTo(0, className === 'detail-panel' && previousContext !== detailContext ? 0 : scrollTop);
}
function action(name) {
  if (name === 'refresh') refreshCurrent();
  if (name === 'palette') openPalette();
  if (name === 'clear-filter') {state.filter = ''; state.selected = state.events[0]?.event_id ?? null; render(); document.querySelector('#incident-filter').focus();}
  if (name === 'previous' || name === 'next') {state.offset += name === 'next' ? pageSize : -pageSize; state.selected = null; state.runId = null; state.filter = ''; loadEvents();}
  if (name === 'back') {state.mobileOpen = false; render(); document.querySelector(`[data-select="${state.selected}"]`)?.focus();}
}
function setWidth(value, persist = true) {
  const max = Math.min(640, window.innerWidth - 56 - 480);
  state.width = Math.min(Math.max(400, value), Math.max(400, max));
  document.querySelector('.workbench').style.setProperty('--inspector-width', state.width + 'px');
  const separator = document.querySelector('.pane-separator'); separator?.setAttribute('aria-valuenow', String(state.width));
  if (persist) {try {localStorage.setItem('aegis-inspector-width', state.width);} catch { /* Storage optional */ }}
}
function bindResize() {
  const separator = document.querySelector('.pane-separator');
  separator.addEventListener('pointerdown', event => {
    separator.setPointerCapture(event.pointerId); document.body.classList.add('resizing');
    const move = event => setWidth(window.innerWidth - event.clientX, false);
    const end = () => {document.body.classList.remove('resizing'); separator.removeEventListener('pointermove', move); setWidth(state.width);};
    separator.addEventListener('pointermove', move); separator.addEventListener('pointerup', end, {once: true}); separator.addEventListener('pointercancel', end, {once: true});
  });
  separator.addEventListener('dblclick', () => setWidth(456));
  separator.addEventListener('keydown', event => {if (['ArrowLeft','ArrowRight','Home'].includes(event.key)) {event.preventDefault(); setWidth(event.key === 'Home' ? 456 : state.width + (event.key === 'ArrowLeft' ? 16 : -16));}});
}
let paletteReturnFocus, commandIndex = 0;
const commands = () => [
  {title: 'Refresh snapshot', hint: 'Read saved API data', run: () => refreshCurrent()},
  {title: 'Open incident inbox', hint: 'Saved source events', run: () => switchView('incidents')},
  {title: 'Open investigation history', hint: 'Saved run snapshots', run: () => switchView('investigations')},
  {title: view === 'investigations' ? 'Filter investigations' : 'Filter incidents', hint: '/', run: () => {if (view === 'investigations') return historyScreen.focusFilter(); state.mobileOpen = false; render(); document.querySelector('#incident-filter').focus();}},
  ...tabs.map(tab => ({title: 'Show ' + label(tab).toLowerCase(), hint: view === 'investigations' ? 'Selected run' : 'Selected incident', run: () => showTab(tab)})),
  ...(view === 'investigations' && historyScreen.selectedId() ? [{title: 'Copy selected run ID', hint: shortId(historyScreen.selectedId()), run: () => clipboard(historyScreen.selectedId(), 'Run ID')}] : []),
  ...(view === 'incidents' && selectedEvent() ? [{title: 'Copy selected event ID', hint: shortId(state.selected), run: () => clipboard(state.selected, 'Event ID')}] : []),
  {title: 'Reset inspector width', hint: '456 px', run: () => setWidth(456)},
];
function showCommands() {
  const query = document.querySelector('#command-search').value.toLowerCase();
  const filtered = commands().filter(command => command.title.toLowerCase().includes(query));
  commandIndex = Math.min(commandIndex, Math.max(0, filtered.length - 1));
  document.querySelector('#command-list').innerHTML = filtered.length ? filtered.map((command, index) => `<button class="command-item ${index === commandIndex ? 'command-selected' : ''}" data-command="${index}"><span>${e(command.title)}</span><span class="data">${e(command.hint)}</span></button>`).join('') : '<p class="command-empty">No matching command</p>';
  document.querySelectorAll('[data-command]').forEach(button => button.addEventListener('click', () => {const command = filtered[Number(button.dataset.command)]; palette.close(); command.run();}));
  return filtered;
}
function openPalette() {paletteReturnFocus = document.activeElement; commandIndex = 0; palette.showModal(); document.querySelector('#command-search').value = ''; showCommands(); document.querySelector('#command-search').focus();}
function closePalette() {palette.close();}
palette.addEventListener('close', () => paletteReturnFocus?.isConnected && paletteReturnFocus.focus());
palette.addEventListener('click', event => {if (event.target === palette && (event.offsetX < 0 || event.offsetY < 0 || event.offsetX > palette.clientWidth || event.offsetY > palette.clientHeight)) closePalette();});
document.querySelector('#command-search').addEventListener('input', () => {commandIndex = 0; showCommands();});
palette.addEventListener('keydown', event => {
  if (['ArrowDown','ArrowUp'].includes(event.key)) {event.preventDefault(); const total = showCommands().length; commandIndex = total ? (commandIndex + (event.key === 'ArrowDown' ? 1 : total - 1)) % total : 0; showCommands();}
  if (event.key === 'Enter') {event.preventDefault(); const command = showCommands()[commandIndex]; if (command) {closePalette(); command.run();}}
});
document.addEventListener('keydown', event => {
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {event.preventDefault(); palette.open ? closePalette() : openPalette(); return;}
  if (palette.open) return;
  if (view === 'investigations') { historyScreen.handleKey(event); return; }
  const editing = event.target.matches('input, textarea, select, [contenteditable="true"]');
  if (editing) return;
  if (event.key === '/') {event.preventDefault(); state.mobileOpen = false; render(); document.querySelector('#incident-filter').focus(); return;}
  if (event.key === 'Escape' && state.mobileOpen) {action('back'); return;}
  if (event.target.matches('[role="tab"]') && ['ArrowLeft','ArrowRight','Home','End'].includes(event.key)) {
    event.preventDefault(); let index = tabs.indexOf(state.tab);
    index = event.key === 'Home' ? 0 : event.key === 'End' ? tabs.length - 1 : (index + (event.key === 'ArrowRight' ? 1 : 2)) % 3;
    state.tab = tabs[index]; render(); document.querySelector('#tab-' + state.tab).focus(); return;
  }
  if (event.target.matches('[role="separator"]')) return;
  if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
  if (['ArrowDown','ArrowUp'].includes(event.key) && !event.target.matches('body, [data-select]')) return;
  if (['j','k','ArrowDown','ArrowUp'].includes(event.key)) {
    const visible = visibleEvents(); if (!visible.length) return;
    event.preventDefault(); const step = ['j','ArrowDown'].includes(event.key) ? 1 : -1;
    const index = Math.max(0, Math.min(visible.length - 1, visible.findIndex(item => item.event_id === state.selected) + step));
    selectEvent(visible[index].event_id); document.querySelector(`[data-select="${state.selected}"]`)?.focus();
  }
});
window.addEventListener('resize', () => {if (window.innerWidth >= 1100) setWidth(state.width, false); updateNavigation();});
function refreshCurrent() { return view === 'investigations' ? historyScreen.refresh() : loadEvents(); }
function updateNavigation() {
  document.title = `AegisOps · ${view === 'investigations' ? 'Investigations' : 'Incidents'}`;
  document.querySelectorAll('[data-screen]').forEach(link => {
    if (link.dataset.screen === view) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  });
  const detail = app.querySelector('.detail-open');
  const target = detail && innerWidth < 1100 ? app.querySelector('.detail-panel') : document.getElementById(view === 'investigations' ? 'history-table' : 'incident-table');
  const skip = document.querySelector('.skip-link');
  skip.href = '#' + (target?.id ?? 'app');
  skip.textContent = detail && innerWidth < 1100 ? 'Skip to report' : `Skip to ${view}`;
}
document.querySelector('.skip-link').addEventListener('click', event => {
  event.preventDefault();
  const target = document.querySelector(document.querySelector('.skip-link').getAttribute('href'));
  target?.focus();
});
function switchView(next) {
  view = next === 'investigations' ? 'investigations' : 'incidents';
  if (location.hash !== '#' + view) window.history.pushState(null, '', '#' + view);
  if (view === 'investigations') historyScreen.enter();
  else {state.mobileOpen = false; render(); if (!state.lastRefresh) loadEvents();}
}
window.addEventListener('hashchange', () => switchView(location.hash.slice(1)));
if (view === 'investigations') historyScreen.enter(); else {render(); loadEvents();}
setInterval(() => document.querySelectorAll('[data-time]').forEach(element => {element.textContent = relativeTime(element.dataset.time);}), 30000);
