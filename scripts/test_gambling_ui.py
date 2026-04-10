"""One-shot test: run the gambling UI prototype with working button handlers."""
from __future__ import annotations

import asyncio
import logging
import os

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

GAMES = [
    {"id": 5, "home": "PSG", "away": "Liverpool", "time": "22:00", "league": "UCL",
     "h_odd": 1.60, "d_odd": 4.10, "a_odd": 4.15},
    {"id": 6, "home": "Barcelona", "away": "Atlético Madrid", "time": "22:00", "league": "UCL",
     "h_odd": 1.45, "d_odd": 4.60, "a_odd": 4.90},
]

# State: {game_id: "1"/"x"/"2" or None}, {game_id: stake}
selections: dict[int, str | None] = {g["id"]: None for g in GAMES}
stakes: dict[int, int] = {g["id"]: 100 for g in GAMES}
bet_locked = False


def _build_message_and_keyboard() -> tuple[str, InlineKeyboardMarkup]:
    lines = ["\U0001f4b0 Balance: 10,000 NIS", ""]
    for g in GAMES:
        sel = selections[g["id"]]
        pick = ""
        if sel == "1":
            pick = f"  \u2192 {g['home']}"
        elif sel == "x":
            pick = "  \u2192 Draw"
        elif sel == "2":
            pick = f"  \u2192 {g['away']}"
        lines.append(f"\u26bd {g['home']} vs {g['away']} \u2014 {g['time']} ISR \u2014 {g['league']}{pick}")
    lines.append("")

    rows = []
    stake_options = [50, 100, 200, 500]
    for i, g in enumerate(GAMES):
        sel = selections[g["id"]]
        # 1/X/2 buttons
        rows.append([
            InlineKeyboardButton(
                f"{'✅ ' if sel == '1' else ''}1 \u2014 {g['h_odd']:.2f}",
                callback_data=f"bet_{g['id']}_1",
            ),
            InlineKeyboardButton(
                f"{'✅ ' if sel == 'x' else ''}X \u2014 {g['d_odd']:.2f}",
                callback_data=f"bet_{g['id']}_x",
            ),
            InlineKeyboardButton(
                f"{'✅ ' if sel == '2' else ''}2 \u2014 {g['a_odd']:.2f}",
                callback_data=f"bet_{g['id']}_2",
            ),
        ])
        # Per-game stake row
        rows.append([
            InlineKeyboardButton(
                f"{'✅ ' if stakes[g['id']] == s else ''}{s}",
                callback_data=f"stake_{g['id']}_{s}",
            )
            for s in stake_options
        ])
        # Divider between games (not after last)
        if i < len(GAMES) - 1:
            rows.append([InlineKeyboardButton("\u2500" * 25, callback_data="noop")])

    all_selected = all(v is not None for v in selections.values())
    label = "\U0001f4e9 SEND BET" if all_selected else "\u26a0\ufe0f Select all games first"
    rows.append([InlineKeyboardButton(label, callback_data="send_bet")])

    return "\n".join(lines), InlineKeyboardMarkup(rows)


async def _handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global current_stake
    query = update.callback_query
    if query is None:
        return
    await query.answer()

    data = query.data or ""

    global bet_locked
    if data == "noop" or bet_locked:
        return

    if data.startswith("bet_"):
        parts = data.split("_")
        game_id = int(parts[1])
        choice = parts[2]
        selections[game_id] = choice

    elif data.startswith("stake_"):
        parts = data.split("_")
        game_id = int(parts[1])
        amount = int(parts[2])
        stakes[game_id] = amount

    elif data == "send_bet":
        if not all(v is not None for v in selections.values()):
            return
        bet_locked = True

        # Build frozen message showing final selections
        lines = ["\u2705 Bets accepted, passing forward to gambling flow to match with AI's bet.", ""]
        for g in GAMES:
            sel = selections[g["id"]]
            stake = stakes[g["id"]]
            if sel == "1":
                pick_label, odds = f"{g['home']} (1)", g["h_odd"]
            elif sel == "x":
                pick_label, odds = "Draw (X)", g["d_odd"]
            else:
                pick_label, odds = f"{g['away']} (2)", g["a_odd"]
            returns = round(stake * odds, 2)
            profit = round(returns - stake, 2)
            lines.append(f"\u26bd {g['home']} vs {g['away']}")
            lines.append(f"    {pick_label} @ {odds:.2f} \u2014 {stake} NIS \u2192 returns {returns} NIS (profit {profit} NIS)")
            lines.append("")

        # Replace betting UI with frozen summary + locked button
        locked_kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("\U0001f512 Bets locked", callback_data="noop")]
        ])
        await query.edit_message_text(text="\n".join(lines), reply_markup=locked_kb)
        return

    text, kb = _build_message_and_keyboard()
    await query.edit_message_text(text=text, reply_markup=kb)


async def _send_initial(app: Application) -> None:
    """Send the initial betting message once bot is ready."""
    text, kb = _build_message_and_keyboard()
    bot = app.bot
    await bot.send_message(chat_id=CHAT_ID, text=text, reply_markup=kb)


def main() -> None:
    app = Application.builder().token(BOT_TOKEN).post_init(_send_initial).build()
    app.add_handler(CallbackQueryHandler(_handle_callback))
    print(f"Bot running — check Telegram (chat_id={CHAT_ID}). Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()
