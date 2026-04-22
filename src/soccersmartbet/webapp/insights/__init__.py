"""AI insights subsystem for the SoccerSmartBet dashboard.

Holds the in-memory async job manager and the LLM prompt / call used by the
``POST /api/insights`` endpoint (Wave 12B).  Intentionally stateless across
process restarts — all job state lives in the ``_JOBS`` dict in
:mod:`soccersmartbet.webapp.insights.jobs`.
"""
