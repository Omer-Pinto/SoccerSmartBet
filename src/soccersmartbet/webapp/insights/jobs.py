"""In-memory async job manager for AI insight generation.

Design notes
------------
*   Storage is a process-wide ``dict[str, InsightJob]`` keyed by UUID4.
    Intentionally NOT backed by the database — this is a dashboard-only
    convenience surface; losing jobs on restart is acceptable.
*   Process-wide concurrency is capped via :class:`asyncio.Semaphore` at
    ``_MAX_CONCURRENT_JOBS`` LLM calls.  Excess jobs remain in the
    ``queued`` state until a slot frees up; the semaphore provides FIFO
    fairness.
*   Expired jobs are swept on each ``enqueue()`` call (lazy eviction — no
    background sweeper task).  Expiration is measured from ``created_at``
    to keep semantics simple; see the uncertainty list in the PR message.

All timestamps use :func:`soccersmartbet.utils.timezone.now_isr` — raw
stdlib clock helpers are banned per ``CLAUDE.md``.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable, Optional

from soccersmartbet.utils.timezone import now_isr

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

#: Maximum number of concurrent background LLM calls across the whole process.
_MAX_CONCURRENT_JOBS: int = 2

#: How long a finished / failed / queued job is retained before being swept.
_JOB_TTL: timedelta = timedelta(hours=1)

# ---------------------------------------------------------------------------
# Module-level state
# ---------------------------------------------------------------------------

#: Lazily-initialised semaphore gating the number of running LLM calls.
#: Built on first use so it binds to the active event loop (FastAPI's), not
#: whatever loop was current at import time.
_semaphore: Optional[asyncio.Semaphore] = None

#: All live job records, keyed by ``job_id`` (UUID4 hex).
_JOBS: dict[str, "InsightJob"] = {}


def _get_semaphore() -> asyncio.Semaphore:
    """Return the module-level semaphore, constructing it on first use."""
    global _semaphore
    if _semaphore is None:
        _semaphore = asyncio.Semaphore(_MAX_CONCURRENT_JOBS)
    return _semaphore


# ---------------------------------------------------------------------------
# Job record
# ---------------------------------------------------------------------------

JobState = str  # "queued" | "running" | "done" | "failed"


@dataclass
class InsightJob:
    """One AI-insight generation job.

    Args:
        job_id: UUID4 hex string.  Client polls against this.
        state: One of ``queued`` / ``running`` / ``done`` / ``failed``.
        filter_dsl: The raw DSL string the insight was computed against
            (echoed back for audit / debugging).
        row_count: Number of rows ``run_filter()`` returned (the input size
            of the LLM prompt).
        markdown: The LLM response body, populated only when ``state`` is
            ``done``.
        error: Short error message, populated only when ``state`` is
            ``failed``.
        created_at: When the job was enqueued.
        started_at: When the LLM call actually began (after the semaphore
            slot was acquired).
        finished_at: When the LLM call returned (success or failure).
    """

    job_id: str
    state: JobState
    filter_dsl: str
    row_count: int
    markdown: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=now_isr)
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def enqueue(
    filter_dsl: str,
    row_count: int,
    worker: Callable[["InsightJob"], Awaitable[str]],
) -> InsightJob:
    """Register a new :class:`InsightJob` and spawn its background task.

    Sweeps expired jobs as a side effect (lazy eviction).

    Args:
        filter_dsl: Raw DSL the job is about (stored on the job record).
        row_count: Number of rows from ``run_filter()`` — purely
            informational, surfaced in the poll response.
        worker: Async callable that receives the :class:`InsightJob` and
            returns the final markdown string.  The worker is expected to
            perform the LLM call; the semaphore guard is applied here.

    Returns:
        The newly-created :class:`InsightJob` (already inserted into
        ``_JOBS``).
    """
    _sweep_expired()

    job = InsightJob(
        job_id=uuid.uuid4().hex,
        state="queued",
        filter_dsl=filter_dsl,
        row_count=row_count,
    )
    _JOBS[job.job_id] = job

    asyncio.create_task(_run_job(job, worker))
    return job


def get(job_id: str) -> Optional[InsightJob]:
    """Look up a job by id.  Returns ``None`` if unknown or already swept."""
    return _JOBS.get(job_id)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


async def _run_job(
    job: InsightJob,
    worker: Callable[["InsightJob"], Awaitable[str]],
) -> None:
    """Background task body: wait for a slot, run the worker, record result."""
    sem = _get_semaphore()
    async with sem:
        job.state = "running"
        job.started_at = now_isr()
        try:
            markdown = await worker(job)
            job.markdown = markdown
            job.state = "done"
        except Exception as exc:  # noqa: BLE001  — propagate as job error
            job.error = f"{type(exc).__name__}: {exc}"[:2000]
            job.state = "failed"
            logger.exception("Insight job %s failed", job.job_id)
        finally:
            job.finished_at = now_isr()


def _sweep_expired() -> None:
    """Evict jobs whose ``created_at`` is older than ``_JOB_TTL``.

    Cheap linear scan — fine up to a few thousand entries.
    """
    cutoff = now_isr() - _JOB_TTL
    stale = [jid for jid, j in _JOBS.items() if j.created_at < cutoff]
    for jid in stale:
        _JOBS.pop(jid, None)
    if stale:
        logger.debug("Insight job sweeper evicted %d expired jobs", len(stale))


def job_to_dict(job: InsightJob) -> dict[str, Any]:
    """Serialise a job to the shape returned by ``GET /api/insights/{id}``."""
    payload: dict[str, Any] = {
        "job_id": job.job_id,
        "state": job.state,
        "row_count": job.row_count,
        "created_at_isr": job.created_at.isoformat(),
        "started_at_isr": job.started_at.isoformat() if job.started_at else None,
        "finished_at_isr": job.finished_at.isoformat() if job.finished_at else None,
    }
    if job.markdown is not None:
        payload["markdown"] = job.markdown
    if job.error is not None:
        payload["error"] = job.error
    return payload
