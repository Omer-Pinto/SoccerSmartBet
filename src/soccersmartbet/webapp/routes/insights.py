"""AI insights endpoint — 202 + poll flow backed by an in-memory job queue.

Routes
------
``POST /api/insights``
    Body ``{filter_dsl: str}``.  Runs the DSL through ``run_filter`` with a
    500-row cap, enqueues a background LLM call, returns ``202 {job_id}``.
    Returns ``422 {error: "empty_result"}`` when the filter yields zero rows
    (nothing to analyse).

``GET /api/insights/{job_id}``
    Returns the current job state plus ``markdown`` / ``error`` when
    terminal.  ``404`` if the id is unknown (never existed or already
    swept after the 1-hour TTL).

The POST handler must return within a couple of hundred milliseconds — the
LLM call runs as a background task gated by an ``asyncio.Semaphore(2)`` in
:mod:`soccersmartbet.webapp.insights.jobs`.  This respects the Wave 10
rule banning sync LLM calls from HTTP handlers.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from soccersmartbet.webapp.insights import jobs as jobs_module
from soccersmartbet.webapp.insights.jobs import InsightJob, enqueue, get, job_to_dict
from soccersmartbet.webapp.insights.prompt import generate_insights
from soccersmartbet.webapp.query.parser import ParseError
from soccersmartbet.webapp.query.service import run_filter

logger = logging.getLogger(__name__)

router = APIRouter()

# Row cap specific to insight generation — smaller than the history tab's
# default (2000) because a 500-row markdown table is already a sizeable LLM
# prompt (~10-30k tokens depending on the model's tokeniser).
_INSIGHT_ROW_CAP: int = 500


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class InsightRequest(BaseModel):
    filter_dsl: str = Field(
        default="",
        description="DSL filter string (see webapp/query/parser.py). Empty = full history.",
    )


# ---------------------------------------------------------------------------
# POST /api/insights
# ---------------------------------------------------------------------------


@router.post("/api/insights", status_code=202)
async def create_insight(body: InsightRequest) -> dict:
    """Kick off an insight-generation job.

    Synchronously runs ``run_filter`` (fast DB query) so we can reject
    empty results up-front, then spawns a background task for the LLM
    call and returns immediately with ``{job_id}``.
    """
    dsl = body.filter_dsl or ""

    try:
        result = await asyncio.to_thread(run_filter, dsl, _INSIGHT_ROW_CAP)
    except ParseError as exc:
        raise HTTPException(
            status_code=400,
            detail={"error": "parse_error", "detail": str(exc)},
        )

    if not result.rows:
        raise HTTPException(
            status_code=422,
            detail={"error": "empty_result"},
        )

    async def _worker(job: InsightJob) -> str:
        # The LLM call is sync — delegate to a worker thread so the event
        # loop stays responsive for the /api/insights/{id} poll endpoint.
        return await asyncio.to_thread(generate_insights, result)

    job = enqueue(dsl, result.aggregates.count, _worker)
    logger.info(
        "Insight job %s enqueued (rows=%d, dsl=%r)",
        job.job_id,
        result.aggregates.count,
        dsl,
    )
    return {
        "job_id": job.job_id,
        "state": job.state,
        "row_count": job.row_count,
        "row_cap_hit": result.row_cap_hit,
    }


# ---------------------------------------------------------------------------
# GET /api/insights/{job_id}
# ---------------------------------------------------------------------------


@router.get("/api/insights/{job_id}")
async def read_insight(job_id: str) -> dict:
    """Return the current job record, or 404 if unknown / swept."""
    job = get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail={"error": "unknown_job_id"})
    return job_to_dict(job)


# Exported for smoke-import / debugging; not part of the public HTTP surface.
__all__ = ["router", "jobs_module"]
