from sqlalchemy import Column, String, DateTime, ForeignKey, Boolean, Text, JSON
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class VoteSession(Base):
    __tablename__ = "vote_sessions"

    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="open")  # open, revote, closed
    deadline = Column(DateTime(timezone=True), nullable=False)
    revote_deadline = Column(DateTime(timezone=True), nullable=True)
    winner_option_id = Column(String, nullable=True)
    is_random_winner = Column(Boolean, default=False)
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    options = relationship("VoteOption", back_populates="session")
    votes = relationship("Vote", back_populates="session")

class VoteOption(Base):
    __tablename__ = "vote_options"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("vote_sessions.id"), nullable=False)
    option_text = Column(String, nullable=False)
    option_description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    session = relationship("VoteSession", back_populates="options")

class Vote(Base):
    __tablename__ = "votes"

    id = Column(String, primary_key=True)
    session_id = Column(String, ForeignKey("vote_sessions.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    # ranked-choice ballot: ordered list of option ids, first = top choice
    rankings = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    session = relationship("VoteSession", back_populates="votes")
