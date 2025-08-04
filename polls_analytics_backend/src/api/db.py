import os
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, DateTime, JSON, Index, select

load_dotenv()

Base = declarative_base()

class PollEventORM(Base):
    __tablename__ = "poll_events"

    id = Column(Integer, primary_key=True, index=True)
    event_id = Column(String, unique=True, index=True, nullable=False)
    poll_id = Column(String, index=True, nullable=False)
    event_type = Column(String, index=True, nullable=False)
    user_id = Column(String, index=True)
    session_id = Column(String)
    device_type = Column(String)
    platform = Column(String)
    geo = Column(String)
    timestamp = Column(DateTime, index=True)
    meta = Column(JSON)

    __table_args__ = (
        Index('ix_poll_id_event_type', 'poll_id', 'event_type'),
    )

def get_database_url():
    """Fetch PostgreSQL URL from environment variables."""
    user = os.environ.get("POSTGRES_USER")
    password = os.environ.get("POSTGRES_PASSWORD")
    host = os.environ.get("POSTGRES_URL")
    port = os.environ.get("POSTGRES_PORT")
    db = os.environ.get("POSTGRES_DB")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"

DATABASE_URL = get_database_url()
engine = create_async_engine(DATABASE_URL, future=True, echo=False)
SessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

# PUBLIC_INTERFACE
async def init_db():
    """Initialize the DB (create tables). Call on startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# PUBLIC_INTERFACE
async def is_duplicate_event(session: AsyncSession, event_id: str) -> bool:
    """
    Check for event_id existence for deduplication.
    """
    res = await session.execute(select(PollEventORM).where(PollEventORM.event_id == event_id))
    return res.scalar_one_or_none() is not None

# PUBLIC_INTERFACE
async def add_event(session: AsyncSession, event_data: dict):
    """
    Attempt to add an event into DB, skipping if duplicate event_id.
    Returns: True if added, False if duplicate.
    """
    if await is_duplicate_event(session, event_data["event_id"]):
        return False
    evt = PollEventORM(**event_data)
    session.add(evt)
    await session.commit()
    return True

# PUBLIC_INTERFACE
async def get_poll_events(session: AsyncSession, poll_id=None, start_time=None, end_time=None):
    """
    Get all events matching criteria (for analytics).
    """
    q = select(PollEventORM)
    if poll_id:
        q = q.where(PollEventORM.poll_id == poll_id)
    if start_time:
        q = q.where(PollEventORM.timestamp >= start_time)
    if end_time:
        q = q.where(PollEventORM.timestamp <= end_time)
    res = await session.execute(q)
    return res.scalars().all()
