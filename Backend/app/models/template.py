from sqlalchemy import Column, String, DateTime, JSON, Text, Integer, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Template(Base):
    __tablename__ = "templates"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    icon = Column(String, nullable=True)
    is_custom = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    questions = relationship("TemplateQuestion", back_populates="template")
    forms = relationship("Form", back_populates="template")

class TemplateQuestion(Base):
    __tablename__ = "template_questions"

    id = Column(String, primary_key=True)
    template_id = Column(String, ForeignKey("templates.id"), nullable=False)  # was missing ForeignKey!
    question_text = Column(String, nullable=False)
    question_type = Column(String, nullable=False)
    options = Column(JSON, nullable=True)
    is_required = Column(Boolean, default=True)
    order = Column(Integer, nullable=False)
    placeholder = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    template = relationship("Template", back_populates="questions")