"""FastAPI backend for the web tool tester."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any

# Load .env file BEFORE importing tools (they read API keys on import)
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from soccersmartbet.pre_gambling_flow.tools.game.fetch_h2h import fetch_h2h
from soccersmartbet.pre_gambling_flow.tools.game.fetch_venue import fetch_venue
from soccersmartbet.pre_gambling_flow.tools.game.fetch_weather import fetch_weather
from soccersmartbet.pre_gambling_flow.tools.game.fetch_odds import fetch_odds
from soccersmartbet.pre_gambling_flow.tools.team.fetch_form import fetch_form
from soccersmartbet.pre_gambling_flow.tools.team.fetch_injuries import fetch_injuries
from soccersmartbet.pre_gambling_flow.tools.team.fetch_league_position import fetch_league_position
from soccersmartbet.pre_gambling_flow.tools.team.calculate_recovery_time import calculate_recovery_time
from soccersmartbet.pre_gambling_flow.tools.fotmob_client import get_fotmob_client

app = FastAPI(
    title="SoccerSmartBet Tool Tester",
    description="Football-themed UI for testing data collection tools",
    version="1.0.0"
)

# Allow CORS for development (restricted to localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


class MatchRequest(BaseModel):
    """Request model for fetching match data."""
    home_team: str
    away_team: str


class ToolResult(BaseModel):
    """Wrapper for tool results with timing info."""
    tool_name: str
    success: bool
    data: dict[str, Any]
    error: str | None
    execution_time_ms: float


class MatchDataResponse(BaseModel):
    """Complete response with all tool results."""
    home_team: str
    away_team: str
    match_date: str | None
    game_tools: list[ToolResult]
    home_team_tools: list[ToolResult]
    away_team_tools: list[ToolResult]
    total_time_ms: float


def _run_tool(tool_name: str, func, *args, **kwargs) -> ToolResult:
    """Run a tool and capture timing/error info."""
    start = datetime.now()
    try:
        result = func(*args, **kwargs)
        error = result.get("error")
        return ToolResult(
            tool_name=tool_name,
            success=error is None,
            data=result,
            error=error,
            execution_time_ms=(datetime.now() - start).total_seconds() * 1000
        )
    except Exception as e:
        return ToolResult(
            tool_name=tool_name,
            success=False,
            data={},
            error=str(e),
            execution_time_ms=(datetime.now() - start).total_seconds() * 1000
        )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return html_path.read_text()


@app.post("/api/fetch-match-data", response_model=MatchDataResponse)
async def fetch_match_data(request: MatchRequest):
    """Fetch all data for a match using all available tools."""
    start_time = datetime.now()
    home_team = request.home_team.strip()
    away_team = request.away_team.strip()

    if not home_team or not away_team:
        raise HTTPException(status_code=400, detail="Both team names are required")

    # Step 1: Get H2H data first (needed for match date)
    h2h_result = _run_tool("fetch_h2h", fetch_h2h, home_team, away_team, 5)

    # Extract match date for other tools
    match_date = None
    match_datetime = None
    if h2h_result.success and h2h_result.data.get("upcoming_match_date"):
        match_date = h2h_result.data["upcoming_match_date"]
        # Try to get exact time from FotMob
        try:
            client = get_fotmob_client()
            home_info = client.find_team(home_team)
            if home_info:
                team_data = client.get_team_data(home_info["id"])
                if team_data and team_data.get("overview", {}).get("nextMatch"):
                    next_match = team_data["overview"]["nextMatch"]
                    if "utcTime" in next_match:
                        match_datetime = next_match["utcTime"]
        except Exception:
            pass

    # If no match date from H2H, use tomorrow as fallback
    if not match_date:
        from datetime import timedelta
        match_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    if not match_datetime:
        match_datetime = f"{match_date}T15:00:00"

    # Step 2: Run remaining game tools
    game_tools = [h2h_result]

    venue_result = _run_tool("fetch_venue", fetch_venue, home_team, away_team)
    game_tools.append(venue_result)

    weather_result = _run_tool("fetch_weather", fetch_weather, home_team, away_team, match_datetime)
    game_tools.append(weather_result)

    odds_result = _run_tool("fetch_odds", fetch_odds, home_team, away_team)
    game_tools.append(odds_result)

    # Step 3: Run home team tools
    home_team_tools = [
        _run_tool("fetch_form", fetch_form, home_team, 5),
        _run_tool("fetch_injuries", fetch_injuries, home_team),
        _run_tool("fetch_league_position", fetch_league_position, home_team),
        _run_tool("calculate_recovery_time", calculate_recovery_time, home_team, match_date),
    ]

    # Step 4: Run away team tools
    away_team_tools = [
        _run_tool("fetch_form", fetch_form, away_team, 5),
        _run_tool("fetch_injuries", fetch_injuries, away_team),
        _run_tool("fetch_league_position", fetch_league_position, away_team),
        _run_tool("calculate_recovery_time", calculate_recovery_time, away_team, match_date),
    ]

    total_time = (datetime.now() - start_time).total_seconds() * 1000

    return MatchDataResponse(
        home_team=home_team,
        away_team=away_team,
        match_date=match_date,
        game_tools=game_tools,
        home_team_tools=home_team_tools,
        away_team_tools=away_team_tools,
        total_time_ms=total_time
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
