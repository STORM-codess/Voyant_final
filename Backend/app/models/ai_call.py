from sqlalchemy import Column, String, DateTime, Integer, Float, Boolean, Text
from datetime import datetime, timezone
from app.database import Base


class AICall(Base):
    """One row per AI model invocation through the gateway.

    This is the foundation for usage tracking, cost reporting, prompt A/B
    testing, and eval metrics — every later AI-maturity feature reads from here.
    """
    __tablename__ = "ai_calls"

    id = Column(String, primary_key=True)

    # what was called
    provider = Column(String, nullable=False)        # "groq" | "gemini"
    model = Column(String, nullable=False)           # e.g. "llama3-8b-8192"
    label = Column(String, nullable=True)            # human label from the gateway config

    # optional context tags (so cost can be sliced by feature/trip later)
    feature = Column(String, nullable=True)          # e.g. "recommendations"
    trip_id = Column(String, nullable=True)
    prompt_version = Column(String, nullable=True)   # set once Layer 2 (prompt versioning) lands

    # outcome
    success = Column(Boolean, nullable=False, default=False)
    fallback_position = Column(Integer, nullable=True)  # 0 = primary model, 1 = first fallback, ...
    latency_ms = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)              # truncated error string when success is False

    # usage + cost
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    total_tokens = Column(Integer, nullable=True)
    tokens_estimated = Column(Boolean, default=False)  # True if counted by char/4 fallback
    estimated_cost_usd = Column(Float, nullable=True)

    # Layer 4: output quality eval (set after a successful generation is scored)
    eval_score = Column(Float, nullable=True)
    eval_checks = Column(Text, nullable=True)  # JSON string of the per-check breakdown

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))