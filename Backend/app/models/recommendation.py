from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Integer
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    destination = Column(String, nullable=False)
    reasoning = Column(Text, nullable=False)
    # optional list of stops for a multi-city route, e.g.
    # [{"place": "Kochi", "nights": 2}, {"place": "Munnar", "nights": 3}].
    # null/empty for a single-base trip where `destination` is the whole stay.
    stops = Column(JSON, nullable=True)
    estimated_budget = Column(JSON, nullable=True)
    activities = Column(JSON, nullable=True)
    hotels = Column(JSON, nullable=True)
    # day-by-day itinerary, generated on demand for the plan detail view.
    # null until a user opens this recommendation and triggers generation.
    itinerary = Column(JSON, nullable=True)
    version = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    trip = relationship("Trip", back_populates="recommendations")