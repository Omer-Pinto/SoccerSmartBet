"""
Telegram callback handlers for the interactive betting UI.

Manages the full lifecycle of a user betting session:
  1. send_want_to_bet  — initial Yes/No prompt
  2. handle_gamble_callback — routes all gbet_/gstake_/gsend_bet/gnoop callbacks
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta

import psycopg2
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from soccersmartbet.reports.telegram_message import get_games_info
from soccersmartbet.telegram.bot import TELEGRAM_CHAT_ID, is_owner
from soccersmartbet.utils.timezone import ISR_TZ

logger = logging.getLogger(__name__)

DATABASE_URL: str | None = os.getenv("DATABASE_URL")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
# Keyed by chat_id (int).  Each value is a dict with:
#   game_ids   : list[int]
#   games      : list[dict]  — enriched rows (info + odds)
#   selections : dict[int, str | None]   — game_id -> "1"/"x"/"2" or None
#   stakes     : dict[int, int]          — game_id -> NIS amount (default 100)
#   locked     : bool
_sessions: dict[int, dict] = {}

_STAKE_OPTIONS: list[int] = [50, 100, 200, 500]
_DEFAULT_STAKE: int = 100


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def _fetch_todays_game_ids() -> list[int]:
    """Query DB for today's games with status 'ready_for_betting'."""
    if not DATABASE_URL:
        return []
    today = datetime.now(tz=ISR_TZ).date()
    sql = """
        SELECT game_id FROM games
        WHERE match_date = %(today)s AND status = 'ready_for_betting'
        ORDER BY kickoff_time ASC
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"today": today})
                return [row[0] for row in cur.fetchall()]
    finally:
        conn.close()

def _fetch_min_kickoff(game_ids: list[int]) -> datetime | None:
    """Return the earliest kickoff_time for the given game IDs as a datetime.

    Args:
        game_ids: List of game primary keys.

    Returns:
        A naive datetime on today's date, or None if no rows found.
    """
    if not game_ids or not DATABASE_URL:
        return None

    sql = """
        SELECT kickoff_time
        FROM games
        WHERE game_id = ANY(%(game_ids)s)
        ORDER BY kickoff_time ASC
        LIMIT 1
    """
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"game_ids": game_ids})
                row = cur.fetchone()
    finally:
        conn.close()

    if row is None:
        return None

    kt = row[0]  # datetime.time from psycopg2
    today = datetime.now(tz=ISR_TZ).date()
    return datetime(today.year, today.month, today.day, kt.hour, kt.minute, tzinfo=ISR_TZ)


def _fetch_odds(game_ids: list[int]) -> dict[int, tuple[float, float, float]]:
    """Return {game_id: (home_win_odd, draw_odd, away_win_odd)} for each ID.

    Args:
        game_ids: List of game primary keys.

    Returns:
        Dict mapping game_id to a 3-tuple of odds floats.
    """
    if not game_ids or not DATABASE_URL:
        return {}

    sql = """
        SELECT game_id, home_win_odd, draw_odd, away_win_odd
        FROM games
        WHERE game_id = ANY(%(game_ids)s)
    """
    conn = psycopg2.connect(DATABASE_URL)
    odds: dict[int, tuple[float, float, float]] = {}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(sql, {"game_ids": game_ids})
                for row in cur.fetchall():
                    gid, h, d, a = row
                    odds[gid] = (float(h), float(d), float(a))
    finally:
        conn.close()

    return odds


def _fetch_user_balance() -> float:
    """Return the user's current bankroll total.

    Returns:
        Float balance in NIS, or 0.0 if not found.
    """
    if not DATABASE_URL:
        return 0.0

    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT total_bankroll FROM bankroll WHERE bettor = 'user'"
                )
                row = cur.fetchone()
    finally:
        conn.close()

    return float(row[0]) if row else 0.0


# ---------------------------------------------------------------------------
# UI builder
# ---------------------------------------------------------------------------

def _build_betting_ui(chat_id: int) -> tuple[str, InlineKeyboardMarkup]:
    """Build the betting message text and inline keyboard for the given session.

    Args:
        chat_id: The owner's chat ID used to look up the active session.

    Returns:
        (text, InlineKeyboardMarkup) ready to pass to send_message / edit_message_text.
    """
    session = _sessions[chat_id]
    games: list[dict] = session["games"]
    selections: dict[int, str | None] = session["selections"]
    stakes: dict[int, int] = session["stakes"]

    balance = _fetch_user_balance()
    lines: list[str] = [f"\U0001f4b0 Balance: {balance:,.0f} NIS", ""]

    for g in games:
        gid = g["game_id"]
        sel = selections.get(gid)
        pick = ""
        if sel == "1":
            pick = f"  \u2192 {g['home_team']}"
        elif sel == "x":
            pick = "  \u2192 Draw"
        elif sel == "2":
            pick = f"  \u2192 {g['away_team']}"
        lines.append(
            f"\u26bd {g['home_team']} vs {g['away_team']}"
            f" \u2014 {g['kickoff_time']} ISR"
            f" \u2014 {g['league']}"
            f"{pick}"
        )
    lines.append("")

    rows: list[list[InlineKeyboardButton]] = []

    for i, g in enumerate(games):
        gid = g["game_id"]
        sel = selections.get(gid)
        h_odd, d_odd, a_odd = g["h_odd"], g["d_odd"], g["a_odd"]
        stake = stakes.get(gid, _DEFAULT_STAKE)

        # 1 / X / 2 outcome row
        rows.append([
            InlineKeyboardButton(
                f"{'✅ ' if sel == '1' else ''}1 \u2014 {h_odd:.2f}",
                callback_data=f"gbet_{gid}_1",
            ),
            InlineKeyboardButton(
                f"{'✅ ' if sel == 'x' else ''}X \u2014 {d_odd:.2f}",
                callback_data=f"gbet_{gid}_x",
            ),
            InlineKeyboardButton(
                f"{'✅ ' if sel == '2' else ''}2 \u2014 {a_odd:.2f}",
                callback_data=f"gbet_{gid}_2",
            ),
        ])

        # Per-game stake row
        rows.append([
            InlineKeyboardButton(
                f"{'✅ ' if stake == s else ''}{s}",
                callback_data=f"gstake_{gid}_{s}",
            )
            for s in _STAKE_OPTIONS
        ])

        # Divider between games (not after the last game)
        if i < len(games) - 1:
            rows.append([
                InlineKeyboardButton("\u2500" * 25, callback_data="gnoop")
            ])

    all_selected = all(selections.get(g["game_id"]) is not None for g in games)
    send_label = "\U0001f4e9 SEND BET" if all_selected else "\u26a0\ufe0f Select all games first"
    rows.append([InlineKeyboardButton(send_label, callback_data="gsend_bet")])

    return "\n".join(lines), InlineKeyboardMarkup(rows)


# ---------------------------------------------------------------------------
# Public entry point: initial "want to bet?" prompt
# ---------------------------------------------------------------------------

async def send_want_to_bet(game_ids: list[int], bot: Bot) -> None:
    """Send the initial Yes/No "want to bet?" prompt to the owner.

    Queries the earliest kickoff time, subtracts 30 minutes for the
    deadline, then sends a message with Yes/No inline buttons.

    Args:
        game_ids: List of game IDs for today's slate.
        bot: An already-initialised Bot instance (used inside an async context).
    """
    if not TELEGRAM_CHAT_ID:
        logger.warning("send_want_to_bet: TELEGRAM_CHAT_ID not set, skipping")
        return

    earliest = _fetch_min_kickoff(game_ids)
    if earliest is not None:
        deadline_dt = earliest - timedelta(minutes=30)
        deadline_str = deadline_dt.strftime("%H:%M")
    else:
        deadline_str = "TBD"

    text = (
        "Gambling Time!\n\n"
        "Today's games are ready. Want to place your bets?\n"
        f"Deadline: {deadline_str} ISR"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Yes", callback_data="gamble_yes"),
            InlineKeyboardButton("No", callback_data="gamble_no"),
        ]
    ])

    await bot.send_message(
        chat_id=int(TELEGRAM_CHAT_ID),
        text=text,
        reply_markup=keyboard,
    )
    logger.info(
        "send_want_to_bet: prompt sent for %d game(s), deadline=%s",
        len(game_ids),
        deadline_str,
    )

    # Store game_ids in a bare session so the Yes handler can reuse them
    _sessions[int(TELEGRAM_CHAT_ID)] = {
        "game_ids": game_ids,
        "games": [],
        "selections": {},
        "stakes": {},
        "locked": False,
    }


# ---------------------------------------------------------------------------
# Callback router
# ---------------------------------------------------------------------------

async def handle_gamble_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Route all gambling-related inline keyboard callbacks.

    Handles the following callback_data prefixes:
      - ``gamble_yes``         — user taps Yes, initialise session and show UI
      - ``gamble_no``          — user declines, send farewell
      - ``gbet_{id}_{pick}``   — user selects 1/X/2 for a game
      - ``gstake_{id}_{amt}``  — user selects a stake amount for a game
      - ``gsend_bet``          — user confirms and locks bets
      - ``gnoop``              — divider tap, ignored

    Args:
        update: Incoming Telegram update.
        context: Handler context (unused but required by the framework).
    """
    query = update.callback_query
    if query is None:
        return

    if update.effective_chat is None:
        return

    chat_id = update.effective_chat.id
    if not is_owner(chat_id):
        logger.info(
            "handle_gamble_callback: ignoring callback from non-owner chat_id=%s",
            chat_id,
        )
        await query.answer()
        return

    await query.answer()

    data: str = query.data or ""

    # ------------------------------------------------------------------ gnoop
    if data == "gnoop":
        return

    # ---------------------------------------------------------------- gamble_no
    if data == "gamble_no":
        await query.edit_message_text("No bets today. See you tomorrow!")
        logger.info("handle_gamble_callback: user declined to bet")
        return

    # ---------------------------------------------------------------- gamble_yes
    if data == "gamble_yes":
        # Query DB for today's ready_for_betting games (works across processes)
        game_ids: list[int] = _fetch_todays_game_ids()

        if not game_ids:
            await query.edit_message_text("No games found for today.")
            logger.warning("handle_gamble_callback: gamble_yes but no ready games in DB")
            return

        games_info = get_games_info(game_ids)
        odds_map = _fetch_odds(game_ids)

        # Merge odds into each game info dict
        enriched: list[dict] = []
        for g in games_info:
            gid = g["game_id"]
            h_odd, d_odd, a_odd = odds_map.get(gid, (0.0, 0.0, 0.0))
            enriched.append({**g, "h_odd": h_odd, "d_odd": d_odd, "a_odd": a_odd})

        _sessions[chat_id] = {
            "game_ids": game_ids,
            "games": enriched,
            "selections": {g["game_id"]: None for g in enriched},
            "stakes": {g["game_id"]: _DEFAULT_STAKE for g in enriched},
            "locked": False,
        }

        text, kb = _build_betting_ui(chat_id)
        await query.edit_message_text(text=text, reply_markup=kb)
        logger.info(
            "handle_gamble_callback: betting UI initialised for %d game(s)", len(game_ids)
        )
        return

    # ----------------------------------------------------------- gbet_{id}_{pick}
    if data.startswith("gbet_"):
        session = _sessions.get(chat_id)
        if session is None or session["locked"]:
            return

        parts = data.split("_")
        # callback_data = "gbet_{game_id}_{pick}" — pick may be "1", "x", or "2"
        # split gives ["gbet", "{game_id}", "{pick}"]
        if len(parts) < 3:
            return

        try:
            game_id = int(parts[1])
        except ValueError:
            return

        pick = parts[2]
        session["selections"][game_id] = pick

        text, kb = _build_betting_ui(chat_id)
        await query.edit_message_text(text=text, reply_markup=kb)
        logger.info(
            "handle_gamble_callback: game_id=%s selection=%s", game_id, pick
        )
        return

    # --------------------------------------------------------- gstake_{id}_{amt}
    if data.startswith("gstake_"):
        session = _sessions.get(chat_id)
        if session is None or session["locked"]:
            return

        parts = data.split("_")
        # callback_data = "gstake_{game_id}_{amount}"
        # split gives ["gstake", "{game_id}", "{amount}"]
        if len(parts) < 3:
            return

        try:
            game_id = int(parts[1])
            amount = int(parts[2])
        except ValueError:
            return

        session["stakes"][game_id] = amount

        text, kb = _build_betting_ui(chat_id)
        await query.edit_message_text(text=text, reply_markup=kb)
        logger.info(
            "handle_gamble_callback: game_id=%s stake=%s", game_id, amount
        )
        return

    # --------------------------------------------------------------- gsend_bet
    if data == "gsend_bet":
        session = _sessions.get(chat_id)
        if session is None or session["locked"]:
            return

        selections: dict[int, str | None] = session["selections"]
        if not all(v is not None for v in selections.values()):
            # User tapped SEND BET without selecting all games — ignore
            return

        session["locked"] = True

        games: list[dict] = session["games"]
        stakes: dict[int, int] = session["stakes"]

        # Build the user_bets payload for the gambling flow
        user_bets: list[dict] = []
        lines: list[str] = [
            "\u2705 Bets accepted, passing forward to gambling flow to match with AI's bet.",
            "",
        ]

        for g in games:
            gid = g["game_id"]
            sel = selections[gid]
            stake = stakes.get(gid, _DEFAULT_STAKE)

            if sel == "1":
                pick_label = f"{g['home_team']} (1)"
                odds = g["h_odd"]
            elif sel == "x":
                pick_label = "Draw (X)"
                odds = g["d_odd"]
            else:
                pick_label = f"{g['away_team']} (2)"
                odds = g["a_odd"]

            returns = round(stake * odds, 2)
            profit = round(returns - stake, 2)

            lines.append(f"\u26bd {g['home_team']} vs {g['away_team']}")
            lines.append(
                f"    {pick_label} @ {odds:.2f} \u2014 {stake} NIS"
                f" \u2192 returns {returns} NIS (profit {profit} NIS)"
            )
            lines.append("")

            user_bets.append(
                {
                    "game_id": gid,
                    "prediction": sel,
                    "odds": odds,
                    "stake": float(stake),
                }
            )

        locked_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f512 Bets locked", callback_data="gnoop")]
        ])
        await query.edit_message_text(text="\n".join(lines), reply_markup=locked_kb)

        logger.info(
            "handle_gamble_callback: bets locked for %d game(s), invoking gambling flow",
            len(user_bets),
        )

        # Run the LangGraph gambling flow in a thread so the event loop stays free
        game_ids = session["game_ids"]

        async def _run_flow() -> None:
            from soccersmartbet.gambling_flow.graph_manager import run_gambling_flow  # noqa: PLC0415

            result = await asyncio.to_thread(run_gambling_flow, game_ids, user_bets)
            logger.info(
                "handle_gamble_callback: gambling flow completed — verification=%s",
                result.get("verification_result", "unknown"),
            )

        asyncio.create_task(_run_flow())
        return
