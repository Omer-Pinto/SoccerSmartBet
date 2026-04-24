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
    btnRegen:       document.getElementById("btn-regen"),
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
    if (!resp.ok) return;
    const data = await resp.json();
    _allBets = data.bets || [];
    _bankroll = data.bankroll || null;
    applyFilterAndRender();
    renderBankroll();
    updateModRibbon();
  } catch (e) {
    console.warn("fetchMatchData failed:", e);
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
      els.statusError.innerHTML = `<span class="sub">none</span>`;
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

  setBtnEnabled(
    els.btnRegen,
    !anyRunning && (st === "idle" || st === "failed" || st === "pre_gambling_done"),
    anyRunning ? "Flow in progress" : null,
  );

  if (anyRunning) {
    disarmOverride();
    setBtnEnabled(els.btnOverride, false, "Flow in progress");
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
    pre_gambling:      els.btnPreGambling,
    post_games:        els.btnPostGames,
    regenerate_report: els.btnRegen,
  }[flowType];

  if (btn) {
    const orig = btn.textContent;
    btn.disabled = true;
    btn.classList.add("btn-queued");
    btn.textContent = "Queued…";
    setTimeout(() => { btn.textContent = orig; btn.classList.remove("btn-queued"); }, 8000);
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
      alert(`Error: ${JSON.stringify(err.detail || err)}`);
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
  els.btnOverride.textContent = "Force Override";
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
  _groups = buildGroups(_allBets);
  _currentPage = 1;
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
      <div id="chip-game-${groupIdx}" class="countdown-chip chip-green" style="margin-top:4px;"></div>`;

    const tdLeague = document.createElement("td");
    tdLeague.rowSpan = 2;
    tdLeague.innerHTML = `<span class="league-pill ${leagueCls}">${escHtml(game.league || "")}</span>`;

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
    tdStatus.innerHTML = `<span class="status-pill">${escHtml(game.status || "")}</span>`;

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
        class="btn-edit"
        id="btn-edit-${userBet.bet_id}"
        data-bet-id="${userBet.bet_id}"
        ${locked ? `disabled title="Edits close 30 min before the first kickoff today"` : ""}
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
            <input type="number" id="edit-stake-${userBet.bet_id}" value="${userBet.stake}" min="1" step="50" style="width:100px">
            <button class="btn-save" onclick="saveEdit(${userBet.bet_id})">Save</button>
            <button class="btn-cancel-edit" onclick="cancelEdit(${userBet.bet_id})">Cancel</button>
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
  if (!tbody) return;
  // Remove any old listeners by replacing the node (simplest approach for re-renders)
  const clone = tbody.cloneNode(true);
  tbody.parentNode.replaceChild(clone, tbody);
  els.tbodyMatches = clone;

  // Re-wire onclick for edit buttons (since cloneNode doesn't copy event listeners,
  // but inline onclick attributes ARE copied as HTML attributes — they'll still work
  // because they reference window.toggleEditRow etc.)

  clone.addEventListener("mouseenter", e => {
    const row = e.target.closest("tr.game-row");
    if (!row) return;
    // Find sibling top/bottom rows
    const top = row.classList.contains("game-row--top") ? row : row.previousElementSibling;
    const bot = top ? top.nextElementSibling : null;
    if (top && top.classList.contains("game-row")) top.classList.add("row-hover");
    if (bot && bot.classList.contains("game-row")) bot.classList.add("row-hover");
  }, true);

  clone.addEventListener("mouseleave", e => {
    const row = e.target.closest("tr.game-row");
    if (!row) return;
    const top = row.classList.contains("game-row--top") ? row : row.previousElementSibling;
    const bot = top ? top.nextElementSibling : null;
    if (top) top.classList.remove("row-hover");
    if (bot) bot.classList.remove("row-hover");
  }, true);
}

// ─────────────────────────────────────────────
// Edit row toggle
// ─────────────────────────────────────────────

function toggleEditRow(betId) {
  const tbody = document.getElementById("tbody-matches");
  const row = document.getElementById(`edit-row-${betId}`);
  if (!row) return;
  const open = row.classList.contains("open");
  // Close all open edit rows
  if (tbody) {
    tbody.querySelectorAll(".inline-edit-row.open").forEach(r => r.classList.remove("open"));
  }
  if (!open) row.classList.add("open");
}

function cancelEdit(betId) {
  const row = document.getElementById(`edit-row-${betId}`);
  if (row) row.classList.remove("open");
}

async function saveEdit(betId) {
  const fb = document.getElementById(`edit-fb-${betId}`);
  const predEl = document.getElementById(`edit-pred-${betId}`);
  const stakeEl = document.getElementById(`edit-stake-${betId}`);
  if (!predEl || !stakeEl) return;

  const body = {
    prediction: predEl.value,
    stake: parseFloat(stakeEl.value),
  };

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
      if (fb) fb.textContent = err.detail || `Error ${resp.status}`;
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
    const chip = document.getElementById(`chip-game-${groupIdx}`);
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
          editBtn.title = "Edits close 30 min before the first kickoff today";
          // Close open edit form if day just locked
          cancelEdit(userBet.bet_id);
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
    user?.balance, user?.today_pnl,
  );
  renderBankrollRow(
    els.aiBalance, els.aiDelta, els.todayPnlAi,
    ai?.balance, ai?.today_pnl,
  );
}

function renderBankrollRow(balEl, deltaEl, todayEl, balance, todayPnl) {
  const START = 10000;
  if (balEl) {
    const delta = balance != null ? balance - START : null;
    balEl.className = "bankroll-amount " + (
      delta == null ? "neutral" : delta >= 0 ? "positive" : "negative"
    );
    balEl.innerHTML = balance != null
      ? `<span class="bankroll-currency">NIS</span>${Math.round(balance).toLocaleString()}`
      : `<span class="bankroll-currency">NIS</span>—`;

    if (deltaEl) {
      if (delta == null) {
        deltaEl.className = "bankroll-delta neutral";
        deltaEl.innerHTML = `<span>Since 10,000</span>—`;
      } else if (delta >= 0) {
        deltaEl.className = "bankroll-delta positive";
        deltaEl.innerHTML = `<span>Since 10,000</span>&#9650; +${Math.round(delta).toLocaleString()} NIS`;
      } else {
        deltaEl.className = "bankroll-delta negative";
        deltaEl.innerHTML = `<span>Since 10,000</span>&#9660; ${Math.round(delta).toLocaleString()} NIS`;
      }
    }
  }

  if (todayEl) {
    if (todayPnl == null) {
      todayEl.innerHTML = "Today P&L: —";
      todayEl.className = "";
    } else if (todayPnl >= 0) {
      todayEl.innerHTML = `Today P&L: <span class="pnl-positive">+${Math.round(todayPnl)} NIS</span>`;
    } else {
      todayEl.innerHTML = `Today P&L: <span class="pnl-negative">${Math.round(todayPnl)} NIS</span>`;
    }
  }
}

// ─────────────────────────────────────────────
// 30-day P&L sparkline
// ─────────────────────────────────────────────

function renderSparkline(history) {
  const svgEl = els.sparklineSvg;
  const xLabelsEl = els.xLabels;
  if (!svgEl) return;

  if (history.length < 2) {
    svgEl.innerHTML = `<text x="50%" y="50%" text-anchor="middle" fill="rgba(255,255,255,0.3)" font-size="12">Not enough data</text>`;
    return;
  }

  const W = 760, H = 180;
  const PADDING = { l: 30, r: 10, t: 10, b: 10 };

  const userVals = history.map(d => d.user_cumulative || 0);
  const aiVals   = history.map(d => d.ai_cumulative   || 0);
  const allVals  = [...userVals, ...aiVals];
  const minV = Math.min(0, ...allVals);
  const maxV = Math.max(0, ...allVals);
  const range = maxV - minV || 1;

  const xw = W - PADDING.l - PADDING.r;
  const xh = H - PADDING.t - PADDING.b;

  function toX(i) { return PADDING.l + (i / (history.length - 1)) * xw; }
  function toY(v) { return PADDING.t + (1 - (v - minV) / range) * xh; }

  const userPoints = history.map((_, i) => `${toX(i)},${toY(userVals[i])}`).join(" ");
  const aiPoints   = history.map((_, i) => `${toX(i)},${toY(aiVals[i])}`).join(" ");
  const zeroY      = toY(0);

  const userFill = `${userPoints} ${toX(history.length - 1)},${zeroY} ${toX(0)},${zeroY}`;
  const aiFill   = `${aiPoints}   ${toX(history.length - 1)},${zeroY} ${toX(0)},${zeroY}`;

  const yTick500 = maxV > 50
    ? `<text x="6" y="${toY(maxV) + 3}" font-size="9" fill="rgba(255,255,255,0.3)" font-family="Space Grotesk, sans-serif">+${Math.round(maxV)}</text>`
    : "";
  const yTickNeg = minV < -50
    ? `<text x="6" y="${toY(minV) + 3}" font-size="9" fill="rgba(255,255,255,0.3)" font-family="Space Grotesk, sans-serif">${Math.round(minV)}</text>`
    : "";

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
    </svg>`;

  if (xLabelsEl) {
    const idxs = [0, Math.floor(history.length / 2), history.length - 1];
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

function leagueCssClass(league) {
  const l = (league || "").toLowerCase();
  if (l.includes("la liga") || l.includes("laliga")) return "laliga";
  if (l.includes("premier")) return "premier";
  if (l.includes("bundesliga")) return "bundesliga";
  if (l.includes("serie a") || l.includes("seriea")) return "seriea";
  return "";
}

function todayISO() {
  if (_status && _status.today_date) return _status.today_date;
  const el = document.getElementById("today-date-iso");
  if (el && el.value) return el.value;
  if (_status && _status.run_date) return _status.run_date;
  return new Date().toISOString().slice(0, 10);
}

// ─────────────────────────────────────────────
// Calendar filter
// ─────────────────────────────────────────────

function onCalendarChange() {
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
  if (els.btnFirst) els.btnFirst.addEventListener("click", () => { _currentPage = 1; renderPage(); });
  if (els.btnPrev)  els.btnPrev.addEventListener("click",  () => { _currentPage--; renderPage(); });
  if (els.btnNext)  els.btnNext.addEventListener("click",  () => { _currentPage++; renderPage(); });
  if (els.btnLast)  els.btnLast.addEventListener("click",  () => {
    _currentPage = Math.ceil(_groups.length / _pageSize);
    renderPage();
  });
  if (els.pageSizeSelect) {
    els.pageSizeSelect.addEventListener("change", () => {
      _pageSize = parseInt(els.pageSizeSelect.value, 10);
      _currentPage = 1;
      renderPage();
    });
  }

  // Wire control buttons
  if (els.btnPreGambling) els.btnPreGambling.addEventListener("click", () => triggerRun("pre_gambling"));
  if (els.btnPostGames)   els.btnPostGames.addEventListener("click",   () => triggerRun("post_games"));
  if (els.btnRegen)       els.btnRegen.addEventListener("click",       () => triggerRun("regenerate_report"));
  if (els.btnOverride)    els.btnOverride.addEventListener("click", onOverrideClick);

  // Wire modal
  if (els.modalConfirmBtn) els.modalConfirmBtn.addEventListener("click", onModalConfirm);
  if (els.modalCancelBtn)  els.modalCancelBtn.addEventListener("click", closeModal);
  if (els.modalBackdrop) {
    els.modalBackdrop.addEventListener("click", e => {
      if (e.target === els.modalBackdrop) closeModal();
    });
  }
  if (els.modalDateInput) {
    els.modalDateInput.addEventListener("keydown", e => {
      if (e.key === "Enter") onModalConfirm();
      if (e.key === "Escape") closeModal();
    });
  }

  // Initial data load
  await poll();
  await fetchMatchData();
  await fetchPnlHistory();

  // Polling & chip tick
  setInterval(poll, POLL_MS);
  setInterval(fetchMatchData, 10000);
  setInterval(fetchPnlHistory, 60000);
  setInterval(tickChips, 1000);
  tickChips();
});

// Expose for inline onclick attributes
window.toggleEditRow = toggleEditRow;
window.cancelEdit    = cancelEdit;
window.saveEdit      = saveEdit;
