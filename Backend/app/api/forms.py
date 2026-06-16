from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from datetime import datetime, timezone
from typing import Optional
from app.database import get_db
from app.models.template import Template, TemplateQuestion
from app.models.form import Form, FormQuestion, FormResponse, Answer
from app.models.trip import Trip, TripMember
from app.firebase import get_current_user
import uuid

router = APIRouter(prefix="/forms", tags=["forms"])

# ─── Pydantic Schemas ───────────────────────────────────────────

class QuestionEdit(BaseModel):
    id: Optional[str] = None        # None means new question
    question_text: str
    question_type: str              # single_choice, multiple_choice, text, scale, range
    options: Optional[list] = None
    is_required: bool = True
    order: int
    placeholder: Optional[str] = None

class CustomQuestionInput(BaseModel):
    question_text: str
    question_type: str  # single_choice | multiple_choice | text | scale | range
    options: Optional[list[str]] = None
    is_required: bool = False
    placeholder: Optional[str] = None


class CreateFormRequest(BaseModel):
    template_id: str
    title: str
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    # when provided, the form is built from THESE questions (admin-authored or
    # toggled from the bank) instead of copying the template's questions.
    custom_questions: Optional[list[CustomQuestionInput]] = None

class EditFormRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    questions: Optional[list[QuestionEdit]] = None

class AnswerItem(BaseModel):
    question_id: str
    answer_text: Optional[str] = None
    answer_options: Optional[list[str]] = None

class SubmitResponseRequest(BaseModel):
    answers: list[AnswerItem]


def serialize_form_member(member: TripMember):
    return {
        "id": member.id,
        "name": member.user.name if member.user else None,
        "email": member.user.email if member.user else None,
        "is_admin": member.is_admin,
    }

async def refresh_form_status(form: Form, db: AsyncSession):
    if form.status != "published":
        return

    now = datetime.now(timezone.utc)
    if form.deadline and now > form.deadline:
        form.status = "completed"
        form.closed_at = form.closed_at or now
        await db.commit()
        return

    member_ids_result = await db.execute(
        select(TripMember.user_id).where(TripMember.trip_id == form.trip_id)
    )
    member_count = len([row[0] for row in member_ids_result.all()])

    responses_result = await db.execute(
        select(FormResponse.user_id).where(
            FormResponse.form_id == form.id,
            FormResponse.is_complete == True
        )
    )
    submitted_count = len(set(responses_result.scalars().all()))

    if member_count > 0 and submitted_count >= member_count:
        form.status = "completed"
        form.closed_at = form.closed_at or now
        await db.commit()

# ─── Templates ──────────────────────────────────────────────────

@router.get("/templates")
async def get_templates(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all available templates"""
    result = await db.execute(select(Template))
    templates = result.scalars().all()

    response = []
    for template in templates:
        questions_result = await db.execute(
            select(TemplateQuestion)
            .where(TemplateQuestion.template_id == template.id)
            .order_by(TemplateQuestion.order)
        )
        questions = questions_result.scalars().all()

        response.append({
            "id": template.id,
            "name": template.name,
            "description": template.description,
            "icon": template.icon,
            "is_custom": template.is_custom,
            "question_count": len(questions),
            "questions": [
                {
                    "id": q.id,
                    "question_text": q.question_text,
                    "question_type": q.question_type,
                    "options": q.options,
                    "is_required": q.is_required,
                    "order": q.order,
                    "placeholder": q.placeholder
                }
                for q in questions
            ]
        })

    return response

# ─── Forms ──────────────────────────────────────────────────────

@router.post("/{trip_id}/create")
async def create_form(
    trip_id: str,
    request: CreateFormRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Creator picks a template and creates a form for the trip"""

    # check trip exists and user is creator
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # only trip members can create a form
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only trip members can create forms")

    # check if there is an active published form for this trip that still needs responses
    active_published_forms_result = await db.execute(
        select(Form).where(
            Form.trip_id == trip_id,
            Form.status == "published"
        )
        .order_by(Form.order_no)
    )
    active_published_forms = active_published_forms_result.scalars().all()

    for active_form in active_published_forms:
        await refresh_form_status(active_form, db)
    active_published_forms = [f for f in active_published_forms if f.status == "published"]

    if active_published_forms:
        member_ids_result = await db.execute(
            select(TripMember.user_id).where(TripMember.trip_id == trip_id)
        )
        member_ids = [row[0] for row in member_ids_result.all()]

        for active_form in active_published_forms:
            responses_result = await db.execute(
                select(FormResponse.user_id).where(
                    FormResponse.form_id == active_form.id,
                    FormResponse.is_complete == True
                )
            )
            submitted_user_ids = set(responses_result.scalars().all())
            pending = [uid for uid in member_ids if uid not in submitted_user_ids]
            if pending:
                raise HTTPException(status_code=400, detail="Current form must be completed first")

    # calculate order number for the new form
    last_form_result = await db.execute(
        select(Form)
        .where(Form.trip_id == trip_id)
        .order_by(Form.order_no.desc())
        .limit(1)
    )
    last_form = last_form_result.scalar_one_or_none()
    next_order = last_form.order_no + 1 if last_form else 1

    # ensure current user completed all previous published forms
    previous_published_forms_result = await db.execute(
        select(Form).where(
            Form.trip_id == trip_id,
            Form.order_no < next_order,
            Form.status == "published"
        )
    )
    previous_published_forms = previous_published_forms_result.scalars().all()
    for previous_form in previous_published_forms:
        await refresh_form_status(previous_form, db)
    previous_published_forms = [f for f in previous_published_forms if f.status == "published"]
    for previous_form in previous_published_forms:
        response_result = await db.execute(
            select(FormResponse)
            .where(
                FormResponse.form_id == previous_form.id,
                FormResponse.user_id == current_user["uid"],
                FormResponse.is_complete == True
            )
            .limit(1)
        )
        if not response_result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="You must complete previous forms first")

    # get template
    template_result = await db.execute(
        select(Template).where(Template.id == request.template_id)
    )
    template = template_result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    # create form
    form = Form(
        id=str(uuid.uuid4()),
        trip_id=trip_id,
        template_id=request.template_id,
        title=request.title,
        description=request.description,
        status="draft",
        created_by=current_user["uid"],
        order_no=next_order,
        deadline=request.deadline
    )
    db.add(form)
    await db.flush()

    # copy questions — from admin-authored custom_questions if given, else template
    VALID_TYPES = {"single_choice", "multiple_choice", "text", "scale", "range"}

    if request.custom_questions:
        if len(request.custom_questions) == 0:
            raise HTTPException(status_code=400, detail="A form needs at least one question")
        question_count = 0
        for i, cq in enumerate(request.custom_questions, start=1):
            if cq.question_type not in VALID_TYPES:
                raise HTTPException(status_code=400, detail=f"Invalid question type: {cq.question_type}")
            # choice questions need at least 2 options
            if cq.question_type in ("single_choice", "multiple_choice"):
                opts = [o.strip() for o in (cq.options or []) if o and o.strip()]
                if len(opts) < 2:
                    raise HTTPException(status_code=400, detail=f"'{cq.question_text}' needs at least 2 options")
            else:
                opts = cq.options or None
            if not cq.question_text or not cq.question_text.strip():
                raise HTTPException(status_code=400, detail="Every question needs text")
            db.add(FormQuestion(
                id=str(uuid.uuid4()),
                form_id=form.id,
                question_text=cq.question_text.strip(),
                question_type=cq.question_type,
                options=opts,
                is_required=cq.is_required,
                order=i,
                placeholder=cq.placeholder,
            ))
            question_count += 1
    else:
        questions_result = await db.execute(
            select(TemplateQuestion)
            .where(TemplateQuestion.template_id == request.template_id)
            .order_by(TemplateQuestion.order)
        )
        template_questions = questions_result.scalars().all()
        for tq in template_questions:
            db.add(FormQuestion(
                id=str(uuid.uuid4()),
                form_id=form.id,
                question_text=tq.question_text,
                question_type=tq.question_type,
                options=tq.options,
                is_required=tq.is_required,
                order=tq.order,
                placeholder=tq.placeholder
            ))
        question_count = len(template_questions)

    await db.commit()

    return {
        "message": "Form created successfully",
        "form_id": form.id,
        "template": template.name,
        "question_count": question_count,
        "status": "draft",
        "next_step": "Edit questions if needed, then publish"
    }

@router.put("/{trip_id}/edit")
async def edit_form(
    trip_id: str,
    request: EditFormRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Creator edits form title, description, or questions"""

    # check trip and creator
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.creator_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Only trip creator can edit forms")

    # get latest form draft for this trip
    form_result = await db.execute(
        select(Form)
        .where(Form.trip_id == trip_id)
        .order_by(Form.order_no.desc())
        .limit(1)
    )
    form = form_result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if form.status == "published":
        raise HTTPException(status_code=400, detail="Cannot edit a published form")

    # update title and description
    if request.title:
        form.title = request.title
    if request.description:
        form.description = request.description

    # update questions if provided
    if request.questions:
        # delete existing questions
        existing_questions = await db.execute(
            select(FormQuestion).where(FormQuestion.form_id == form.id)
        )
        for q in existing_questions.scalars().all():
            await db.delete(q)

        # add new questions
        for q in request.questions:
            form_question = FormQuestion(
                id=str(uuid.uuid4()),
                form_id=form.id,
                question_text=q.question_text,
                question_type=q.question_type,
                options=q.options,
                is_required=q.is_required,
                order=q.order,
                placeholder=q.placeholder
            )
            db.add(form_question)

    await db.commit()

    return {"message": "Form updated successfully"}

@router.post("/{trip_id}/publish")
async def publish_form(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Creator publishes form — members can now fill it"""

    # check trip and membership
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only trip members can publish forms")

    # get latest draft form for this trip
    form_result = await db.execute(
        select(Form)
        .where(Form.trip_id == trip_id, Form.status == "draft")
        .order_by(Form.order_no.desc())
        .limit(1)
    )
    form = form_result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")
    if form.status == "published":
        raise HTTPException(status_code=400, detail="Form is already published")

    form.status = "published"
    form.published_at = datetime.now(timezone.utc)
    await db.commit()

    return {
        "message": "Form published! Members can now fill it.",
        "form_id": form.id
    }

@router.get("/{trip_id}")
async def list_forms(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all forms for a trip, newest first"""
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    forms_result = await db.execute(
        select(Form)
        .where(Form.trip_id == trip_id)
        .order_by(Form.order_no.desc())
    )
    forms = forms_result.scalars().all()
    form_ids = [form.id for form in forms]

    submitted_counts = {}
    if form_ids:
        responses_result = await db.execute(
            select(FormResponse.form_id)
            .where(
                FormResponse.form_id.in_(form_ids),
                FormResponse.is_complete == True
            )
        )
        for row in responses_result.scalars().all():
            submitted_counts[row] = submitted_counts.get(row, 0) + 1

    return [
        {
            "id": form.id,
            "title": form.title,
            "description": form.description,
            "status": form.status,
            "order_no": form.order_no,
            "created_at": form.created_at.isoformat() if form.created_at else None,
            "published_at": form.published_at.isoformat() if form.published_at else None,
            "closed_at": form.closed_at.isoformat() if form.closed_at else None,
            "deadline": form.deadline.isoformat() if form.deadline else None,
            "submitted_count": submitted_counts.get(form.id, 0)
        }
        for form in forms
    ]

@router.get("/{trip_id}/form")
async def get_form(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get form with all questions for a trip"""

    # check member
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    # get latest form for this trip, including completed form state
    form_result = await db.execute(
        select(Form)
        .where(Form.trip_id == trip_id)
        .order_by(Form.order_no.desc())
        .limit(1)
    )
    form = form_result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    await refresh_form_status(form, db)

    # get questions
    questions_result = await db.execute(
        select(FormQuestion)
        .where(FormQuestion.form_id == form.id)
        .order_by(FormQuestion.order)
    )
    questions = questions_result.scalars().all()

    # check if current user already submitted
    response_result = await db.execute(
        select(FormResponse)
        .where(
            FormResponse.form_id == form.id,
            FormResponse.user_id == current_user["uid"]
        )
        .limit(1)
    )
    existing_response = response_result.scalar_one_or_none()

    existing_answers = []
    if existing_response:
        answers_result = await db.execute(
            select(Answer).where(Answer.response_id == existing_response.id)
        )
        existing_answers = [
            {
                "question_id": answer.question_id,
                "answer_text": answer.answer_text,
                "answer_options": answer.answer_options
            }
            for answer in answers_result.scalars().all()
        ]

    return {
        "form_id": form.id,
        "title": form.title,
        "description": form.description,
        "status": form.status,
        "deadline": form.deadline.isoformat() if form.deadline else None,
        "already_submitted": existing_response.is_complete if existing_response else False,
        "answers": existing_answers,
        "questions": [
            {
                "id": q.id,
                "question_text": q.question_text,
                "question_type": q.question_type,
                "options": q.options,
                "is_required": q.is_required,
                "order": q.order,
                "placeholder": q.placeholder
            }
            for q in questions
        ]
    }

@router.post("/{trip_id}/submit")
async def submit_form_response(
    trip_id: str,
    request: SubmitResponseRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Member submits their form response"""

    # check member
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    # get latest published form
    form_result = await db.execute(
        select(Form)
        .where(
            Form.trip_id == trip_id,
            Form.status == "published"
        )
        .order_by(Form.order_no.desc())
        .limit(1)
    )
    form = form_result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="No published form found")

    await refresh_form_status(form, db)
    if form.status != "published":
        raise HTTPException(status_code=400, detail="This form is no longer active")

    # validate answers against form questions
    questions_result = await db.execute(
        select(FormQuestion).where(FormQuestion.form_id == form.id)
    )
    questions = questions_result.scalars().all()
    question_map = {q.id: q for q in questions}

    errors = []
    seen_question_ids = set()
    for answer_data in request.answers:
        question = question_map.get(answer_data.question_id)
        if not question:
            errors.append(f"Unknown question_id: {answer_data.question_id}")
            continue
        if answer_data.question_id in seen_question_ids:
            errors.append(f"Duplicate answer for question: {question.question_text}")
            continue
        seen_question_ids.add(answer_data.question_id)

        selected = answer_data.answer_options or []
        if question.question_type == "single_choice":
            if len(selected) != 1:
                errors.append(f"'{question.question_text}' requires exactly one selected option")
            elif question.options and selected[0] not in question.options:
                errors.append(f"Invalid option for '{question.question_text}': {selected[0]}")
        elif question.question_type == "multiple_choice":
            if question.options:
                invalid_options = [o for o in selected if o not in question.options]
                if invalid_options:
                    errors.append(f"Invalid options for '{question.question_text}': {invalid_options}")

    # required questions must be answered with actual content
    for question in questions:
        if not question.is_required:
            continue
        if question.id not in seen_question_ids:
            errors.append(f"Required question not answered: {question.question_text}")
            continue
        answer_data = next(a for a in request.answers if a.question_id == question.id)
        has_text = bool(answer_data.answer_text and answer_data.answer_text.strip())
        if not has_text and not answer_data.answer_options:
            errors.append(f"Required question has empty answer: {question.question_text}")

    if errors:
        raise HTTPException(
            status_code=422,
            detail={"message": "Invalid form submission", "errors": errors}
        )

    # check if already submitted — if yes, update
    response_result = await db.execute(
        select(FormResponse)
        .where(
            FormResponse.form_id == form.id,
            FormResponse.user_id == current_user["uid"]
        )
        .limit(1)
    )
    existing_response = response_result.scalar_one_or_none()

    if existing_response:
        # delete old answers
        old_answers = await db.execute(
            select(Answer).where(Answer.response_id == existing_response.id)
        )
        for answer in old_answers.scalars().all():
            await db.delete(answer)
        form_response = existing_response
    else:
        # create new response
        form_response = FormResponse(
            id=str(uuid.uuid4()),
            form_id=form.id,
            user_id=current_user["uid"],
            is_complete=False
        )
        db.add(form_response)
        await db.flush()

    # save answers
    for answer_data in request.answers:
        answer = Answer(
            id=str(uuid.uuid4()),
            response_id=form_response.id,
            question_id=answer_data.question_id,
            answer_text=answer_data.answer_text,
            answer_options=answer_data.answer_options
        )
        db.add(answer)

    form_response.is_complete = True
    form_response.submitted_at = datetime.now(timezone.utc)

    # auto-complete form when all members have submitted
    member_ids_result = await db.execute(
        select(TripMember.user_id).where(TripMember.trip_id == trip_id)
    )
    member_count = len([row[0] for row in member_ids_result.all()])

    responses_result = await db.execute(
        select(FormResponse.user_id).where(
            FormResponse.form_id == form.id,
            FormResponse.is_complete == True
        )
    )
    submitted_count = len(set(responses_result.scalars().all()))

    if form.deadline and datetime.now(timezone.utc) > form.deadline:
        form.status = "completed"
        form.closed_at = datetime.now(timezone.utc)
    elif submitted_count == member_count and (not form.deadline or datetime.now(timezone.utc) >= form.deadline):
        form.status = "completed"
        form.closed_at = datetime.now(timezone.utc)

    await db.commit()

    return {"message": "Form submitted successfully"}

@router.get("/{trip_id}/status")
async def get_form_status(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get who has submitted and who hasn't"""

    # check member
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    # get all members with user metadata
    members_result = await db.execute(
        select(TripMember)
        .options(selectinload(TripMember.user))
        .where(TripMember.trip_id == trip_id)
    )
    members = members_result.scalars().all()

    # get latest form for this trip, including completed form state
    form_result = await db.execute(
        select(Form)
        .where(Form.trip_id == trip_id)
        .order_by(Form.order_no.desc())
        .limit(1)
    )
    form = form_result.scalar_one_or_none()
    if not form:
        raise HTTPException(status_code=404, detail="Form not found")

    await refresh_form_status(form, db)

    # get all responses
    responses_result = await db.execute(
        select(FormResponse).where(
            FormResponse.form_id == form.id,
            FormResponse.is_complete == True
        )
    )
    submitted_user_ids = {r.user_id for r in responses_result.scalars().all()}

    submitted = [m.user_id for m in members if m.user_id in submitted_user_ids]
    pending = [
        {
            "id": m.id,
            "user_id": m.user_id,
            "name": m.user.name if m.user else None,
            "email": m.user.email if m.user else None,
            "is_admin": m.is_admin,
            "joined_at": m.joined_at.isoformat() if m.joined_at else None,
        }
        for m in members if m.user_id not in submitted_user_ids
    ]

    return {
        "form_id": form.id,
        "form_status": form.status,
        "total_members": len(members),
        "submitted_count": len(submitted),
        "pending_count": len(pending),
        "submitted": submitted,
        "pending": pending,
        "all_submitted": len(pending) == 0
    }