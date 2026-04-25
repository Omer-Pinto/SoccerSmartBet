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
 *  - Live polling: /api/today/live every 60s while any game is live/starting soon
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

// Live polling: start when a game is within 5 min of kickoff, poll every 60s
const LIVE_POLL_MS      = 60000;
const LIVE_START_MIN    = 5;    // minutes before kickoff to start live polling

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

// Chip ticker pause flag — true while any EDIT row is open
let _chipTickerPaused = false;

// Live data state — keyed by game_id
let _lastLiveData = null;   // full response from /api/today/live
let _liveInterval = null;   // handle for live polling interval
let _livePollingActive = false;

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
    // After fresh match data, re-evaluate whether live polling should start/stop
    manageLivePolling();
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
// Live polling — /api/today/live
// ─────────────────────────────────────────────

/**
 * Determines whether any game warrants live polling.
 * Start conditions:
 *   - period is 1H, HT, 2H (in-play)
 *   - period is "pre" AND kickoff is within LIVE_START_MIN minutes
 * Stop condition: all games are FT or unknown (no more live/starting-soon).
 */
function _shouldPollLive() {
  if (!_allBets.length) return false;
  const now = Date.now();
  const seenGames = new Set();
  for (const bet of _allBets) {
    const game = bet.game || {};
    const gid  = game.game_id;
    if (seenGames.has(gid)) continue;
    seenGames.add(gid);

    // Check live payload if available
    if (_lastLiveData && _lastLiveData.games) {
      const liveGame = _lastLiveData.games.find(g => g.game_id === gid);
      if (liveGame) {
        if (["1H","HT","2H"].includes(liveGame.period)) return true;
        if (liveGame.period === "pre") {
          const msLeft = kickoffMillis(game.kickoff_iso) - now;
          if (msLeft <= LIVE_START_MIN * 60000) return true;
        }
        // "FT" or "unknown" — not a reason to poll
        continue;
      }
    }
    // No live data yet — fall back to kickoff proximity
    const msLeft = kickoffMillis(game.kickoff_iso) - now;
    if (msLeft <= LIVE_START_MIN * 60000 && msLeft > -3 * 60 * 60 * 1000) return true;
  }
  return false;
}

function manageLivePolling() {
  const should = _shouldPollLive();
  if (should && !_livePollingActive) {
    _startLivePolling();
  } else if (!should && _livePollingActive) {
    _stopLivePolling();
  }
}

function _startLivePolling() {
  if (_livePollingActive) return;
  _livePollingActive = true;
  console.info("[live] Starting live polling every", LIVE_POLL_MS, "ms");
  pollLive(); // immediate first fetch
  _liveInterval = setInterval(pollLive, LIVE_POLL_MS);
}

function _stopLivePolling() {
  if (!_livePollingActive) return;
  _livePollingActive = false;
  console.info("[live] Stopping live polling — all games finished");
  if (_liveInterval !== null) {
    clearInterval(_liveInterval);
    _liveInterval = null;
  }
}

async function pollLive() {
  // Task 1: pause live render while edit row is open
  if (_chipTickerPaused) {
    console.debug("[live] Skipping live poll — edit row open");
    return;
  }

  try {
    const resp = await fetch("/api/today/live");
    if (resp.status === 404) {
      // Endpoint not yet deployed — fail open
      console.debug("[live] /api/today/live 404 — keeping current rendering");
      return;
    }
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    _lastLiveData = await resp.json();
    console.debug("[live] received:", _lastLiveData);
    // Patch in-place without full re-render (no edit disruption)
    applyLiveOverlay();
    renderScoreboard();
    // Re-evaluate polling need
    manageLivePolling();
  } catch (e) {
    console.warn("[live] pollLive failed:", e);
    // Fail open — don't break the page
  }
}

/**
 * Walk rendered game rows and patch live state into them.
 * Does NOT trigger a full re-render — surgically updates cells already in DOM.
 */
function applyLiveOverlay() {
  if (!_lastLiveData || !_lastLiveData.games) return;
  if (!els.tbodyMatches) return;

  const liveMap = new Map(_lastLiveData.games.map(g => [g.game_id, g]));

  _groups.forEach((group, groupIdx) => {
    const { game, userBet, aiBet } = group;
    const gid = game.game_id;
    const liveGame = liveMap.get(gid);
    if (!liveGame) return;

    // ── Score cell: update scoreline and period chip ──
    const scorelineId  = `scoreline-${gid ?? groupIdx}`;
    const periodChipId = `period-chip-${gid ?? groupIdx}`;
    const chipId       = `chip-game-${gid ?? group.userBet?.bet_id ?? group.aiBet?.bet_id ?? groupIdx}`;
    const chipEl       = document.getElementById(chipId);

    // The score cell is the parent of the flex wrapper that holds scoreline + period chip.
    // We locate it via the countdown chip (still in Kickoff cell) then walk to tdScore.
    // More reliably: use scorelineId / periodChipId since those live in tdScore now.
    const scorelinePeerParent = (function() {
      const existing = document.getElementById(scorelineId) || document.getElementById(periodChipId);
      return existing ? existing.parentNode : (chipEl ? chipEl.closest("td")?.nextElementSibling?.nextElementSibling?.nextElementSibling : null);
    })();

    // Scoreline
    let scoreEl = document.getElementById(scorelineId);
    if (!scoreEl && liveGame.period !== "pre" && scorelinePeerParent) {
      scoreEl = document.createElement("div");
      scoreEl.id = scorelineId;
      scoreEl.className = "live-scoreline";
      scorelinePeerParent.firstElementChild
        ? scorelinePeerParent.firstElementChild.insertBefore(scoreEl, scorelinePeerParent.firstElementChild.firstChild)
        : scorelinePeerParent.appendChild(scoreEl);
    }
    if (scoreEl && liveGame.period !== "pre") {
      const hs = liveGame.home_score ?? 0;
      const as_ = liveGame.away_score ?? 0;
      scoreEl.textContent = `${hs} - ${as_}`;
      scoreEl.className = "live-scoreline" + (liveGame.finished ? " live-scoreline--ft" : "");
    } else if (scoreEl && liveGame.period === "pre") {
      scoreEl.textContent = "";
    }

    // Period chip
    let pChipEl = document.getElementById(periodChipId);
    if (!pChipEl && scorelinePeerParent) {
      pChipEl = document.createElement("div");
      pChipEl.id = periodChipId;
      pChipEl.style.marginTop = "4px";
      const flexWrap = scorelinePeerParent.firstElementChild;
      if (flexWrap) flexWrap.appendChild(pChipEl);
    }
    if (pChipEl) {
      const { text: pText, cls: pCls } = periodChipContent(liveGame);
      const isLiveNow = ["1H","2H"].includes(liveGame.period);
      pChipEl.className = pCls;
      if (pText) {
        const liveDot = isLiveNow ? `<span class="live-dot" aria-hidden="true"></span>` : "";
        pChipEl.innerHTML = liveDot + escHtml(pText);
      } else {
        pChipEl.innerHTML = "";
      }
    }

    // ── Row-state classes: finished / live ──
    const isFinished  = liveGame.finished || liveGame.period === "FT";
    const isLiveOrHT  = ["1H","2H","HT"].includes(liveGame.period);
    // Find the top and bottom rows for this group by their shared groupId
    const topRow = els.tbodyMatches.querySelector(`tr[data-group-id="${groupIdx}"]`);
    if (topRow) {
      let botRow = topRow.nextElementSibling;
      while (botRow && !botRow.classList.contains("game-row--bottom")) {
        botRow = botRow.nextElementSibling;
      }
      for (const tr of [topRow, botRow].filter(Boolean)) {
        tr.classList.remove("game-row--finished", "game-row--live");
        if (isFinished)  tr.classList.add("game-row--finished");
        if (isLiveOrHT)  tr.classList.add("game-row--live");
      }
    }

    // ── Odds bolding: re-evaluate based on current score ──
    _applyOddsBolding(gid ?? groupIdx, liveGame);

    // ── P&L cells: update both USER and AI bet rows ──
    _applyLivePnlToRow(userBet, liveGame);
    _applyLivePnlToRow(aiBet, liveGame);
  });
}

/**
 * Updates the P&L display in a single bet's row.
 * - If period != "FT": show dash (hide P&L).
 * - If period == "FT" and estimate present: show preview P&L.
 * - If stored pnl arrives: show confirmed P&L (drop preview style).
 */
function _applyLivePnlToRow(bet, liveGame) {
  if (!bet) return;
  const pnlCellId = `pnl-cell-${bet.bet_id}`;
  const pnlEl = document.getElementById(pnlCellId);
  if (!pnlEl) return;

  const isFinished = liveGame.finished || liveGame.period === "FT";
  const estimate   = bet.bettor === "user" ? liveGame.user_pnl_estimate : liveGame.ai_pnl_estimate;
  const storedPnl  = bet.pnl;

  if (!isFinished) {
    pnlEl.innerHTML = `<span class="pnl-pending">—</span>`;
    pnlEl.className = "pnl-cell";
    return;
  }

  if (storedPnl != null) {
    // Confirmed result already in DB — show it plainly
    const val = parseFloat(storedPnl);
    const sign = val >= 0 ? "+" : "";
    pnlEl.innerHTML = `<span class="${val >= 0 ? "pnl-positive" : "pnl-negative"}">${sign}${val.toFixed(0)} NIS</span>`;
    pnlEl.className = "pnl-cell";
  } else if (estimate != null) {
    // DB hasn't synced yet — show preview
    const val = parseFloat(estimate);
    const sign = val >= 0 ? "+" : "";
    pnlEl.innerHTML =
      `<span class="${val >= 0 ? "pnl-positive" : "pnl-negative"} pnl-estimated"
             title="Estimated — pending post-games confirmation"
       >${sign}${val.toFixed(0)} NIS</span>`;
    pnlEl.className = "pnl-cell";
  } else {
    pnlEl.innerHTML = `<span class="pnl-pending">—</span>`;
    pnlEl.className = "pnl-cell";
  }
}

/**
 * Applies bold to the odds span that matches the current match result.
 *
 * Pre-match (no live data or period === "pre"): no span bolded.
 * Live or FT:
 *   home > away  → bold the "1" span
 *   home == away → bold the "X" span
 *   home < away  → bold the "2" span
 *
 * gameKey is the value used when building the odds cell ID (game.game_id ?? groupIdx).
 */
function _applyOddsBolding(gameKey, liveGame) {
  const oddsId = `odds-cell-${gameKey}`;
  const span1 = document.getElementById(`${oddsId}-1`);
  const spanX = document.getElementById(`${oddsId}-x`);
  const span2 = document.getElementById(`${oddsId}-2`);
  if (!span1 || !spanX || !span2) return;

  // Clear all existing bold
  span1.classList.remove("odds-bold");
  spanX.classList.remove("odds-bold");
  span2.classList.remove("odds-bold");

  if (!liveGame || liveGame.period === "pre") return;

  const hs = liveGame.home_score ?? 0;
  const as_ = liveGame.away_score ?? 0;
  if (hs > as_)       span1.classList.add("odds-bold");
  else if (hs === as_) spanX.classList.add("odds-bold");
  else                 span2.classList.add("odds-bold");
}

/**
 * Returns { text, cls } for a period chip given live game data.
 * Classes extend the countdown-chip base for consistent sizing/padding.
 */
function periodChipContent(liveGame) {
  const p = liveGame.period;
  const min = liveGame.minute;
  if (p === "1H") {
    return {
      text: min ? `1H ${min}` : "1H",
      cls: "countdown-chip chip-live",
    };
  }
  if (p === "HT") {
    return { text: "HT", cls: "countdown-chip chip-ht" };
  }
  if (p === "2H") {
    return {
      text: min ? `2H ${min}` : "2H",
      cls: "countdown-chip chip-live",
    };
  }
  if (p === "FT") {
    return { text: "FT", cls: "countdown-chip chip-ft" };
  }
  return { text: "", cls: "countdown-chip chip-unknown" };
}

// ─────────────────────────────────────────────
// Today's Scoreboard (reworked — two columns)
// ─────────────────────────────────────────────

function renderScoreboard() {
  const loadingEl = document.getElementById("scoreboard-loading");
  const contentEl = document.getElementById("scoreboard-content");
  if (!contentEl) return;

  // ISR 04:00 cutoff: keep showing scoreboard until 04:00 ISR next day
  const isrNow = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Jerusalem" }));
  const isrHour = isrNow.getHours();
  // If it's between midnight and 04:00 ISR, still show today's scoreboard
  // If past 04:00, only show if there are today's bets loaded
  const pastCutoff = isrHour >= 4 && isrNow.getHours() < 24;

  if (!_allBets.length) {
    if (loadingEl) loadingEl.style.display = "none";
    contentEl.style.display = "none";
    return;
  }

  // Build live game map from live data
  const liveMap = new Map();
  if (_lastLiveData && _lastLiveData.games) {
    _lastLiveData.games.forEach(g => liveMap.set(g.game_id, g));
  }

  // Categorise each UNIQUE game_id into "livePlay" (in-play), "pending" (pre-kickoff), or "final"
  const seenGames = new Set();
  const stats = {
    livePlay: { count: 0, userPnl: 0, aiPnl: 0, hasPnl: false },
    pending:  { count: 0 },
    final:    { count: 0, userPnl: 0, aiPnl: 0, userW: 0, userL: 0, userD: 0, aiW: 0, aiL: 0, aiD: 0 },
  };

  // Walk all bets — gather per-game, per-bettor P&L
  const gameStats = new Map(); // game_id → { period, finished, pnlEstimateLive, bets: [] }
  _allBets.forEach(bet => {
    const game  = bet.game || {};
    const gid   = game.game_id;
    if (!gameStats.has(gid)) {
      const liveGame = liveMap.get(gid);
      gameStats.set(gid, {
        period: liveGame ? liveGame.period : null,
        finished: liveGame ? liveGame.finished : false,
        pnlEstimateLive: liveGame ? !!liveGame.pnl_estimate_is_live : false,
        liveGame: liveGame || null,
        bets: [],
      });
    }
    gameStats.get(gid).bets.push(bet);
  });

  gameStats.forEach(({ period, finished, pnlEstimateLive, liveGame, bets }, gid) => {
    // Determine bucket
    const isFinal = finished || period === "FT" ||
      bets.some(b => b.pnl !== null && b.result !== null);
    const inPlay  = !isFinal && period && ["1H","HT","2H"].includes(period);
    const isPending = !isFinal && !inPlay; // pre-match or no live data yet

    const bucket = isFinal ? "final" : inPlay ? "livePlay" : "pending";

    if (!seenGames.has(gid)) {
      seenGames.add(gid);
      stats[bucket].count++;
    }

    bets.forEach(bet => {
      const who = bet.bettor;
      if (who !== "user" && who !== "ai") return;

      // Final bucket: accumulate confirmed/estimated P&L for record
      if (isFinal) {
        let pnlVal = null;
        if (bet.pnl != null) {
          pnlVal = parseFloat(bet.pnl);
        } else if (liveGame) {
          const est = who === "user" ? liveGame.user_pnl_estimate : liveGame.ai_pnl_estimate;
          if (est != null) pnlVal = parseFloat(est);
        }
        if (pnlVal !== null) {
          if (who === "user") {
            stats.final.userPnl += pnlVal;
            if (pnlVal > 0) stats.final.userW++;
            else if (pnlVal < 0) stats.final.userL++;
            else stats.final.userD++;
          } else {
            stats.final.aiPnl += pnlVal;
            if (pnlVal > 0) stats.final.aiW++;
            else if (pnlVal < 0) stats.final.aiL++;
            else stats.final.aiD++;
          }
        }
      }

      // Live bucket: accumulate live P&L estimates (only when pnl_estimate_is_live flag set)
      if (inPlay && pnlEstimateLive && liveGame) {
        const est = who === "user" ? liveGame.user_pnl_estimate : liveGame.ai_pnl_estimate;
        if (est != null) {
          const val = parseFloat(est);
          if (who === "user") stats.livePlay.userPnl += val;
          else                stats.livePlay.aiPnl   += val;
          stats.livePlay.hasPnl = true;
        }
      }
    });
  });

  // Render three-column scoreboard
  const fmtPnl = v => {
    const n = parseFloat(v) || 0;
    const sign = n > 0 ? "+" : "";
    return `${sign}${n.toFixed(0)} NIS`;
  };
  const fmtRecord = (w, l, d) => `${w}W / ${l}L${d > 0 ? ` / ${d}D` : ""}`;
  const pnlColor = v => parseFloat(v) > 0 ? "var(--emerald)" : parseFloat(v) < 0 ? "var(--vermilion)" : "rgba(255,255,255,0.6)";

  // LIVE column body — count + live P&L per side (estimates, dotted underline)
  // Falls back to "0 NIS" when estimates not yet available (pnl_estimate_is_live not set)
  const sbLivePlayBody = stats.livePlay.count === 0
    ? `<p class="sb-col-empty">No live games</p>`
    : stats.livePlay.hasPnl
      ? `<div class="sb-row">
          <span class="sb-row-label">User</span>
          <span class="sb-row-pnl pnl-estimated" style="color:${pnlColor(stats.livePlay.userPnl)}" title="Live estimate — updates each poll">${fmtPnl(stats.livePlay.userPnl)}</span>
        </div>
        <div class="sb-row">
          <span class="sb-row-label">AI</span>
          <span class="sb-row-pnl pnl-estimated" style="color:${pnlColor(stats.livePlay.aiPnl)}" title="Live estimate — updates each poll">${fmtPnl(stats.livePlay.aiPnl)}</span>
        </div>`
      : `<div class="sb-row">
          <span class="sb-row-label">User</span>
          <span class="sb-row-pnl" style="color:rgba(255,255,255,0.6)">0 NIS</span>
        </div>
        <div class="sb-row">
          <span class="sb-row-label">AI</span>
          <span class="sb-row-pnl" style="color:rgba(255,255,255,0.6)">0 NIS</span>
        </div>`;

  // PENDING column body — count + subtitle only
  const sbPendingBody = stats.pending.count === 0
    ? `<p class="sb-col-empty">None</p>`
    : `<p class="sb-col-status">Awaiting kickoff</p>`;

  // FINAL column body
  const sbFinalBody = stats.final.count === 0
    ? `<p class="sb-col-empty">No results yet</p>`
    : `<div class="sb-row">
            <span class="sb-row-label">User</span>
            <span class="sb-row-pnl" style="color:${pnlColor(stats.final.userPnl)}">${fmtPnl(stats.final.userPnl)}</span>
            <span class="sb-row-record">${fmtRecord(stats.final.userW, stats.final.userL, stats.final.userD)}</span>
          </div>
          <div class="sb-row">
            <span class="sb-row-label">AI</span>
            <span class="sb-row-pnl" style="color:${pnlColor(stats.final.aiPnl)}">${fmtPnl(stats.final.aiPnl)}</span>
            <span class="sb-row-record">${fmtRecord(stats.final.aiW, stats.final.aiL, stats.final.aiD)}</span>
          </div>`;

  contentEl.innerHTML = `
    <div class="sb-three-col">
      <div class="sb-col sb-col--live">
        <div class="sb-col-header">
          <span class="sb-col-title">Live</span>
          <span class="sb-col-count">${stats.livePlay.count} game${stats.livePlay.count !== 1 ? "s" : ""}</span>
        </div>
        <div class="sb-col-body">
          ${sbLivePlayBody}
        </div>
      </div>
      <div class="sb-col sb-col--pending">
        <div class="sb-col-header">
          <span class="sb-col-title">Pending</span>
          <span class="sb-col-count">${stats.pending.count} game${stats.pending.count !== 1 ? "s" : ""}</span>
        </div>
        <div class="sb-col-body">
          ${sbPendingBody}
        </div>
      </div>
      <div class="sb-col sb-col--final">
        <div class="sb-col-header">
          <span class="sb-col-title">Final</span>
          <span class="sb-col-count">${stats.final.count} game${stats.final.count !== 1 ? "s" : ""}</span>
        </div>
        <div class="sb-col-body">
          ${sbFinalBody}
        </div>
      </div>
    </div>
    ${_scoreboardLeader(stats)}
  `;

  if (loadingEl) loadingEl.style.display = "none";
  contentEl.style.display = "flex";
  contentEl.style.flexDirection = "column";
}

function _scoreboardLeader(stats) {
  const totalUser = (stats.livePlay?.userPnl || 0) + stats.final.userPnl;
  const totalAi   = (stats.livePlay?.aiPnl   || 0) + stats.final.aiPnl;
  const hasActivity = ((stats.livePlay?.count || 0) + (stats.pending?.count || 0) + stats.final.count) > 0;
  if (!hasActivity) return "";
  if (totalUser > totalAi) {
    return `<div class="scoreboard-row scoreboard-row--leader"><span class="scoreboard-trophy">&#127942;</span><span class="scoreboard-leader-label">User leads today</span></div>`;
  } else if (totalAi > totalUser) {
    return `<div class="scoreboard-row scoreboard-row--leader"><span class="scoreboard-trophy">&#127942;</span><span class="scoreboard-leader-label">AI leads today</span></div>`;
  }
  return "";
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
      <tr><td colspan="8" class="empty-state">No bets for today</td></tr>`;
    return;
  }

  // Compute per-day lock: earliest kickoff across ALL today's bets (not just current page)
  let earliestKickoffMs = Infinity;
  _allBets.forEach(bet => {
    const ms = kickoffMillis((bet.game || {}).kickoff_iso);
    if (ms < earliestKickoffMs) earliestKickoffMs = ms;
  });
  const dayLocked = (earliestKickoffMs - Date.now()) / 60000 <= LOCK_MINUTES;

  // Build live map for this render pass
  const liveMap = new Map();
  if (_lastLiveData && _lastLiveData.games) {
    _lastLiveData.games.forEach(g => liveMap.set(g.game_id, g));
  }

  els.tbodyMatches.innerHTML = "";

  groups.forEach((group, groupIdx) => {
    const { game, userBet, aiBet } = group;
    const isEven = groupIdx % 2 === 0;
    const rowClass = isEven ? "game-row game-row--even" : "game-row game-row--odd";

    const leagueCls = leagueCssClass(game.league || "");
    const kickoffTime = game.kickoff_time || "--:--";
    const kickoffMs = kickoffMillis(game.kickoff_iso);
    const liveGame  = liveMap.get(game.game_id);

    // Determine row-state classes
    const isFinished = liveGame
      ? (liveGame.finished || liveGame.period === "FT")
      : (userBet?.pnl != null && aiBet?.pnl != null);
    const isLiveOrHT  = liveGame && ["1H","2H","HT"].includes(liveGame.period);

    let rowStateClass = "";
    if (isFinished)  rowStateClass = " game-row--finished";
    if (isLiveOrHT)  rowStateClass = " game-row--live";

    // Build the top row (USER bet)
    const topRow = document.createElement("tr");
    topRow.className = rowClass + " game-row--top" + rowStateClass;
    if (userBet) topRow.dataset.groupId = String(groupIdx);

    // ── LEFT cells (rowspan=2) ──

    // Kickoff cell — countdown chip only (scoreline moved to Score cell)
    const chipId = `chip-game-${game.game_id ?? group.userBet?.bet_id ?? group.aiBet?.bet_id ?? groupIdx}`;
    const periodChipId = `period-chip-${game.game_id ?? groupIdx}`;
    const scorelineId  = `scoreline-${game.game_id ?? groupIdx}`;

    const tdKickoff = document.createElement("td");
    tdKickoff.rowSpan = 2;
    tdKickoff.innerHTML = `
      <div class="kickoff-time">${escHtml(kickoffTime)}</div>
      <div id="${chipId}" class="countdown-chip chip-green" style="margin-top:4px;"></div>`;

    const tdLeague = document.createElement("td");
    tdLeague.rowSpan = 2;
    tdLeague.innerHTML = `<span class="league-pill ${leagueCls}">${escHtml(leagueDisplay(game.league || ""))}</span>`;

    const tdMatch = document.createElement("td");
    tdMatch.rowSpan = 2;
    tdMatch.innerHTML = `
      <span class="team-name">${escHtml(game.home_team || "")}</span>
      <span class="vs-sep">vs</span>
      <span class="team-name">${escHtml(game.away_team || "")}</span>`;

    // Score cell — scoreline + period/countdown chip live here
    let scorelineHtml = "";
    let periodHtml    = "";

    if (liveGame && liveGame.period !== "pre") {
      const hs = liveGame.home_score ?? 0;
      const as_ = liveGame.away_score ?? 0;
      const ftCls = liveGame.finished ? " live-scoreline--ft" : "";
      scorelineHtml = `<div id="${scorelineId}" class="live-scoreline${ftCls}">${hs} - ${as_}</div>`;
    }

    if (liveGame) {
      const { text: pText, cls: pCls } = periodChipContent(liveGame);
      if (pText) {
        const isLiveNow = ["1H","2H"].includes(liveGame.period);
        const liveDot   = isLiveNow ? `<span class="live-dot" aria-hidden="true"></span>` : "";
        periodHtml = `<div id="${periodChipId}" class="${pCls}" style="margin-top:4px;">${liveDot}${escHtml(pText)}</div>`;
      }
    }

    const tdScore = document.createElement("td");
    tdScore.rowSpan = 2;
    tdScore.className = "score-cell center";
    tdScore.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;gap:4px;white-space:nowrap;">
        ${scorelineHtml}
        ${periodHtml}
      </div>`;

    const oddsId = `odds-cell-${game.game_id ?? groupIdx}`;
    const tdOdds = document.createElement("td");
    tdOdds.rowSpan = 2;
    tdOdds.className = "odds-cell center";
    tdOdds.id = oddsId;
    tdOdds.innerHTML = `
      <span class="odds-1" id="${oddsId}-1">${fmt2(game.home_win_odd)}</span>
      <span class="sep">/</span><span id="${oddsId}-x">${fmt2(game.draw_odd)}</span><span class="sep">/</span><span id="${oddsId}-2">${fmt2(game.away_win_odd)}</span>`;

    const tdStatus = document.createElement("td");
    tdStatus.rowSpan = 2;
    tdStatus.className = "center";
    tdStatus.innerHTML = `<span class="status-pill ${statusPillClass(game.status)}">${escHtml(statusDisplay(game.status || ""))}</span>`;

    // ── RIGHT cells — USER sub-row ──
    const tdUserBet = document.createElement("td");
    tdUserBet.className = "col-bet";
    if (userBet) {
      const pnlHtml = _renderPnlHtml(userBet, liveGame);
      tdUserBet.innerHTML = `
        <span class="bettor-label bet-user">USER</span>
        ${escHtml((userBet.prediction || "").toUpperCase())}
        <br><span class="bet-amount">NIS ${fmt2(userBet.stake)}</span>
        ${pnlHtml}`;
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
    topRow.appendChild(tdScore);
    topRow.appendChild(tdOdds);
    topRow.appendChild(tdStatus);
    topRow.appendChild(tdUserBet);
    topRow.appendChild(tdUserEdit);
    els.tbodyMatches.appendChild(topRow);
    // Spans are now in the live DOM — apply odds bolding
    _applyOddsBolding(game.game_id ?? groupIdx, liveGame);

    // Inline edit row for USER bet (hidden by default)
    if (userBet) {
      const editTr = document.createElement("tr");
      editTr.className = "inline-edit-row";
      editTr.id = `edit-row-${userBet.bet_id}`;
      editTr.innerHTML = `
        <td colspan="8" class="inline-edit-cell">
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

    // ── Bottom row (AI bet) ──
    const botRow = document.createElement("tr");
    botRow.className = rowClass + " game-row--bottom" + rowStateClass;

    const tdAiBet = document.createElement("td");
    tdAiBet.className = "col-bet";
    if (aiBet) {
      const pnlHtml = _renderPnlHtml(aiBet, liveGame);
      tdAiBet.innerHTML = `
        <span class="bettor-label bet-ai">AI</span>
        ${escHtml((aiBet.prediction || "").toUpperCase())}
        <br><span class="bet-amount">NIS ${fmt2(aiBet.stake)}</span>
        ${pnlHtml}`;
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
    sepRow.innerHTML = `<td colspan="8"></td>`;
    els.tbodyMatches.appendChild(sepRow);
  });

  // Wire hover delegation on tbody
  wireHoverDelegation(els.tbodyMatches);

  // Tick chips immediately
  tickChips();
}

/**
 * Returns the HTML for the P&L cell for a single bet, given optional live game data.
 * - No live data or period == "pre": empty (no P&L yet)
 * - period != "FT": dash (game in progress)
 * - period == "FT": show confirmed or preview P&L
 */
function _renderPnlHtml(bet, liveGame) {
  if (!bet) return "";
  const betId = bet.bet_id;
  const wrapOpen  = `<span id="pnl-cell-${betId}" class="pnl-cell">`;
  const wrapClose = `</span>`;

  // Stored result already in DB — show confirmed regardless of live state
  if (bet.pnl != null) {
    const val  = parseFloat(bet.pnl);
    const sign = val >= 0 ? "+" : "";
    const cls  = val >= 0 ? "pnl-positive" : "pnl-negative";
    return `${wrapOpen}<span class="${cls}">${sign}${val.toFixed(0)} NIS</span>${wrapClose}`;
  }

  if (!liveGame) return `${wrapOpen}${wrapClose}`;

  const isFinished = liveGame.finished || liveGame.period === "FT";

  if (!isFinished) {
    if (liveGame.period === "pre") return `${wrapOpen}${wrapClose}`;
    // In-progress: show dash
    return `${wrapOpen}<span class="pnl-pending">—</span>${wrapClose}`;
  }

  // FT — show estimate as preview if available
  const estimate = bet.bettor === "user" ? liveGame.user_pnl_estimate : liveGame.ai_pnl_estimate;
  if (estimate != null) {
    const val  = parseFloat(estimate);
    const sign = val >= 0 ? "+" : "";
    const cls  = val >= 0 ? "pnl-positive" : "pnl-negative";
    return `${wrapOpen}<span class="${cls} pnl-estimated" title="Estimated — pending post-games confirmation">${sign}${val.toFixed(0)} NIS</span>${wrapClose}`;
  }

  return `${wrapOpen}<span class="pnl-pending">—</span>${wrapClose}`;
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
    // Pause chip ticker while this edit row is open — prevents re-render jitter / focus loss
    _chipTickerPaused = true;
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
  // Resume chip ticker now that the edit row is closing
  _chipTickerPaused = false;

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
  // Pause while any EDIT row is open to avoid focus-stealing / layout jitter
  if (_chipTickerPaused) return;

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
  const totalMin = Math.ceil(msLeft / 60000);
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
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
    setInterval(tickChips,      60000),  // 60s tick — avoid UI jitter during EDIT
  ];
  tickChips();

  // LOW: Pause all pollers when the tab is hidden, resume when visible again.
  // Avoids wasted network requests and prevents timer drift in background tabs.
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) {
      _intervals.forEach(id => clearInterval(id));
      _intervals = [];
      // Stop live polling too
      _stopLivePolling();
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
        setInterval(tickChips,      60000),
      ];
      // manageLivePolling will be called inside fetchMatchData callback
    }
  });
});

// Expose for inline onclick attributes
window.toggleEditRow = toggleEditRow;
window.cancelEdit    = cancelEdit;
window.saveEdit      = saveEdit;
// Expose for DevTools testing
window._lastLiveData       = undefined; // will be set by pollLive
window._applyLiveOverlay   = applyLiveOverlay;
window._pollLive           = pollLive;
window._manageLivePolling  = manageLivePolling;
