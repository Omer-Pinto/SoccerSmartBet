/**
 * SoccerSmartBet — Today Tab JS
 *
 * Responsibilities:
 *  - Poll /api/status/today every 2500ms
 *  - Update status strip
 *  - Lock/unlock control buttons based on flow status
 *  - Force Override two-phase UX
 *  - Fetch today's matches from /api/today/data and render them
 *  - Inline bet editing with countdown chips (1s tick)
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
const LOCK_MINUTES = 30; // minutes before kickoff when edits close

// ─────────────────────────────────────────────
// State
// ─────────────────────────────────────────────

let _status = null;        // latest /api/status/today payload
let _matches = [];         // today's bets + game data
let _bankroll = null;      // bankroll data
let _pnlHistory = [];      // 30-day P&L
let _overrideArmed = false;
let _overrideTimer = null;
let _countdown = 5;        // Force Override arm countdown (s)

// ─────────────────────────────────────────────
// DOM refs (populated on DOMContentLoaded)
// ─────────────────────────────────────────────

let els = {};

function initRefs() {
  els = {
    // status strip
    statusValue:    document.getElementById("status-value"),
    statusAttempts: document.getElementById("status-attempts"),
    statusError:    document.getElementById("status-error"),
    preGamblingTile:document.getElementById("tile-pre-gambling"),
    gamblingTile:   document.getElementById("tile-gambling"),
    postGamesTile:  document.getElementById("tile-post-games"),

    // buttons
    btnPreGambling: document.getElementById("btn-pre-gambling"),
    btnPostGames:   document.getElementById("btn-post-games"),
    btnRegen:       document.getElementById("btn-regen"),
    btnOverride:    document.getElementById("btn-override"),

    // matches
    tbodyMatches:   document.getElementById("tbody-matches"),
    modRibbon:      document.getElementById("mod-ribbon"),

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
    updateStatusStrip(_status);
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
    _matches = data.bets || [];
    _bankroll = data.bankroll || null;
    renderMatches();
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
    _pnlHistory = data.history || [];
    renderSparkline(_pnlHistory);
  } catch (e) {
    console.warn("fetchPnlHistory failed:", e);
  }
}

// ─────────────────────────────────────────────
// Status strip update
// ─────────────────────────────────────────────

function statusLabel(st) {
  const map = {
    idle:                "Idle",
    pre_gambling_running:"Pre-Gambling Running…",
    pre_gambling_done:   "Pre-Gambling Done",
    gambling_running:    "Gambling Running…",
    gambling_done:       "Gambling Done",
    post_games_running:  "Post-Games Running…",
    post_games_done:     "Post-Games Done",
    failed:              "Failed",
  };
  return map[st] || st;
}

function statusColorClass(st) {
  if (RUNNING_STATUSES.has(st)) return "clock";
  if (st === "failed")          return "err";
  if (st.endsWith("_done"))     return "check";
  return "";
}

function updateStatusStrip(s) {
  if (!els.statusValue) return;
  const cls = statusColorClass(s.status);
  els.statusValue.innerHTML = cls
    ? `<span class="${cls}">${statusLabel(s.status)}</span>`
    : statusLabel(s.status);

  if (els.statusAttempts) {
    els.statusAttempts.textContent =
      s.attempt_count != null ? `Attempt ${s.attempt_count}` : "";
  }

  if (els.statusError) {
    if (s.status === "failed" && s.last_error) {
      els.statusError.innerHTML = `<span class="err">${escHtml(s.last_error.slice(0, 120))}</span>`;
    } else {
      els.statusError.textContent = "";
    }
  }

  updateTile(els.preGamblingTile, s.pre_gambling_started_at, s.pre_gambling_completed_at, "Pre-Gambling");
  updateTile(els.gamblingTile,    s.gambling_completed_at,   s.gambling_completed_at,     "Gambling");
  updateTile(els.postGamesTile,   s.post_games_trigger_at,   s.post_games_completed_at,   "Post-Games");
}

function updateTile(el, startedAt, completedAt, label) {
  if (!el) return;
  const labelEl = el.querySelector(".stat-tile-label");
  const valueEl = el.querySelector(".stat-tile-value");
  if (labelEl) labelEl.textContent = label;
  if (!valueEl) return;
  if (completedAt) {
    const t = completedAt.slice(11, 16);
    valueEl.innerHTML = `<span class="check">&#10003;</span>&nbsp;Done <span class="sub">${t}</span>`;
  } else if (startedAt) {
    valueEl.innerHTML = `<span class="clock">&#9200;</span>&nbsp;Running`;
  } else {
    valueEl.innerHTML = `<span class="sub">—</span>`;
  }
}

// ─────────────────────────────────────────────
// Button lock / unlock
// ─────────────────────────────────────────────

function updateButtons(s) {
  const anyRunning = RUNNING_STATUSES.has(s.status);
  const st = s.status;

  // Pre-Gambling: available from idle or failed
  setBtnEnabled(
    els.btnPreGambling,
    !anyRunning && (st === "idle" || st === "failed"),
    anyRunning ? "Flow in progress" : null,
  );

  // Post-Games: available when pre_gambling_done or gambling_done or failed
  setBtnEnabled(
    els.btnPostGames,
    !anyRunning && ["pre_gambling_done", "gambling_done", "failed"].includes(st),
    anyRunning ? "Flow in progress" : null,
  );

  // Regenerate Report: same as pre_gambling but label says regen
  setBtnEnabled(
    els.btnRegen,
    !anyRunning && (st === "idle" || st === "failed" || st === "pre_gambling_done"),
    anyRunning ? "Flow in progress" : null,
  );

  // Force Override: always interactive unless running
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
  const today = todayISO();
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
      body: JSON.stringify({ run_date: today, flow_type: flowType, force }),
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

  // Immediate status refresh
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
    // Second click — open confirmation modal
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
// Match table rendering
// ─────────────────────────────────────────────

function renderMatches() {
  if (!els.tbodyMatches) return;
  if (_matches.length === 0) {
    els.tbodyMatches.innerHTML = `
      <tr><td colspan="9" class="empty-state">No bets for today</td></tr>`;
    return;
  }

  els.tbodyMatches.innerHTML = "";
  _matches.forEach((bet, idx) => {
    const game = bet.game || {};
    const kickoffMs = kickoffMillis(game.match_date, game.kickoff_time);
    const locked = isLocked(kickoffMs);

    // Main bet row
    const tr = document.createElement("tr");
    tr.id = `bet-row-${bet.bet_id}`;
    if (locked) tr.classList.add("row-locked");
    tr.innerHTML = `
      <td>
        <div class="kickoff-time">${game.kickoff_time || "--:--"}</div>
        <div id="chip-${bet.bet_id}" class="countdown-chip chip-green" style="margin-top:4px;"></div>
      </td>
      <td><span class="league-pill ${leagueCssClass(game.league)}">${escHtml(game.league || "")}</span></td>
      <td>
        <span class="team-name">${escHtml(game.home_team || "")}</span>
        <span class="vs-sep">vs</span>
        <span class="team-name">${escHtml(game.away_team || "")}</span>
      </td>
      <td class="odds-cell">
        <span class="odds-1">${fmt2(game.home_win_odd)}</span>
        <span class="sep">/</span>${fmt2(game.draw_odd)}<span class="sep">/</span>${fmt2(game.away_win_odd)}
      </td>
      <td class="bet-cell bet-user" id="pred-user-${bet.bet_id}">
        ${bet.bettor === "user" ? escHtml((bet.prediction || "").toUpperCase()) : "—"}
        ${bet.bettor === "user" ? `<br><span class="bet-amount">@ ${fmt2(bet.stake)} NIS</span>` : ""}
      </td>
      <td class="bet-cell bet-ai" id="pred-ai-${bet.bet_id}">
        ${bet.bettor === "ai" ? escHtml((bet.prediction || "").toUpperCase()) : "—"}
        ${bet.bettor === "ai" ? `<br><span class="bet-amount">@ ${fmt2(bet.stake)} NIS</span>` : ""}
      </td>
      <td><span class="status-pill">${escHtml(game.status || "")}</span></td>
      <td class="edit-cell">
        <button
          class="btn-edit"
          id="btn-edit-${bet.bet_id}"
          data-bet-id="${bet.bet_id}"
          ${locked ? "disabled title=\"Locked — edits close 30 minutes before kickoff\"" : ""}
          onclick="toggleEditRow(${bet.bet_id})"
        >${locked ? "Locked" : "Edit"}</button>
      </td>`;
    els.tbodyMatches.appendChild(tr);

    // Inline edit row (hidden by default)
    const editTr = document.createElement("tr");
    editTr.className = "inline-edit-row";
    editTr.id = `edit-row-${bet.bet_id}`;
    editTr.innerHTML = `
      <td colspan="9" class="inline-edit-cell">
        <div class="inline-edit-form">
          <label>Prediction</label>
          <select id="edit-pred-${bet.bet_id}">
            <option value="1" ${bet.prediction === "1" ? "selected" : ""}>1 (Home)</option>
            <option value="x" ${bet.prediction === "x" ? "selected" : ""}>X (Draw)</option>
            <option value="2" ${bet.prediction === "2" ? "selected" : ""}>2 (Away)</option>
          </select>
          <label>Stake (NIS)</label>
          <input type="number" id="edit-stake-${bet.bet_id}" value="${bet.stake}" min="1" step="50" style="width:100px">
          <button class="btn-save" onclick="saveEdit(${bet.bet_id})">Save</button>
          <button class="btn-cancel-edit" onclick="cancelEdit(${bet.bet_id})">Cancel</button>
          <span class="edit-feedback" id="edit-fb-${bet.bet_id}"></span>
        </div>
      </td>`;
    els.tbodyMatches.appendChild(editTr);
  });
}

function toggleEditRow(betId) {
  const row = document.getElementById(`edit-row-${betId}`);
  if (!row) return;
  const open = row.classList.contains("open");
  // close all edit rows first
  document.querySelectorAll(".inline-edit-row.open").forEach(r => r.classList.remove("open"));
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
      const updated = await resp.json();
      if (fb) fb.textContent = "";
      cancelEdit(betId);
      // patch in-memory so chip logic stays correct
      const match = _matches.find(b => b.bet_id === betId);
      if (match) {
        match.prediction = updated.prediction;
        match.stake = updated.stake;
      }
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
// Countdown chips (1s tick)
// ─────────────────────────────────────────────

function tickChips() {
  _matches.forEach(bet => {
    const game = bet.game || {};
    const chip = document.getElementById(`chip-${bet.bet_id}`);
    const editBtn = document.getElementById(`btn-edit-${bet.bet_id}`);
    const betRow = document.getElementById(`bet-row-${bet.bet_id}`);
    if (!chip) return;

    const kickoffMs = kickoffMillis(game.match_date, game.kickoff_time);
    const msLeft = kickoffMs - Date.now();
    const minLeft = msLeft / 60000;

    chip.textContent = formatCountdown(msLeft);

    if (minLeft > 30) {
      chip.className = "countdown-chip chip-green";
      if (editBtn) { editBtn.disabled = false; editBtn.textContent = "Edit"; editBtn.title = ""; }
      if (betRow) betRow.classList.remove("row-locked");
    } else if (minLeft > 5) {
      chip.className = "countdown-chip chip-amber";
      if (editBtn) { editBtn.disabled = false; editBtn.textContent = "Edit"; editBtn.title = ""; }
    } else {
      chip.className = "countdown-chip chip-red";
      const kickoffStr = game.kickoff_time || "--:--";
      if (editBtn) {
        editBtn.disabled = true;
        editBtn.textContent = "Locked";
        editBtn.title = `Locked — edits close 30 minutes before kickoff at ${kickoffStr} ISR`;
      }
      if (betRow) betRow.classList.add("row-locked");
      // Close any open edit row
      cancelEdit(bet.bet_id);
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

function kickoffMillis(matchDate, kickoffTime) {
  if (!matchDate || !kickoffTime) return Infinity;
  // kickoffTime is "HH:MM" or "HH:MM:SS" already in ISR.
  // We construct an ISO string and let the browser parse it as local if server
  // is in ISR, but since this is a local-only dashboard we rely on matching TZ.
  // The approach: build a UTC timestamp using the known ISR offset (UTC+3 standard, UTC+2 DST).
  // However, to stay simple and avoid TZ math in JS we just treat it as local
  // and note the uncertainty in the report.
  const dt = new Date(`${matchDate}T${kickoffTime.slice(0, 5)}:00`);
  return dt.getTime();
}

function isLocked(kickoffMs) {
  return (kickoffMs - Date.now()) / 60000 <= LOCK_MINUTES;
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
// Mod ribbon
// ─────────────────────────────────────────────

function updateModRibbon() {
  if (!els.modRibbon) return;
  // Find earliest kickoff
  let earliest = Infinity;
  _matches.forEach(bet => {
    const game = bet.game || {};
    const ms = kickoffMillis(game.match_date, game.kickoff_time);
    if (ms < earliest) earliest = ms;
  });

  if (earliest === Infinity) {
    els.modRibbon.innerHTML = "No bets today";
    return;
  }

  const lockTime = new Date(earliest - LOCK_MINUTES * 60000);
  const hh = lockTime.getHours().toString().padStart(2, "0");
  const mm = lockTime.getMinutes().toString().padStart(2, "0");
  els.modRibbon.innerHTML =
    `Bets modifiable until&nbsp;<strong>${hh}:${mm} ISR</strong>&nbsp;&mdash;&nbsp;Click Edit on a row to modify`;
}

// ─────────────────────────────────────────────
// 30-day P&L sparkline (inline SVG, no library)
// ─────────────────────────────────────────────

function renderSparkline(history) {
  const svgEl = els.sparklineSvg;
  const xLabelsEl = els.xLabels;
  if (!svgEl) return;

  // history: [{date, user_cumulative, ai_cumulative}, ...] sorted oldest first
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

  function toX(i) {
    return PADDING.l + (i / (history.length - 1)) * xw;
  }
  function toY(v) {
    return PADDING.t + (1 - (v - minV) / range) * xh;
  }

  const userPoints = history.map((_, i) => `${toX(i)},${toY(userVals[i])}`).join(" ");
  const aiPoints   = history.map((_, i) => `${toX(i)},${toY(aiVals[i])}`).join(" ");
  const zeroY      = toY(0);

  const userFill = `${userPoints} ${toX(history.length - 1)},${zeroY} ${toX(0)},${zeroY}`;
  const aiFill   = `${aiPoints}   ${toX(history.length - 1)},${zeroY} ${toX(0)},${zeroY}`;

  // Y-axis tick at 0 (dashed), midpoints
  const midPos = Math.round((maxV + minV) / 2);
  const yTick500 = maxV > 50 ? `<text x="6" y="${toY(maxV) + 3}" font-size="9" fill="rgba(255,255,255,0.3)" font-family="Space Grotesk, sans-serif">+${Math.round(maxV)}</text>` : "";
  const yTickNeg = minV < -50 ? `<text x="6" y="${toY(minV) + 3}" font-size="9" fill="rgba(255,255,255,0.3)" font-family="Space Grotesk, sans-serif">${Math.round(minV)}</text>` : "";

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

  // X-axis labels: first, middle, last
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
  if (!league) return "";
  const l = league.toLowerCase();
  if (l.includes("la liga") || l.includes("laliga")) return "laliga";
  if (l.includes("premier")) return "premier";
  if (l.includes("bundesliga")) return "bundesliga";
  if (l.includes("serie a") || l.includes("seriea")) return "seriea";
  return "";
}

function todayISO() {
  // Use the date shown in the masthead (set by server at page render)
  const el = document.getElementById("today-date-iso");
  return el ? el.value : new Date().toISOString().slice(0, 10);
}

// ─────────────────────────────────────────────
// Boot
// ─────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", async () => {
  initRefs();

  // Wire control buttons
  if (els.btnPreGambling) {
    els.btnPreGambling.addEventListener("click", () => triggerRun("pre_gambling"));
  }
  if (els.btnPostGames) {
    els.btnPostGames.addEventListener("click", () => triggerRun("post_games"));
  }
  if (els.btnRegen) {
    els.btnRegen.addEventListener("click", () => triggerRun("regenerate_report"));
  }
  if (els.btnOverride) {
    els.btnOverride.addEventListener("click", onOverrideClick);
  }

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
  setInterval(fetchMatchData, 10000);   // refresh match data every 10s
  setInterval(fetchPnlHistory, 60000);  // refresh P&L every 60s
  setInterval(tickChips, 1000);
  tickChips(); // immediate first tick
});

// Expose for inline onclick
window.toggleEditRow = toggleEditRow;
window.cancelEdit    = cancelEdit;
window.saveEdit      = saveEdit;
