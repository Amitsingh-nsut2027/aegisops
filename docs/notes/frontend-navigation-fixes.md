# Frontend interaction fixes — 2026-10-19

The user reported that the site was not working properly. The running local bridge and events/investigations endpoints returned HTTP 200; opening an actual saved report worked. The user's in-app browser was narrow enough to hide the desktop rail.

## Problems corrected

1. Below 768 px, the desktop rail disappeared without visible replacement destinations. Added a persistent, compact Incidents / Investigations navigation bar, including selected-page and focus states. Inspector height subtracts its 44 px height.
2. The skip link always targeted the incident table. It now targets the active table or narrow report, focuses it without changing the screen's routing hash, and has a matching label. The document title also follows the screen.
3. Global arrow shortcuts could change the selected event/run while the operator was reading a report. Up/down selection is now limited to a focused row or the page body; report panels retain ordinary keyboard scrolling. Modified shortcuts are not intercepted.
4. Report tabs and different selected runs reused the previous report's scroll offset. The inspector now has an explicit event/run/tab context: unchanged content retains its position, changed content starts at the top.
5. Investigation rerenders preserved only the inspector scroll. They now preserve the table and workspace scroll as well, so refreshing and editing a filter do not reset those panes. Entering history through navigation returns to its list, rather than an earlier narrow detail view.

## Verification

- Used the existing user-owned preview server; did not stop it or alter cloud resources.
- In the actual in-app browser: switched Incidents / Investigations, opened a saved report, viewed Evidence / Trace / Runbooks, returned to history, and confirmed the skip link focuses history-table while the hash stays #investigations.
- Pressing ArrowDown with the report panel focused retained the selected run. Changing tabs started the panel at scrollTop 0. A nonzero-to-zero scroll transition was not measured in this check.
- Inspected widths 390 / 768 / 1024 / 1280: document scrollWidth did not exceed viewport width. Restored the original browser viewport after checking.
- Browser error log was empty during the check. Both modified modules passed syntax checks. All six formatter unit checks passed. The full earlier browser fixture suites were not rerun for this fix.
- Current narrow-view capture: ../design/bugfix-navigation/verified.png.

## Interview explanation

Responsive design must preserve access to tasks, not merely fit content into a smaller width. Keyboard shortcuts must respect the focused control. Scroll restoration belongs to a specific content identity: retaining a position is useful for the same report, but confusing for a different run or tab.
