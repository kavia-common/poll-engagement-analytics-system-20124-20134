from datetime import datetime
from typing import Optional, Dict
from pydantic import BaseModel, Field

# PUBLIC_INTERFACE
class PollEventIn(BaseModel):
    """Schema for an incoming poll event."""
    event_id: str = Field(..., description="Unique identifier for the event for deduplication")
    poll_id: str = Field(..., description="Poll identifier")
    event_type: str = Field(..., description="Event type, e.g., 'impression', 'vote'")
    user_id: Optional[str] = Field(None, description="Unique user identifier, if available")
    session_id: Optional[str] = Field(None, description="Session identifier")
    device_type: Optional[str] = Field(None, description="Device type (e.g. web, mobile, tv)")
    platform: Optional[str] = Field(None, description="Platform / OS (e.g. iOS, Android, Web)")
    geo: Optional[str] = Field(None, description="Geographic location (country/city)")
    timestamp: datetime = Field(..., description="Event timestamp in ISO8601 format")
    meta: Optional[Dict] = Field(None, description="Additional optional metadata (dict)")

# PUBLIC_INTERFACE
class PollEvent(PollEventIn):
    id: int = Field(..., description="Database-assigned ID")

# PUBLIC_INTERFACE
class PollSummaryRequest(BaseModel):
    poll_id: Optional[str] = Field(None, description="If provided, summary for this poll; otherwise, All Polls")

    # Optional: filter by time range, device, etc.
    start_time: Optional[datetime] = Field(None, description="Beginning of time range filter")
    end_time: Optional[datetime] = Field(None, description="End of time range filter")

# PUBLIC_INTERFACE
class PollSummaryResponse(BaseModel):
    poll_id: str = Field(..., description="Poll identifier")
    impressions: int = Field(..., description="Number of unique impressions")
    votes: int = Field(..., description="Number of votes cast")
    unique_users: int = Field(..., description="Number of unique users participated")
    device_breakdown: Dict[str, int] = Field(..., description="Device type -> count")
    platform_breakdown: Dict[str, int] = Field(..., description="Platform / OS -> count")
    geo_breakdown: Dict[str, int] = Field(..., description="Geo -> count")
    first_event: Optional[datetime] = Field(None, description="Timestamp of first event")
    last_event: Optional[datetime] = Field(None, description="Timestamp of last event")
