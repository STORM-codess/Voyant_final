from sqlalchemy import Column, String, DateTime, ForeignKey
from datetime import datetime, timezone
from app.database import Base

class PendingInvite(Base):
    __tablename__ = "pending_invites"

    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    email = Column(String, nullable=False)
    invited_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
