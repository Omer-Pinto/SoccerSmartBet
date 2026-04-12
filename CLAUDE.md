# SoccerSmartBet — Project Rules

## TIMEZONE: ISR ONLY — NO EXCEPTIONS

**NEVER use `datetime.now()`, `datetime.now(ISR_TZ)`, `datetime.utcnow()`, or any raw datetime construction.**

ALWAYS use the helpers from `soccersmartbet.utils.timezone`:
- `now_isr()` — current time
- `utc_to_isr()` — convert API responses
- `format_isr_time()` — display HH:MM
- `format_isr_date()` — display YYYY-MM-DD

Before committing ANY code, grep for `datetime.now` — if it appears outside `utils/timezone.py`, the code is WRONG.

This rule has been violated 10+ times. There are no exceptions. No "it's technically equivalent." Use the utils.
