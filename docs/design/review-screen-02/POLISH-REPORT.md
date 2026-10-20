# Screen-two polish evidence

Scope: the approved investigation-history screen and its saved-report inspector states. Critique before user review is in CRITIQUE.md with five concrete fixes. Dedicated final review checked:

- Alignment: page heading, local toolbar and exact-event filter share the same left anchor.
- Density/shape: square table rows, compact version values, small-radius controls, hairline separators, and differentiated 4 px-based spacing.
- Fonts/data: locally bundled Space Grotesk and IBM Plex Mono; run IDs, timestamps, source paths and numeric timing use monospace/tabular numerals.
- Contrast: 121 sampled rendered text pairs passed 4.5:1. This is not full WCAG conformance or a screen-reader audit.
- Controls: sampled hover/active states and visible 2 px keyboard focus, disabled pagination, form validation, independent copy actions, source timestamps and tab focus.
- Responsive: desktop split view at 1280; list/detail navigation at 1024/768/390 with no document overflow. Mobile rows retain version/outcome context.
- Data semantics: exact saved run/source reads, microsecond UTC display, explicit elapsed-workflow labeling, no inference of absent legacy fields, and no borrowing newer evidence/runbooks.
- Failure states: session expired, empty journal/filter, API unavailable, stale retained history, missing run/source, legacy absent metadata and selected-report loading.
- Motion/access: no simulated live activity; existing reduced-motion/focus conventions remain shared.

Machine evidence: browser-checks.json and polish-audit.json. Before captures: 01-initial-1280.png and 01-initial-390.png. Final populated capture: 02-final-1280.png; narrow layouts: 06-list-* and 07-detail-*. Additional files record old snapshots, guidance, filter-empty and exceptional states. These are actual browser renders, not generated mockups.

The existing incident workbench browser regression passed after navigation/shared-rendering changes. Browser-only pagination/error fixtures did not mutate PostgreSQL. The local-only viewer bridge and API permissions were not expanded. Startup remains python3 scripts/start_workbench.py; new screen URL ends in /#investigations.
