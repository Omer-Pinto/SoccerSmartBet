"""Fetch latest team news using FotMob API."""

from typing import Any, Dict, List

from ..fotmob_client import get_fotmob_client


def fetch_team_news(team_name: str, limit: int = 10) -> Dict[str, Any]:
    """Fetch latest news articles for a team.

    Uses FotMob's ``/api/data/tlnews`` endpoint which returns news articles
    aggregated from multiple sources in English.

    Args:
        team_name: Team name (e.g., "Barcelona", "Manchester City").
        limit: Maximum number of articles to return (default 10).

    Returns:
        Dictionary with keys:
            team_name (str): Resolved team name.
            articles (list[dict]): Each entry has ``title``, ``source``,
                ``published``, and ``language``.
            total_available (int): Total articles available on the server.
            error (str | None): Error message or ``None`` on success.
    """
    try:
        client = get_fotmob_client()

        team_info = client.find_team(team_name)
        if not team_info:
            return _error(team_name, f"Team '{team_name}' not found")

        news_data = client.get_team_news(team_info["id"])
        if not news_data:
            return _error(team_info.get("name", team_name), "Could not fetch team news")

        raw_articles: List[Dict[str, Any]] = news_data.get("data", [])
        total_available: int = news_data.get("totalItems", len(raw_articles))

        articles: List[Dict[str, Any]] = [
            {
                "title": item.get("title", ""),
                "source": item.get("sourceStr", ""),
                "published": item.get("gmtTime", ""),
                "language": item.get("language", ""),
            }
            for item in raw_articles[:limit]
        ]

        return {
            "team_name": team_info.get("name", team_name),
            "articles": articles,
            "total_available": total_available,
            "error": None,
        }

    except Exception as exc:
        return _error(team_name, str(exc))


def _error(team_name: str, msg: str) -> Dict[str, Any]:
    return {
        "team_name": team_name,
        "articles": [],
        "total_available": 0,
        "error": msg,
    }
