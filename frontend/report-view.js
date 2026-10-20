import {escapeHTML as e, relativeTime, exactTime, shortId} from './format.js';
const evidenceLabel = key => ({cpu_samples:'CPU samples', request_rate:'Request rate', deployment_history:'Deployment history', application_logs:'Application logs'}[key] ?? key.replaceAll('_', ' '));
export const time = (value, prefix = '') => `<button class="timestamp data" data-time="${e(value)}" title="${e(exactTime(value))}" aria-label="${e(prefix + exactTime(value))}">${e(relativeTime(value))}</button>`;
export const copy = (value, name, text = 'Copy') => `<button class="copy-button" data-copy="${e(value)}" aria-label="Copy ${e(name)}" title="Copy ${e(name)}">${text}</button>`;
export function panelState(title, detail, action = '') {
  return `<div class="designed-state"><span class="state-rule"></span><h3>${e(title)}</h3><p>${e(detail)}</p>${action}</div>`;
}
export function evidenceContent(event, run) {
  const report = run?.payload;
  const checks = report?.evidence_checks ?? [];
  const supplemental = report?.supplemental_evidence ?? [];
  const evidenceRows = checks.length ? checks.map(check => {
    const source = supplemental.find(item => item.kind === check.kind);
    return `<article class="evidence-item"><div class="evidence-item-head"><h3>${e(evidenceLabel(check.kind))}</h3><span class="neutral-status">${check.status === 'available' ? 'Available' : check.status === 'unavailable' ? 'Unavailable' : 'Not recorded'}</span></div><p>${e(check.detail)}</p><div class="source-line data">${e(check.source)}</div>${source ? `<div class="source-meta">${time(source.observed_at)}<span class="data">${shortId(source.evidence_id)}</span>${copy(source.evidence_id, 'evidence ID')}</div>` : ''}</article>`;
  }).join('') : panelState('No saved evidence inventory', 'This event has no report, or the selected report predates evidence inventories.');
  const trigger = event ? `<section class="inspector-section"><div class="label-row"><span class="eyebrow">TRIGGER</span><span class="data">${event.payload?.cpu_evidence?.length ?? 0} samples</span></div><div class="trigger-values">${(event.payload?.cpu_evidence ?? []).map((value, index) => `<div><span class="eyebrow">SAMPLE ${index + 1}</span><span class="data">${e(value)}<small>%</small></span></div>`).join('')}</div><p class="trigger-rule data">&gt; ${e(event.payload?.threshold ?? '—')}% · ${e(event.payload?.required_samples ?? '—')} consecutive samples</p></section>` : '';
  return `${trigger}
    ${run ? `<section class="conclusion"><span class="eyebrow">FINDING</span><h3>${report?.analysis?.result ? 'Cause undetermined' : 'No finding recorded'}</h3><p class="finding-state">${e(report?.analysis?.result?.status?.replaceAll('_', ' ') ?? 'No result saved')}</p><details class="saved-summary"><summary>Read saved summary</summary><p>${e(report?.analysis?.result?.summary ?? 'No summary was saved in this report.')}</p></details>${report?.analysis?.used_fallback ? '<p class="fallback-note">Deterministic fallback used. Provider output did not pass validation.</p>' : ''}</section>` : ''}
    <section class="inspector-section"><div class="label-row"><span class="eyebrow">EVIDENCE INVENTORY</span><span class="data">${checks.length}</span></div>${evidenceRows}</section>`;
}
export function traceContent(run) {
  const trace = run?.payload?.trace ?? [];
  if (!trace.length) return panelState('No execution trace', 'Select a saved run containing an observable workflow trace.');
  return `<section class="inspector-section"><div class="label-row"><span class="eyebrow">EXECUTION TRACE</span><span class="data">${trace.length} steps</span></div><p class="section-description">Recorded workflow outcomes. Not streamed model reasoning.</p><ol class="trace-list">${trace.map(step => `<li><span class="trace-number data">${e(step.sequence)}</span><div><div class="label-row"><h3>${e(step.step.replaceAll('_', ' '))}</h3><span class="neutral-status">${e(step.status.replaceAll('_', ' '))}</span></div><p>${e(step.detail)}</p>${time(step.recorded_at)}</div></li>`).join('')}</ol></section>`;
}
function runbookMarkup(text) {
  return String(text ?? '').replace(/^# [^\n]+\n*/, '').split(/\n\s*\n/).filter(Boolean).map(block => {
    const lines = block.split('\n');
    if (lines.every(line => /^\d+\.\s/.test(line))) return '<ol>' + lines.map(line => '<li>' + e(line.replace(/^\d+\.\s/, '')) + '</li>').join('') + '</ol>';
    return '<p>' + e(block) + '</p>';
  }).join('');
}
export function docsContent(run) {
  const context = run?.payload?.runbook_context;
  if (!context?.matches?.length) return panelState(context?.status === 'unavailable' ? 'Guidance unavailable' : 'No saved runbook matches', 'This view contains guidance saved with the selected run. It does not query a global catalog.');
  return `<section class="inspector-section"><div class="label-row"><span class="eyebrow">LOCAL RUNBOOKS</span><span class="data">${context.matches.length} sources</span></div><p class="section-description">Guidance only. No instructions have been executed.</p>${context.matches.map(match => `<details class="runbook" open><summary><span>${e(match.title)}</span><span class="data">${e(match.score)} tags</span></summary><div class="runbook-source data">${e(match.source)}</div><div class="runbook-excerpt">${runbookMarkup(match.excerpt)}</div><div class="revision"><span class="eyebrow">CONTENT REVISION</span><code>${e(match.revision)}</code>${copy(match.revision, 'runbook revision')}</div>${match.excerpt_truncated ? '<p class="section-description">Excerpt truncated in saved report.</p>' : ''}</details>`).join('')}</section>`;
}
