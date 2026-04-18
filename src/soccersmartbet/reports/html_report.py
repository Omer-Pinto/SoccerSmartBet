from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

_EL_LEAGUES = {"Europa League", "UEFA Europa League", "UEFA Europa Conference League", "Conference League"}

_FETCH_GAME_SQL = """
SELECT game_id, match_date, kickoff_time, home_team, away_team, league, venue,
       home_win_odd, away_win_odd, draw_odd
FROM games WHERE game_id = %(game_id)s
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

_CSS = """\
/* === reset === */
*{margin:0;padding:0;box-sizing:border-box}

/* === typography === */
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  font-size:14px;
  line-height:1.5;
  background:#0f0f0f;
  color:#d4d4d4;
  padding:12px;
}
h1,h2,h3{font-weight:600}

/* === header === */
.header{
  border-bottom:1px solid #222;
  padding-bottom:10px;
  margin-bottom:10px;
}
.header-teams{
  font-size:1.05rem;
  font-weight:700;
  color:#e8e8e8;
  letter-spacing:0.02em;
}
.header-sep{
  color:#555;
  padding:0 6px;
}
.header-meta{
  font-size:0.78rem;
  color:#888;
  margin-top:3px;
}

/* === odds === */
.odds-row{
  display:flex;
  align-items:center;
  gap:4px;
  font-size:0.88rem;
  color:#d4d4d4;
  padding:6px 0;
  border-bottom:1px solid #1a1a1a;
}
.odds-source{
  margin-left:auto;
  font-size:0.72rem;
  color:#555;
}

/* === probability bar === */
.prob-bar{
  display:flex;
  height:3px;
  width:100%;
  margin-bottom:10px;
  border-radius:1px;
  overflow:hidden;
}
.prob-home{background:#4a4a4a}
.prob-draw{background:#2a2a2a}
.prob-away{background:#3a3a3a}

/* === comparison table === */
.cmp-table{
  width:100%;
  border-collapse:collapse;
  margin-bottom:10px;
}
.cmp-table td{
  vertical-align:top;
  padding:7px 4px;
  border-bottom:1px solid #1a1a1a;
  font-size:0.82rem;
}
.cmp-table td.home-cell{
  width:38%;
  text-align:right;
  padding-right:8px;
}
.cmp-table td.label-cell{
  width:24%;
  text-align:center;
  color:#c8a84b;
  font-size:0.72rem;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.05em;
  white-space:nowrap;
}
.cmp-table td.away-cell{
  width:38%;
  text-align:left;
  padding-left:8px;
}

/* === pills === */
.pills{
  display:flex;
  gap:3px;
  flex-wrap:wrap;
  justify-content:flex-end;
}
.pills.away-pills{justify-content:flex-start}
.pill{
  display:inline-block;
  width:20px;
  height:20px;
  line-height:20px;
  text-align:center;
  font-size:0.68rem;
  font-weight:700;
  border-radius:2px;
  background:#242424;
  color:#aaa;
}
.pill-w{background:#1e2e1e;color:#5a8a5a}
.pill-d{background:#222;color:#888}
.pill-l{background:#2e1e1e;color:#8a5a5a}
.pill-q{background:#1c1c1c;color:#555}

/* === last-5 mini table === */
.l5-table{
  width:100%;
  border-collapse:collapse;
  font-size:0.72rem;
  margin-top:5px;
  color:#999;
}
.l5-table td{
  padding:2px 2px;
  border-bottom:1px solid #1a1a1a;
}
.l5-table td:first-child{text-align:center;width:18px}
.l5-table .l5-score{color:#bbb;font-variant-numeric:tabular-nums}

/* === bullets === */
.bullets{
  list-style:none;
  margin-top:5px;
}
.bullets li{
  font-size:0.78rem;
  color:#aaa;
  padding-left:10px;
  position:relative;
}
.bullets li::before{
  content:'·';
  position:absolute;
  left:0;
  color:#555;
}

/* === shared rows === */
.shared-row{
  padding:8px 0;
  border-bottom:1px solid #1a1a1a;
  font-size:0.82rem;
}
.shared-label{
  color:#c8a84b;
  font-size:0.72rem;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.05em;
  margin-bottom:4px;
}
.shared-body{color:#c0c0c0}
.cancel-risk{color:#b08040;font-size:0.75rem;margin-top:3px}

/* === expert === */
.expert-section{
  padding-top:10px;
}
.expert-title{
  color:#c8a84b;
  font-size:0.72rem;
  font-weight:600;
  text-transform:uppercase;
  letter-spacing:0.05em;
  margin-bottom:6px;
}

/* === utilities === */
.em{color:#888}
@media(max-width:375px){
  body{padding:8px;font-size:13px}
  .cmp-table td{padding:6px 2px;font-size:0.78rem}
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


def _pill(char: str) -> str:
    c = char.upper()
    css = {"W": "pill-w", "D": "pill-d", "L": "pill-l"}.get(c, "pill-q")
    return f'<span class="pill {css}">{_esc(c)}</span>'


def _form_pills_html(streak: str | None, side: str) -> str:
    if not streak:
        return '<span class="em">\u2014</span>'
    align_cls = "" if side == "home" else "away-pills"
    pills = "".join(_pill(ch) for ch in streak)
    return f'<div class="pills {align_cls}">{pills}</div>'


def _last5_html(last5: list[dict] | None, side: str) -> str:
    if not last5:
        return ""
    rows = ""
    for m in last5[:5]:
        result = _esc(m.get("result", "?"))
        gf = m.get("goals_for", "?")
        ga = m.get("goals_against", "?")
        opp = _esc(m.get("opponent", "\u2014"))
        ha = _esc(m.get("home_or_away", "?"))
        rows += (
            f"<tr>"
            f"<td>{result}</td>"
            f'<td class="l5-score">{gf}:{ga}</td>'
            f"<td>{opp}</td>"
            f"<td>{ha}</td>"
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
    pts_s = f"{pts} pts" if pts is not None else "\u2014"
    mp_s = f"{mp} MP" if mp is not None else "\u2014"
    summary = f"{rank_s} \u00b7 {pts_s} \u00b7 {mp_s}"
    bullets = _bullets_html(report.get("league_bullets"))
    return f"<div>{_esc(summary)}</div>{bullets}"


def _recovery_cell(report: dict | None) -> str:
    if report is None:
        return '<span class="em">\u2014</span>'
    days = report.get("recovery_days")
    if days is None:
        return '<span class="em">\u2014</span>'
    return f"{_esc(str(days))} days"


def _injuries_cell(report: dict | None) -> str:
    if report is None:
        return '<span class="em">\u2014</span>'
    bullets = report.get("injury_bullets") or []
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


def _prob_bar_html(h_odd: Any, d_odd: Any, a_odd: Any) -> str:
    try:
        h = 1 / float(h_odd)
        d = 1 / float(d_odd)
        a = 1 / float(a_odd)
        total = h + d + a
        hp = round(h / total * 100, 1)
        dp = round(d / total * 100, 1)
        ap = round(100 - hp - dp, 1)
        return (
            f'<div class="prob-bar">'
            f'<div class="prob-home" style="width:{hp}%"></div>'
            f'<div class="prob-draw" style="width:{dp}%"></div>'
            f'<div class="prob-away" style="width:{ap}%"></div>'
            f"</div>"
        )
    except (TypeError, ValueError, ZeroDivisionError):
        return ""


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
        aggregate = "H2H not tracked for this competition"
    elif h2h_total is not None and h2h_total > 0 and h2h_home and h2h_away:
        aggregate = (
            f"{_esc(h2h_home)} {h2h_hw or 0} "
            f"\u2013 {h2h_d or 0} draws "
            f"\u2013 {h2h_aw or 0} {_esc(h2h_away)}"
        )
    else:
        aggregate = "H2H: No data available."

    bullets = _bullets_html(h2h_bullets)
    return f'<div class="shared-body">{aggregate}</div>{bullets}'


def _weather_html(weather_bullets: list[str] | None, cancel_risk: str | None) -> str:
    if not weather_bullets:
        return '<span class="em">\u2014</span>'
    bullets = _bullets_html(weather_bullets)
    risk_line = ""
    if cancel_risk in ("medium", "high"):
        risk_line = f'<div class="cancel-risk">Weather cancellation risk: {_esc(cancel_risk)}.</div>'
    return bullets + risk_line


def generate_game_report_html(game_id: int) -> str:
    """Query DB and return a complete self-contained HTML string for one game."""
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(_FETCH_GAME_SQL, {"game_id": game_id})
                game_row = cur.fetchone()
                if game_row is None:
                    return f"<html><body><p>Game {game_id} not found.</p></body></html>"

                (
                    _gid, match_date, kickoff_time, home_team, away_team, league,
                    venue_from_games, home_win_odd, away_win_odd, draw_odd,
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
    finally:
        conn.close()

    home_report = team_map.get(home_team)
    away_report = team_map.get(away_team)

    date_str = str(match_date) if match_date else "\u2014"
    time_str = kickoff_time.strftime("%H:%M") if kickoff_time else "\u2014"

    h_odd_disp = f"{float(home_win_odd):.2f}" if home_win_odd is not None else "\u2014"
    d_odd_disp = f"{float(draw_odd):.2f}" if draw_odd is not None else "\u2014"
    a_odd_disp = f"{float(away_win_odd):.2f}" if away_win_odd is not None else "\u2014"

    prob_bar = _prob_bar_html(home_win_odd, draw_odd, away_win_odd)

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

    venue_html = (
        f'<div class="shared-row">'
        f'<div class="shared-label">Venue</div>'
        f'<div class="shared-body">{_esc(venue_display) if venue_display else "\u2014"}</div>'
        f'</div>'
    )

    expert_html = ""
    if expert_bullets:
        bullet_items = "".join(f"<li>{_esc(b)}</li>" for b in expert_bullets)
        expert_html = (
            f'<div class="expert-section">'
            f'<div class="expert-title">Expert analysis</div>'
            f'<ul class="bullets">{bullet_items}</ul>'
            f'</div>'
        )

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

<div class="header">
  <div class="header-teams">
    {_esc(home_team)}<span class="header-sep">vs</span>{_esc(away_team)}
  </div>
  <div class="header-meta">{_esc(date_str)} &middot; {_esc(time_str)} ISR &middot; {_esc(league)}</div>
</div>

<div class="odds-row">
  <span>1&nbsp;{_esc(h_odd_disp)}&nbsp;&middot;&nbsp;X&nbsp;{_esc(d_odd_disp)}&nbsp;&middot;&nbsp;2&nbsp;{_esc(a_odd_disp)}</span>
  <span class="odds-source">winner.co.il</span>
</div>
{prob_bar}

<table class="cmp-table">
{cmp_rows}
</table>

<div class="shared-row">
  <div class="shared-label">H2H</div>
  {h2h_content}
</div>

{venue_html}

<div class="shared-row">
  <div class="shared-label">Weather</div>
  <div class="shared-body">{weather_content}</div>
</div>

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
