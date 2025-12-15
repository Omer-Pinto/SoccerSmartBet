# Smart AI Soccer Betting System

This project implements a **non-monetary, AI-assisted daily soccer game betting system**, built around four independent flows. The AI and user each place simulated bets on selected daily games, using rich real-time data and structured analysis. All logic runs in **Python 3.13**, powered by **LangGraph + LangGraphWrappers** (infrastructure) and follows the graph/style patterns demonstrated in **StocksMarketRecommender**.

This file gives a **high-level architectural overview** and defines guidelines and structure for code structure and generation.

---

## 1. System Architecture Overview

The system is organized around four main application flows, each responsible for a distinct stage of the daily 
soccer-betting lifecycle.
Refer to the architecture diagram as canonical. This md file must be read together with that visual:

![System Architecture Diagram](./resources/app_flows.png)

### Daily execution order and triggering
- **Pre-Gambling Flow** runs first each day on a fixed schedule (cron).  
  It selects the day’s games, fetches all required data, builds reports, and then triggers the next flow.

- **Gambling Flow** runs immediately after Pre-Gambling finishes.  
  It collects bets from both the user and the AI for the games of the day. It schedules the Post-Games Flow trigger for later.

- **Post-Games Flow** runs later, when all games for that day have completed.  
  Its trigger time is scheduled dynamically, e.g. *3 hours after the latest kickoff time*.

- **Offline Analysis Flow** runs on demand, any time a user requests statistics or insights from the UI.  
  It can execute multiple times per day and does not depend on the other flows.

---

## 2. Technology Stack (Concise)
- **Runtime:** Python **3.13**  
- **Graph engine:**  
  - **LangGraph** for orchestration  
  - **LangGraphWrappers** (my infra repo) for simplified, unified node/graph creation patterns  
- **Patterns Reference:**  
  - **StocksMarketRecommender** (my repo also) — demonstrates how to build multi-node, multi-toolgraphs using GraphManager, NodeActions, State, StructuredOutputs, ToolsSetup.
- **DB:** PostgreSQL or MySQL (TBD; relational expected).  
- **Frontend:** TBD (Telegram bot or app).  
- **Scraping / Data:** Prefer APIs when possible; fallback to scrapers. MCP integration may be used to sandbox scraping tasks.  
- **Parallelism:** Game-level and team-level subflows run in **parallel** using LangGraph subgraphs.

---

## 3. Purpose & Assumptions

**Goal:** Each day, pick meaningful games (main matches with minnimum lines above configurable threshold that allows substantial gain) , fetch structured data (game + team), produce AI-enriched reports, collect user & AI bets, compute P&L, and support offline analytics.

**Betting assumptions:**
1. Each game has **3 outcomes**: `'1'` = home win, `'x'` = draw, `'2'` = away win.  
2. Each game has **3 lines**: `n1`, `n2`, `n3` (float odds).  
3. Only **single bets per game** (no combos).  
4. Each day’s gambling is **per-game**, not tournaments.  
5. Both user & AI place **100 NIS** simulated stakes per game (win = stake × odds; loss = − stake).

---

## 4. Data Fetcher Logic (Pre-Gambling Flow)

The Pre-Gambling Flow contains **two extendible subflows**:

### A. Game Data Fetchers  
Fetch per-game information:
- Venue  
- Expected crowd  
- Atmosphere news  
- Weather (important: cancellations → `x`)  
- Head-to-head recent results  

### B. Team Data Fetchers  
Fetch for each team:
- Recent form (5 games)  
- Recovery time (days since last match)  
- Injury list  
- Suspension list  
- Returning players  
- Rotation/absence list (incl. coach)  
- Near-future match importance  
- Top players form (goals/assists/GA)  
- Team morale & coach stability  
- Preparation/training news  
- Any other relevant news

**Important:**  
- These subflows must be **modular & extendible**.  
- Some fetchers may return empty data; the system must tolerate partial information.  
- MCP tools *may* replace scrapers to reduce fragility.

---

## 5. Flow Overview (Short)

### 5.1 Pre-Gambling Flow
- Triggered daily.  
- Picks games, fetches lines, filters interesting matches.  
- Runs **game** and **team** subgraphs in parallel (configurable amount of games, min. 3, and 2 teams per game).  
- Combines + persists reports.  
- Triggers next flow.

### 5.2 Gambling Flow
- Fetches today's games and their reports from DB.  
- User places bet (UI/Bot).  
- AI places bet (ModelWrapper-driven agent).  
- Collector/verifier checks both arrived before deadline.  
- Either persist bets or cancel that day's run.  
- Schedules the Post-Games Flow trigger for later (e.g., several hours after the latest kickoff time). It does not directly start that flow.

### 5.3 Post-Games Flow
- Fetches results online.  
- Computes P&L for both sides.  
- Updates DB.  
- Sends summary to user.

### 5.4 Offline Analysis Flow
- On demand.  
- Queries DB for success rate, P&L slices, team/league stats.  
- AI generates additional insights/explanations.  
- Returns enhanced analytics to user.

---

## 6. Implementation References

- **LangGraphWrappers DSL:** See `external_projects/LangGraphWrappers.md` for the up-to-date overview of the wrapper layer (GraphWrapper, node/model/tool abstractions, MCP integration, and guidance on when to fall back to raw LangGraph/LangChain APIs).
- **StocksMarketRecommender Patterns:** See `external_projects/StocksMarketRecommender.md` for the reference flow architecture (graph managers, state/structured outputs, routers, subgraph orchestration) that SoccerSmartBet should mirror.

Both summaries supersede earlier high-level notes, so use them as the canonical references when designing new flows or extending infrastructure.

---

## 7. TBD Areas (Explicit)
- Full DB schema  
- Full tool/scraper API sourcing  
- Frontend (Telegram vs App)  
- Authentication, deployment, notifications  
- Exact HTML/JSON of returned reports  

Keep code modular so these can be swapped later.

---

## 8. Extensions (Future)
- New data fetchers added via adding nodes to game/team subflows.  
- New competitions, leagues, or analytic flows plug into the same structure.  
- Additional AI agents can be added easily by defining new ModelWrappers + NodeWrappers.

---
## 9. Git Workflow & Pull Request Best Practices

### 9.0 Standard Task Workflow - CRITICAL PROCESS

**Every task MUST follow this workflow:**

1. **Create worktree with dedicated branch:**
   ```bash
   git worktree add /path/to/SoccerSmartBet-task-description -b task-N.M/description
   cd /path/to/SoccerSmartBet-task-description
   ```
   Example: `batch-2/api-testing` for tasks 0.3 + 0.4

2. **Do the work:**
   - Make changes, create files, implement features
   - Commit frequently with clear messages
   - Test thoroughly

3. **Push to remote:**
   ```bash
   git push -u origin task-N.M/description
   ```
   - **NEVER** push directly to main
   - Push the feature branch only

4. **Open Pull Request:**
   ```bash
   gh pr create --base main --title "[Task N.M] Description" --body "..."
   ```
   - Use GitHub CLI or web UI
   - Write clear PR description with summary of changes
   - Reference relevant task numbers (e.g., Task 0.4)

5. **Get approval:**
   - Wait for human review
   - Address any PR comments (see section 9.3)
   - Push additional commits if needed (regular push, NO --force)

6. **Merge from GitHub (NOT locally):**
   ```bash
   gh pr merge <PR#> --squash --delete-branch
   ```
   - **CRITICAL:** Merge via GitHub UI or `gh pr merge` command
   - **NEVER** do `git merge` locally then push
   - This maintains proper PR history and audit trail

7. **Update local main and close worktree:**
   ```bash
   cd /path/to/SoccerSmartBet  # Main worktree
   git checkout main
   git pull origin main
   git worktree remove /path/to/SoccerSmartBet-task-description
   ```

8. **Update state tracking files:**
   - Update the **relevant flow's task file** to mark tasks complete
     - Currently: `PRE_GAMBLING_OPTIMIZED_FLOW_TASKS.md` (Pre-Gambling Flow)
     - Future flows will have their own task tracking files
   - Update `ORCHESTRATION_STATE.md` with PR number and status
   - Commit and push these updates to main

**Why this workflow matters:**
- ✅ Every change goes through PR review
- ✅ Full audit trail in GitHub
- ✅ Clean separation of work across tasks
- ✅ Easy to rollback if something breaks
- ✅ Proper co-authorship tracking with factory-droid

**Common mistakes to avoid:**
- ❌ Merging locally (`git merge task-N.M/description`) then pushing to main
- ❌ Working directly on main branch
- ❌ Forgetting to push branch before creating PR
- ❌ Closing worktree before merge completes

### 9.1 Git Hygiene - CRITICAL RULES

**NEVER do the following on shared PR branches:**
- ❌ **`git commit --amend`** - Rewrites history, breaks collaboration
- ❌ **`git push --force`** - Overwrites remote history, can lose others' work
- ❌ **`git rebase`** on pushed branches - Rewrites commit history
- ❌ **`git reset --hard`** followed by force push - Destructive

**Always do:**
- ✅ Create **new commits** for fixes and changes
- ✅ Use **regular push** (no --force)
- ✅ Keep full commit history visible
- ✅ Only amend/force-push on **personal branches before anyone has pulled**

**Why this matters:**
- Maintains audit trail of what changed and when
- Allows reviewers to see incremental fixes
- Prevents loss of work if others have pulled the branch
- Makes debugging easier with bisect/blame

### 9.2 Code Review Comment Protocol (Initial Review)

**When reviewing code and leaving initial comments:**

1. **ALWAYS use line-specific comments** - NOT general PR comments
   - Post comments on specific lines of code
   - Use GitHub API: `gh api /repos/{owner}/{repo}/pulls/{pr_number}/comments`
   - Required parameters: `commit_id`, `path`, `line`, `body`
   - Example:
     ```bash
     gh api --method POST \
       -H "Accept: application/vnd.github+json" \
       /repos/Omer-Pinto/SoccerSmartBet/pulls/22/comments \
       -f body="Function signature should accept match_id directly" \
       -f commit_id="abc123..." \
       -f path="src/tools/fetch_h2h.py" \
       -F line=19
     ```

2. **General PR comments ONLY for:**
   - Overall architecture concerns that apply to entire PR
   - Approval/rejection decisions
   - Comments that genuinely don't relate to specific code lines

3. **NEVER use `gh pr review --comment --body`** for code-specific issues
   - This creates general comments without line context
   - Reviewers/droids can't see WHAT code you're referring to
   - Makes it impossible to track which fixes address which comments
   - Forces reader to search through entire PR to find the issue

**Why line-specific comments are REQUIRED:**
- Reviewer sees exactly what line needs fixing (no guessing)
- Can click "View file" to see code context
- GitHub tracks resolution per-comment
- No ambiguity about what needs fixing
- AI agents can reliably fix issues (general comments cause them to guess wrong)
- Humans drowning in 300-line PRs need to know WHERE the issue is

**Getting commit SHA for line comments:**
```bash
gh pr view <PR#> --json commits --jq '.commits[-1].oid'
```

### 9.3 Pull Request Comment Protocol (Responding to Reviews)

**When responding to PR review comments:**

1. **Reply DIRECTLY to each comment thread** - Don't post a summary comment
   - Use GitHub's "Reply" button on each specific comment
   - Address the exact concern raised in that thread
   - Format: "✅ Fixed. [Brief description]. Commit: [short-sha]"

2. **Never post standalone summary comments** like:
   - ❌ "All comments addressed in commits X, Y, Z"
   - ❌ Large markdown table summarizing all fixes
   - These create clutter and don't help reviewers track individual threads

3. **Link fixes to specific commits:**
   - Each reply should mention the commit that addresses it
   - Example: "✅ Fixed. Moved file to docs/setup/. Commit: abc1234"
   - Helps reviewers verify the fix

4. **For multiple related comments:**
   - Still reply to each individually
   - You can reference related fixes: "✅ Fixed (also addresses comment above). Commit: abc1234"

5. **Droids MUST follow this protocol:**
   - When asked to "fix PR comments", droids must:
     1. Read ALL comment threads using \`gh api /repos/{owner}/{repo}/pulls/{pr}/comments\`
     2. Make code fixes and commit
     3. Reply to EACH comment individually using:
        \`\`\`bash
        gh api -X POST /repos/{owner}/{repo}/pulls/comments/{comment_id}/replies \\
          -f body="✅ Fixed. [description]. Commit: [sha]"
        \`\`\`
     4. NOT post a general issue comment summarizing fixes

### 9.4 Code Review Response Workflow

**Standard workflow for addressing PR feedback:**

1. **Read all comments first** - Don't start coding until you understand all requests
2. **Group related changes** - Make logical commits, not one commit per comment
3. **Commit with clear messages** - Reference what comments you're addressing
4. **Push changes** - Regular push, no force
5. **Reply to each comment thread** - As described in 9.3
6. **Request re-review** - Mark yourself as ready after all addressed

**Example good commit message:**
\`\`\`
[Fix PR #1] Consolidate to single .env at project root

- Addresses comments #2551043155, #2553097325
- Move from config/langsmith/.env to project root
- Update tests and documentation
\`\`\`

### 9.5 What NOT to Do (Lessons Learned)

**Real examples of bad practices:**
- ❌ Amending commits on a shared PR branch (loses history)
- ❌ Posting "✅ All comments addressed" as one big comment (reviewers can't track)
- ❌ Not replying to individual comment threads (reviewer has to hunt for fixes)
- ❌ Force-pushing after reviewer has looked at code (breaks their diff view)
- ❌ Writing "pip install X" in docs instead of adding to pyproject.toml
- ❌ Manual .env parsing instead of using standard libraries (python-dotenv)

**Result of bad practices:**
- Wasted ~30% of token budget on back-and-forth
- Multiple iterations to fix simple issues
- Frustration for both human and AI
- Messy git history that's hard to understand

### 9.6 Droid-Specific Instructions

**When a droid is asked to "fix PR comments":**

# Pseudocode for droid PR comment fixing workflow:
1. fetch_all_pr_comments(pr_number)
2. parse_comments_into_actionable_tasks()
3. make_code_fixes()
4. git_commit(message="[Fix PR #X] Description of fixes")
5. git_push()  # NEVER git push --force
6. for each comment in pr_comments:
       reply_to_comment_thread(
           comment_id=comment.id,
           body=f"✅ Fixed. {description}. Commit: {commit_sha}"
       )
7. resolve_all_comment_threads()  # Mark threads as resolved
8. NOT: post_general_summary_comment()  # DON'T DO THIS
\`\`\`

**Reply format - CRITICAL:**
- Keep replies **BRIEF**: 1-2 lines maximum
- Format: `"✅ Fixed. [what changed]. Commit: [sha]"`
- Example: `"✅ Fixed. Changed signature to accept match_id. Commit: 8236560"`
- **DO NOT** write paragraphs, tables, or verbose summaries
- **DO NOT** post general PR comments - only reply to specific line comment threads

**Resolving threads - CRITICAL:**
Before declaring work complete, droids MUST resolve all line-specific comment threads:
```bash
# Get thread IDs
gh api graphql -f query='query { repository(owner: "...", name: "...") { 
  pullRequest(number: X) { reviewThreads(first: 20) { nodes { id isResolved } } } } }'

# Resolve each thread
gh api graphql -f query='mutation { 
  resolveReviewThread(input: {threadId: "PRRT_..."}) { thread { isResolved } } }'
```

**Testing before pushing:**
- Run tests locally if possible
- Verify file paths are correct
- Check pyproject.toml syntax if modifying
- Ensure .env.example has no secrets

### 9.7 Git User Attribution for Droids

**CRITICAL: All droids MUST use git config overrides when committing.**

Every `git commit` command MUST be preceded by `-c` options to set proper user attribution:

**Required commit syntax:**
```bash
git -c user.name="omer-pinto-ai-agent" \
    -c user.email="moshon776@gmail.com" \
    commit -m "Your commit message"
```

**Why this is required:**
- Separates AI agent commits from human commits in git history
- Maintains proper attribution and audit trail
- Enables GitHub to track contributions correctly

**Examples:**

✅ **Correct:**
```bash
git -c user.name="omer-pinto-ai-agent" \
    -c user.email="moshon776@gmail.com" \
    commit -m "[Task 1.5] Implement new feature"
```

❌ **Wrong:**
```bash
git commit -m "Implement new feature"  # Uses wrong user from global config
```

**Notes:**
- The `-c` flag temporarily overrides git config for that single command
- This applies to ALL droids, not just the main agent
- Human commits use standard git workflow (no overrides needed)

### 9.8 Posting Inline PR Comments (Code Review)

**To post comments on specific lines in "Files Changed" tab:**

```bash
cat <<'EOF' | gh api repos/{owner}/{repo}/pulls/{pr}/reviews -X POST --input -
{
  "commit_id": "HEAD_SHA",
  "event": "COMMENT",
  "body": "Summary",
  "comments": [
    {"path":"src/file.py","position":LINE_NUM,"body":"Comment text"}
  ]
}
EOF
```

**Key:** Use `position` (NOT `line`). For new files, `position` = line number.

