"""FastAPI backend for the web tool tester."""

import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Load .env file BEFORE importing tools (they read API keys on import)
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json

from soccersmartbet.pre_gambling_flow.tools.game.fetch_h2h import fetch_h2h
from soccersmartbet.pre_gambling_flow.tools.game.fetch_venue import fetch_venue
from soccersmartbet.pre_gambling_flow.tools.game.fetch_weather import fetch_weather
from soccersmartbet.pre_gambling_flow.tools.game.fetch_odds import fetch_odds
from soccersmartbet.pre_gambling_flow.tools.game.fetch_winner_odds import fetch_winner_odds
from soccersmartbet.pre_gambling_flow.tools.team.fetch_form import fetch_form
from soccersmartbet.pre_gambling_flow.tools.team.fetch_injuries import fetch_injuries
from soccersmartbet.pre_gambling_flow.tools.team.fetch_league_position import fetch_league_position
from soccersmartbet.pre_gambling_flow.tools.team.calculate_recovery_time import calculate_recovery_time
from soccersmartbet.pre_gambling_flow.tools.team.fetch_team_news import fetch_team_news
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
def root():
    """Serve the main HTML page."""
    html_path = Path(__file__).parent / "templates" / "index.html"
    return html_path.read_text()


@app.post("/api/fetch-match-data", response_model=MatchDataResponse)
def fetch_match_data(request: MatchRequest):
    """Fetch all data for a match using all available tools."""
    start_time = datetime.now()
    home_team = request.home_team.strip()
    away_team = request.away_team.strip()

    if not home_team or not away_team:
        raise HTTPException(status_code=400, detail="Both team names are required")

    # Step 0: Pre-warm FotMob cache for both teams (avoids thundering herd
    # when 14 threads all call find_team() on an empty cache simultaneously)
    client = get_fotmob_client()
    client.find_team(home_team)
    client.find_team(away_team)

    # Step 1: Get H2H data first (needed for match date)
    h2h_result = _run_tool("fetch_h2h", fetch_h2h, home_team, away_team, 10)

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
                    status = next_match.get("status", {})
                    utc_time = status.get("utcTime")
                    if utc_time:
                        match_datetime = utc_time
        except Exception:
            pass

    # If no match date from H2H, use tomorrow as fallback
    if not match_date:
        match_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    if not match_datetime:
        match_datetime = f"{match_date}T15:00:00"

    # Step 2: Run ALL remaining tools concurrently
    # Each future maps to (category, tool_name) so results can be sorted back
    game_tools = [h2h_result]
    home_team_tools: list[ToolResult] = []
    away_team_tools: list[ToolResult] = []

    _concurrent_tasks: dict[Any, tuple[str, str]] = {}

    with ThreadPoolExecutor(max_workers=14) as executor:
        # Game tools
        _concurrent_tasks[executor.submit(_run_tool, "fetch_venue", fetch_venue, home_team, away_team)] = ("game", "fetch_venue")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_weather", fetch_weather, home_team, away_team, match_datetime)] = ("game", "fetch_weather")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_odds", fetch_odds, home_team, away_team)] = ("game", "fetch_odds")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_winner_odds", fetch_winner_odds, home_team, away_team)] = ("game", "fetch_winner_odds")

        # Home team tools
        _concurrent_tasks[executor.submit(_run_tool, "fetch_form", fetch_form, home_team, 5)] = ("home", "fetch_form")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_injuries", fetch_injuries, home_team)] = ("home", "fetch_injuries")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_league_position", fetch_league_position, home_team)] = ("home", "fetch_league_position")
        _concurrent_tasks[executor.submit(_run_tool, "calculate_recovery_time", calculate_recovery_time, home_team, match_date)] = ("home", "calculate_recovery_time")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_team_news", fetch_team_news, home_team)] = ("home", "fetch_team_news")

        # Away team tools
        _concurrent_tasks[executor.submit(_run_tool, "fetch_form", fetch_form, away_team, 5)] = ("away", "fetch_form")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_injuries", fetch_injuries, away_team)] = ("away", "fetch_injuries")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_league_position", fetch_league_position, away_team)] = ("away", "fetch_league_position")
        _concurrent_tasks[executor.submit(_run_tool, "calculate_recovery_time", calculate_recovery_time, away_team, match_date)] = ("away", "calculate_recovery_time")
        _concurrent_tasks[executor.submit(_run_tool, "fetch_team_news", fetch_team_news, away_team)] = ("away", "fetch_team_news")

        for future in as_completed(_concurrent_tasks):
            category, _ = _concurrent_tasks[future]
            result = future.result()
            if category == "game":
                game_tools.append(result)
            elif category == "home":
                home_team_tools.append(result)
            else:
                away_team_tools.append(result)

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


@app.post("/api/stream-match-data")
async def stream_match_data(request: MatchRequest):
    """Stream tool results via SSE as each completes, instead of waiting for all."""
    home_team = request.home_team.strip()
    away_team = request.away_team.strip()

    if not home_team or not away_team:
        raise HTTPException(status_code=400, detail="Both team names are required")

    async def generate():
        loop = asyncio.get_event_loop()

        # Pre-warm FotMob cache for both teams
        client = get_fotmob_client()
        await loop.run_in_executor(None, client.find_team, home_team)
        await loop.run_in_executor(None, client.find_team, away_team)

        # H2H first — needed to extract match_date for other tools
        h2h_result = await loop.run_in_executor(
            None, lambda: _run_tool("fetch_h2h", fetch_h2h, home_team, away_team, 10)
        )
        yield f"data: {json.dumps({'category': 'game', 'result': h2h_result.model_dump()})}\n\n"

        # Extract match date
        match_date = None
        match_datetime = None
        if h2h_result.success and h2h_result.data.get("upcoming_match_date"):
            match_date = h2h_result.data["upcoming_match_date"]
            try:
                home_info = client.find_team(home_team)
                if home_info:
                    team_data = await loop.run_in_executor(
                        None, client.get_team_data, home_info["id"]
                    )
                    if team_data and team_data.get("overview", {}).get("nextMatch"):
                        next_match = team_data["overview"]["nextMatch"]
                        utc_time = next_match.get("status", {}).get("utcTime")
                        if utc_time:
                            match_datetime = utc_time
            except Exception:
                pass

        if not match_date:
            match_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        if not match_datetime:
            match_datetime = f"{match_date}T15:00:00"

        # Launch all 14 remaining tools concurrently, yield each as it completes
        tool_defs = [
            ("game", "fetch_venue", fetch_venue, [home_team, away_team]),
            ("game", "fetch_weather", fetch_weather, [home_team, away_team, match_datetime]),
            ("game", "fetch_odds", fetch_odds, [home_team, away_team]),
            ("game", "fetch_winner_odds", fetch_winner_odds, [home_team, away_team]),
            ("home", "fetch_form", fetch_form, [home_team, 5]),
            ("home", "fetch_injuries", fetch_injuries, [home_team]),
            ("home", "fetch_league_position", fetch_league_position, [home_team]),
            ("home", "calculate_recovery_time", calculate_recovery_time, [home_team, match_date]),
            ("home", "fetch_team_news", fetch_team_news, [home_team]),
            ("away", "fetch_form", fetch_form, [away_team, 5]),
            ("away", "fetch_injuries", fetch_injuries, [away_team]),
            ("away", "fetch_league_position", fetch_league_position, [away_team]),
            ("away", "calculate_recovery_time", calculate_recovery_time, [away_team, match_date]),
            ("away", "fetch_team_news", fetch_team_news, [away_team]),
        ]

        async def run_one(cat, name, func, args):
            result = await loop.run_in_executor(None, lambda: _run_tool(name, func, *args))
            return cat, result

        pending = [
            asyncio.create_task(run_one(cat, name, func, args))
            for cat, name, func, args in tool_defs
        ]

        for coro in asyncio.as_completed(pending):
            cat, result = await coro
            yield f"data: {json.dumps({'category': cat, 'result': result.model_dump()})}\n\n"

        yield 'data: {"done": true}\n\n'

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}


if __name__ == "__main__":
    import sys
    # Ensure src/ is on the path so soccersmartbet package resolves
    sys.path.insert(0, str(Path(__file__).parent.parent))
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
