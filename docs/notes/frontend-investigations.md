# Frontend — investigation history

## What was approved and built
The user approved the second screen's ASCII layout and data proposal in docs/design/SCREEN-02-INVESTIGATIONS.md. It is now implemented as a run-focused history table plus saved-report inspector. The original incident inbox remains event-focused and retains its own selection/filter when switching screens. This approval does not cover any further screen.

Start the same local application:
```sh
python3 scripts/start_workbench.py
```
Open http://127.0.0.1:5173/#investigations or choose RUN from the rail. INC returns to the existing inbox. DOC opens the selected run's saved guidance tab, without inventing a global catalog page. Narrow layouts use History → run detail → Back to history.

## Why distinguish events and runs?
An event describes a detected symptom at its synthetic observation time. Each invocation creates a separate run with actual execution start/finish timestamps. Reinvestigating an event does not overwrite its earlier report. Workflow versions, available fixtures, fallback flags, and runbook snapshots may differ between runs.

The history table shows actual saved rows, not a fixed count. Compact workflow v1/v2/v3 labels support scanning; complete version/provider values remain in the selected report's metadata. No SEV level, diagnosis, recovery claim, or agent activity is invented.

## Data flow
1. GET /investigations?limit=25&offset=... supplies one sorted page.
2. An optional event_id is an exact server-side filter across saved history. A malformed ID is rejected in the browser before an API request.
3. A separate text filter applies only to the loaded page. It matches identifiers, resource, workflow version, and provider; it is not global text search.
4. GET /investigations/{run_id} reads the selected report snapshot. It never substitutes the newest run when the requested run is missing.
5. GET /events/{event_id} supplies original trigger samples. If missing/unavailable, retain the report and show the source error explicitly; do not invent zero CPU readings or borrow another event.

All reads pass through the existing loopback viewer bridge. No backend route, JWT permission, database grant, or write operation was added for this screen. The local session still expires after 15 minutes; refresh it with scripts/create_viewer_token.py and click Retry.

## Snapshot fidelity and missing metadata
Evidence/Trace/Runbooks reuse shared report-view components. They render the selected snapshot, including earlier versions without supplemental evidence or runbooks. Unknown provider, workflow, fallback, model-call, or finding fields remain not recorded; an absent value is not silently treated as false or successful.

The run ID and source event ID have separate copy actions. Timing details distinguish actual execution from synthetic source observation. Exact UTC timestamps retain their recorded microsecond fraction; elapsed workflow time is the finished-started interval, preserving sub-millisecond values from the fake local workflow. It is not model latency, customer impact duration, database-write latency, or recovery time. Missing/invalid/negative intervals display Not recorded.

List and detail requests carry monotonically increasing request counters. When a newer run is selected, a delayed response from a prior selection cannot replace the active report. Refresh also invalidates outstanding detail work. Changing screens does not discard the other screen's page/filter/selection state; browser hash navigation is supported.

## Interaction and exceptional states
The shared resizer supports pointer and keyboard operation. Cmd/Ctrl+K adapts its commands to the current screen and can switch between inbox/history, filter, change inspector tab, copy the selected run ID, refresh, or reset width. Slash targets the current page's text filter; j/k/arrows select runs. Tab navigation, clipboard feedback, and exact-time activation reuse the approved interaction rules.

History failure after a successful load keeps the last successful page and shows a stale banner. Loaded page numbers and event-filter labels continue to describe the retained data, not a failed new request. Session errors clear private records. Successful empty history, successful empty event filter, local no-match, missing selected run, and missing original event are distinct states. Selected-report loading has its own skeleton and does not show another run's data while waiting.

## Structure
- history.js owns screen-two state, requests, list/filter controls, and run selection.
- report-view.js owns shared safe report rendering and source/copy/time markup.
- app.js coordinates navigation, the incident screen, common resizer, palette, and keyboard routing.
- format.js contains escaping, UTC/relative time, precise workflow elapsed-time formatting, and event-ID filter validation.

The interface remains browser-native modules/HTML/CSS with no framework or new runtime dependency. A larger product may justify component/state tooling later; the separation here keeps the bounded two-screen implementation inspectable.

## Critique, verification, and polish
The required five-item critique/fixes are in docs/design/review-screen-02/CRITIQUE.md. Initial and final desktop/mobile captures are separate from screen-one evidence. Corrections include actual timing data instead of explanatory filler, a run-focused heading, scannable version labels, explicit filter scopes, and mobile outcome visibility.

The dedicated polish audit checked 121 sampled rendered text pairs at 4.5:1 or greater, heading/filter alignment, sampled hover/active/2 px keyboard focus, disabled pagination, and saved trace rendering. Responsive browser review covered 1280, 1024, 768, and 390 px without page overflow. This is not a claim of a complete accessibility certification or screen-reader audit.

Six JavaScript unit tests now cover escaping/time formatting plus exact-ID validation and precise elapsed time. Six bridge boundary tests still pass. Browser scripts cover actual saved data, older snapshots, independent ID copying, tabs, filters, inbox preservation/browser back, keyboard/palette/resizer, rapid-selection races, responsive navigation, session/API/empty/stale states, missing run/source, absent legacy metadata, loading, and pagination. Pagination uses isolated 26-run browser fixtures; exceptional states are browser-intercepted responses. No saved report is modified or inserted for UI testing. The original incident-screen browser regression also passed after shared-component extraction.

Run the lightweight checks:
```sh
node --test frontend/tests/format.test.js
python3 -m unittest discover -s frontend/tests -p test_bridge.py -v
```
History browser scripts: frontend/tests/history.cjs and history-polish.cjs. They require a running bridge/API, Playwright, and installed Chrome; this workspace supplies the bundled Playwright module via PLAYWRIGHT_MODULE. Results/captures are in docs/design/review-screen-02/.

## Interview explanation
“I separated the incident-event inbox from per-invocation investigation history. The history view reads immutable report snapshots, preserves version-specific evidence and guidance, and distinguishes synthetic observation time from actual execution time. Scoped filters and pagination reflect the API contract. Sequence guards prevent late responses from changing the selected run, and missing source records do not discard the saved report or substitute other telemetry. It remains a read-only local simulation.”

## Remaining boundaries
No cross-run automated comparison, global text search, new approval/remediation action, realtime stream, production identity, or public deployment is implemented. The current API still supplies full JSON snapshots in list responses. Final product integration and deployment remain future work; new screens need their own approved wireframe.
