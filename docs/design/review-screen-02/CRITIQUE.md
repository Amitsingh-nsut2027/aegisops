# Screen two — five concrete critique fixes

Before implementation the user approved the run-history ASCII/data proposal. Before user review, the first running browser pass exposed these issues; corrected as follows.

1. **An explanatory footer looked like filler.** “One event. Separate runs.” used screen space to teach a concept rather than inspect data. Replaced it with a selected-run timing ledger: actual start/finish, synthetic source observation time, and elapsed workflow time. Missing source/report values remain explicit. Exact UTC rendering now preserves the recorded microsecond fraction.
2. **The inspector still looked incident-focused.** Its primary headline was the repeated resource name while the run ID was small metadata. Promoted the selected run identity to a monospace heading with a full-ID copy action; the original resource stays immediately below.
3. **Workflow strings were difficult to compare.** Every row repeated cpu-investigator-vN at micro-label size. Show compact v1/v2/v3 values at 13 px in the table, with the complete version retained in its title and always visible in the selected report metadata. Provider text stays a secondary datum.
4. **The two filters looked interchangeable.** The exact server event-ID field and loaded-page text filter had insufficient scope differentiation. Added “All saved runs · exact match” beside the event-ID label; the local filter retains its this-page label. Clear becomes enabled while typing, and editing removes obsolete validation errors.
5. **Narrow rows lost important outcome context.** At 390 px, hidden workflow/result columns meant a user had to open each run to discover its version or fallback. Added a compact mobile-only version/outcome line, with fallback shown when recorded, and adjusted touch-row height. No new outcome is inferred for older snapshots.

Initial captures: 01-initial-1280.png and 01-initial-390.png. After captures, keyboard/data-state verification, and final polish results are stored in this directory. No records or reports were altered for visual effect.
