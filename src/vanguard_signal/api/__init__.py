"""
Vanguard Signal — FastAPI Backend

This package exposes the REST API that the dashboard UI and external
systems (SIEMs, analyst tools) consume.

Modules
-------
app          – FastAPI application factory with lifespan management
deps         – Dependency injection (DB session, current user, etc.)
routes/      – One module per resource:
    alerts       – CRUD for alerts, status transitions
    sources      – Source registry management
    evidence     – Evidence chain retrieval
    feedback     – Analyst confirm/dismiss verdicts
    dashboard    – Aggregate stats for the dashboard UI
    watchlist    – Keyword management
    detection    – Trigger detection cycles manually
"""
