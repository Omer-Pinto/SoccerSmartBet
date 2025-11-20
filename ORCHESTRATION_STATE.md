# Droid Orchestration State

> **Maintained by:** Main orchestrator Claude
> **Purpose:** Track parallel droid work across git worktrees for crash recovery and status visibility

---

## Current Batch: Not Started

**Batch Status:** Preparing Batch 1
**Last Updated:** 2025-11-20

---

## Active Worktrees

| Task | Droid | Worktree Path | Branch | Status | PR | Started | Notes |
|------|-------|---------------|--------|--------|-----|---------|-------|
| - | - | - | - | - | - | - | Batch 1 not started yet |

---

## Batch 1: Research & Foundation (Parallelizable)

**Dependencies:** None - all tasks can run in parallel

| Task ID | Task Name | Assigned Droid | Status | Branch | PR |
|---------|-----------|----------------|--------|--------|-----|
| 0.1 | Football Data Sources Research | FootballResearchDroid | Not Started | research/data-sources | - |
| 0.2 | LangSmith Integration Setup | InfraDroid | Not Started | infra/langsmith | - |
| 1.2 | Configuration Management | InfraDroid | Not Started | infra/config | - |

---

## Batch 2: Schema & Foundation (Depends on Batch 1)

**Dependencies:** 
- 1.1 depends on 0.1 (needs data source structure understanding)
- 1.4 depends on 1.1 (needs schema)

| Task ID | Task Name | Assigned Droid | Status | Branch | PR |
|---------|-----------|----------------|--------|--------|-----|
| 1.1 | PostgreSQL Schema Design | InfraDroid | Waiting | - | - |
| 1.4 | Docker Compose for Database | InfraDroid | Waiting | - | - |

---

## Completed Batches

None yet.

---

## Worktree Management

### Active Worktrees
```bash
# List active worktrees
git worktree list
```

### Cleanup Commands (when PRs merged)
```bash
# Remove worktree
git worktree remove ../SoccerSmartBet-{name}
git branch -d {branch-name}
```

---

## Recovery Instructions

If orchestrator session crashes:

1. Read this file to see active worktrees
2. Check git worktree list to verify they exist
3. For each "Working" task:
   - Check worktree for uncommitted changes
   - Check if PR exists
   - Resume monitoring or restart droid

---

## Notes

- Each droid works independently in their worktree
- Droids can modify any files (not directory-isolated)
- Conflicts resolved at PR merge time
- Only user approves merges to main
