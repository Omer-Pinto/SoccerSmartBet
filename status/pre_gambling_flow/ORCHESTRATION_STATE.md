# Orchestration State

> Task status tracking for parallel droid work

---

## Batch 1: Research & Foundation

| Task | Status | PR | Notes |
|------|--------|-----|-------|
| 0.1 Football Research | ✅ COMPLETE | #2 | Complete |
| 0.2 LangSmith Setup | ✅ COMPLETE | #1 | Complete |
| 1.2 Config Management | ✅ COMPLETE | #3 | Complete |

---

## Batch 2: API Registration & Testing

| Task | Status | PR | Notes |
|------|--------|-----|-------|
| 0.3 API Key Registration | ✅ COMPLETE | - | User completed: 3 API keys registered |
| 0.4 API Integration Tests | ✅ COMPLETE | #10 | 24 passing tests across 4 APIs |

---

## Batch 3: Schema & Docker

| Task | Status | PR | Notes |
|------|--------|-----|-------|
| 1.1 DB Schema | ✅ COMPLETE | #4 | Complete (simplified to 5 tables) |
| 1.4 Docker Compose | ✅ COMPLETE | #5 | Complete |

---

## Batch 4: Core Architecture

| Task | Status | PR | Notes |
|------|--------|-----|-------|
| 1.3 State Definition | ✅ COMPLETE | #13 | state.py - Phase enum, GameContext, PreGamblingState |
| 2.3 Structured Outputs | ✅ COMPLETE | #14 | structured_outputs.py - LLM output schemas only |
| 2.4 Prompts | ✅ COMPLETE | #15 | prompts.py - 3 agent system messages |

---

## Batch 5: Tools Implementation ✅ COMPLETE

| Task | Status | PR | Notes |
|------|--------|-----|-------|
| 2.5.1 fetch_h2h | ✅ COMPLETE | #33, #36 | football-data.org |
| 2.5.2 fetch_venue | ✅ COMPLETE | #33, #36 | FotMob (mobfot) |
| 2.5.3 fetch_weather | ✅ COMPLETE | #33, #36 | FotMob + Open-Meteo |
| 2.5.4 fetch_odds | ✅ COMPLETE | #33, #36 | The Odds API |
| 2.5.5 fetch_form | ✅ COMPLETE | #33, #36 | FotMob (mobfot) |
| 2.5.6 fetch_injuries | ✅ COMPLETE | #33, #36 | FotMob (mobfot) |
| 2.5.7 fetch_league_position | ✅ COMPLETE | #36 | FotMob (mobfot) - replaces fetch_key_players_form |
| 2.5.8 calculate_recovery_time | ✅ COMPLETE | #33, #36 | FotMob (mobfot) |
| ~~2.5.9 fetch_suspensions~~ | ❌ CANCELLED | #26, #32 | API limitation - returns empty data |
| ~~2.5.10 fetch_returning_players~~ | ❌ CANCELLED | #29 | API limitation - cannot track status changes |

**Note:** Originally used apifootball.com (PR #33). Migrated to FotMob (PR #36) after trial expired.

---

## Batch 6: Main Flow Nodes

| Task | Status | PR | Notes |
|------|--------|-----|-------|
| 3.1 Pre-Gambling Trigger | ⏪ REVERTED | #39→#43 | Merged then reverted |
| 3.2 Smart Game Picker Node | ⏪ REVERTED | #40→#42 | Merged then reverted |
| 3.3 Fetch Lines from The Odds API | ❌ NOT STARTED | - | |
| 3.4 Persist Unfiltered Games | ❌ NOT STARTED | - | |
| 3.5 Combine Results to Reports | ❌ NOT STARTED | - | |
| 3.6 Persist Reports to DB | ❌ NOT STARTED | - | |
| 3.7 Send Gambling Trigger | ❌ NOT STARTED | - | |

**Batch Status:** REVERTED — PRs #39, #40 merged then reverted via #42, #43. Revival in progress on `revive` branch. See `docs/system_revive/` for new plan.

---

## Revival (2026-04-05)

Work continues on `revive` branch with new wave-based plan. See `docs/system_revive/progress.md` for current status.
