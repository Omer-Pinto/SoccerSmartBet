# UI Bug Tracker — SoccerSmartBet Operator Dashboard

## Fixed

| ID | Description | Commit | Notes |
|----|-------------|--------|-------|
| U1 | AI bets editable | _REDESIGN_SHA_ | Merged-row redesign puts Edit button only on USER sub-row; AI sub-row gets an empty `<td class="col-edit--empty">` — no button, no cursor. |
| U2 | Locked-row edit form opens | _REDESIGN_SHA_ | Per-day lock model in `tickChips` disables ALL edit buttons when earliest kickoff ≤ 30 min away; `cancelEdit()` is also called on lock transition. |
| U_REDESIGN | Merged-row table redesign — Today, History, Team | _REDESIGN_SHA_ | Replaced flat per-bet rows with rowspan=2 game-groups across all three pages. 7-col Today, 5-col History/Team. USER always top, AI always bottom, separator row between groups. |
| U_CHROME | Ping banner + footer wave label removed | _REDESIGN_SHA_ | Deleted `masthead-accent` block and footer wave-label string from all 5 static pages (today, history, team, league, pnl). |
| U_STATS | Top-row stats redesign — USER/AI split tiles, flow timeline pill | _REDESIGN_SHA_ | Today status strip collapsed to single flow-timeline pill (Pre-Gambling → Gambling → Post-Games \| Last error). Attempt tile removed. History/Team show USER and AI aggregate tiles side-by-side. |
| F5 | Atlético team-stats 404 on accented/prefixed stored names | d5c7488 | Added `get_normalized_variants()` to team registry; replaced ILIKE pattern query with Python-side accent-folded matching. |

## Open

| ID | Description | Notes |
|----|-------------|-------|
| U3 | DSL autocomplete misfires on partial tokens | Out of scope for this pass. |
| U4 | DSL autocomplete — partial token suggestions | Out of scope for current dispatch. |
| U5 | Button widths inconsistent across viewport sizes | Out of scope. |
| U6 | Override/Regenerate actions should merge into single confirm flow | Out of scope. |
| U7 | P&L tooltip math off by one day | Out of scope. |
