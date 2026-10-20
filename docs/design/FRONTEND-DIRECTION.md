# AegisOps frontend direction — proposal for review

Status: SUPERSEDED by the user's detailed 2026-10-19 direction and [DESIGN.md](../../DESIGN.md). The PNG/SVG previews in this folder are historical, unapproved artifacts. Do not implement their green/warm-white palette, system-only type, or layouts as the current contract. No frontend application code has been written.

## Product direction
An incident workspace for an operator: select a symptom, inspect its supporting evidence, understand what the investigator did, and read attributed guidance. The interface should feel deliberately composed, readable, and credible in a portfolio. Visual quality is judged through layout and working behavior, not claims that software authorship can be detected by appearance.

The proposal uses a deep green navigation rail with a warm neutral workspace, restrained orange data lines, and amber warning/uncertainty states. The alternate dark palette keeps the same hierarchy. No decorative KPI totals, invented recovery metrics, chat hero, gradients, or fake remediation buttons are proposed.

## Reviewable previews
- [Light desktop](dashboard-light.png), recommended default: strong separation between navigation, inbox, and evidence.
- [Dark desktop](dashboard-dark.png): the same structure with a charcoal green workspace.
- [Mobile incident detail](incident-mobile.png): one task at a time, with a back link to the inbox and stacked evidence rows.

Editable SVG sources are stored beside these PNGs. They are static design artifacts, not functional application screens. Search, navigation, and tabs shown here specify intended interactions; none are being claimed as working yet. The mobile preview is a vertically scrolling page concept, not a promise that the entire workflow fits on one device screen.

## Palette and semantic tokens
| Token | Light | Dark | Use |
|---|---|---|---|
| Navigation | #17251F | #17251F | Stable workspace rail |
| Canvas | #F5F4F0 | #171D1B | Main workspace |
| Surface | #FFFFFF | #1D2521 | Inbox and evidence surfaces |
| Primary text | #202927 | #E8EDE5 | Content |
| Secondary text | #68736E | #A2AFA4 | Source/timing metadata |
| Border | #DEDFD8 | #354038 | Quiet separators |
| Selected row | #EBEEE6 | #2B382E | Current event |
| Data/action accent | #9E4A20 | #E7A67B | CPU line and selection marker |
| Warning background | #FBF1DB | #302B1C | Warning and uncertain evidence |
| Warning text | #815B16 | #E6C585 | Warning labels |

Additional proposed severity tokens for future states: critical #A83332 on #FBE9E7 in light mode / #F2B1A8 on #38201F in dark mode; informational #315C77 on #EAF0F4 / #AFCCDF on #1E303B; confirmed success #356543 on #EAF1E7 / #B6D1AB on #253325. Success colors must not imply recovery until recovery is actually verified. Status text accompanies color. The present dataset has warning events and needs_evidence outcomes; no critical incidents or resolved states are invented for the preview.

## Typography and spacing
Use the native system sans-serif stack for clear body text and headings, with a system monospace stack for IDs, source paths, timestamps, and numeric chart annotations. The static SVG uses Arial/Helvetica and Menlo fallbacks for portable rendering. Avoid a remote font dependency for the first implementation.

Implementation scale: 28–30 px main heading, 18–20 px page/section headings, 14 px body, 12 px metadata, and 11 px uppercase micro-labels used sparingly. The wide preview uses denser annotations to show the full composition; implementation must preserve comfortable reading sizes instead of scaling a screenshot into the browser.

Use a 4 px spacing base, 8/12 px internal gaps, 16 px content padding, and 24/32 px section gutters. Corners are 4–6 px on controls and surfaces. Prefer separators to shadows. Use tabular numerals for aligned numbers. Maintain visible keyboard focus and generous targets; phone controls should reach 44 px minimum height.

## Layouts
Desktop above roughly 1280 px: compact navigation rail, scrollable incident inbox, and flexible detail workspace. Event selection stays visible while reading a report. At medium widths, navigation collapses and the inbox can open as a list view/drawer rather than stealing evidence space. Below roughly 768 px, use dedicated inbox/detail views with back navigation, stacked evidence and rule details, and a horizontally fitting tab row. Validate actual breakpoints against rendered content, not just device names.

The CPU chart displays only the three readings supplied by the event, with units, timestamps, threshold, and a clearly labeled 80–100% range. No smoothed or interpolated history is invented. Observation timestamps and report execution timestamps are distinct. The chart needs an accessible textual/table equivalent.

The overview contains the evidence summary, rule, scripted context inventory, short trace, and runbook links. Evidence, Trace, and Runbooks views expand their respective detail with source records, per-step outcomes, and saved excerpts/revisions. These views should use ordinary browser navigation or accessible tabs, with no decorative dead controls.

## Mapping to implemented data
| Visible content | Existing source |
|---|---|
| Event inbox and selected event | GET /events and /events/{event_id} |
| CPU readings/rule/resource/source | Event payload |
| Selected event's run history | GET /investigations?event_id=... |
| Complete report and trace | GET /investigations/{run_id} payload |
| Scripted context | supplemental_evidence and evidence_checks |
| Attributed runbook guidance | runbook_context.matches in saved report |

The current API has pagination and an event-ID history filter, without a general server-side resource search or dedicated global runbook catalog endpoint. A working implementation must either add appropriate backend support or explicitly scope local filtering to loaded data. It must not imply that one loaded page represents all server data. Global Runbooks can browse guidance from saved reports with that scope labeled, or wait for a real catalog read endpoint. Do not add a new empty navigation destination to satisfy the mockup.

History selection must handle no report, multiple runs, and older report schemas without supplemental evidence or runbook_context. The preview shows the four known seeded events, one selected enriched report, and five workflow steps from the current implementation. Runtime counts and text must come from responses, not screenshot constants.

## Authentication and exceptional states
The development viewer JWT must remain a local development mechanism. Handle session expiration without repeatedly retrying a failing request, display an actionable unlock state, and never log or expose token contents. Production identity/login and public portfolio access remain separate unimplemented work.

Design and verify initial loading, empty inbox, no saved investigation, unavailable API, expired session, missing event, missing runbooks, unavailable collectors, provider fallback, stale data, and refresh-in-progress. Preserve existing visible data while refreshing where appropriate, with last-refresh time and failure state. Do not display reconnecting/live-stream claims without an implemented connection mechanism.

Keyboard acceptance includes event selection, search focus, navigation, tabs, command palette with real destinations/actions, Escape dismissal, and focus restoration. Commands are UI navigation/refresh, not infrastructure actions. Responsive implementation must be visually inspected on desktop and mobile, with contrast/focus checked in both themes before completion.

## Review checkpoint
The standing UI-REQUIREMENTS.md says: “Present the palette, typography, spacing, severity tokens, and representative layouts for user approval before writing frontend implementation.” These previews and tokens make that decision concrete. Request review of light/dark preference and layout before building the frontend application. After review, implement a working vertical slice against the existing read-only API and record its validation evidence.
