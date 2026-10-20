import {escapeHTML as e, shortId, relativeTime, exactTime, validEventFilter, workflowElapsed} from './format.js';
import {time, copy, panelState, evidenceContent, traceContent, docsContent} from './report-view.js';

const tabNames = {evidence:'Evidence',trace:'Trace',docs:'Runbooks'};
const tabs = Object.keys(tabNames);
const pageSize = 25;
export function createHistoryScreen({app, api, environmentLabel, announce, toast, clipboard, getWidth, bindResize, navigate, openPalette, onRender, isActive}) {
  const state = {
    rows:[], selected:null, detail:null, source:null, sourceError:null, detailError:null,
    tab:'evidence', filter:'', eventDraft:'', eventApplied:'', eventLoaded:'', fieldError:null,
    offset:0, loadedOffset:0, hasMore:false, loading:true, refreshing:false, detailLoading:false,
    error:null, lastRefresh:null, mobileOpen:false, loaded:false,
  };
  let listSequence=0, detailSequence=0;
  const visible = () => state.rows.filter(row => [row.run_id,row.event_id,row.payload?.resource_id,row.payload?.workflow_version,row.payload?.analysis?.provider].some(value=>String(value??'').toLowerCase().includes(state.filter.toLowerCase())));
  const errorKind = error => error.status===401?'session':error.status===403?'forbidden':'offline';
  const selectedRow = () => state.rows.find(row=>row.run_id===state.selected);
  const selectedRun = () => state.detail?.run_id===state.selected ? state.detail : null;
  const versionLabel = value => typeof value === 'string' ? (value.match(/-v\d+$/)?.[0].slice(1) ?? value) : 'Not recorded';
  function modelUsage(report) {return report?.analysis?.model_called===false?'No model call':report?.analysis?.model_called===true?'Model call recorded':'Model usage not recorded';}
  function clearPrivateState() {state.rows=[];state.detail=null;state.source=null;state.selected=null;}
  async function refresh() {
    const sequence=++listSequence;
    ++detailSequence; state.detailLoading=false;
    state.refreshing=true;state.loading=!state.rows.length;
    render();
    try {
      const query=new URLSearchParams({limit:String(pageSize),offset:String(state.offset)});
      if(state.eventApplied)query.set('event_id',state.eventApplied);
      const page=await api('/investigations?'+query);
      if(sequence!==listSequence)return;
      state.rows=page.items;state.loadedOffset=state.offset;state.eventLoaded=state.eventApplied;
      state.hasMore=page.has_more;state.error=null;state.lastRefresh=new Date().toISOString();state.loaded=true;
      if(!visible().some(row=>row.run_id===state.selected))state.selected=visible()[0]?.run_id??null;
      // Never reuse another run's report during a selection or refresh.
      state.detail=null;state.source=null;state.detailError=null;state.sourceError=null;
      announce(`${page.returned} saved investigation runs loaded.`);
    } catch(error) {
      if(sequence!==listSequence)return;
      state.error=errorKind(error);state.offset=state.loadedOffset;
      if(['session','forbidden'].includes(state.error))clearPrivateState();
    } finally {
      if(sequence===listSequence){state.loading=false;state.refreshing=false;render();}
    }
    if(sequence===listSequence&&!state.error&&state.selected)await select(state.selected);
  }
  async function select(id, open=false) {
    const sequence=++detailSequence;
    state.selected=id;state.detail=null;state.source=null;state.detailError=null;state.sourceError=null;
    state.detailLoading=true;if(open)state.mobileOpen=true;
    render();
    if(open)document.querySelector('#history-tab-'+state.tab)?.focus({preventScroll:true});
    try {
      const run=await api('/investigations/'+id);
      if(sequence!==detailSequence)return;
      if(run.run_id!==id)throw new Error('Run identity mismatch');
      state.detail=run;
      try {
        const source=await api('/events/'+run.event_id);
        if(sequence!==detailSequence)return;
        if(source.event_id!==run.event_id)throw new Error('Source identity mismatch');
        state.source=source;
      } catch(error) {
        if(sequence!==detailSequence)return;
        if([401,403].includes(error.status))throw error;
        state.sourceError=error.status===404?'missing':'unavailable';
      }
    } catch(error) {
      if(sequence!==detailSequence)return;
      if([401,403].includes(error.status)){state.error=errorKind(error);clearPrivateState();}
      else state.detailError=error.status===404?'missing':'unavailable';
    } finally {
      if(sequence===detailSequence){state.detailLoading=false;render();}
    }
  }
  function loadingRows() {
    return `<div class="table-skeleton history-skeleton" aria-label="Loading investigation history" aria-busy="true">${Array.from({length:5},()=>'<div class="skeleton-row"><span class="skeleton line-0"></span><span class="skeleton line-1"></span><span class="skeleton stub"></span></div>').join('')}</div>`;
  }
  function banner() {
    if(!state.error)return '';
    const messages={session:['Session expired','Renew the local viewer session, then retry.'],forbidden:['Read access denied','The viewer session cannot read this history.'],offline:[state.rows.length?'History snapshot is stale':'History unavailable',state.rows.length?'Refresh failed. The last successful page remains visible.':'The investigation API did not respond.']};
    const [title,detail]=messages[state.error];
    return `<div class="error-banner" role="alert"><div><strong>${title}</strong><span>${detail}</span>${state.error==='session'?'<code>python3 scripts/create_viewer_token.py</code>':''}</div><button data-history-action="refresh" ${state.refreshing?'disabled':''}>Retry</button></div>`;
  }
  function rows() {
    return visible().map(row=>{
      const report=row.payload??{};const active=row.run_id===state.selected;
      return `<tr class="event-row history-row ${active?'selected':''}" data-history-row="${e(row.run_id)}" aria-selected="${active}">
        <td class="run-column"><button class="row-select data" data-history-select="${e(row.run_id)}" tabindex="${active?0:-1}" aria-label="Inspect run ${e(shortId(row.run_id))}">${e(shortId(row.run_id))}<span class="event-source">${e(report.resource_id?.split('/').at(-1)??'Resource not recorded')} · event ${e(shortId(row.event_id))}</span><span class="mobile-run-outcome data">${e(versionLabel(report.workflow_version))} · ${e(row.state.replaceAll('_',' '))}${report.analysis?.used_fallback===true?' · fallback':''}</span></button></td>
        <td class="run-started">${time(row.started_at,'Run started ')}<span class="observed-clock data">${e(exactTime(row.started_at).slice(11,19))} UTC</span></td>
        <td class="run-version"><span class="data" title="${e(report.workflow_version??'Not recorded')}">${e(versionLabel(report.workflow_version))}</span><span class="event-source">${e(report.analysis?.provider??'Provider not recorded')}</span></td>
        <td class="run-result"><span class="row-state ${active?'row-state-active':''}">${e(row.state.replaceAll('_',' '))}</span><span class="event-source">${report.analysis?.used_fallback===true?'Fallback used':report.analysis?.used_fallback===false?'Primary output':'Fallback not recorded'}</span></td>
        <td class="row-arrow" aria-hidden="true">${active?'↗':'→'}</td></tr>`;
    }).join('');
  }
  function detail() {
    const row=selectedRow();const run=selectedRun();const report=run?.payload;
    if(state.loading)return `<aside class="inspector skeleton-inspector">${loadingRows()}</aside>`;
    if(!row)return `<aside class="inspector inspector-empty">${panelState('Select a run','Choose a saved invocation to inspect its exact report snapshot.')}</aside>`;
    const resource=report?.resource_id??row.payload?.resource_id;
    const missingLabel=state.detailLoading?'Loading…':state.detailError?'Unavailable':'Not recorded';
    let content;
    if(state.detailLoading)content=`<div class="history-detail-loading" role="status" aria-label="Loading selected report">${loadingRows()}<p>Loading the selected snapshot…</p></div>`;
    else if(state.detailError)content=panelState(state.detailError==='missing'?'Run not found':'Report unavailable','The selected saved report could not be read. Another run has not been substituted.','<button data-history-action="retry-detail">Retry report</button>');
    else if(state.tab==='trace')content=traceContent(run);
    else if(state.tab==='docs')content=docsContent(run);
    else content=`${state.sourceError?panelState('Source event '+(state.sourceError==='missing'?'not found':'unavailable'),'The saved report remains available. Original CPU trigger data has not been substituted.','<button data-history-action="retry-detail">Retry source</button>'):''}${evidenceContent(state.source,run)}`;
    return `<aside class="inspector history-inspector" aria-label="Investigation inspector"><div class="inspector-title"><button class="mobile-back" data-history-action="back">← History</button><div class="label-row"><span class="eyebrow">RUN INSPECTOR</span>${copy(row.run_id,'run ID','Copy ID')}</div><h2 class="data">Run ${e(shortId(row.run_id))}</h2><div class="inspector-event-id data">${e(resource??'Resource not recorded')}</div><div class="inspector-subline"><span class="neutral-status">${e(row.state.replaceAll('_',' '))}</span><span class="data">Saved snapshot</span></div></div>
      <div class="history-run-meta"><dl><div><dt>Workflow</dt><dd>${e(report?.workflow_version??missingLabel)}</dd></div><div><dt>Provider</dt><dd>${e(report?.analysis?.provider??missingLabel)}</dd></div><div><dt>Workflow elapsed</dt><dd>${state.detailLoading?'Loading…':state.detailError?'Unavailable':workflowElapsed(run?.started_at,run?.finished_at)}</dd></div><div><dt>Run started</dt><dd>${run?time(run.started_at,'Run started '):'Not loaded'}</dd></div><div><dt>Source event</dt><dd>${e(shortId(row.event_id))} ${copy(row.event_id,'source event ID')}</dd></div></dl></div>
      <div class="inspector-tabs" role="tablist" aria-label="Saved report detail">${tabs.map(tab=>`<button id="history-tab-${tab}" role="tab" aria-selected="${state.tab===tab}" aria-controls="history-panel" tabindex="${state.tab===tab?0:-1}" data-history-tab="${tab}">${tabNames[tab]}</button>`).join('')}</div>
      <div id="history-panel" class="detail-panel" role="tabpanel" tabindex="0" aria-labelledby="history-tab-${state.tab}">${content}</div>
      <div class="inspector-footer"><span>${state.detailLoading?'Loading report':state.detailError?'Report unavailable':modelUsage(report)}</span><span>Read only · simulation</span></div></aside>`;
  }
  function render() {
    if(!isActive())return;
    const focus=document.activeElement;const focusId=focus?.id;const focusedRow=focus?.dataset?.historySelect;const cursor=focus?.selectionStart;
    const context = `${state.selected}/${state.tab}`;
    const previousContext = app.querySelector('.workbench')?.dataset.detailContext;
    const scrolls = [...app.querySelectorAll('.detail-panel, .table-scroll, .workspace-scroll')].map(el => [el.className, el.scrollTop]);
    app.innerHTML=`<div data-detail-context="${e(context)}" class="workbench history-workbench ${state.mobileOpen?'detail-open':''}" style="--inspector-width:${getWidth()}px"><nav class="rail" aria-label="Workspace navigation"><a class="brand" href="#incidents" aria-label="AegisOps incident inbox">A<span class="brand-notch"></span></a><div class="rail-controls"><button class="rail-button" data-history-action="incidents" aria-label="Open incident inbox">INC<span>01</span></button><button class="rail-button active" data-history-action="history" aria-current="page" aria-label="Investigation history">RUN<span>02</span></button><button class="rail-button" data-history-tab="docs" aria-label="Selected run guidance" ${!state.selected?'disabled':''}>DOC<span>03</span></button></div><button class="rail-command" data-history-action="palette" aria-label="Open command palette">⌘K</button><span class="rail-version data">v0.1</span></nav>
    <main class="workspace"><header class="workspace-header"><div class="workspace-breadcrumb"><span class="small-logo">AEGISOPS</span><span class="slash">/</span><span>INVESTIGATIONS</span></div><div class="header-meta"><span class="simulation-indicator">${environmentLabel}</span><button class="command-trigger" data-history-action="palette">Commands <kbd>⌘ K</kbd></button></div></header>
    <div class="workspace-scroll"><div class="page-heading"><div><div class="eyebrow">SAVED EXECUTIONS</div><h1>Investigations<span class="heading-period">.</span></h1><p>Run history · independent report snapshots</p></div><button class="refresh-button" data-history-action="refresh" ${state.refreshing?'disabled':''}>${state.refreshing?'Refreshing…':'Refresh'}<span aria-hidden="true">↻</span></button></div>
    ${banner()}<form class="history-event-filter" id="history-event-form" novalidate><div class="label-row"><label for="history-event-id">EVENT ID</label><span class="filter-scope-hint">All saved runs · exact match</span></div><div class="event-filter-controls"><input id="history-event-id" class="data" type="text" placeholder="Exact event ID · all runs if empty" value="${e(state.eventDraft)}" autocomplete="off" spellcheck="false" aria-invalid="${Boolean(state.fieldError)}" aria-describedby="history-filter-error"><button type="submit" ${state.refreshing?'disabled':''}>Apply</button><button type="button" data-history-action="clear-event" ${!state.eventDraft&&!state.eventLoaded?'disabled':''}>Clear</button></div><span id="history-filter-error" class="field-error" role="status">${e(state.fieldError??'')}</span></form>
    ${state.eventLoaded?`<div class="applied-event data">Showing event ${e(shortId(state.eventLoaded))} ${copy(state.eventLoaded,'filtered event ID')}</div>`:''}
    <div class="table-toolbar"><label class="filter-label" for="history-filter"><span class="search-symbol" aria-hidden="true"></span><input id="history-filter" type="search" placeholder="Filter this page…" value="${e(state.filter)}" autocomplete="off"><kbd>/</kbd></label><span class="toolbar-scope data">${state.loading?'Loading':visible().length+' / '+state.rows.length} <span>on this page</span></span></div>
    <div class="table-scroll history-table-scroll" id="history-table" tabindex="-1"><table class="history-table"><caption class="sr-only">Saved investigation runs sorted by execution start time. Text filtering applies only to this page.</caption><thead><tr><th class="run-column">RUN / SOURCE EVENT</th><th class="run-started">STARTED</th><th class="run-version">WORKFLOW</th><th class="run-result">RESULT</th><th><span class="sr-only">Inspect</span></th></tr></thead><tbody>${state.loading?'':rows()}</tbody></table>${state.loading?loadingRows():!state.rows.length?panelState(state.error?'History unavailable':state.eventLoaded?'No runs for this event':'No saved investigations',state.error?'Restore access to read saved history.':state.eventLoaded?'The query completed successfully without matching saved runs.':'Run the local investigator to append a report.'):!visible().length?panelState('No runs match this filter','This text filter applies only to the loaded page.','<button data-history-action="clear-filter">Clear page filter</button>'):''}</div>
    <div class="table-footer"><span class="data">${state.rows.length?state.loadedOffset+1:0}–${state.loadedOffset+state.rows.length} loaded</span><div class="pagination"><button data-history-action="previous" aria-label="Previous investigation page" ${state.offset===0||state.refreshing?'disabled':''}>←</button><span class="data">Page ${Math.floor(state.loadedOffset/pageSize)+1}</span><button data-history-action="next" aria-label="Next investigation page" ${!state.hasMore||state.refreshing||state.offset+pageSize>10000?'disabled':''}>→</button></div></div>
    ${selectedRow()?`<section class="history-scope history-timing"><div class="label-row"><span class="eyebrow">SELECTED RUN / EXECUTION TIMING</span><span class="data">${e(shortId(state.selected))}</span></div><dl><div><dt>Started · actual</dt><dd>${e(selectedRun()?exactTime(selectedRun().started_at):'Loading selected report…')}</dd></div><div><dt>Finished · actual</dt><dd>${e(selectedRun()?exactTime(selectedRun().finished_at):'Not loaded')}</dd></div><div><dt>Observed · synthetic</dt><dd>${e(state.source?exactTime(state.source.observed_at):state.sourceError?'Source unavailable':'Not loaded')}</dd></div><div><dt>Workflow elapsed</dt><dd>${workflowElapsed(selectedRun()?.started_at,selectedRun()?.finished_at)}</dd></div></dl></section>`:''}
    <footer class="workspace-footer"><span class="snapshot-mark">SNAPSHOT</span><span>${state.lastRefresh?'Last refreshed '+time(state.lastRefresh):'Not refreshed'}</span><span class="footer-readonly">Read-only history</span></footer></div></main>
    <div class="pane-separator" role="separator" aria-label="Resize investigation inspector" aria-orientation="vertical" aria-valuemin="400" aria-valuemax="640" aria-valuenow="${getWidth()}" tabindex="0" title="Drag or use arrow keys. Double-click to reset."><span></span></div>${detail()}</div>`;
    app.querySelectorAll('[data-time]').forEach(el=>el.addEventListener('click',()=>toast(exactTime(el.dataset.time))));
    app.querySelectorAll('[data-copy]').forEach(el=>el.addEventListener('click',()=>clipboard(el.dataset.copy,el.getAttribute('aria-label').replace('Copy ',''))));
    app.querySelectorAll('[data-history-action]').forEach(el=>el.addEventListener('click',()=>action(el.dataset.historyAction)));
    app.querySelectorAll('[data-history-tab]').forEach(el=>el.addEventListener('click',()=>showTab(el.dataset.historyTab)));
    app.querySelectorAll('[data-history-row]').forEach(el=>el.addEventListener('click',event=>{if(!event.target.closest('[data-time]'))select(el.dataset.historyRow,true);}));
    app.querySelectorAll('[data-history-select]').forEach(el=>el.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();select(el.dataset.historySelect,true);}}));
    document.querySelector('#history-event-id').addEventListener('input',event=>{state.eventDraft=event.target.value;state.fieldError=null;event.target.setAttribute('aria-invalid','false');document.querySelector('#history-filter-error').textContent='';document.querySelector('[data-history-action="clear-event"]').disabled=!state.eventDraft&&!state.eventLoaded;});
    document.querySelector('#history-event-form').addEventListener('submit',event=>{event.preventDefault();applyEvent();});
    document.querySelector('#history-filter').addEventListener('input',event=>{
      state.filter=event.target.value;
      const next=visible();
      if(!next.some(row=>row.run_id===state.selected)){state.selected=next[0]?.run_id??null;state.detail=null;state.source=null;state.detailError=null;render();if(state.selected)select(state.selected);}
      else render();
    });
    bindResize();
    if(focusId){const target=document.getElementById(focusId);target?.focus({preventScroll:true});if(typeof cursor==='number'&&['search','text'].includes(target?.type))target.setSelectionRange(cursor,cursor);}
    else if(focusedRow)document.querySelector(`[data-history-select="${focusedRow}"]`)?.focus({preventScroll:true});
    onRender();
    for (const [className, scroll] of scrolls) [...app.querySelectorAll('.detail-panel, .table-scroll, .workspace-scroll')].find(el => el.className === className)?.scrollTo(0, className === 'detail-panel' && context !== previousContext ? 0 : scroll);
  }
  function applyEvent() {
    const id=state.eventDraft.trim();
    if(!validEventFilter(id)){state.fieldError='Enter a complete 64-character lowercase hexadecimal event ID.';render();document.querySelector('#history-event-id').focus();return;}
    state.fieldError=null;state.eventApplied=id;state.offset=0;state.filter='';refresh();
  }
  function action(name) {
    if(name==='refresh')refresh();
    if(name==='palette')openPalette();
    if(name==='incidents')navigate('incidents');
    if(name==='history'){state.mobileOpen=false;render();}
    if(name==='back'){state.mobileOpen=false;render();document.querySelector(`[data-history-select="${state.selected}"]`)?.focus();}
    if(name==='retry-detail'&&state.selected)select(state.selected);
    if(name==='clear-event'){state.eventDraft='';applyEvent();}
    if(name==='clear-filter'){state.filter='';state.selected=state.rows[0]?.run_id??null;render();if(state.selected)select(state.selected);}
    if(name==='previous'||name==='next'){state.offset+=name==='next'?pageSize:-pageSize;state.filter='';refresh();}
  }
  function showTab(tab) {state.tab=tab;if(state.selected)state.mobileOpen=true;render();document.querySelector('#history-tab-'+tab)?.focus({preventScroll:true});}
  function handleKey(event) {
    if(event.target.matches('input,textarea,select,[contenteditable="true"]'))return;
    if(event.key==='/'){event.preventDefault();state.mobileOpen=false;render();document.querySelector('#history-filter').focus();return;}
    if(event.key==='Escape'&&state.mobileOpen){action('back');return;}
    if(event.target.matches('[role="separator"]'))return;
    if(event.target.matches('[role="tab"]')&&['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){
      event.preventDefault();const index=event.key==='Home'?0:event.key==='End'?2:(tabs.indexOf(state.tab)+(event.key==='ArrowRight'?1:2))%3;showTab(tabs[index]);return;
    }
    if(event.defaultPrevented||event.metaKey||event.ctrlKey||event.altKey)return;
    if(['ArrowDown','ArrowUp'].includes(event.key)&&!event.target.matches('body, [data-history-select]'))return;
    if(['j','k','ArrowDown','ArrowUp'].includes(event.key)){
      const rows=visible();if(!rows.length)return;event.preventDefault();
      const index=Math.max(0,Math.min(rows.length-1,rows.findIndex(row=>row.run_id===state.selected)+(['j','ArrowDown'].includes(event.key)?1:-1)));
      select(rows[index].run_id);document.querySelector(`[data-history-select="${state.selected}"]`)?.focus();
    }
  }
  return {render,refresh,showTab,handleKey,enter(){state.mobileOpen=false;if(!state.loaded)refresh();else render();},focusFilter(){state.mobileOpen=false;render();document.querySelector('#history-filter').focus();},selectedId(){return state.selected;}};
}
