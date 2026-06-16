from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import enum
from app.database import Base

class TripStatus(enum.Enum):
    planning = "planning"
    voting = "voting"
    completed = "completed"

class Trip(Base):
    __tablename__ = "trips"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    # destination & date are optional at creation — the whole point of Voyant
    # is the group decides the destination (via AI recs + voting) afterward.
    destination = Column(String, nullable=True)
    trip_date = Column(DateTime(timezone=True), nullable=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(TripStatus), default=TripStatus.planning)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    creator_id = Column(String, ForeignKey("users.id"), nullable=False)

    # relationships
    creator = relationship("User", back_populates="created_trips")
    members = relationship("TripMember", back_populates="trip")
    recommendations = relationship("Recommendation", back_populates="trip")
    forms = relationship("Form", back_populates="trip")

class TripMember(Base):
    __tablename__ = "trip_members"

    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    is_admin = Column(Boolean, default=False)

    # relationships
    trip = relationship("Trip", back_populates="members")
    user = relationship("User", back_populates="trip_memberships")