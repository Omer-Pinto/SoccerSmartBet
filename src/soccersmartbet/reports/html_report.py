from __future__ import annotations

import base64
import logging
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Logos are embedded as base64 data URIs so they render from file:// pages
# (downloaded HTML attachments in Telegram's in-app browser block external
# https:// image requests from file:// origin). Cache is process-lifetime;
# entries are either a data URI string or None on failed fetch.
_LOGO_CACHE: dict[str, str | None] = {}
_LOGO_FETCH_TIMEOUT_S = 5


def _fetch_logo_data_uri(url: str) -> str | None:
    if url in _LOGO_CACHE:
        return _LOGO_CACHE[url]
    try:
        resp = requests.get(url, timeout=_LOGO_FETCH_TIMEOUT_S)
        if resp.status_code != 200:
            logger.info("logo fetch failed: %s -> %d", url, resp.status_code)
            _LOGO_CACHE[url] = None
            return None
        content_type = resp.headers.get("content-type", "image/png").split(";")[0].strip()
        encoded = base64.b64encode(resp.content).decode("ascii")
        data_uri = f"data:{content_type};base64,{encoded}"
        _LOGO_CACHE[url] = data_uri
        return data_uri
    except requests.RequestException as e:
        logger.info("logo fetch error for %s: %s", url, e)
        _LOGO_CACHE[url] = None
        return None

from soccersmartbet.db import get_conn

_EL_LEAGUES = {"Europa League", "UEFA Europa League", "UEFA Europa Conference League", "Conference League"}

# FotMob league IDs — verified 200 via curl before embedding
# Verified: 47 (PL), 87 (La Liga), 55 (Serie A), 54 (Bundesliga), 53 (Ligue 1), 42 (UCL), 73 (EL), 264 (Israeli)
FOTMOB_LEAGUE_ID: dict[str, int] = {
    "Premier League": 47,
    "La Liga": 87,
    "Serie A": 55,
    "Bundesliga": 54,
    "Ligue 1": 53,
    "Champions League": 42,
    "UEFA Champions League": 42,
    "Europa League": 73,
    "UEFA Europa League": 73,
    "Conference League": 10216,
    "UEFA Conference League": 10216,
    "UEFA Europa Conference League": 10216,
    "Israeli Premier League": 264,
    "\u05dc\u05d9\u05d2\u05ea Winner": 264,
}

_FETCH_GAME_SQL = """
SELECT g.game_id, g.match_date, g.kickoff_time, g.home_team, g.away_team, g.league, g.venue,
       g.home_win_odd, g.away_win_odd, g.draw_odd,
       th.fotmob_id AS home_fotmob_id,
       ta.fotmob_id AS away_fotmob_id
FROM games g
LEFT JOIN teams th ON th.canonical_name = g.home_team
                   OR th.aliases @> to_jsonb(g.home_team)
LEFT JOIN teams ta ON ta.canonical_name = g.away_team
                   OR ta.aliases @> to_jsonb(g.away_team)
WHERE g.game_id = %(game_id)s
"""

_FETCH_GAME_REPORT_SQL = """
SELECT h2h_home_team, h2h_away_team, h2h_home_team_wins, h2h_away_team_wins,
       h2h_draws, h2h_total_meetings, h2h_bullets,
       weather_bullets, weather_cancellation_risk, venue
FROM game_reports WHERE game_id = %(game_id)s
LIMIT 1
"""

_FETCH_TEAM_REPORTS_SQL = """
SELECT team_name, recovery_days, form_streak, last_5_games, form_bullets,
       league_rank, league_points, league_matches_played, league_bullets,
       injury_bullets, news_bullets
FROM team_reports WHERE game_id = %(game_id)s ORDER BY team_name
"""

_FETCH_EXPERT_SQL = """
SELECT expert_analysis
FROM expert_game_reports WHERE game_id = %(game_id)s
LIMIT 1
"""

# ---------------------------------------------------------------------------
# CSS — v6 green palette
# ---------------------------------------------------------------------------
_CSS = """\
/* === portrait overflow safety net === */
html,body{max-width:100vw;overflow-x:hidden}

/* === reset === */
*{margin:0;padding:0;box-sizing:border-box}

/* === typography === */
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  font-size:14px;
  line-height:1.5;
  background:#0d1410;
  color:#e4e4e4;
  padding:12px;
}
h1,h2,h3{font-weight:600}

/* === section cards — alternating backgrounds === */
.section-a{background:#121a15;padding:10px;margin-bottom:2px}
.section-b{background:#0f1512;padding:10px;margin-bottom:2px}
.section-header{
  background:#0d1410;
  padding:12px 0 12px 0;
  border-top:2px solid #2e6b2d;
  border-bottom:1px solid #1e2a22;
  margin-bottom:2px;
}

/* === hero === */
.header-teams{
  font-size:1.8rem;
  font-weight:700;
  color:#e4e4e4;
  letter-spacing:0.01em;
  line-height:1.2;
}
.header-sep{
  color:#8a938d;
  padding:0 8px;
  font-size:1.2rem;
  font-weight:400;
}
.header-meta{
  font-size:1.1rem;
  color:#8a938d;
  margin-top:5px;
}
.header-league{
  font-weight:600;
  color:#c8a84b;
}
/* team logo: inline next to team name in hero */
.team-logo{
  height:32px;
  width:auto;
  vertical-align:middle;
  margin-right:6px;
  display:inline-block;
}
/* league logo: inline before league name */
.league-logo{
  height:24px;
  width:auto;
  vertical-align:middle;
  margin-right:4px;
  display:inline-block;
}

/* === odds === */
.odds-row{
  display:flex;
  align-items:center;
  gap:6px;
  font-size:1.5rem;
  font-weight:700;
  color:#e4e4e4;
  padding:4px 0;
}
.odds-label{
  color:#e4e4e4;
  font-size:1.5rem;
  font-weight:700;
}
.odds-dot{
  color:#3d7a37;
  font-size:1.5rem;
  font-weight:700;
  padding:0 2px;
}
.odds-value{
  color:#c8a84b;
  font-size:1.5rem;
  font-weight:700;
}
.odds-sep{
  color:#1e2a22;
  font-size:1.2rem;
  padding:0 6px;
}
.odds-source{
  margin-left:auto;
  font-size:0.7rem;
  color:#888;
  font-weight:400;
  white-space:nowrap;
}

/* === comparison table — fixed layout, 3 cols: 40/20/40 === */
.cmp-table{
  width:100%;
  border-collapse:collapse;
  table-layout:fixed;
  max-width:100%;
}
.cmp-table th{
  padding:6px 4px;
  font-size:0.8rem;
  font-weight:600;
  color:#8a938d;
  border-bottom:1px solid #1e2a22;
  text-align:center;
  overflow-wrap:break-word;
  word-break:break-word;
}
.cmp-table th.th-home{
  width:40%;
  text-align:left;
  padding-left:8px;
  color:#e4e4e4;
}
.cmp-table th.th-label{
  width:20%;
  text-align:center;
}
.cmp-table th.th-away{
  width:40%;
  text-align:left;
  padding-left:8px;
  color:#e4e4e4;
}
.cmp-table td{
  vertical-align:top;
  padding:7px 4px;
  border-bottom:1px solid #1e2a22;
  font-size:0.82rem;
  text-align:left;
  overflow-wrap:break-word;
  word-break:break-word;
}
/* in-table bullets are smaller to fit narrow columns */
.cmp-table .bullets li{font-size:0.78rem}
.cmp-table td.home-cell{
  width:40%;
  text-align:left;
  padding-left:8px;
}
.cmp-table td.label-cell{
  width:20%;
  text-align:center;
  color:#c8a84b;
  font-size:0.72rem;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.05em;
  white-space:nowrap;
  border-left:2px solid #2e6b2d;
  border-right:2px solid #2e6b2d;
}
.cmp-table td.away-cell{
  width:40%;
  text-align:left;
  padding-left:8px;
}

/* === form pills — both sides left-aligned === */
.pills{
  display:flex;
  gap:3px;
  flex-wrap:wrap;
  justify-content:flex-start;
  align-items:flex-start;
}
.pill{
  display:inline-flex;
  width:22px;
  height:22px;
  align-items:center;
  justify-content:center;
  font-size:0.68rem;
  font-weight:700;
  border-radius:50%;
  background:#242424;
  color:#e4e4e4;
  flex-shrink:0;
}
.pill.w{background:#2e6b2d;color:#e4e4e4}
.pill.d{background:#4a4f4a;color:#e4e4e4}
.pill.l{background:#8a2a2a;color:#e4e4e4}
.pill.q{background:#1c1c1c;color:#555}
/* newest-pill underscore indicator: short bar below the circle, no vertical shift */
.pill-newest{
  display:inline-flex;
  flex-direction:column;
  align-items:center;
  vertical-align:top;
  flex-shrink:0;
}
.pill-newest-bar{
  margin-top:3px;
  width:60%;
  height:2px;
  border-radius:1px;
}
.pill-newest-bar.w{background:#2e6b2d}
.pill-newest-bar.d{background:#4a4f4a}
.pill-newest-bar.l{background:#8a2a2a}
.pill-newest-bar.q{background:#333}

/* === last-5 mini table: 100% width, fixed layout, % columns === */
.l5-table{
  width:100%;
  border-collapse:collapse;
  table-layout:fixed;
  font-size:0.72rem;
  margin-top:5px;
  color:#8a938d;
}
.l5-table td{
  padding:2px 2px;
  border-bottom:1px solid #1e2a22;
  overflow:hidden;
  white-space:nowrap;
}
/* result col: 15%, score col: 22%, opp col: 48%, h/a col: 15% */
.l5-table td:first-child{text-align:center;width:15%}
.l5-table .l5-score{color:#e4e4e4;font-variant-numeric:tabular-nums;width:22%}
.l5-table .l5-opp{width:48%;overflow:hidden;text-overflow:ellipsis}
.l5-table .l5-ha{width:15%;text-align:center}
.l5-res-w{color:#2e6b2d;font-weight:700}
.l5-res-d{color:#4a4f4a;font-weight:700}
.l5-res-l{color:#8a2a2a;font-weight:700}

/* === bullets — clean left-gutter === */
.bullets{list-style:none;padding-left:0;margin:6px 0}
.bullets li{
  position:relative;
  padding-left:16px;
  margin-bottom:4px;
  line-height:1.5;
  font-size:0.78rem;
  color:#8a938d;
}
.bullets li::before{
  content:"•";
  position:absolute;
  left:4px;
  top:0;
  color:#c8a84b;
}

/* === section labels with green left-rule === */
.shared-label{
  color:#c8a84b;
  font-size:0.72rem;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.05em;
  margin-bottom:4px;
  border-left:3px solid #2e6b2d;
  padding-left:7px;
}
.shared-body{color:#e4e4e4;font-size:0.82rem}
.cancel-risk{color:#c8a84b;font-size:0.75rem;margin-top:3px}

/* === h2h dot separators === */
.h2h-dot{
  color:#c8a84b;
  font-size:1.1rem;
  font-weight:700;
  padding:0 4px;
}

/* === expert === */
.expert-title{
  color:#c8a84b;
  font-size:0.72rem;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.05em;
  margin-bottom:6px;
  border-left:3px solid #2e6b2d;
  padding-left:7px;
}

/* === utilities === */
.em{color:#8a938d}
@media(max-width:420px){
  body{padding:8px;font-size:13px}
  .header-teams{font-size:1.5rem}
  .header-meta{font-size:0.95rem}
  .cmp-table td{padding:6px 2px;font-size:0.78rem}
  .cmp-table .bullets li{font-size:0.75rem}
  /* shrink pills so 5 fit in ~125px column */
  .cmp-table .pill{width:18px;height:18px;line-height:18px;font-size:0.62rem}
  .cmp-table .pill-newest-bar{width:60%;height:2px}
  .odds-row,.odds-label,.odds-dot,.odds-value{font-size:1.3rem}
  .team-logo{height:24px}
  .league-logo{height:18px}
}
@media(min-width:668px){
  body{max-width:660px;margin:0 auto}
}
"""


def _esc(value: Any) -> str:
    if value is None:
        return "\u2014"
    s = str(value)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def _bullets_html(items: list[str] | None, side: str = "") -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{_esc(b)}</li>" for b in items)
    return f'<ul class="bullets">{lis}</ul>'


def _pill_class(char: str) -> str:
    return {"W": "w", "D": "d", "L": "l"}.get(char.upper(), "q")


def _pill(char: str, newest: bool = False) -> str:
    c = char.upper()
    css = _pill_class(c)
    circle = f'<span class="pill {css}">{_esc(c)}</span>'
    if newest:
        bar = f'<span class="pill-newest-bar {css}"></span>'
        return f'<span class="pill-newest">{circle}{bar}</span>'
    return circle


def _form_pills_html(streak: str | None, side: str) -> str:
    if not streak:
        return '<span class="em">\u2014</span>'
    # Both sides left-aligned — no away-pills class needed.
    # form_streak is stored newest-first (same convention as last_5_games).
    # Reverse so pills read oldest→newest left-to-right; the rightmost pill
    # (last after reversal) is the most-recent result and gets the underscore.
    chars = list(reversed(streak))
    parts = []
    for i, ch in enumerate(chars):
        is_newest = (i == len(chars) - 1)
        parts.append(_pill(ch, newest=is_newest))
    pills = "".join(parts)
    return f'<div class="pills">{pills}</div>'


def _last5_html(last5: list[dict] | None, side: str) -> str:
    if not last5:
        return ""
    # last_5_games JSONB is stored oldest-first; render most-recent at top
    games = list(reversed(last5[:5]))
    rows = ""
    for m in games:
        result = (m.get("result") or "?").upper()
        gf = m.get("goals_for", "?")
        ga = m.get("goals_against", "?")
        opp = _esc(m.get("opponent", "\u2014"))
        ha = _esc(m.get("home_or_away", "?"))
        res_class = {"W": "l5-res-w", "D": "l5-res-d", "L": "l5-res-l"}.get(result, "")
        rows += (
            f"<tr>"
            f'<td class="{res_class}">{_esc(result)}</td>'
            f'<td class="l5-score">{gf}:{ga}</td>'
            f'<td class="l5-opp">{opp}</td>'
            f'<td class="l5-ha">{ha}</td>'
            f"</tr>"
        )
    return f'<table class="l5-table">{rows}</table>'


def _form_cell(report: dict | None, side: str) -> str:
    if report is None:
        return '<span class="em">\u2014</span>'
    streak = report.get("form_streak") or ""
    last5 = report.get("last_5_games") or []
    form_bullets = report.get("form_bullets") or []
    pills = _form_pills_html(streak, side)
    tbl = _last5_html(last5, side)
    bullets = _bullets_html(form_bullets)
    return pills + tbl + bullets


def _league_cell(report: dict | None) -> str:
    if report is None:
        return '<span class="em">\u2014</span>'
    rank = report.get("league_rank")
    pts = report.get("league_points")
    mp = report.get("league_matches_played")
    rank_s = str(rank) if rank is not None else "\u2014"
    pts_s = str(pts) if pts is not None else "\u2014"
    mp_s = str(mp) if mp is not None else "\u2014"
    summary = (
        f'{_esc(rank_s)}'
        f' · {_esc(pts_s)} pts'
        f' · {_esc(mp_s)} MP'
    )
    bullets = _bullets_html(report.get("league_bullets"))
    return f"<div>{summary}</div>{bullets}"


def _recovery_cell(report: dict | None) -> str:
    if report is None:
        return '<span class="em">\u2014</span>'
    days = report.get("recovery_days")
    if days is None:
        return '<span class="em">\u2014</span>'
    return f'{_esc(str(days))} days'


def _injuries_cell(report: dict | None) -> str:
    if report is None:
        return '<span class="em">\u2014</span>'
    bullets = report.get("injury_bullets") or []
    if not bullets:
        return '<span class="em">\u2014</span>'
    return _bullets_html(bullets)


def _news_cell(report: dict | None) -> str:
    if report is None:
        return '<span class="em">\u2014</span>'
    bullets = report.get("news_bullets") or []
    if not bullets:
        return '<span class="em">\u2014</span>'
    return _bullets_html(bullets)


def _cmp_row(home_content: str, label: str, away_content: str) -> str:
    return (
        f"<tr>"
        f'<td class="home-cell">{home_content}</td>'
        f'<td class="label-cell">{_esc(label)}</td>'
        f'<td class="away-cell">{away_content}</td>'
        f"</tr>"
    )


def _h2h_html(
    league: str,
    h2h_home: str | None,
    h2h_away: str | None,
    h2h_hw: int | None,
    h2h_aw: int | None,
    h2h_d: int | None,
    h2h_total: int | None,
    h2h_bullets: list[str] | None,
) -> str:
    if league in _EL_LEAGUES:
        fallback = "H2H not tracked for this competition"
        return (
            f'<div class="shared-label">H2H</div>'
            f'<div class="shared-body">{_esc(fallback)}</div>'
            + _bullets_html(h2h_bullets)
        )

    if h2h_total is not None and h2h_total > 0 and h2h_home and h2h_away:
        hw = h2h_hw or 0
        d = h2h_d or 0
        aw = h2h_aw or 0
        line = (
            f'<div class="shared-label">H2H</div>'
            f'<div class="shared-body">'
            f'<span>{_esc(h2h_home)}</span>'
            f'<span class="h2h-dot">·</span>'
            f'<span>{hw}</span>'
            f'<span class="h2h-dot"> — </span>'
            f'<span>Draws</span>'
            f'<span class="h2h-dot">·</span>'
            f'<span>{d}</span>'
            f'<span class="h2h-dot"> — </span>'
            f'<span>{_esc(h2h_away)}</span>'
            f'<span class="h2h-dot">·</span>'
            f'<span>{aw}</span>'
            f'</div>'
        )
        return line + _bullets_html(h2h_bullets)

    # text fallback
    fallback = "H2H: No data available."
    return (
        f'<div class="shared-label">H2H</div>'
        f'<div class="shared-body">{_esc(fallback)}</div>'
        + _bullets_html(h2h_bullets)
    )


def _weather_html(weather_bullets: list[str] | None, cancel_risk: str | None) -> str:
    if not weather_bullets:
        return '<span class="em">\u2014</span>'
    bullets = _bullets_html(weather_bullets)
    risk_line = ""
    if cancel_risk in ("medium", "high"):
        risk_line = f'<div class="cancel-risk">Weather cancellation risk: {_esc(cancel_risk)}.</div>'
    return bullets + risk_line


def _odds_row_html(h_odd_disp: str, d_odd_disp: str, a_odd_disp: str) -> str:
    """Render the odds as a single inline row."""
    return (
        f'<div class="odds-row">'
        f'<span class="odds-label">1</span>'
        f'<span class="odds-dot">·</span>'
        f'<span class="odds-value">{_esc(h_odd_disp)}</span>'
        f'<span class="odds-sep">|</span>'
        f'<span class="odds-label">X</span>'
        f'<span class="odds-dot">·</span>'
        f'<span class="odds-value">{_esc(d_odd_disp)}</span>'
        f'<span class="odds-sep">|</span>'
        f'<span class="odds-label">2</span>'
        f'<span class="odds-dot">·</span>'
        f'<span class="odds-value">{_esc(a_odd_disp)}</span>'
        f'<span class="odds-source">winner.co.il</span>'
        f'</div>'
    )


def _cmp_header_row(home_team: str, away_team: str) -> str:
    return (
        f"<tr>"
        f'<th class="th-home">{_esc(home_team)}</th>'
        f'<th class="th-label"></th>'
        f'<th class="th-away">{_esc(away_team)}</th>'
        f"</tr>"
    )


def generate_game_report_html(game_id: int) -> str:
    """Query DB and return a complete self-contained HTML string for one game."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(_FETCH_GAME_SQL, {"game_id": game_id})
            game_row = cur.fetchone()
            if game_row is None:
                return f"<html><body><p>Game {game_id} not found.</p></body></html>"

            (
                _gid, match_date, kickoff_time, home_team, away_team, league,
                venue_from_games, home_win_odd, away_win_odd, draw_odd,
                home_fotmob_id, away_fotmob_id,
            ) = game_row

            h2h_home = h2h_away = None
            h2h_hw = h2h_aw = h2h_d = h2h_total = None
            h2h_bullets: list[str] = []
            weather_bullets: list[str] = []
            cancel_risk: str | None = None
            venue_from_report: str | None = None

            cur.execute(_FETCH_GAME_REPORT_SQL, {"game_id": game_id})
            report_row = cur.fetchone()
            if report_row is not None:
                (
                    h2h_home, h2h_away, h2h_hw, h2h_aw, h2h_d, h2h_total,
                    h2h_bullets_raw, weather_bullets_raw, cancel_risk, venue_from_report,
                ) = report_row
                h2h_bullets = h2h_bullets_raw or []
                weather_bullets = weather_bullets_raw or []

            venue_display = venue_from_report or venue_from_games

            cur.execute(_FETCH_TEAM_REPORTS_SQL, {"game_id": game_id})
            team_rows = cur.fetchall()
            team_map: dict[str, dict[str, Any]] = {}
            for row in team_rows:
                (
                    t_name, recovery_days, form_streak, last5_raw, form_bullets_raw,
                    league_rank, league_points, league_mp, league_bullets_raw,
                    injury_bullets_raw, news_bullets_raw,
                ) = row
                team_map[t_name] = {
                    "recovery_days": recovery_days,
                    "form_streak": form_streak,
                    "last_5_games": last5_raw or [],
                    "form_bullets": form_bullets_raw or [],
                    "league_rank": league_rank,
                    "league_points": league_points,
                    "league_matches_played": league_mp,
                    "league_bullets": league_bullets_raw or [],
                    "injury_bullets": injury_bullets_raw or [],
                    "news_bullets": news_bullets_raw or [],
                }

            cur.execute(_FETCH_EXPERT_SQL, {"game_id": game_id})
            expert_row = cur.fetchone()
            expert_bullets: list[str] = expert_row[0] if expert_row else []
            if not isinstance(expert_bullets, list):
                expert_bullets = [str(expert_bullets)] if expert_bullets else []
        # read-only: no commit needed

    home_report = team_map.get(home_team)
    away_report = team_map.get(away_team)

    date_str = str(match_date) if match_date else "\u2014"
    time_str = kickoff_time.strftime("%H:%M") if kickoff_time else "\u2014"

    h_odd_disp = f"{float(home_win_odd):.2f}" if home_win_odd is not None else "\u2014"
    d_odd_disp = f"{float(draw_odd):.2f}" if draw_odd is not None else "\u2014"
    a_odd_disp = f"{float(away_win_odd):.2f}" if away_win_odd is not None else "\u2014"

    # --- logo HTML helpers ---
    _fotmob_team_base = "https://images.fotmob.com/image_resources/logo/teamlogo"
    _fotmob_league_base = "https://images.fotmob.com/image_resources/logo/leaguelogo"

    def _team_logo_img(fotmob_id: int | None) -> str:
        if fotmob_id is None:
            return ""
        url = f"{_fotmob_team_base}/{fotmob_id}.png"
        data_uri = _fetch_logo_data_uri(url)
        if data_uri is None:
            return ""
        return f'<img class="team-logo" src="{data_uri}" alt="">'

    def _league_logo_img(league_name: str | None) -> str:
        if not league_name:
            return ""
        lid = FOTMOB_LEAGUE_ID.get(league_name)
        if lid is None:
            return ""
        url = f"{_fotmob_league_base}/{lid}.png"
        data_uri = _fetch_logo_data_uri(url)
        if data_uri is None:
            return ""
        return f'<img class="league-logo" src="{data_uri}" alt="">'

    home_logo_html = _team_logo_img(home_fotmob_id)
    away_logo_html = _team_logo_img(away_fotmob_id)
    league_logo_html = _league_logo_img(league)

    cmp_header = _cmp_header_row(home_team, away_team)
    cmp_rows = "".join([
        _cmp_row(_form_cell(home_report, "home"), "Form", _form_cell(away_report, "away")),
        _cmp_row(_league_cell(home_report), "League", _league_cell(away_report)),
        _cmp_row(_recovery_cell(home_report), "Recovery", _recovery_cell(away_report)),
        _cmp_row(_injuries_cell(home_report), "Injuries", _injuries_cell(away_report)),
    ])

    h2h_content = _h2h_html(
        league or "",
        h2h_home, h2h_away, h2h_hw, h2h_aw, h2h_d, h2h_total, h2h_bullets,
    )

    weather_content = _weather_html(weather_bullets, cancel_risk)

    news_cmp_header = _cmp_header_row(home_team, away_team)
    news_cmp_row = _cmp_row(_news_cell(home_report), "", _news_cell(away_report))
    news_html = (
        f'<div class="section-b">'
        f'<div class="shared-label">News</div>'
        f'<table class="cmp-table">'
        f'{news_cmp_header}'
        f'{news_cmp_row}'
        f'</table>'
        f'</div>'
    )

    venue_html = (
        f'<div class="section-b">'
        f'<div class="shared-label">Venue</div>'
        f'<div class="shared-body">{_esc(venue_display) if venue_display else "\u2014"}</div>'
        f'</div>'
    )

    expert_html = ""
    if expert_bullets:
        bullet_items = "".join(f"<li>{_esc(b)}</li>" for b in expert_bullets)
        expert_html = (
            f'<div class="section-a">'
            f'<div class="expert-title">Expert analysis</div>'
            f'<ul class="bullets">{bullet_items}</ul>'
            f'</div>'
        )

    odds_html = _odds_row_html(h_odd_disp, d_odd_disp, a_odd_disp)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>{_esc(home_team)} vs {_esc(away_team)}</title>
<style>
{_CSS}
</style>
</head>
<body>

<div class="section-header">
  <div class="header-teams">
    {home_logo_html}{_esc(home_team)}<span class="header-sep">vs</span>{away_logo_html}{_esc(away_team)}
  </div>
  <div class="header-meta">
    {_esc(date_str)} · {_esc(time_str)} ISR ·
    {league_logo_html}<span class="header-league">{_esc(league or "\u2014")}</span>
  </div>
</div>

<div class="section-a">
{odds_html}
</div>

<div class="section-b">
<table class="cmp-table">
{cmp_header}
{cmp_rows}
</table>
</div>

<div class="section-a">
  {h2h_content}
</div>

{venue_html}

<div class="section-a">
  <div class="shared-label">Weather</div>
  <div class="shared-body">{weather_content}</div>
</div>

{news_html}

{expert_html}

</body>
</html>"""


def generate_all_reports(game_ids: list[int], output_dir: str) -> dict[int, str]:
    """Generate HTML files for multiple games. Returns {game_id: file_path}."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    result: dict[int, str] = {}
    for game_id in game_ids:
        html = generate_game_report_html(game_id)
        file_path = out_path / f"{game_id}.html"
        file_path.write_text(html, encoding="utf-8")
        result[game_id] = str(file_path)

    return result
