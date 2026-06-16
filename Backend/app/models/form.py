from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Integer, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.database import Base

class Form(Base):
    __tablename__ = "forms"

    id = Column(String, primary_key=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    template_id = Column(String, ForeignKey("templates.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(String, default="draft")
    created_by = Column(String, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    published_at = Column(DateTime(timezone=True), nullable=True)
    deadline = Column(DateTime(timezone=True), nullable=True)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    order_no = Column(Integer, nullable=False, default=1)

    # relationships
    trip = relationship("Trip", back_populates="forms")
    template = relationship("Template", back_populates="forms")
    questions = relationship("FormQuestion", back_populates="form")
    responses = relationship("FormResponse", back_populates="form")

class FormQuestion(Base):
    __tablename__ = "form_questions"

    id = Column(String, primary_key=True)
    form_id = Column(String, ForeignKey("forms.id"), nullable=False)
    question_text = Column(String, nullable=False)
    question_type = Column(String, nullable=False)
    options = Column(JSON, nullable=True)
    is_required = Column(Boolean, default=True)
    order = Column(Integer, nullable=False)
    placeholder = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    form = relationship("Form", back_populates="questions")
    answers = relationship("Answer", back_populates="question")

class FormResponse(Base):
    __tablename__ = "form_responses"

    id = Column(String, primary_key=True)
    form_id = Column(String, ForeignKey("forms.id"), nullable=False)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    is_complete = Column(Boolean, default=False)
    submitted_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    form = relationship("Form", back_populates="responses")
    answers = relationship("Answer", back_populates="response")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(String, primary_key=True)
    response_id = Column(String, ForeignKey("form_responses.id"), nullable=False)
    question_id = Column(String, ForeignKey("form_questions.id"), nullable=False)
    answer_text = Column(Text, nullable=True)
    answer_options = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # relationships
    response = relationship("FormResponse", back_populates="answers")
    question = relationship("FormQuestion", back_populates="answers")