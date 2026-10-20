# Frontend — approved incident workbench

## What is implemented
The first approved screen is a working local incident workbench, not a static mockup. It follows DESIGN.md: Space Grotesk headings, IBM Plex Mono data, near-black neutrals, one lime accent, dense tables, and a resizable inspector. No component library or browser framework is required for this bounded first screen; it uses browser-native JavaScript modules, HTML, CSS, and a small Python local bridge.

The user approved this screen's ASCII layout before code. That approval covers this incident workbench and its Evidence/Trace/Runbooks inspector states; each later screen still requires a separate wireframe and approval.

## Start it
Run from the project root with Docker Desktop running:
```sh
python3 scripts/start_workbench.py
```
This preserves local secrets, builds/starts the API and its database dependencies, refreshes the private viewer token, and serves http://127.0.0.1:5173. Keep that terminal running. Ctrl+C stops the browser bridge; existing Docker API/database containers remain running.

The development viewer token expires after 15 minutes. To refresh while the bridge keeps running, use a second terminal:
```sh
python3 scripts/create_viewer_token.py
```
Then click Retry/Refresh. The bridge rereads the private file for each request, so it does not require restarting. No token is pasted into browser storage or URLs. This remains a trusted local development session, not a production login system.

## Operator workflow
- Select a saved incident to inspect its actual evidence and run history. Repeated service names remain distinguishable by scenario, event ID, and exact UTC observation clock time.
- Filter the loaded page by resource, event ID, scenario, or event type. The control explicitly says this page; it is not global server search.
- Choose a saved run. Only existing run data is displayed. No saved run and history unavailable are different states.
- Evidence shows trigger samples, a saved summary disclosure, supplemental records, source labels, timestamps, and evidence IDs.
- Trace shows recorded workflow steps, outcomes, and exact timestamps. Nothing is artificially streamed or animated as agent activity.
- Runbooks shows saved source excerpts, revisions, tag-match scores, and copyable hashes. It is guidance from this run, not a live global knowledge catalog. The simple safe renderer escapes text before formatting paragraphs and numbered checklists; arbitrary HTML is never interpreted.
- Refresh fetches a fresh snapshot. If a later request fails, existing records stay visible with a stale-data warning. Session expiration clears records and shows the renewal action.

## Keyboard and interaction details
Cmd/Ctrl+K opens the command palette. Arrow keys select commands; Enter executes; Escape dismisses and restores focus. Commands navigate within the approved screen, refresh data, copy an ID, or reset pane width. Slash focuses the page filter outside text-entry controls. j/k or up/down select events; Enter opens the inspector. Tabs support left/right/Home/End.

At desktop widths, drag the divider or focus it and use left/right arrows to resize; Home or double-click resets it. Only the pane preference is stored locally. Copy actions use full values, with success/failure feedback. Relative timestamps reveal exact UTC time on hover, focus, or activation. Relative labels refresh every 30 seconds without rerendering the page.

At 1024/768/390 px, selection opens a dedicated inspector/detail view and Inbox returns to the list. At 1280 px, the asymmetric split view is visible. Table headings stay sticky inside their bounded scrolling region. The observation chart uses only the saved trigger samples and labels the nonzero axis range; it has an accessible text description and labeled focusable sample points. No hidden historical time series is invented.

## Data and trust boundaries
The browser reads same-origin /api/events and /api/investigations through scripts/serve_frontend.py. The bridge binds only 127.0.0.1, serves only frontend/, reads the ignored private viewer-token file, and forwards it only as an Authorization header to the existing API on 127.0.0.1:8000. It permits only allowlisted GET read paths, rejects foreign Host/cross-site browser fetches, hides private/hidden paths, bounds upstream responses, and sends no-store/security headers.

The API still validates the JWT and uses its SELECT-only database role. The browser receives neither the signing key nor a database password. Any local process/user authorized to access this loopback bridge can use its development viewer session; do not expose this helper as public hosting. Production identity, public demo isolation, TLS/deployment, and cloud sandbox/cost review remain separate work.

Initial load requests one 25-event page and up to one bounded history page per event. Each history is capped at 100 latest runs, with an explicit limit label when more exist. This is simple and correct for the current small dataset, but a server-side latest-run projection would reduce requests at larger scale. It is not a realtime subscription. The interface displays Untriaged because warning source severity is not a verified SEV impact assessment.

## Design critique and dedicated polish
The required five-item critique and concrete fixes are in docs/design/review/SCREEN-01-CRITIQUE.md, with before/after browser captures. An additional polish pass replaced raw Markdown runbook formatting with readable, safely escaped paragraphs/checklists; retained source metadata remains monospace.

Separate alignment and contrast checks confirmed the heading, toolbar, and observation share the same anchor and 117 sampled rendered text pairs meet 4.5:1. Focus/hover/active samples and disabled pagination were inspected, including visible 2 px keyboard outlines. This does not establish complete WCAG conformance or assistive-technology certification.

Browser checks covered 1280, 1024, 768, and 390 px, with no document overflow. Populated, no-run, empty-filter, empty-journal, expired-session, loading, API-error, history-error, and stale-snapshot states were exercised. Reduced motion suppresses transitions. Screenshots and machine-readable results are in docs/design/review/.

## Verification and repeatability
- Three JavaScript formatter tests: escaping untrusted markup, relative past/future timestamps, exact UTC/ID formatting.
- Six Python bridge boundary tests: static headers, host/origin guard, route allowlist, private paths, missing sessions, and header-only token forwarding.
- Real-browser checks: actual API data, loaded fonts, event/run selection, tabs, copy, exact time, filtering, j/k, pointer/keyboard resizing, palette, storage isolation, responsive navigation, errors, reduced motion, and no runtime errors.
- The existing backend code is unchanged by this screen; its prior 66-test unit checkpoint remains recorded separately.

Run the lightweight checks:
```sh
node --test frontend/tests/format.test.js
python3 -m unittest discover -s frontend/tests -p test_bridge.py -v
```
Browser scripts are frontend/tests/workbench.cjs and polish.cjs. They require Playwright plus installed Chrome, and a running bridge/API. In this workspace the bundled Playwright module was supplied through PLAYWRIGHT_MODULE. They use an isolated browser profile, not your signed-in browser. API error/empty states are browser-intercepted test responses, not inserted fake incident rows. The main browser scenario currently expects the known four seeded events.

## Honest project explanation
“I built a read-only incident workbench connected to the saved event and investigation APIs. It supports keyboard navigation, a command palette, scoped filtering, resizable panes, saved-run selection, evidence provenance, recorded traces, and revisioned guidance. I designed explicit error/empty/stale states and checked four responsive sizes. A loopback bridge keeps the development viewer token outside browser storage. The telemetry and analysis are still clearly labeled simulation; production identity and AWS deployment are not implemented.”

## Remaining scope
Only screen one is implemented. No incident mutation, approval action, remediation, streaming agents, new SEV classification, global search/catalog, or public deployment is implied by the UI. Dark mode is the approved first theme; a separately audited light theme remains deferred. A new screen requires its own approved wireframe.
