# AegisOps — design contract

Status: the user approved the incident workbench and, separately, the investigation-history screen on 2026-10-19. Both are implemented locally; see docs/notes/frontend-workbench.md, docs/notes/frontend-investigations.md, and their separate review evidence. Approval covers those screens and their inspector states; later screens still need separate approval. This contract supersedes the earlier green-rail/warm-white previews in docs/design. Do not weaken the user's requirements into optional styling advice.

## Intent
A dense incident workbench with the operational clarity of Linear, Vercel, Honeycomb, Grafana, Raycast, and a terminal. Use those as reference qualities, without copying a product's branding. The central task is inspecting evidence and investigation history, not admiring a landing page. Visual quality must be demonstrated through deliberate design and functional behavior; appearance cannot establish who authored software.

## Type — two families, fixed roles
- Space Grotesk: headings, navigation, labels, and explanatory prose. Weights 400/500/600. Characterful letterforms without sacrificing compact headings.
- IBM Plex Mono: every data value, ID, ARN, log entry, timestamp, numeric label, shortcut, and table datum. Weights 400/500. Use tabular lining numerals; never align numbers with spaces in proportional text.
- Fixed scale: 11 / 12 / 13 / 15 / 20 / 28 px. 11 is reserved for compact metadata, never primary body text. Body prose is 15/22; data rows 13/20; labels 12/16; section headings 20/26; page heading 28/34. Headings use restrained negative tracking; data uses normal tracking.
- Bundle licensed font files locally during implementation, retain license files, and verify actual loaded faces. Generic fallbacks are for load failure only, not the intended appearance. Font sources: [Space Grotesk author repository](https://github.com/floriankarsten/space-grotesk) and [IBM Plex Mono](https://github.com/IBM/plex/tree/master/packages/plex-mono). Both projects provide open font license information in their repositories; preserve it when bundling.

## Color — near-black default, one accent
Commit to the dark workbench for screen one. A light theme is deferred until its own token and state audit; the old light preview is not the new specification.

The following CSS variables are the implementation contract, recorded here before any screen code:

```css
:root {
  --canvas: #111313;
  --surface: #191c1b;
  --surface-raised: #222724;
  --text: #e6e7e3;
  --text-secondary: #a5aaa5;
  --text-muted: #8e958f;
  --hairline: #353c37;
  --control-border: #748077;
  --accent: #d7f65b;
  --on-accent: #111313;
  --sev1-text: #ffa8a8;
  --sev1-bg: #2a181a;
  --sev2-text: #ffcb82;
  --sev2-bg: #2b2216;
  --sev3-text: #e6de9b;
  --sev3-bg: #282719;
  --sev4-text: #a9cce5;
  --sev4-bg: #1b252d;
  --radius-row: 0;
  --radius-control: 2px;
  --radius-dialog: 4px;
  --space-unit: 4px;
  --motion-fast: 120ms;
  --motion-standard: 160ms;
  --motion-slow: 200ms;
  --motion-ease: cubic-bezier(0, 0, 0.2, 1);
}
```

Lime is the sole sharp non-severity accent: selected row marker, primary action, focus, and active navigation. Chart series use neutral strokes; the selected datum may use lime. No additional decorative accent colors. Statuses such as needs_evidence, unavailable, fallback, and awaiting approval use neutral labels and explicit text; they must not borrow severity hues.

Severity scale, exclusively for severity: SEV1 critical impact, SEV2 major impact, SEV3 degraded impact, SEV4 low impact. These describe a future assessed impact classification. Current CPU events contain source severity warning, without assessed impact; display Untriaged in the SEV column and preserve warning as source metadata. Never silently convert a CPU threshold into a SEV level or add severe incidents just to exercise colors. Fixture-only severity examples, if later needed for QA, must be labeled and kept separate from API records.

### Contrast verification
Computed sRGB contrast is recorded in docs/design/contrast-audit.json. All 19 checked pairs pass: primary/secondary/muted/accent text on three neutral surfaces meets 4.5:1; four severity text/background pairs meet 4.5:1; control boundaries on all three surfaces meet 3:1. Examples: primary/canvas 15.01:1, secondary/canvas 7.90:1, muted/surface 5.60:1, accent/canvas 15.29:1. Hairlines are decorative separators, not the sole indication of an interactive control or chart datum. Use control-border or visible text/focus for required affordances. This is token-level verification, not a claim that an unbuilt screen passes WCAG AA; rendered states and keyboard behavior must also be audited.

## Shape, density, and hierarchy
Use asymmetric panes on a 4 px spacing grid. This does not mean uniform padding: 4 px within tightly related data, 8 px between labels and values, 12 px within inspector sections, 16 px between subsections, and 24/32 px between major groups. Table rows are 36 px on desktop; touch rows reach 44 px. Controls use 2 px corners, dialogs 4 px, table selections square. No shadows, blur, glowing edges, or bouncy interactions. Elevation uses a border and one neutral background shift.

Primary structures are tables, split panes, timelines, and source excerpts. No icon-circle card grids. Icons appear only when they clarify an action such as copying or expanding; every icon-only control needs an accessible label. Prefer text navigation to decorative glyphs. No rounded-2xl/default component-library theme or untouched demo components.

## First screen — incident workbench, approval required
Data: saved GET /events rows and selected event, GET /investigations filtered by event_id, selected run payload. No live AWS claims. No root-cause, agent-count, or recovery metrics are invented. Multiple runs are selectable; older/no-report payloads get explicit states.

```text
1280+ px
┌──────┬──────────────────────────────────────────┬──────────────────────────┐
│ AO   │ INCIDENTS                 / filter  ⌘K  │ api-service    copy ID   │
│      │ LOCAL · SIMULATION                       │ Untriaged · warning src │
│ INC  ├────────┬────────────────┬────────┬────────┤                          │
│ RUN  │ SEV    │ RESOURCE       │ TIME   │ STATE  │ CPU trigger              │
│ DOC  ├────────┼────────────────┼────────┼────────┤ 91 / 92 / 93%            │
│      │ —      │ api-service    │ … ago  │ needs… │ >90% · 3 samples         │
│      │ —      │ api-service    │ … ago  │ needs… │ [source + exact time]    │
│      │ —      │ api-service    │ … ago  │ no run │                          │
│      │        │                │        │        │ Run: [select saved run]  │
│      │ table body scrolls                       │ Evidence | Trace | Docs  │
│      │ sticky column headings                  │                          │
│      │                                       │ [scoped evidence rows]   │
│      │                                       │ [5-step trace]           │
│      │                                       │ [revisioned runbooks]    │
├──────┼──────────────────────────────────────────┼──────────────────────────┤
│      │ page controls · last refresh / exact time│ fake-v2 · no model call  │
└──────┴──────────────────────────────────────────┴──────────────────────────┘
       rail 56px       flexible main pane         inspector 400–480px
                         ← keyboard/resizable separator →
```

Rows show actual source event resource identifiers. If display names repeat, include scenario and shortened event ID as secondary data to distinguish them. Do not claim every row has an investigation; fetch/derive its actual saved-run state. No decorative statistics header.

At 1024 px keep the inspector only if readable minimum widths fit; otherwise open detail separately. At 768 px show a full-width list and inspector drawer/detail view. At 390 px use list → full-page incident detail with a back action, stacked evidence, and no clipped table columns. Show exact timestamps via both hover and keyboard/touch activation. Absolute synthetic observation dates remain visible; relative values such as 291d ago are calculated, never hardcoded.

## Functional interaction commitments
- Cmd/Ctrl+K opens a command palette with real navigation/refresh/copy actions. Escape closes it and restores focus. Slash focuses filter when focus is not in a text input. j/k or arrows move the active row; Enter opens its detail; shortcuts do not hijack text editing.
- Visible 2 px lime focus outline with offset. Accessible tabs, live regions for meaningful status, and labeled keyboard-operable resize separators. Separators support arrows and a reset action, with minimum widths and persisted pane preferences.
- Copy IDs, resource identifiers, ARNs where actually present, and full timestamps. Announce Copied or Copy failed without exposing credentials. Never manufacture ARNs for existing simulated/ecs events.
- Sticky table headers, explicit pagination, clear loaded-data versus global filter scope. The API lacks general search: add appropriate support or label filtering as this page; do not imply cross-dataset results from a loaded slice.
- Skeletons match actual table rows and inspector fields. Designed empty inbox, no saved run, expired token, unavailable API, stale data, missing runbooks, unavailable evidence, and provider fallback states. No welcome slogans or generic empty illustrations.
- No nonfunctional navigation destinations. Existing runbook guidance comes from saved report snapshots, not a global catalog endpoint. Implement required reads or clearly constrain the view to its data source.

## Motion and live state
Functional transitions only: 120–200 ms ease-out. New incident rows may translate 4 px and fade into place only when genuinely inserted, without jumping a user's active selection. Streaming step cursor and a pulsing live dot are allowed only after actual streaming/live delivery is implemented. The present snapshot API uses refresh; no fake stream, artificial typewriter, or simulated agent activity. Respect prefers-reduced-motion by removing movement and nonessential fades/pulses while preserving status text.

## Voice and realistic data
Terse operational copy: Needs evidence, No saved run, Source unavailable, Session expired, Retry, Copy ID. Phrases such as Awaiting approval or Rollback available appear only when those capabilities/states actually exist. No Welcome back, supercharge, seamlessly, unlock, Lorem ipsum, or Service A.

Use actual saved simulation data first. Future QA scenarios may use real AWS service names (ECS, ALB, CloudWatch) and syntactically plausible synthetic ARNs with reserved example account IDs, varied deterministic timestamps, and messy structured log lines. Every such record must be marked simulated, validated, and attributed. Current rounded values belong to explicitly scripted fixtures; do not silently alter evidence values to make them look measured. Never present seeded activity as live telemetry, use the user's real account identifiers as decoration, or invent performance claims.

## Mandatory per-screen process
1. Describe the layout in ASCII and list its data and states.
2. Wait for the user's explicit approval of that screen before screen code. A broad earlier approval does not approve later unreviewed screens. The wireframe above was approved for screen one; it does not approve another screen.
3. Build the approved slice with functioning controls and inspect rendered output.
4. Write a self-critique naming five specific elements that still look generic or careless, then fix all five before asking the user to review. Record before/after evidence. Do not claim problems were fixed without a visible implementation change; record unresolved issues honestly.
5. Verify core keyboard/operator tasks and exceptional states. Code completion alone is not UI completion.

## Dedicated final polish gate
Perform separate alignment, spacing, and contrast audits. Check hover/focus/active/disabled states for every control and loading/empty/error cases. Review 1280, 1024, 768, and 390 px renders, with no horizontal clipping or unusable controls. Confirm actual font loading, numeric alignment, severity semantics, pane resizing, scroll/sticky behavior, reduced motion, copy feedback, exact-time access, and command palette focus restoration. Keep the user-facing polish review separate from adding new features.

## Current implementation boundary
The two approved screens are implemented against the local read-only API, each with its own five-item critique/fixes, four-width browser review, and dedicated polish audit. Current captures live in docs/design/review/ and docs/design/review-screen-02/. Earlier static desktop/mobile PNGs in docs/design/ remain superseded artifacts. Production identity, public deployment, later screens, and cloud spending/sandbox checks remain outstanding.
