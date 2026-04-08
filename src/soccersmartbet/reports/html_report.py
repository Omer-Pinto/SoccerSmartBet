from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg2

DATABASE_URL = os.getenv("DATABASE_URL")

_NOT_AVAILABLE = "Not available"

_FETCH_GAME_SQL = """
SELECT game_id, match_date, kickoff_time, home_team, away_team, league, venue,
       home_win_odd, away_win_odd, draw_odd
FROM games WHERE game_id = %(game_id)s
"""

_FETCH_GAME_REPORT_SQL = """
SELECT h2h_insights, weather_risk, venue
FROM game_reports WHERE game_id = %(game_id)s
LIMIT 1
"""

_FETCH_TEAM_REPORTS_SQL = """
SELECT team_name, recovery_days, form_trend, injury_impact, league_position, team_news
FROM team_reports WHERE game_id = %(game_id)s ORDER BY team_name
"""

_FETCH_EXPERT_SQL = """
SELECT expert_analysis
FROM expert_game_reports WHERE game_id = %(game_id)s
LIMIT 1
"""

_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: linear-gradient(135deg, #2d5a27 0%, #3d7a37 100%);
    min-height: 100vh;
    color: #ffffff;
    padding: 16px;
}

.container {
    max-width: 1100px;
    margin: 0 auto;
    padding: 16px;
}

/* Match Header */
.match-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(26, 26, 46, 0.95);
    border-radius: 16px;
    padding: 28px 24px;
    margin-bottom: 16px;
    border: 1px solid rgba(79, 195, 247, 0.3);
    flex-wrap: wrap;
    gap: 16px;
}

.team-badge {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    flex: 1;
    min-width: 140px;
}

.team-crest {
    width: 72px;
    height: 72px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    font-weight: 700;
    border: 3px solid;
}

.team-badge.home .team-crest {
    background: linear-gradient(135deg, #4caf50 0%, #388e3c 100%);
    border-color: #4caf50;
}

.team-badge.away .team-crest {
    background: linear-gradient(135deg, #f44336 0%, #c62828 100%);
    border-color: #f44336;
}

.team-name {
    font-size: 1.3rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    text-align: center;
}

.team-badge.home .team-name { color: #4caf50; }
.team-badge.away .team-name { color: #f44336; }

.match-center {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    min-width: 160px;
}

.vs-badge {
    font-size: 1.4rem;
    font-weight: 700;
    color: #f5a623;
    border: 2px solid #f5a623;
    border-radius: 50%;
    width: 52px;
    height: 52px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.match-datetime {
    font-size: 1rem;
    font-weight: 600;
    color: #f5a623;
    text-align: center;
}

.league-label {
    font-size: 0.8rem;
    color: rgba(255,255,255,0.6);
    padding: 4px 12px;
    background: rgba(255,255,255,0.1);
    border-radius: 4px;
    text-align: center;
}

.venue-label {
    font-size: 0.8rem;
    color: #4fc3f7;
    text-align: center;
}

/* Section card */
.section-card {
    background: rgba(26, 26, 46, 0.95);
    border-radius: 12px;
    padding: 20px;
    margin-bottom: 16px;
    border: 1px solid rgba(79, 195, 247, 0.3);
}

.section-title {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: rgba(255,255,255,0.6);
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
}

/* Odds */
.odds-row {
    display: flex;
    justify-content: center;
    gap: 16px;
    flex-wrap: wrap;
}

.odd-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 18px 28px;
    background: rgba(255,255,255,0.05);
    border-radius: 10px;
    border: 2px solid transparent;
    min-width: 110px;
}

.odd-card.home-win { border-color: #4caf50; }
.odd-card.draw     { border-color: #9e9e9e; }
.odd-card.away-win { border-color: #f44336; }

.odd-label {
    font-size: 1.2rem;
    font-weight: 700;
    margin-bottom: 4px;
}

.odd-value {
    font-size: 2.4rem;
    font-weight: 700;
    color: #f5a623;
    line-height: 1;
}

.odd-desc {
    font-size: 0.75rem;
    color: rgba(255,255,255,0.5);
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 1px;
}

/* Expert analysis */
.expert-card {
    background: rgba(26, 26, 46, 0.95);
    border-radius: 12px;
    padding: 24px;
    margin-bottom: 16px;
    border: 1px solid rgba(245, 166, 35, 0.4);
    border-left: 4px solid #f5a623;
}

.expert-title {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #f5a623;
    margin-bottom: 14px;
    display: flex;
    align-items: center;
    gap: 6px;
}

.expert-body {
    font-size: 0.95rem;
    line-height: 1.75;
    color: #e0e0e0;
    white-space: pre-wrap;
}

/* Comparison grid */
.comparison-grid {
    display: grid;
    grid-template-columns: 1fr 1fr 1fr;
    gap: 16px;
    margin-bottom: 16px;
}

@media (max-width: 900px) {
    .comparison-grid {
        grid-template-columns: 1fr;
    }
    .center-col { order: -1; }
}

.team-col {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.col-header {
    text-align: center;
    padding: 12px;
    border-radius: 8px;
    margin-bottom: 4px;
}

.team-col.home .col-header {
    background: linear-gradient(135deg, rgba(76,175,80,0.3) 0%, rgba(76,175,80,0.1) 100%);
    border: 1px solid #4caf50;
}

.team-col.away .col-header {
    background: linear-gradient(135deg, rgba(244,67,54,0.3) 0%, rgba(244,67,54,0.1) 100%);
    border: 1px solid #f44336;
}

.center-col {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.col-tag {
    display: block;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 3px;
    color: rgba(255,255,255,0.5);
    margin-bottom: 4px;
}

.col-title {
    display: block;
    font-size: 1.1rem;
    font-weight: 700;
    text-transform: uppercase;
}

/* Stat card */
.stat-card {
    background: rgba(26, 26, 46, 0.95);
    border-radius: 10px;
    padding: 16px;
    border: 1px solid rgba(79, 195, 247, 0.2);
}

.stat-label {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: rgba(255,255,255,0.5);
    margin-bottom: 10px;
}

.stat-body {
    font-size: 0.88rem;
    line-height: 1.65;
    color: #e0e0e0;
    white-space: pre-wrap;
}

/* Recovery badge */
.recovery-number {
    font-size: 2.4rem;
    font-weight: 700;
    display: block;
    margin-bottom: 4px;
}

.recovery-tag {
    display: inline-block;
    padding: 3px 12px;
    border-radius: 4px;
    font-size: 0.78rem;
    font-weight: 600;
}

.recovery-tag.short    { background: rgba(244,67,54,0.2);  color: #f44336; }
.recovery-tag.normal   { background: rgba(158,158,158,0.2); color: #9e9e9e; }
.recovery-tag.extended { background: rgba(76,175,80,0.2);  color: #4caf50; }

/* Match header responsive */
@media (max-width: 600px) {
    .match-header { flex-direction: column; align-items: center; }
    .team-badge { min-width: unset; width: 100%; }
    .odd-value { font-size: 1.8rem; }
}
"""


def _esc(value: Any) -> str:
    if value is None:
        return _NOT_AVAILABLE
    s = str(value)
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def _recovery_class(days: int | None) -> str:
    if days is None:
        return "normal"
    if days < 3:
        return "short"
    if days <= 5:
        return "normal"
    return "extended"


def _recovery_label(days: int | None) -> str:
    if days is None:
        return "Unknown"
    if days < 3:
        return "Short turnaround"
    if days <= 5:
        return "Normal rest"
    return "Well rested"


def _team_initials(name: str) -> str:
    parts = name.split()
    if len(parts) >= 2:
        return (parts[0][0] + parts[-1][0]).upper()
    return name[:2].upper()


def _team_card_html(team_name: str, report: dict[str, Any] | None, side: str) -> str:
    col_class = "home" if side == "home" else "away"
    tag = "HOME" if side == "home" else "AWAY"

    recovery_days = report["recovery_days"] if report else None
    r_class = _recovery_class(recovery_days)
    r_label = _recovery_label(recovery_days)
    r_display = str(recovery_days) if recovery_days is not None else "?"

    form_trend     = _esc(report["form_trend"] if report else None)
    injury_impact  = _esc(report["injury_impact"] if report else None)
    league_position = _esc(report["league_position"] if report else None)
    team_news      = _esc(report["team_news"] if report else None)

    return f"""
<div class="team-col {col_class}">
    <div class="col-header">
        <span class="col-tag">{tag}</span>
        <span class="col-title">{_esc(team_name)}</span>
    </div>

    <div class="stat-card">
        <div class="stat-label">League Position</div>
        <div class="stat-body">{league_position}</div>
    </div>

    <div class="stat-card">
        <div class="stat-label">Form Trend</div>
        <div class="stat-body">{form_trend}</div>
    </div>

    <div class="stat-card">
        <div class="stat-label">Recovery</div>
        <div style="text-align:center; margin-bottom:6px;">
            <span class="recovery-number" style="color: {'#f44336' if r_class == 'short' else ('#4caf50' if r_class == 'extended' else '#9e9e9e')};">{r_display}</span>
            <span style="display:block; font-size:0.78rem; color:rgba(255,255,255,0.5); margin-bottom:6px;">days since last match</span>
            <span class="recovery-tag {r_class}">{r_label}</span>
        </div>
    </div>

    <div class="stat-card">
        <div class="stat-label">Injury Impact</div>
        <div class="stat-body">{injury_impact}</div>
    </div>

    <div class="stat-card">
        <div class="stat-label">Team News</div>
        <div class="stat-body">{team_news}</div>
    </div>
</div>
"""


def _center_card_html(h2h_insights: str, weather_risk: str, venue_text: str) -> str:
    return f"""
<div class="center-col">
    <div class="col-header" style="background: rgba(79,195,247,0.1); border: 1px solid rgba(79,195,247,0.4);">
        <span class="col-tag">SHARED</span>
        <span class="col-title" style="color:#4fc3f7;">Match Data</span>
    </div>

    <div class="stat-card">
        <div class="stat-label">H2H Insights</div>
        <div class="stat-body">{_esc(h2h_insights)}</div>
    </div>

    <div class="stat-card">
        <div class="stat-label">Weather Risk</div>
        <div class="stat-body">{_esc(weather_risk)}</div>
    </div>

    <div class="stat-card">
        <div class="stat-label">Venue</div>
        <div class="stat-body">{_esc(venue_text)}</div>
    </div>
</div>
"""


def generate_game_report_html(game_id: int) -> str:
    """Query DB for all data about a game and return a complete self-contained HTML string."""
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

                cur.execute(_FETCH_GAME_REPORT_SQL, {"game_id": game_id})
                report_row = cur.fetchone()
                if report_row is not None:
                    h2h_insights, weather_risk, venue_from_report = report_row
                    h2h_insights  = h2h_insights  or _NOT_AVAILABLE
                    weather_risk  = weather_risk  or _NOT_AVAILABLE
                    venue_text    = venue_from_report or venue_from_games or _NOT_AVAILABLE
                else:
                    h2h_insights = weather_risk = _NOT_AVAILABLE
                    venue_text   = venue_from_games or _NOT_AVAILABLE

                cur.execute(_FETCH_TEAM_REPORTS_SQL, {"game_id": game_id})
                team_rows = cur.fetchall()
                team_map: dict[str, dict[str, Any]] = {}
                for row in team_rows:
                    t_name, recovery_days, form_trend, injury_impact, league_position, team_news = row
                    team_map[t_name] = {
                        "recovery_days": recovery_days,
                        "form_trend": form_trend,
                        "injury_impact": injury_impact,
                        "league_position": league_position,
                        "team_news": team_news,
                    }

                cur.execute(_FETCH_EXPERT_SQL, {"game_id": game_id})
                expert_row = cur.fetchone()
                expert_analysis = expert_row[0] if expert_row else _NOT_AVAILABLE
    finally:
        conn.close()

    home_report = team_map.get(home_team)
    away_report = team_map.get(away_team)

    # Format date/time display
    date_str    = str(match_date) if match_date else "TBD"
    time_str    = str(kickoff_time) if kickoff_time else "TBD"
    datetime_display = f"{date_str} — {time_str} ISR"

    home_initials = _team_initials(home_team)
    away_initials = _team_initials(away_team)

    home_win_odd_display = f"{float(home_win_odd):.2f}" if home_win_odd is not None else "—"
    draw_odd_display     = f"{float(draw_odd):.2f}"     if draw_odd     is not None else "—"
    away_win_odd_display = f"{float(away_win_odd):.2f}" if away_win_odd is not None else "—"

    home_col_html   = _team_card_html(home_team, home_report, "home")
    away_col_html   = _team_card_html(away_team, away_report, "away")
    center_col_html = _center_card_html(h2h_insights, weather_risk, venue_text)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{_esc(home_team)} vs {_esc(away_team)} — SoccerSmartBet</title>
<style>
{_CSS}
</style>
</head>
<body>
<div class="container">

    <!-- Match Header -->
    <div class="match-header">
        <div class="team-badge home">
            <div class="team-crest">{_esc(home_initials)}</div>
            <div class="team-name">{_esc(home_team)}</div>
        </div>

        <div class="match-center">
            <div class="vs-badge">VS</div>
            <div class="match-datetime">{_esc(datetime_display)}</div>
            <div class="league-label">{_esc(league)}</div>
            <div class="venue-label">{_esc(venue_text if venue_text != _NOT_AVAILABLE else "")}</div>
        </div>

        <div class="team-badge away">
            <div class="team-crest">{_esc(away_initials)}</div>
            <div class="team-name">{_esc(away_team)}</div>
        </div>
    </div>

    <!-- Odds -->
    <div class="section-card">
        <div class="section-title">&#127922; Odds (winner.co.il)</div>
        <div class="odds-row">
            <div class="odd-card home-win">
                <div class="odd-label">1</div>
                <div class="odd-value">{_esc(home_win_odd_display)}</div>
                <div class="odd-desc">Home Win</div>
            </div>
            <div class="odd-card draw">
                <div class="odd-label">X</div>
                <div class="odd-value">{_esc(draw_odd_display)}</div>
                <div class="odd-desc">Draw</div>
            </div>
            <div class="odd-card away-win">
                <div class="odd-label">2</div>
                <div class="odd-value">{_esc(away_win_odd_display)}</div>
                <div class="odd-desc">Away Win</div>
            </div>
        </div>
    </div>

    <!-- Expert Analysis -->
    <div class="expert-card">
        <div class="expert-title">&#129504; Expert Analysis</div>
        <div class="expert-body">{_esc(expert_analysis)}</div>
    </div>

    <!-- Three-column grid -->
    <div class="comparison-grid">
        {home_col_html}
        {center_col_html}
        {away_col_html}
    </div>

</div>
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
