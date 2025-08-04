from fastapi import FastAPI, Depends, HTTPException, status, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .models import PollEventIn, PollSummaryResponse
from .db import SessionLocal, init_db, add_event, get_poll_events

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime

openapi_tags = [
    {
        "name": "Events",
        "description": "Endpoints to ingest poll engagement events."
    },
    {
        "name": "Analytics",
        "description": "Endpoints for poll analytics and aggregated metrics."
    }
]

app = FastAPI(
    title="Poll Engagement Analytics API",
    description=(
        "API for logging poll engagement events and exposing aggregated analytics "
        "to power dashboards and reporting for poll performance across devices."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    # Initialize/create tables
    await init_db()

@app.get("/", tags=["Events"])
def health_check():
    """Simple health check endpoint."""
    return {"message": "Healthy"}

# Dependency to provide DB session for each request
async def get_db():
    async with SessionLocal() as session:
        yield session

# PUBLIC_INTERFACE
@app.post(
    "/fanEngage/analytics/v1/events",
    summary="Ingest a poll engagement event (deduplicated).",
    description="Ingests an event (impression, vote, etc.) for a poll, with deduplication by `event_id`. Event data includes device, user, platform, geo, and timestamp.",
    response_description="Returns saved response or duplicate detected message.",
    tags=["Events"],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Created / accepted (not duplicate)", "content": {"application/json": {}}},
        409: {"description": "Duplicate, event ignored.", "content": {"application/json": {}}},
        400: {"description": "Validation error"},
    }
)
async def ingest_event(
    payload: PollEventIn = Body(..., description="Poll event data"),
    db: AsyncSession = Depends(get_db)
):
    """
    Receives poll event data, deduplicates using `event_id`, and inserts if new.
    Returns status (created or duplicate).
    """
    try:
        inserted = await add_event(db, payload.model_dump())
    except Exception as ex:
        raise HTTPException(status_code=400, detail=f"Event ingestion error: {ex}")

    if inserted:
        return JSONResponse(status_code=201, content={"status": "created"})
    else:
        return JSONResponse(status_code=409, content={"status": "duplicate"})

# PUBLIC_INTERFACE
@app.get(
    "/fanEngage/analytics/v1/pollSummary",
    summary="Get poll analytics summary (aggregated).",
    description="Aggregate analytics for polls, including impressions, votes, unique users, breakdown by device/platform/geo, and more. Filterable by poll, time window.",
    response_model=List[PollSummaryResponse],
    tags=["Analytics"],
    responses={
        200: {"description": "Aggregated poll analytics (one item per poll)", "content": {"application/json": {}}},
        400: {"description": "Validation error"}
    }
)
async def get_poll_summary(
    poll_id: Optional[str] = Query(None, description="Poll ID to query (aggregates over all if not provided)"),
    start_time: Optional[datetime] = Query(None, description="Start datetime (ISO8601)"),
    end_time: Optional[datetime] = Query(None, description="End datetime (ISO8601)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Returns aggregate analytics per poll. 
    If poll_id is omitted, summarizes all polls.
    """
    try:
        events = await get_poll_events(db, poll_id=poll_id, start_time=start_time, end_time=end_time)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Database error: {e}")

    # Organize: {poll_id: [events...]}
    from collections import defaultdict
    grouped = defaultdict(list)
    for e in events:
        grouped[e.poll_id].append(e)
    results = []
    for pid, entries in grouped.items():
        summary = {
            "poll_id": pid,
            "impressions": sum(1 for x in entries if x.event_type == "impression"),
            "votes": sum(1 for x in entries if x.event_type == "vote"),
            "unique_users": len(set(x.user_id for x in entries if x.user_id)),
            "device_breakdown": {},
            "platform_breakdown": {},
            "geo_breakdown": {},
            "first_event": min((x.timestamp for x in entries), default=None),
            "last_event": max((x.timestamp for x in entries), default=None)
        }
        # Device/Platform/Geo breakdown
        from collections import Counter
        summary["device_breakdown"] = dict(Counter(e.device_type or "Unknown" for e in entries))
        summary["platform_breakdown"] = dict(Counter(e.platform or "Unknown" for e in entries))
        summary["geo_breakdown"] = dict(Counter(e.geo or "Unspecified" for e in entries))
        results.append(summary)

    return results
