from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import HTMLResponse

from soccersmartbet.reports.html_report import generate_game_report_html

router = APIRouter()


@router.get("/reports/{game_id}", response_class=HTMLResponse)
def serve_report(game_id: int):
    """Serve a generated HTML report for a game."""
    try:
        html = generate_game_report_html(game_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if f"Game {game_id} not found" in html:
        raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

    return HTMLResponse(content=html)
