/**
 * SoccerSmartBet — Today Tab JS
 *
 * Responsibilities:
 *  - Poll /api/status/today every 2500ms
 *  - Update flow-timeline pill in status strip (Pre-Gambling → Gambling → Post-Games | Last error)
 *  - Lock/unlock control buttons based on flow status
 *  - Force Override two-phase UX
 *  - Fetch today's matches from /api/today/data and render merged-row table
 *  - Inline bet editing (USER sub-row only)
 *  - Per-day lock: ALL Edit buttons disable when earliest kickoff ≤ 30 min away
 *  - Countdown chips (1s tick) per game, colour independent of lock state
 *  - Calendar filter (client-side slice of already-fetched data)
 *  - Paging: 25/50/100, hide bar when single page
 *  - P&L sparkline from /api/today/pnl
 */

"use strict";

// ─────────────────────────────────────────────
// Constants
// ─────────────────────────────────────────────

const POLL_MS = 2500;
const RUNNING_STATUSES = new Set([
  "pre_gambling_running",
  "gambling_running",
  "post_games_running",
]);
const LOCK_MINUTES = 30;

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────

let _status = null;
let _allBets = [];      // all bets from /api/today/data (raw, unfiltered)
let _groups = [];       // game-groups after grouping + calendar filtering
let _bankroll = null;

let _overrideArmed = false;
let _overrideTimer = null;
let _countdown = 5;

// Paging
let _pageSize = 25;
let _currentPage = 1;

// Calendar
let _calFrom = "";
let _calTo   = "";

let _debounceTimer = null;

// Stale-data notice (Fix A)
let _staleNoticeShown = false;

// Idle-cancel timer (Fix A) — tracks the 5-minute auto-cancel per open edit row
let _idleTimer = null;
const IDLE_CANCEL_MS = 5 * 60 * 1000;

// ─────────────────────────────────────────────
// DOM refs
// ─────────────────────────────────────────────

let els = {};

function initRefs() {
  els = {
    // status strip
    flowTimeline:   document.getElementById("flow-timeline"),
    statusError:    document.getElementById("status-error"),

    // buttons
    btnPreGambling: document.getElementById("btn-pre-gambling"),
    btnPostGames:   document.getElementById("btn-post-games"),
    btnOverride:    document.getElementById("btn-override"),

    // matches
    tbodyMatches:   document.getElementById("tbody-matches"),
    modRibbon:      document.getElementById("mod-ribbon"),

    // paging
    pagingToday:    document.getElementById("paging-today"),
    pageSummary:    document.getElementById("paging-summary-today"),
    pageInfo:       document.getElementById("today-page-info"),
    btnFirst:       document.getElementById("today-first"),
    btnPrev:        document.getElementById("today-prev"),
    btnNext:        document.getElementById("today-next"),
    btnLast:        document.getElementById("today-last"),
    pageSizeSelect: document.getElementById("today-page-size"),

    // calendar
    calFrom:        document.getElementById("cal-from"),
    calTo:          document.getElementById("cal-to"),

    // bankroll
    userBalance:    document.getElementById("bankroll-user"),
    userDelta:      document.getElementById("bankroll-user-delta"),
    aiBalance:      document.getElementById("bankroll-ai"),
    aiDelta:        document.getElementById("bankroll-ai-delta"),
    todayPnlUser:   document.getElementById("today-pnl-user"),
    todayPnlAi:     document.getElementById("today-pnl-ai"),

    // sparkline
    sparklineSvg:   document.getElementById("sparkline-svg"),
    xLabels:        document.getElementById("x-labels"),

    // modal
    modalBackdrop:  document.getElementById("modal-backdrop"),
    modalDateInput: document.getElementById("modal-date-input"),
    modalConfirmBtn:document.getElementById("modal-confirm"),
    modalCancelBtn: document.getElementById("modal-cancel"),

    // date display
    mastheadDate:   document.getElementById("masthead-date"),

    // stale-data notice (Fix A) — created once here, inserted above the table
    staleNotice:    (function() {
      let el = document.getElementById("stale-data-notice");
      if (!el) {
        el = document.createElement("div");
        el.id = "stale-data-notice";
        el.className = "stale-data-notice";
        el.setAttribute("role", "status");
        el.setAttribute("aria-live", "polite");
        el.textContent = "";          // Fix iter-18: start empty so first mutation is announced
        el.style.display = "none";
        const tableSection = document.querySelector(".matches-section");
        if (tableSection) tableSection.insertBefore(el, tableSection.firstChild);
      }
      return el;
    })(),
  };
}

// ─────────────────────────────────────────────
// Polling loop
// ─────────────────────────────────────────────

async function poll() {
  try {
    const resp = await fetch("/api/status/today");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    _status = await resp.json();
    updateFlowTimeline(_status);
    updateButtons(_status);
  } catch (e) {
    console.warn("poll /api/status/today failed:", e);
  }
}

async function fetchMatchData() {
  try {
    const resp = await fetch("/api/today/data");
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    // MEDIUM-3: clear any persisted error markup before assigning new data
    for (const el of [els.userBalance, els.aiBalance]) {
      if (el && el.querySelector(".bankroll-unavailable")) {
        el.className = "bankroll-amount neutral";
        el.innerHTML = `<span class="bankroll-currency">NIS</span>—`;
      }
    }
    const data = await resp.json();
    _allBets = data.bets || [];
    _bankroll = data.bankroll || null;
    applyFilterAndRender();
    renderBankroll();
    renderScoreboard();
    updateModRibbon();
  } catch (e) {
    console.warn("fetchMatchData failed:", e);
    // MEDIUM-5: surface error inline instead of silent placeholder
    _showBankrollError();
  }
}

function _showBankrollError() {
  const retryBtn = `<button type="button" class="bankroll-retry-btn" onclick="fetchMatchData()">Retry</button>`;
  for (const el of [els.userBalance, els.aiBalance]) {
    if (!el) continue;
    el.className = "bankroll-amount neutral";
    el.innerHTML = `<span class="bankroll-unavailable">Bankroll unavailable ${retryBtn}</span>`;
  }
}

async function fetchPnlHistory() {
  try {
    const resp = await fetch("/api/today/pnl");
    if (!resp.ok) return;
    const data = await resp.json();
    renderSparkline(data.history || []);
  } catch (e) {
    console.warn("fetchPnlHistory failed:", e);
  }
}

// ─────────────────────────────────────────────
// Today's Scoreboard
// ─────────────────────────────────────────────

function renderScoreboard() {
  const loadingEl = document.getElementById("scoreboard-loading");
  const contentEl = document.getElementById("scoreboard-content");
  if (!contentEl) return;

  // Count games that have finished today (pnl is non-null, result set)
  const finishedBets = _allBets.filter(b => b.pnl !== null && b.result !== null);
  // Unique finished games (by game_id)
  const finishedGameIds = new Set(finishedBets.map(b => b.game_id));
  const gamesFinished = finishedGameIds.size;

  // P&L per bettor today
  const pnlByBettor = { user: 0, ai: 0 };
  const winsByBettor = { user: 0, ai: 0 };
  const lossesByBettor = { user: 0, ai: 0 };

  finishedBets.forEach(b => {
    const who = b.bettor;
    if (who !== "user" && who !== "ai") return;
    pnlByBettor[who] += b.pnl || 0;
    if (b.pnl > 0) winsByBettor[who]++;
    else if (b.pnl < 0) lossesByBettor[who]++;
  });

  const fmtMoney = (v) => {
    const sign = v > 0 ? "+" : v < 0 ? "" : "";
    return `User: ${sign}${parseFloat(v).toFixed(0)} NIS`;
  };
  const fmtMoneyAI = (v) => {
    const sign = v > 0 ? "+" : v < 0 ? "" : "";
    return `AI: ${sign}${parseFloat(v).toFixed(0)} NIS`;
  };

  // Update DOM
  const sbGames = document.getElementById("sb-games-finished");
  if (sbGames) sbGames.textContent = gamesFinished;

  const sbUserMoney = document.getElementById("sb-user-money");
  if (sbUserMoney) {
    const v = pnlByBettor.user;
    const sign = v > 0 ? "+" : "";
    sbUserMoney.textContent = `User: ${sign}${v.toFixed(0)} NIS`;
    sbUserMoney.style.color = v > 0 ? "var(--emerald)" : v < 0 ? "var(--vermilion)" : "rgba(255,255,255,0.7)";
  }

  const sbAiMoney = document.getElementById("sb-ai-money");
  if (sbAiMoney) {
    const v = pnlByBettor.ai;
    const sign = v > 0 ? "+" : "";
    sbAiMoney.textContent = `AI: ${sign}${v.toFixed(0)} NIS`;
    sbAiMoney.style.color = v > 0 ? "var(--emerald)" : v < 0 ? "var(--vermilion)" : "rgba(255,255,255,0.7)";
  }

  const sbUserRecord = document.getElementById("sb-user-record");
  if (sbUserRecord) sbUserRecord.textContent = `User: ${winsByBettor.user}W / ${lossesByBettor.user}L`;

  const sbAiRecord = document.getElementById("sb-ai-record");
  if (sbAiRecord) sbAiRecord.textContent = `AI: ${winsByBettor.ai}W / ${lossesByBettor.ai}L`;

  // Trophy — show next to whoever leads by money (only if there's a clear winner)
  const leaderRow = document.getElementById("sb-leader-row");
  const leaderLabel = document.getElementById("sb-leader-label");
  if (leaderRow && leaderLabel && gamesFinished > 0) {
    if (pnlByBettor.user > pnlByBettor.ai) {
      leaderLabel.textContent = "User leads today";
      leaderRow.style.display = "flex";
    } else if (pnlByBettor.ai > pnlByBettor.user) {
      leaderLabel.textContent = "AI leads today";
      leaderRow.style.display = "flex";
    } else {
      leaderRow.style.display = "none";
    }
  } else if (leaderRow) {
    leaderRow.style.display = "none";
  }

  if (loadingEl) loadingEl.style.display = "none";
  contentEl.style.display = "flex";
}

// ─────────────────────────────────────────────
// Flow timeline pill
// ─────────────────────────────────────────────

function fmtPhaseTime(isoStr) {
  if (!isoStr) return "&mdash;";
  const t = isoStr.slice(11, 16);
  return t || "&mdash;";
}

function updateFlowTimeline(s) {
  if (!els.flowTimeline) return;

  const preT  = fmtPhaseTime(s.pre_gambling_completed_at  || s.pre_gambling_started_at);
  const gamT  = fmtPhaseTime(s.gambling_completed_at);
  const postT = fmtPhaseTime(s.post_games_completed_at    || s.post_games_trigger_at);

  const preHtml  = s.pre_gambling_completed_at
    ? `<span class="check">Pre-Gambling</span> ${s.pre_gambling_completed_at.slice(11, 16)}`
    : s.pre_gambling_started_at
      ? `<span class="clock">Pre-Gambling</span> Running`
      : `<span class="sub">Pre-Gambling</span> &mdash;`;

  const gamHtml  = s.gambling_completed_at
    ? `<span class="check">Gambling</span> ${s.gambling_completed_at.slice(11, 16)}`
    : `<span class="sub">Gambling</span> &mdash;`;

  const postHtml = s.post_games_completed_at
    ? `<span class="check">Post-Games</span> ${s.post_games_completed_at.slice(11, 16)}`
    : s.post_games_trigger_at
      ? `<span class="sub">Post-Games</span> ${s.post_games_trigger_at.slice(11, 16)}`
      : `<span class="sub">Post-Games</span> &mdash;`;

  els.flowTimeline.innerHTML =
    `${preHtml} <span class="flow-arrow">&#8594;</span> ${gamHtml} <span class="flow-arrow">&#8594;</span> ${postHtml}`;

  // Last error
  if (els.statusError) {
    if (s.status === "failed" && s.last_error) {
      const truncated = s.last_error.slice(0, 60) + (s.last_error.length > 60 ? "…" : "");
      els.statusError.innerHTML = `<span class="err">${escHtml(truncated)}</span>`;
    } else if (s.last_error) {
      const truncated = s.last_error.slice(0, 60) + (s.last_error.length > 60 ? "…" : "");
      els.statusError.innerHTML = `<span class="sub">${escHtml(truncated)}</span>`;
    } else {
      els.statusError.innerHTML = `<span class="sub">None</span>`;
    }
  }
}

// ─────────────────────────────────────────────
// Button lock / unlock
// ─────────────────────────────────────────────

function updateButtons(s) {
  const anyRunning = RUNNING_STATUSES.has(s.status);
  const st = s.status;

  setBtnEnabled(
    els.btnPreGambling,
    !anyRunning && (st === "idle" || st === "failed"),
    anyRunning ? "Flow in progress" : null,
  );

  const pendingPostGamesDate = s.pending_post_games_date;
  setBtnEnabled(
    els.btnPostGames,
    !anyRunning && !!pendingPostGamesDate,
    anyRunning ? "Flow in progress"
      : !pendingPostGamesDate ? "No pending post-games run"
      : `Will run post-games for ${pendingPostGamesDate}`,
  );

  // Override Pre-Gambling: enabled only after pre-gambling has completed (or later stage / failed),
  // and when nothing is currently running.
  const overrideAllowed = !anyRunning && (
    st === "pre_gambling_done" ||
    st === "gambling_done" ||
    st === "post_games_done" ||
    st === "failed"
  );
  if (anyRunning) {
    disarmOverride();
    setBtnEnabled(els.btnOverride, false, "Flow in progress");
  } else if (!overrideAllowed) {
    disarmOverride();
    setBtnEnabled(els.btnOverride, false, "No pre-gambling run yet today");
  } else {
    setBtnEnabled(els.btnOverride, true, null);
  }
}

function setBtnEnabled(btn, enabled, title) {
  if (!btn) return;
  btn.disabled = !enabled;
  if (title) {
    btn.title = title;
  } else {
    btn.removeAttribute("title");
  }
}

// ─────────────────────────────────────────────
// Control button click handlers
// ─────────────────────────────────────────────

async function triggerRun(flowType, force = false) {
  const runDate = (flowType === "post_games" && _status?.pending_post_games_date)
    ? _status.pending_post_games_date
    : todayISO();
  const btn = {
    pre_gambling: els.btnPreGambling,
    post_games:   els.btnPostGames,
  }[flowType];

  if (btn) {
    // Guard: ignore re-clicks while the queued state is active
    if (btn.dataset.queued === "1") return;
    btn.dataset.queued = "1";
    btn.disabled = true;
    btn.classList.add("btn-queued");
    btn.innerHTML = `Queued<span class="loading-dots btn-queued-dots"><span></span><span></span><span></span></span>`;
    setTimeout(() => {
      // Restore from the label cached at boot, not from live textContent
      btn.textContent = btn.dataset.label || btn.textContent;
      btn.classList.remove("btn-queued");
      delete btn.dataset.queued;
    }, 8000);
  }

  try {
    const resp = await fetch("/api/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ run_date: runDate, flow_type: flowType, force }),
    });
    if (resp.status === 409) {
      const err = await resp.json();
      alert(`Flow conflict: ${err.detail?.current_status || "already running"}`);
    } else if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      alert("Error: " + (err.detail?.message || err.detail || `HTTP ${resp.status}`));
    }
  } catch (e) {
    alert("Network error: " + e.message);
  }

  await poll();
  await fetchMatchData();
}

// ─────────────────────────────────────────────
// Force Override two-phase UX
// ─────────────────────────────────────────────

function armOverride() {
  if (_overrideArmed) return;
  _overrideArmed = true;
  _countdown = 5;
  els.btnOverride.classList.add("armed");
  els.btnOverride.textContent = `ARMED — confirm (${_countdown}s)`;

  _overrideTimer = setInterval(() => {
    _countdown--;
    if (_countdown <= 0) {
      disarmOverride();
    } else {
      els.btnOverride.textContent = `ARMED — confirm (${_countdown}s)`;
    }
  }, 1000);
}

function disarmOverride() {
  _overrideArmed = false;
  if (_overrideTimer) { clearInterval(_overrideTimer); _overrideTimer = null; }
  if (!els.btnOverride) return;
  els.btnOverride.classList.remove("armed");
  els.btnOverride.textContent = "Override Pre-Gambling";
}

function onOverrideClick() {
  if (!_overrideArmed) {
    armOverride();
  } else {
    disarmOverride();
    openModal();
  }
}

function openModal() {
  if (!els.modalBackdrop) return;
  els.modalBackdrop.classList.add("open");
  if (els.modalDateInput) {
    els.modalDateInput.value = "";
    els.modalDateInput.focus();
  }
  // Reset confirm button — disabled until correct date is typed
  if (els.modalConfirmBtn) els.modalConfirmBtn.disabled = true;
}

function closeModal() {
  if (!els.modalBackdrop) return;
  els.modalBackdrop.classList.remove("open");
}

async function onModalConfirm() {
  const typed = (els.modalDateInput?.value || "").trim();
  const today = todayISO();
  if (typed !== today) {
    alert(`Please type exactly: ${today}`);
    return;
  }
  closeModal();
  await triggerRun("pre_gambling", true);
}

// ─────────────────────────────────────────────
// Grouping: pair USER + AI bets per game
// ─────────────────────────────────────────────

/**
 * Groups _allBets into game-groups where each group has:
 *   { game, userBet, aiBet }
 * USER always top, AI always bottom.
 * Applies calendar filter after grouping.
 */
function buildGroups(bets) {
  const map = new Map(); // game_id → {game, userBet, aiBet}

  bets.forEach(bet => {
    const game = bet.game || {};
    const gameId = game.game_id || `${game.kickoff_iso}_${game.home_team}`;
    if (!map.has(gameId)) {
      map.set(gameId, { game, userBet: null, aiBet: null });
    }
    const g = map.get(gameId);
    if (bet.bettor === "user") {
      g.userBet = bet;
    } else if (bet.bettor === "ai") {
      g.aiBet = bet;
    }
  });

  let groups = Array.from(map.values());

  // Calendar filter on match_date (game.match_date is YYYY-MM-DD)
  if (_calFrom || _calTo) {
    groups = groups.filter(g => {
      const d = g.game.match_date || "";
      if (_calFrom && d < _calFrom) return false;
      if (_calTo   && d > _calTo)   return false;
      return true;
    });
  }

  // Sort by kickoff ascending for Today view
  groups.sort((a, b) => {
    const ka = a.game.kickoff_iso || "";
    const kb = b.game.kickoff_iso || "";
    return ka < kb ? -1 : ka > kb ? 1 : 0;
  });

  return groups;
}

// ─────────────────────────────────────────────
// Apply filter and render
// ─────────────────────────────────────────────

function applyFilterAndRender() {
  // If the user is mid-edit, skip resetting groups / page so the open row survives.
  // renderMatches() has its own identical guard; this one prevents the page-reset too.
  const openEditRow = els.tbodyMatches?.querySelector(".inline-edit-row.open");
  if (openEditRow) {
    // Fix A: show stale-data banner on first bail
    if (!_staleNoticeShown && els.staleNotice) {
      els.staleNotice.textContent = "Refresh paused — close edit to update"; // Fix iter-18: set text on show to trigger live-region announce
      els.staleNotice.style.display = "";
      _staleNoticeShown = true;
    }
    return;
  }

  // Edit row is gone — clear stale notice
  if (_staleNoticeShown && els.staleNotice) {
    els.staleNotice.style.display = "none";
    els.staleNotice.textContent = ""; // Fix iter-18: clear text so next show re-triggers announce
    _staleNoticeShown = false;
  }

  _groups = buildGroups(_allBets);
  // Do NOT reset _currentPage here — this function is called from the 10s poll
  // (fetchMatchData) and resetting would silently kick users back to page 1 mid-browse.
  // Each user-initiated action (filter change, page-size change, btnFirst) sets
  // _currentPage = 1 itself before calling applyFilterAndRender / renderPage.
  // renderPage() already clamps _currentPage to the last valid page if data shrank.
  renderPage();
}

function renderPage() {
  if (!els.tbodyMatches) return;

  const total = _groups.length;
  const totalPages = Math.max(1, Math.ceil(total / _pageSize));
  _currentPage = Math.max(1, Math.min(_currentPage, totalPages));

  const start = (_currentPage - 1) * _pageSize;
  const end   = Math.min(start + _pageSize, total);
  const slice = _groups.slice(start, end);

  // Summary
  if (els.pageSummary) {
    if (total === 0) {
      els.pageSummary.textContent = "No games today";
    } else {
      els.pageSummary.textContent = `Showing ${start + 1}–${end} of ${total} games`;
    }
  }

  // Paging controls visibility
  const showPaging = totalPages > 1;
  if (els.pagingToday) {
    els.pagingToday.style.display = showPaging ? "flex" : "none";
  }
  if (els.pageInfo) {
    els.pageInfo.textContent = `Page ${_currentPage} of ${totalPages}`;
  }
  if (els.btnFirst) els.btnFirst.disabled = _currentPage === 1;
  if (els.btnPrev)  els.btnPrev.disabled  = _currentPage === 1;
  if (els.btnNext)  els.btnNext.disabled  = _currentPage === totalPages;
  if (els.btnLast)  els.btnLast.disabled  = _currentPage === totalPages;

  renderMatches(slice);
}

// ─────────────────────────────────────────────
// Match table rendering (merged-row)
// ─────────────────────────────────────────────

function renderMatches(groups) {
  if (!els.tbodyMatches) return;

  // CRITICAL: If an inline-edit row is open the user is actively typing.
  // Re-rendering would clobber their input with no warning. Skip this cycle.
  // The status strip (poll()) and chip ticker (tickChips()) continue independently.
  const openEditRow = els.tbodyMatches.querySelector(".inline-edit-row.open");
  if (openEditRow) return;

  if (groups.length === 0) {
    els.tbodyMatches.innerHTML = `
      <tr><td colspan="7" class="empty-state">No bets for today</td></tr>`;
    return;
  }

  // Compute per-day lock: earliest kickoff across ALL today's bets (not just current page)
  let earliestKickoffMs = Infinity;
  _allBets.forEach(bet => {
    const ms = kickoffMillis((bet.game || {}).kickoff_iso);
    if (ms < earliestKickoffMs) earliestKickoffMs = ms;
  });
  const dayLocked = (earliestKickoffMs - Date.now()) / 60000 <= LOCK_MINUTES;

  els.tbodyMatches.innerHTML = "";

  groups.forEach((group, groupIdx) => {
    const { game, userBet, aiBet } = group;
    const isEven = groupIdx % 2 === 0;
    const rowClass = isEven ? "game-row game-row--even" : "game-row game-row--odd";

    // Determine colspan for LEFT columns: kickoff, league, match, odds, status = 5
    // Then right cols: prediction+stake, edit = 2

    const leagueCls = leagueCssClass(game.league || "");
    const kickoffTime = game.kickoff_time || "--:--";
    const kickoffMs = kickoffMillis(game.kickoff_iso);

    // Build the top row (USER bet)
    const topRow = document.createElement("tr");
    topRow.className = rowClass + " game-row--top";
    if (userBet) topRow.dataset.groupId = String(groupIdx);

    // LEFT cells (rowspan=2)
    const tdKickoff = document.createElement("td");
    tdKickoff.rowSpan = 2;
    tdKickoff.innerHTML = `
      <div class="kickoff-time">${escHtml(kickoffTime)}</div>
      <div id="chip-game-${group.game.game_id ?? group.userBet?.bet_id ?? group.aiBet?.bet_id ?? groupIdx}" class="countdown-chip chip-green" style="margin-top:4px;"></div>`;

    const tdLeague = document.createElement("td");
    tdLeague.rowSpan = 2;
    tdLeague.innerHTML = `<span class="league-pill ${leagueCls}">${escHtml(leagueDisplay(game.league || ""))}</span>`;

    const tdMatch = document.createElement("td");
    tdMatch.rowSpan = 2;
    tdMatch.innerHTML = `
      <span class="team-name">${escHtml(game.home_team || "")}</span>
      <span class="vs-sep">vs</span>
      <span class="team-name">${escHtml(game.away_team || "")}</span>`;

    const tdOdds = document.createElement("td");
    tdOdds.rowSpan = 2;
    tdOdds.className = "odds-cell center";
    tdOdds.innerHTML = `
      <span class="odds-1">${fmt2(game.home_win_odd)}</span>
      <span class="sep">/</span>${fmt2(game.draw_odd)}<span class="sep">/</span>${fmt2(game.away_win_odd)}`;

    const tdStatus = document.createElement("td");
    tdStatus.rowSpan = 2;
    tdStatus.className = "center";
    tdStatus.innerHTML = `<span class="status-pill ${statusPillClass(game.status)}">${escHtml(statusDisplay(game.status || ""))}</span>`;

    // RIGHT cells — USER sub-row
    const tdUserBet = document.createElement("td");
    tdUserBet.className = "col-bet";
    if (userBet) {
      tdUserBet.innerHTML = `
        <span class="bettor-label bet-user">USER</span>
        ${escHtml((userBet.prediction || "").toUpperCase())}
        <br><span class="bet-amount">NIS ${fmt2(userBet.stake)}</span>`;
    } else {
      tdUserBet.innerHTML = `<span class="sub">—</span>`;
    }

    const tdUserEdit = document.createElement("td");
    tdUserEdit.className = "col-edit center";
    if (userBet) {
      const locked = dayLocked;
      tdUserEdit.innerHTML = `<button
        type="button"
        class="btn-edit"
        id="btn-edit-${userBet.bet_id}"
        data-bet-id="${userBet.bet_id}"
        ${locked ? `disabled title="Edits closed — within 30 min of first kickoff"` : ""}
        onclick="toggleEditRow(${userBet.bet_id})"
      >${locked ? "Locked" : "Edit"}</button>`;
    } else {
      tdUserEdit.className = "col-edit col-edit--empty";
    }

    topRow.appendChild(tdKickoff);
    topRow.appendChild(tdLeague);
    topRow.appendChild(tdMatch);
    topRow.appendChild(tdOdds);
    topRow.appendChild(tdStatus);
    topRow.appendChild(tdUserBet);
    topRow.appendChild(tdUserEdit);
    els.tbodyMatches.appendChild(topRow);

    // Inline edit row for USER bet (hidden by default)
    if (userBet) {
      const editTr = document.createElement("tr");
      editTr.className = "inline-edit-row";
      editTr.id = `edit-row-${userBet.bet_id}`;
      editTr.innerHTML = `
        <td colspan="7" class="inline-edit-cell">
          <div class="inline-edit-form">
            <label>Prediction</label>
            <select id="edit-pred-${userBet.bet_id}">
              <option value="1" ${userBet.prediction === "1" ? "selected" : ""}>1 (Home)</option>
              <option value="x" ${userBet.prediction === "x" ? "selected" : ""}>X (Draw)</option>
              <option value="2" ${userBet.prediction === "2" ? "selected" : ""}>2 (Away)</option>
            </select>
            <label>Stake (NIS)</label>
            <input type="number" id="edit-stake-${userBet.bet_id}" value="${userBet.stake}" min="50" step="50" style="width:100px">
            <button type="button" class="btn-save" onclick="saveEdit(${userBet.bet_id})">Save</button>
            <button type="button" class="btn-cancel-edit" onclick="cancelEdit(${userBet.bet_id})">Cancel</button>
            <span class="edit-feedback" id="edit-fb-${userBet.bet_id}"></span>
          </div>
        </td>`;
      els.tbodyMatches.appendChild(editTr);
    }

    // Bottom row (AI bet) — no LEFT cells (spanned above)
    const botRow = document.createElement("tr");
    botRow.className = rowClass + " game-row--bottom";

    const tdAiBet = document.createElement("td");
    tdAiBet.className = "col-bet";
    if (aiBet) {
      tdAiBet.innerHTML = `
        <span class="bettor-label bet-ai">AI</span>
        ${escHtml((aiBet.prediction || "").toUpperCase())}
        <br><span class="bet-amount">NIS ${fmt2(aiBet.stake)}</span>`;
    } else {
      tdAiBet.innerHTML = `<span class="sub">—</span>`;
    }

    const tdAiEdit = document.createElement("td");
    tdAiEdit.className = "col-edit col-edit--empty";

    botRow.appendChild(tdAiBet);
    botRow.appendChild(tdAiEdit);
    els.tbodyMatches.appendChild(botRow);

    // Separator row
    const sepRow = document.createElement("tr");
    sepRow.className = "game-group-separator";
    sepRow.setAttribute("aria-hidden", "true");
    sepRow.innerHTML = `<td colspan="7"></td>`;
    els.tbodyMatches.appendChild(sepRow);
  });

  // Wire hover delegation on tbody
  wireHoverDelegation(els.tbodyMatches);

  // Tick chips immediately
  tickChips();
}

// ─────────────────────────────────────────────
// Row hover delegation
// ─────────────────────────────────────────────

function wireHoverDelegation(tbody) {
  if (!tbody || tbody._hoverWired) return;
  tbody._hoverWired = true;
  // Use mouseover/mouseout (which bubble) instead of mouseenter/mouseleave (which don't).
  // The tbody element is stable across renderMatches calls (innerHTML is replaced, not the
  // element itself), so wiring once here is safe and no cloneNode dance is needed.
  tbody.addEventListener("mouseover", e => {
    const triggered = e.target.closest("tr.game-row");
    if (!triggered) return;
    let top = triggered.classList.contains("game-row--top") ? triggered : triggered.previousElementSibling;
    while (top && !top.classList.contains("game-row--top")) top = top.previousElementSibling;
    let bot = top ? top.nextElementSibling : null;
    while (bot && !bot.classList.contains("game-row--bottom")) bot = bot.nextElementSibling;
    if (top && bot) {
      top.classList.add("row-hover");
      bot.classList.add("row-hover");
    }
  });
  tbody.addEventListener("mouseout", e => {
    const triggered = e.target.closest("tr.game-row");
    if (!triggered) return;
    let top = triggered.classList.contains("game-row--top") ? triggered : triggered.previousElementSibling;
    while (top && !top.classList.contains("game-row--top")) top = top.previousElementSibling;
    let bot = top ? top.nextElementSibling : null;
    while (bot && !bot.classList.contains("game-row--bottom")) bot = bot.nextElementSibling;
    if (top) top.classList.remove("row-hover");
    if (bot) bot.classList.remove("row-hover");
  });
}

// ─────────────────────────────────────────────
// Edit idle-cancel helpers (Fix A)
// ─────────────────────────────────────────────

let _toastTimer = null;

function _showEditToast(msg) {
  let el = document.getElementById("edit-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "edit-toast";
    el.setAttribute("role", "status");
    el.setAttribute("aria-live", "polite");
    document.body.appendChild(el);
  }
  if (_toastTimer !== null) {
    clearTimeout(_toastTimer);
    _toastTimer = null;
  }
  el.textContent = msg;
  el.classList.add("toast-visible");
  _toastTimer = setTimeout(() => {
    el.classList.remove("toast-visible");
    _toastTimer = null;
  }, 4000);
}

function _startIdleTimer(betId) {
  _clearIdleTimer();
  _idleTimer = setTimeout(() => {
    // Auto-cancel after 5 minutes of no input activity inside the edit form
    cancelEdit(betId);
    _showEditToast("Edit auto-closed after 5 minutes of inactivity");
  }, IDLE_CANCEL_MS);
}

function _clearIdleTimer() {
  if (_idleTimer !== null) {
    clearTimeout(_idleTimer);
    _idleTimer = null;
  }
}

// ─────────────────────────────────────────────
// Edit row toggle
// ─────────────────────────────────────────────

function toggleEditRow(betId) {
  const tbody = document.getElementById("tbody-matches");
  const row = document.getElementById(`edit-row-${betId}`);
  if (!row) return;
  const open = row.classList.contains("open");
  // Close all open edit rows (Fix 3: also clear any leaking idle timer from the outgoing row)
  _clearIdleTimer();
  if (tbody) {
    tbody.querySelectorAll(".inline-edit-row.open").forEach(r => r.classList.remove("open"));
  }
  if (!open) {
    row.classList.add("open");
    // Auto-focus the prediction select for immediate keyboard navigation
    const predEl = document.getElementById(`edit-pred-${betId}`);
    if (predEl) predEl.focus();
    // Wire keyboard shortcuts for this edit row (Escape = cancel, Enter = save)
    // Use a one-time handler stored on the row element to avoid duplicates
    if (!row._kbHandler) {
      row._kbHandler = function onEditRowKeydown(e) {
        if (e.key === "Escape") {
          e.preventDefault();
          cancelEdit(betId);
        } else if (e.key === "Enter") {
          const tag = (e.target.tagName || "").toUpperCase();
          if (tag === "INPUT" || tag === "SELECT") {
            e.preventDefault();
            // Do not save when the row is day-locked — inputs are disabled
            if (!row.classList.contains("edit-row-locked")) {
              saveEdit(betId);
            }
          }
        }
      };
      row.addEventListener("keydown", row._kbHandler);
    }
    // Fix A: wire input/change events to reset the idle timer on any user activity
    if (!row._idleResetHandler) {
      row._idleResetHandler = function() { _startIdleTimer(betId); };
      row.addEventListener("input",  row._idleResetHandler);
      row.addEventListener("change", row._idleResetHandler);
    }
    // Fix A: start the 5-minute idle timer when the row opens
    _startIdleTimer(betId);
  }
}

function cancelEdit(betId) {
  // Fix A: stop the idle auto-cancel timer
  _clearIdleTimer();

  // Reset form fields to saved bet values before closing, so a quick re-open
  // within the same poll window shows the actual stored values, not stale edits.
  const userBet = _allBets.find(b => b.bet_id === betId && b.bettor === "user");
  if (userBet) {
    const predEl  = document.getElementById(`edit-pred-${betId}`);
    const stakeEl = document.getElementById(`edit-stake-${betId}`);
    if (predEl)  predEl.value  = userBet.prediction;
    if (stakeEl) stakeEl.value = userBet.stake;
  }

  const row = document.getElementById(`edit-row-${betId}`);
  if (row) {
    row.classList.remove("open");

    // Fix D: clear lock-state residue so re-opening the row shows a clean form
    row.classList.remove("edit-row-locked");
    // Re-enable any inputs that tickChips may have disabled
    row.querySelectorAll("select, input, button.btn-save").forEach(el => {
      el.disabled = false;
    });
    const fb = document.getElementById(`edit-fb-${betId}`);
    if (fb) {
      delete fb.dataset.lockNotice;
      fb.className = "edit-feedback";
      fb.textContent = "";
    }
  }
}

async function saveEdit(betId) {
  // Guard: refuse to save if the row is day-locked (inputs are disabled)
  const editRow = document.getElementById(`edit-row-${betId}`);
  if (editRow && editRow.classList.contains("edit-row-locked")) return;

  const fb = document.getElementById(`edit-fb-${betId}`);
  const predEl = document.getElementById(`edit-pred-${betId}`);
  const stakeEl = document.getElementById(`edit-stake-${betId}`);
  if (!predEl || !stakeEl) return;

  const body = {
    prediction: predEl.value,
    stake: parseFloat(stakeEl.value),
  };

  // Fix A: stop idle timer while a save is in flight (and cancelEdit will also clear it)
  _clearIdleTimer();
  if (fb) fb.textContent = "Saving…";
  try {
    const resp = await fetch(`/api/bets/${betId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (resp.ok) {
      if (fb) fb.textContent = "";
      cancelEdit(betId);
      await fetchMatchData(); // full re-render
    } else {
      const err = await resp.json().catch(() => ({}));
      let msg;
      if (typeof err.detail === "string") {
        msg = err.detail;
      } else if (typeof err.detail?.message === "string") {
        msg = err.detail.message;
      } else if (Array.isArray(err.detail)) {
        msg = err.detail.map(d => d.msg).join("; ");
      } else {
        msg = `HTTP ${resp.status}`;
      }
      if (fb) fb.textContent = msg;
    }
  } catch (e) {
    if (fb) fb.textContent = "Network error";
  }
}

// ─────────────────────────────────────────────
// Countdown chips (1s tick) — per-game colour,
// per-day lock for all Edit buttons
// ─────────────────────────────────────────────

function tickChips() {
  // Compute day-lock from earliest kickoff across ALL bets
  let earliestKickoffMs = Infinity;
  _allBets.forEach(bet => {
    const ms = kickoffMillis((bet.game || {}).kickoff_iso);
    if (ms < earliestKickoffMs) earliestKickoffMs = ms;
  });
  const dayLocked = (earliestKickoffMs - Date.now()) / 60000 <= LOCK_MINUTES;

  _groups.forEach((group, groupIdx) => {
    const { game, userBet } = group;
    const chip = document.getElementById(`chip-game-${game.game_id ?? group.userBet?.bet_id ?? group.aiBet?.bet_id ?? groupIdx}`);
    if (!chip) return;

    const kickoffMs = kickoffMillis(game.kickoff_iso);
    const msLeft = kickoffMs - Date.now();

    chip.textContent = formatCountdown(msLeft);

    const minLeft = msLeft / 60000;
    if (minLeft > 30) {
      chip.className = "countdown-chip chip-green";
    } else if (minLeft > 5) {
      chip.className = "countdown-chip chip-amber";
    } else {
      chip.className = "countdown-chip chip-red";
    }

    // Update USER Edit button per-day lock
    if (userBet) {
      const editBtn = document.getElementById(`btn-edit-${userBet.bet_id}`);
      if (editBtn) {
        editBtn.disabled = dayLocked;
        editBtn.textContent = dayLocked ? "Locked" : "Edit";
        if (dayLocked) {
          editBtn.title = "Edits closed — within 30 min of first kickoff";
          // Do NOT silently close an open edit form when the lock kicks in —
          // that would drop typed input with no warning.
          // Instead, mark the open row as locked so the user sees an inline notice.
          const editRow = document.getElementById(`edit-row-${userBet.bet_id}`);
          if (editRow && editRow.classList.contains("open")) {
            editRow.classList.add("edit-row-locked");
            // Disable inputs so no further changes can be submitted
            editRow.querySelectorAll("select, input, button.btn-save").forEach(el => {
              el.disabled = true;
            });
            // Show the lock notice in the feedback span if not already shown
            const fb = document.getElementById(`edit-fb-${userBet.bet_id}`);
            if (fb && !fb.dataset.lockNotice) {
              fb.dataset.lockNotice = "1";
              fb.textContent = "Locked — edits closed for today";
              fb.classList.add("edit-feedback-locked");
            }
          }
        } else {
          editBtn.removeAttribute("title");
        }
      }
    }
  });
}

function formatCountdown(msLeft) {
  if (msLeft <= 0) return "KO";
  const totalSec = Math.floor(msLeft / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s.toString().padStart(2, "0")}s`;
  return `${s}s`;
}

function kickoffMillis(kickoffIso) {
  if (!kickoffIso) return Infinity;
  const ms = new Date(kickoffIso).getTime();
  return isNaN(ms) ? Infinity : ms;
}

// ─────────────────────────────────────────────
// Mod ribbon
// ─────────────────────────────────────────────

function updateModRibbon() {
  if (!els.modRibbon) return;
  let earliest = Infinity;
  _allBets.forEach(bet => {
    const ms = kickoffMillis((bet.game || {}).kickoff_iso);
    if (ms < earliest) earliest = ms;
  });

  if (earliest === Infinity) {
    els.modRibbon.innerHTML = "No bets today";
    return;
  }

  const lockTime = new Date(earliest - LOCK_MINUTES * 60000);
  const fmt = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Asia/Jerusalem",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
  const hhmm = fmt.format(lockTime);
  els.modRibbon.innerHTML =
    `Bets modifiable until&nbsp;<strong>${hhmm} ISR</strong>&nbsp;&mdash;&nbsp;Click Edit on a USER row to modify`;
}

// ─────────────────────────────────────────────
// Bankroll rendering
// ─────────────────────────────────────────────

function renderBankroll() {
  if (!_bankroll) return;
  const { user, ai } = _bankroll;
  renderBankrollRow(
    els.userBalance, els.userDelta, els.todayPnlUser,
    user?.balance, user?.today_pnl, "User",
  );
  renderBankrollRow(
    els.aiBalance, els.aiDelta, els.todayPnlAi,
    ai?.balance, ai?.today_pnl, "AI",
  );
}

function fmtNIS(n) {
  // "NIS 1,234.50" — thousands separator, 2 decimal places
  if (n == null) return null;
  return parseFloat(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function renderBankrollRow(balEl, deltaEl, todayEl, balance, todayPnl, label) {
  const START = 10000;
  if (balEl) {
    const delta = balance != null ? balance - START : null;
    const newClass = "bankroll-amount " + (
      delta == null ? "neutral" : delta >= 0 ? "positive" : "negative"
    );
    const newHtml = balance != null
      ? `<span class="bankroll-currency">NIS</span>${fmtNIS(balance)}`
      : `<span class="bankroll-currency">NIS</span>—`;

    // MEDIUM-3: opacity flash on update to avoid jarring snap at 56px font size
    if (balEl.innerHTML !== newHtml || balEl.className !== newClass) {
      balEl.style.opacity = "0.4";
      setTimeout(() => {
        balEl.className = newClass;
        balEl.innerHTML = newHtml;
        balEl.style.opacity = "1";
      }, 50);
    }

    if (deltaEl) {
      let newDeltaClass, newDeltaHtml;
      if (delta == null) {
        newDeltaClass = "bankroll-delta neutral";
        newDeltaHtml  = `<span>vs baseline</span>—`;
      } else if (delta >= 0) {
        newDeltaClass = "bankroll-delta positive";
        newDeltaHtml  = `<span>vs baseline</span>&#9650; +${fmtNIS(delta)} NIS`;
      } else {
        newDeltaClass = "bankroll-delta negative";
        newDeltaHtml  = `<span>vs baseline</span>&#9660; ${fmtNIS(Math.abs(delta))} NIS`;
      }
      // HIGH-1: skip write when nothing changed — avoids layout churn and SR re-announce
      if (deltaEl.innerHTML !== newDeltaHtml || deltaEl.className !== newDeltaClass) {
        deltaEl.className = newDeltaClass;
        deltaEl.innerHTML = newDeltaHtml;
      }
    }
  }

  // HIGH-1 / HIGH-2: only rewrite today-pnl when value changes
  if (todayEl) {
    const lbl = label || "User";
    let newTodayClass, newTodayHtml;
    if (todayPnl == null) {
      newTodayHtml  = `Today P&L (${lbl}): —`;
      newTodayClass = "";
    } else if (parseFloat(todayPnl) >= 0) {
      newTodayHtml  = `Today P&L (${lbl}): <span class="pnl-positive">+${parseFloat(todayPnl).toFixed(2)} NIS</span>`;
      newTodayClass = todayEl.className;
    } else {
      newTodayHtml  = `Today P&L (${lbl}): <span class="pnl-negative">${parseFloat(todayPnl).toFixed(2)} NIS</span>`;
      newTodayClass = todayEl.className;
    }
    if (todayEl.innerHTML !== newTodayHtml || todayEl.className !== newTodayClass) {
      todayEl.className = newTodayClass;
      todayEl.innerHTML = newTodayHtml;
    }
  }
}

// ─────────────────────────────────────────────
// 30-day P&L sparkline
// ─────────────────────────────────────────────

// Sparkline tooltip state
let _sparklinePoints = [];

function _showSparklineTooltip(idx, mouseEvt) {
  const tooltip = document.getElementById("sparkline-tooltip");
  const p = _sparklinePoints[idx];
  if (!p || !tooltip) return;
  const uVal = parseFloat(p.user_cumulative || 0);
  const aVal = parseFloat(p.ai_cumulative   || 0);
  tooltip.innerHTML =
    `<div class="stt-date">${escHtml(p.date)}</div>` +
    `<div class="stt-user">User: ${uVal >= 0 ? "+" : ""}${uVal.toFixed(2)}</div>` +
    `<div class="stt-ai">AI: ${aVal >= 0 ? "+" : ""}${aVal.toFixed(2)}</div>`;
  tooltip.style.display = "block";

  if (mouseEvt) {
    const wrap = tooltip.parentElement;
    const rect = wrap.getBoundingClientRect();
    const ttW  = tooltip.offsetWidth  || 140;
    const ttH  = tooltip.offsetHeight || 60;
    let left = mouseEvt.clientX - rect.left + 12;
    let top  = mouseEvt.clientY - rect.top  - 20;
    if (left + ttW > rect.width)  left = mouseEvt.clientX - rect.left - ttW - 12;
    if (left < 0) left = 4; // LOW-7: clamp left edge on narrow viewports
    if (top  + ttH > rect.height) top  = mouseEvt.clientY - rect.top  - ttH - 4;
    if (top < 0) top = 4;
    tooltip.style.left = left + "px";
    tooltip.style.top  = top  + "px";
  }
}

function _hideSparklineTooltip() {
  const tooltip = document.getElementById("sparkline-tooltip");
  if (tooltip) tooltip.style.display = "none";
}

function renderSparkline(history) {
  // MEDIUM-4: dismiss any open tooltip before rebuilding the DOM
  _hideSparklineTooltip();
  const svgEl = els.sparklineSvg;
  const xLabelsEl = els.xLabels;
  if (!svgEl) return;

  if (history.length < 2) {
    svgEl.innerHTML = `<p class="sparkline-empty">Not enough data</p>`;
    _sparklinePoints = [];
    return;
  }

  const userVals = history.map(d => d.user_cumulative || 0);
  const aiVals   = history.map(d => d.ai_cumulative   || 0);
  const allVals  = [...userVals, ...aiVals];
  const minV = Math.min(0, ...allVals);
  const maxV = Math.max(0, ...allVals);

  // MEDIUM-7: all-zero data — flat line is indistinguishable from real data
  if (minV === 0 && maxV === 0) {
    svgEl.innerHTML = `<p class="sparkline-empty">No P&L history yet</p>`;
    _sparklinePoints = [];
    if (xLabelsEl) xLabelsEl.innerHTML = "";
    return;
  }

  _sparklinePoints = history;

  const W = 760, H = 180;
  const PADDING = { l: 30, r: 10, t: 10, b: 10 };
  const range = maxV - minV || 1;
  const xw = W - PADDING.l - PADDING.r;
  const xh = H - PADDING.t - PADDING.b;
  const n  = history.length;

  function toX(i) { return PADDING.l + (i / (n - 1)) * xw; }
  function toY(v) { return PADDING.t + (1 - (v - minV) / range) * xh; }

  const userPoints = history.map((_, i) => `${toX(i)},${toY(userVals[i])}`).join(" ");
  const aiPoints   = history.map((_, i) => `${toX(i)},${toY(aiVals[i])}`).join(" ");
  const zeroY      = toY(0);

  const userFill = `${userPoints} ${toX(n - 1)},${zeroY} ${toX(0)},${zeroY}`;
  const aiFill   = `${aiPoints}   ${toX(n - 1)},${zeroY} ${toX(0)},${zeroY}`;

  const yTick500 = maxV > 50
    ? `<text x="6" y="${toY(maxV) + 3}" font-size="9" fill="rgba(255,255,255,0.3)" font-family="Space Grotesk, sans-serif">+${Math.round(maxV)}</text>`
    : "";
  const yTickNeg = minV < -50
    ? `<text x="6" y="${toY(minV) + 3}" font-size="9" fill="rgba(255,255,255,0.3)" font-family="Space Grotesk, sans-serif">${Math.round(minV)}</text>`
    : "";

  // HIGH-1: invisible hit-bars per data point, used for hover tooltips
  const barW = Math.max(6, xw / n);
  const hitBars = history.map((_, i) => {
    const cx = toX(i);
    return `<rect class="sparkline-hit" x="${(cx - barW / 2).toFixed(1)}" y="${PADDING.t}"
                  width="${barW.toFixed(1)}" height="${xh}"
                  fill="transparent" data-index="${i}"
                  style="cursor:crosshair;"/>`;
  }).join("");

  svgEl.innerHTML = `
    <svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">
      <line x1="0" y1="${zeroY}" x2="${W}" y2="${zeroY}" stroke="rgba(255,255,255,0.15)" stroke-width="1.5" stroke-dasharray="4 4"/>
      ${yTick500}
      <text x="6" y="${zeroY - 4}" font-size="9" fill="rgba(255,255,255,0.3)" font-family="Space Grotesk, sans-serif">0</text>
      ${yTickNeg}
      <polygon points="${userFill}" fill="rgba(0,168,90,0.12)"/>
      <polyline points="${userPoints}" fill="none" stroke="#00a85a" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
      <polygon points="${aiFill}" fill="rgba(242,97,48,0.1)"/>
      <polyline points="${aiPoints}" fill="none" stroke="#f26130" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
      ${hitBars}
    </svg>`;

  // Attach tooltip listeners after SVG is in DOM
  const svg = svgEl.querySelector("svg");
  if (svg) {
    svg.querySelectorAll(".sparkline-hit").forEach(bar => {
      bar.addEventListener("mouseenter", evt => {
        _showSparklineTooltip(parseInt(bar.dataset.index, 10), evt);
      });
      bar.addEventListener("mousemove", evt => {
        _showSparklineTooltip(parseInt(bar.dataset.index, 10), evt);
      });
      bar.addEventListener("mouseleave", _hideSparklineTooltip);
    });
  }

  if (xLabelsEl) {
    const idxs = [0, Math.floor(n / 2), n - 1];
    xLabelsEl.innerHTML = "";
    idxs.forEach(i => {
      const span = document.createElement("span");
      span.className = "chart-x-label";
      span.textContent = history[i].date || "";
      xLabelsEl.appendChild(span);
    });
  }
}

// ─────────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────────

function escHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmt2(v) {
  if (v == null) return "—";
  return parseFloat(v).toFixed(2);
}

/** Normalize DB snake_case game.status → human-readable Title Case */
function statusDisplay(s) {
  if (!s) return "";
  const map = {
    pending:           "Pending",
    selected:          "Selected",
    processing:        "Processing",
    ready_for_betting: "Ready",
    betting_open:      "Open",
    betting_closed:    "Closed",
    completed:         "Finished",
    cancelled:         "Cancelled",
    // legacy / uppercase passthrough
    scheduled:         "Scheduled",
    live:              "Live",
    finished:          "Finished",
    postponed:         "Postponed",
    in_play:           "Live",
  };
  return map[s.toLowerCase()] || s.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

/** CSS modifier for status pill colour */
function statusPillClass(s) {
  if (!s) return "";
  const l = s.toLowerCase();
  if (l === "completed" || l === "finished") return "status-pill--finished";
  if (l === "live" || l === "in_play" || l === "betting_open") return "status-pill--live";
  if (l === "cancelled" || l === "postponed") return "status-pill--cancelled";
  return "status-pill--scheduled";
}

function leagueCssClass(league) {
  const l = (league || "").toLowerCase();
  if (l.includes("la liga") || l.includes("laliga") || l.includes("primera division")) return "laliga";
  if (l.includes("premier")) return "premier";
  if (l.includes("bundesliga")) return "bundesliga";
  if (l.includes("serie a") || l.includes("seriea")) return "seriea";
  return "";
}
function leagueDisplay(league) {
  // U3: normalise legacy alias → canonical UI label (DB unchanged)
  if ((league || "").trim().toLowerCase() === "primera division") return "La Liga";
  return league;
}

function todayISO() {
  if (_status && _status.today_date) return _status.today_date;
  const el = document.getElementById("today-date-iso");
  if (el && el.value) return el.value;
  if (_status && _status.run_date) return _status.run_date;
  return new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Jerusalem" });
}

// ─────────────────────────────────────────────
// Calendar filter
// ─────────────────────────────────────────────

function onCalendarChange() {
  // Fix B: if an edit row is open, cancel it before applying the filter change.
  // Without this, the calendar updates _calFrom/_calTo but applyFilterAndRender bails
  // due to the open edit guard, leaving the rows visually out of sync with the filter.
  if (els.tbodyMatches) {
    const openEditRow = els.tbodyMatches.querySelector(".inline-edit-row.open");
    if (openEditRow) {
      const betId = openEditRow.id.replace("edit-row-", "");
      cancelEdit(Number(betId));
    }
  }
  clearTimeout(_debounceTimer);
  _debounceTimer = setTimeout(() => {
    _calFrom = els.calFrom ? els.calFrom.value : "";
    _calTo   = els.calTo   ? els.calTo.value   : "";
    _currentPage = 1;
    applyFilterAndRender();
  }, 350);
}

// ─────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  initRefs();

  // Cache original run-button labels once so rapid re-clicks cannot corrupt them
  if (els.btnPreGambling) els.btnPreGambling.dataset.label = els.btnPreGambling.textContent;
  if (els.btnPostGames)   els.btnPostGames.dataset.label   = els.btnPostGames.textContent;

  // Set calendar defaults to today
  const todayStr = new Date().toLocaleDateString("sv-SE", { timeZone: "Asia/Jerusalem" });
  if (els.calFrom) els.calFrom.value = todayStr;
  if (els.calTo)   els.calTo.value   = todayStr;
  _calFrom = todayStr;
  _calTo   = todayStr;

  // Wire calendar inputs
  if (els.calFrom) els.calFrom.addEventListener("change", onCalendarChange);
  if (els.calTo)   els.calTo.addEventListener("change", onCalendarChange);

  // Wire paging
  function _cancelOpenEdit() {
    const openRow = document.querySelector(".inline-edit-row.open");
    if (openRow) {
      const betId = openRow.id.replace("edit-row-", "");
      cancelEdit(parseInt(betId, 10));
    }
  }

  if (els.btnFirst) els.btnFirst.addEventListener("click", () => { _cancelOpenEdit(); _currentPage = 1; renderPage(); });
  if (els.btnPrev)  els.btnPrev.addEventListener("click",  () => { _cancelOpenEdit(); _currentPage--; renderPage(); });
  if (els.btnNext)  els.btnNext.addEventListener("click",  () => { _cancelOpenEdit(); _currentPage++; renderPage(); });
  if (els.btnLast)  els.btnLast.addEventListener("click",  () => {
    _cancelOpenEdit();
    _currentPage = Math.ceil(_groups.length / _pageSize) || 1;
    renderPage();
  });
  if (els.pageSizeSelect) {
    els.pageSizeSelect.addEventListener("change", () => {
      _cancelOpenEdit();
      _pageSize = parseInt(els.pageSizeSelect.value, 10);
      _currentPage = 1;
      renderPage();
    });
  }

  // Wire control buttons
  if (els.btnPreGambling) els.btnPreGambling.addEventListener("click", () => triggerRun("pre_gambling"));
  if (els.btnPostGames)   els.btnPostGames.addEventListener("click",   () => triggerRun("post_games"));
  if (els.btnOverride)    els.btnOverride.addEventListener("click", onOverrideClick);

  // Wire modal
  if (els.modalConfirmBtn) els.modalConfirmBtn.addEventListener("click", onModalConfirm);
  if (els.modalCancelBtn)  els.modalCancelBtn.addEventListener("click", closeModal);
  if (els.modalBackdrop) {
    els.modalBackdrop.addEventListener("click", e => {
      if (e.target === els.modalBackdrop) closeModal();
    });
  }
  // Document-level Escape closes modal regardless of which element has focus
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && els.modalBackdrop && els.modalBackdrop.classList.contains("open")) {
      e.preventDefault();
      closeModal();
    }
  });
  if (els.modalDateInput) {
    els.modalDateInput.addEventListener("keydown", e => {
      if (e.key === "Enter") onModalConfirm();
      // Escape is handled by the document-level handler above; no duplicate needed here
    });
    // Disable Confirm until typed date matches today
    els.modalDateInput.addEventListener("input", () => {
      const typed = (els.modalDateInput.value || "").trim();
      if (els.modalConfirmBtn) {
        els.modalConfirmBtn.disabled = (typed !== todayISO());
      }
    });
  }

  // Initial data load
  await poll();
  await fetchMatchData();
  await fetchPnlHistory();

  // Polling & chip tick — stored so we can pause/resume on visibility change
  let _intervals = [
    setInterval(poll,           POLL_MS),
    setInterval(fetchMatchData, 10000),
    setInterval(fetchPnlHistory, 60000),
    setInterval(tickChips,      1000),
  ];
  tickChips();

  // LOW: Pause all pollers when the tab is hidden, resume when visible again.
  // Avoids wasted network requests and prevents timer drift in background tabs.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      _intervals.forEach(id => clearInterval(id));
      _intervals = [];
      // Fix iter-18: clear idle timer so it doesn't fire silently while tab is hidden
      _clearIdleTimer();
      // Fix iter-19: disarm override countdown so it doesn't expire invisibly
      if (_overrideArmed) disarmOverride();
    } else {
      // Fix iter-19: clear any stale intervals before re-creating to prevent doubling
      _intervals.forEach(id => clearInterval(id));
      _intervals = [];
      // Resume immediately then restart intervals
      poll();
      fetchMatchData();
      tickChips();
      _intervals = [
        setInterval(poll,           POLL_MS),
        setInterval(fetchMatchData, 10000),
        setInterval(fetchPnlHistory, 60000),
        setInterval(tickChips,      1000),
      ];
    }
  });
});

// Expose for inline onclick attributes
window.toggleEditRow = toggleEditRow;
window.cancelEdit    = cancelEdit;
window.saveEdit      = saveEdit;
