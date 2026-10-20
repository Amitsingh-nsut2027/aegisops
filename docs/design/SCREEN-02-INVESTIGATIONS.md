# Screen 02 — investigation history proposal

Status: the user explicitly approved this proposal with “ok” on 2026-10-19. Screen two is now implemented locally. See docs/notes/frontend-investigations.md and docs/design/review-screen-02/ for critique, browser captures, and verification. The layout/data below record the approved scope; they do not approve another screen.

## Operator task
Find an investigation run, distinguish its source event from its execution, and inspect the exact report saved at that point. The incident inbox remains event-focused; this view is run-focused. One event can have multiple runs with different workflow versions, fixture context, and runbook snapshots.

## Layout for approval
```text
┌──────┬─────────────────────────────────────────┬───────────────────────────┐
│ AO   │ INVESTIGATIONS                 Refresh  │ Run 8aec198…525f   Copy ID │
│      │ LOCAL / SIMULATION                      │ api-service               │
│ INC  ├─────────────────────────────────────────┤ Needs evidence            │
│ RUN* │ Event ID filter   Filter loaded page    │                           │
│ DOC  ├────────────┬────────┬─────────┬──────────┤ WORKFLOW / PROVIDER       │
│      │ RUN / EVENT│ STARTED│ VERSION │ RESULT   │ cpu-investigator-v3       │
│      ├────────────┼────────┼─────────┼──────────┤ fake-v2 · no model call    │
│      │ 8aec…     │ … ago  │ v3      │ needs…   ├───────────────────────────┤
│      │ 0e69…     │ … ago  │ v2      │ needs…   │ Evidence | Trace | Docs   │
│      │ 408c…     │ … ago  │ v1      │ needs…   │                           │
│      │           scrollable history           │ Saved snapshot content    │
│      │ sticky headings                       │ Source + exact timestamps │
├──────┼─────────────────────────────────────────┼───────────────────────────┤
│      │ Pagination · last successful refresh    │ Read only · simulation    │
└──────┴─────────────────────────────────────────┴───────────────────────────┘
```

Keep the approved dark tokens, typography, density, resize behavior, keyboard palette, and focus conventions. At 1024/768/390 px use list → full-page run detail with Back to history. Do not shrink the desktop table until it clips.

## Data and semantics
- GET /investigations?limit=25&offset=... supplies the run table, sorted by started_at descending and run_id ascending. Optional event_id is an exact server-side filter.
- GET /investigations/{run_id} supplies the selected saved report. Its resource, workflow/provider metadata, timing, fallback flag, evidence, trace, and runbook context are read from that snapshot.
- GET /events/{event_id}, when needed, supplies original CPU samples for the selected run. Clearly distinguish source-event observation time from run execution time; do not substitute another event after a missing ID.
- A local text filter is explicitly scoped to the loaded page. It can match run/event/resource identifiers and workflow/provider strings. No unimplemented global text search is implied.
- Version and fallback indicators describe real saved metadata. No fixed run count, duration, “agents active,” accuracy, diagnosis, or recovery statistics.
- Duration may be displayed only as finished_at minus started_at for that recorded run, labeled elapsed workflow time. It is not model latency or incident recovery time. A missing or invalid duration is shown as unavailable.
- Missing older fields are unavailable, not inferred. An older report with no runbooks must not inherit the newest run's guidance. The selected snapshot remains unchanged while it is read.

## Functional scope
RUN in the rail opens this run-focused history. INC returns to the existing event inbox, ideally preserving its filter/selection. DOC remains scoped to the selected report's guidance; no unapproved global runbook catalog screen is added.

Select rows with pointer/keyboard, navigate saved pages, filter by source event, switch inspector tabs, copy run/event/source IDs and hashes, and reveal exact UTC times. Reuse the existing local bridge and viewer permissions; no new write endpoint, token storage, or infrastructure action is needed.

## States to design and verify
Loading rows with matched inspector skeleton; empty history; no runs for exact event ID; invalid event-ID input before request; loaded-page filter with no matches; session expired; API unavailable; stale retained history; missing selected run/source event; older report metadata; fallback; unavailable evidence/guidance. Always distinguish a successful empty result from a failed lookup.

## Process gate
Wait for the user's explicit approval of this screen's ASCII layout/data before implementation, as required in DESIGN.md. After building, list five concrete generic/careless elements and fix them before review, then perform a dedicated alignment/spacing/contrast/control-state/responsive polish pass at 1280/1024/768/390. Record results alongside screen-one evidence without overwriting it.
