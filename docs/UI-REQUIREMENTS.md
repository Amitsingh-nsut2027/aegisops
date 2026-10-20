# AegisOps AI frontend quality requirements

## Binding design contract — updated 2026-10-19
The user's latest detailed direction supersedes the earlier visual proposals. [DESIGN.md](../DESIGN.md) is the canonical contract: Space Grotesk + IBM Plex Mono, fixed 11/12/13/15/20/28 scale, near-black neutrals, one lime accent, severity-only SEV1–SEV4 tokens, 2–4 px controls, square dense tables, asymmetric rail/main/inspector panes, and functional motion only.

Before **each screen**, provide an ASCII wireframe and its data, then wait for the user's approval. Before user review of a built screen, list five specific generic/careless design problems and fix them. Final polish is a dedicated phase with alignment/spacing/contrast audits, every control state, loading/empty/error states, and renders at 1280/1024/768/390 px.

Explicit bans: gradients, glow, glassmorphism, blurred blobs, default component-library styling, rounded-2xl/shadowed card grids, decorative emoji/icons, Inter/Roboto/system-only typography, hero layouts, marketing filler, invented metrics, and uniform spacing/radii. Include real command-palette actions, visible focus, matched skeletons, deliberate exceptional states, relative plus accessible exact timestamps, ID/ARN copying where present, resizable panes, and sticky table headers.

Use realistic service names, source identifiers, varied deterministic timestamps, and messy logs in explicitly labeled simulation fixtures. Preserve actual saved evidence; do not disguise fixtures as live AWS or fabricate ARNs for existing records. Current source severity warning is not an assessed SEV classification. Existing draft PNGs are superseded and unapproved.

## User priority
The user explicitly requires the best frontend we can deliver: a polished, distinctive SRE product suitable for their resume, without a generic AI-generated or vibe-coded appearance. This is a standing project requirement, reaffirmed on 2026-10-17.

## Design and review process
- Present the palette, typography, spacing, severity tokens, and representative layouts for user approval before writing frontend implementation.
- Design around operator tasks and realistic incident data.
- Inspect rendered desktop and mobile layouts and refine them before declaring completion.
- Judge quality through visible design and working interactions; do not claim that AI authorship can be objectively detected or ruled out by appearance.

## Visual acceptance criteria
- Consistent typography, alignment, spacing, and information hierarchy.
- Restrained dark and light themes with accessible semantic severity colors.
- Dense, readable tables and charts with useful labels, units, and time windows.
- No purple-to-blue gradients, emoji icons, oversized hero sections, excessive rounded cards or shadows, placeholder copy, or untouched component-library demo styling.
- Deliberate responsive layouts rather than merely shrinking desktop panels.

## Interaction acceptance criteria
- Working navigation, filters, command palette, and keyboard interactions.
- Complete loading, empty, error, reconnecting, and stale-data states.
- Accessible focus indicators, labels, contrast, and keyboard navigation.
- Investigation timeline with evidence, tool calls, citations, confidence context, risk, and approval confirmation.
- Explicit simulation labeling; seeded/demo activity must not masquerade as live AWS telemetry.
- No decorative controls that appear functional but do nothing.

## Completion evidence
Review representative populated and exceptional states, desktop and mobile screenshots, keyboard behavior, and core operator workflows. Record unresolved defects rather than hiding them behind polished screenshots.
