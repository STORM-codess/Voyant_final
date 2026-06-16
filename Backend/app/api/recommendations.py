from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.database import get_db
from app.models.trip import Trip, TripMember
from app.models.form import Form, FormResponse, Answer, FormQuestion
from app.models.recommendation import Recommendation
from app.models.vote import VoteSession
from app.firebase import get_current_user
from app.services.ai_service import generate_recommendations, generate_itinerary
from app.services.prompts import get_prompt, list_prompts
from app.config import settings
from app.rate_limit import limiter
import uuid

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/prompt-versions")
async def get_prompt_versions(
    current_user: dict = Depends(get_current_user)
):
    """List available prompt versions and which is the default per feature."""
    return list_prompts()


@router.post("/{trip_id}/ab-test")
@limiter.limit(settings.RATE_LIMIT_AI)
async def ab_test_prompts(
    request: Request,
    trip_id: str,
    version_a: str = "recommendations_v1",
    version_b: str = "recommendations_v2",
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Run the SAME group form data through two prompt versions, score each
    output with the eval harness, and return a side-by-side comparison.

    This is the experiment behind 'A/B tested prompts': identical input, two
    prompts, objective quality scores. Both runs are logged to ai_calls with
    their prompt_version + eval_score, so the aggregate also shows up in
    /ai-metrics/by-prompt-version.
    """
    member = (await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"],
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a trip member")

    trip = (await db.execute(select(Trip).where(Trip.id == trip_id))).scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    form_data = await get_form_answers_for_ai(trip_id, db)
    if not form_data:
        raise HTTPException(status_code=400, detail="No form responses to test against.")

    from app.services.eval_service import evaluate_recommendations

    results = {}
    for label, version in [("A", version_a), ("B", version_b)]:
        try:
            parsed = await generate_recommendations(
                trip_name=trip.name, form_data=form_data,
                db=db, trip_id=trip_id, prompt_version=version,
            )
            ev = evaluate_recommendations(parsed, form_data=form_data)
            results[label] = {
                "prompt_version": version,
                "eval": ev.as_dict(),
                "item_count": len(parsed) if isinstance(parsed, list) else 0,
            }
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

    await db.commit()

    a_score = results["A"]["eval"]["score"]
    b_score = results["B"]["eval"]["score"]
    winner = "A" if a_score > b_score else "B" if b_score > a_score else "tie"

    return {
        "trip_id": trip_id,
        "comparison": results,
        "winner": winner,
        "score_delta": round(abs(a_score - b_score), 3),
    }

async def get_form_answers_for_ai(trip_id: str, db: AsyncSession) -> dict:
    """
    Read all form responses across every form for a trip and structure them for AI.
    Includes both published and completed forms (a form flips to 'completed' once
    everyone has answered, so it must still feed the AI).
    """
    # all forms that have been published at some point (published or completed)
    forms_result = await db.execute(
        select(Form).where(
            Form.trip_id == trip_id,
            Form.status.in_(["published", "completed"])
        ).order_by(Form.order_no)
    )
    forms = forms_result.scalars().all()
    if not forms:
        return {}

    aggregated = {}
    responder_ids = set()
    form_titles = []

    for form in forms:
        form_titles.append(form.title)

        responses_result = await db.execute(
            select(FormResponse).where(
                FormResponse.form_id == form.id,
                FormResponse.is_complete == True
            )
        )
        responses = responses_result.scalars().all()
        if not responses:
            continue

        questions_result = await db.execute(
            select(FormQuestion).where(
                FormQuestion.form_id == form.id
            ).order_by(FormQuestion.order)
        )
        question_map = {q.id: q.question_text for q in questions_result.scalars().all()}

        for response in responses:
            responder_ids.add(response.user_id)
            answers_result = await db.execute(
                select(Answer).where(Answer.response_id == response.id)
            )
            for answer in answers_result.scalars().all():
                question_text = question_map.get(answer.question_id, "Unknown")
                aggregated.setdefault(question_text, [])
                if answer.answer_text:
                    aggregated[question_text].append(answer.answer_text)
                if answer.answer_options:
                    aggregated[question_text].extend(answer.answer_options)

    if not aggregated:
        return {}

    # group size = distinct trip members (not response count)
    member_count_result = await db.execute(
        select(func.count(TripMember.user_id)).where(TripMember.trip_id == trip_id)
    )
    group_size = member_count_result.scalar() or len(responder_ids)

    return {
        "form_title": ", ".join(form_titles),
        "total_responses": len(responder_ids),
        "group_size": group_size,
        "answers": aggregated
    }

@router.post("/{trip_id}/generate")
@limiter.limit(settings.RATE_LIMIT_AI)
async def generate_trip_recommendations(
    request: Request,
    trip_id: str,
    prompt_version: str = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # check trip exists
    trip_result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # check user is member AND admin (only the trip admin generates,
    # consistent with admin-only invites)
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    member = member_result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a trip member")
    if not member.is_admin:
        raise HTTPException(
            status_code=403,
            detail="Only the trip admin can generate recommendations."
        )

    # lock generation once voting is underway — recommendations are the
    # ballot, so they must not change after a vote session opens
    active_vote = await db.execute(
        select(VoteSession).where(
            VoteSession.trip_id == trip_id,
            VoteSession.status.in_(["open", "revote"])
        )
    )
    if active_vote.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="Voting is open — recommendations are locked and cannot be regenerated."
        )

    # get form answers
    form_data = await get_form_answers_for_ai(trip_id, db)
    if not form_data:
        raise HTTPException(
            status_code=400,
            detail="No form responses found. Make sure form is published and members have responded."
        )

    # get current version number
    version_result = await db.execute(
        select(func.max(Recommendation.version)).where(
            Recommendation.trip_id == trip_id
        )
    )
    current_version = version_result.scalar() or 0
    new_version = current_version + 1

    # generate AI recommendations via gateway
    # generate AI recommendations via gateway
    try:
        recommendations = await generate_recommendations(
            trip_name=trip.name,
            form_data=form_data,
            db=db,
            trip_id=trip_id,
            prompt_version=prompt_version,
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # save to database with version number
    saved = []
    for rec in recommendations:
        if not isinstance(rec, dict) or not rec.get("destination"):
            continue  # skip malformed items rather than crashing the request
        new_rec = Recommendation(
            id=str(uuid.uuid4()),
            trip_id=trip_id,
            destination=rec["destination"],
            reasoning=rec.get("reasoning", ""),
            stops=rec.get("stops", []),
            estimated_budget=rec.get("estimated_budget", {}),
            activities=rec.get("best_activities", []),
            hotels=rec.get("hotels", []),
            version=new_version
        )
        db.add(new_rec)
        saved.append(new_rec)

    if not saved:
        raise HTTPException(
            status_code=502,
            detail="AI returned no usable recommendations. Try generating again."
        )

    await db.commit()

    return {
        "message": f"Generation {new_version} complete",
        "version": new_version,
        "prompt_version": get_prompt("recommendations", prompt_version).version,
        "form_data": form_data,
        "recommendations": recommendations
    }

@router.get("/{trip_id}")
async def get_recommendations(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # check user is member
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    # get all recommendations grouped by version
    result = await db.execute(
        select(Recommendation).where(
            Recommendation.trip_id == trip_id
        ).order_by(Recommendation.version, Recommendation.created_at)
    )
    recommendations = result.scalars().all()

    # group by version
    grouped = {}
    for rec in recommendations:
        version = rec.version
        if version not in grouped:
            grouped[version] = []
        grouped[version].append({
            "id": rec.id,
            "destination": rec.destination,
            "stops": rec.stops or [],
            "reasoning": rec.reasoning,
            "estimated_budget": rec.estimated_budget,
            "activities": rec.activities,
            "has_itinerary": rec.itinerary is not None,
            "version": rec.version,
            "created_at": rec.created_at
        })

    return {
        "trip_id": trip_id,
        "total_recommendations": len(recommendations),
        "generations": len(grouped),
        "recommendations_by_version": grouped
    }

@router.get("/{trip_id}/{recommendation_id}")
async def get_single_recommendation(
    trip_id: str,
    recommendation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # check user is member
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    result = await db.execute(
        select(Recommendation).where(
            Recommendation.id == recommendation_id,
            Recommendation.trip_id == trip_id
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    return rec


@router.post("/{trip_id}/{recommendation_id}/itinerary")
@limiter.limit(settings.RATE_LIMIT_AI)
async def generate_recommendation_itinerary(
    request: Request,
    trip_id: str,
    recommendation_id: str,
    days: int = 5,
    regenerate: bool = False,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Generate (or return cached) a day-by-day itinerary for one
    recommendation. Any trip member can view/generate it; the result is
    stored on the recommendation so it's only generated once unless
    ?regenerate=true is passed.
    """
    # membership check
    member = (await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"],
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a trip member")

    trip = (await db.execute(select(Trip).where(Trip.id == trip_id))).scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    rec = (await db.execute(
        select(Recommendation).where(
            Recommendation.id == recommendation_id,
            Recommendation.trip_id == trip_id,
        )
    )).scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")

    # return cached itinerary unless asked to regenerate
    if rec.itinerary and not regenerate:
        return {"destination": rec.destination, "itinerary": rec.itinerary, "cached": True}

    # group size = distinct trip members
    group_size = (await db.execute(
        select(func.count(TripMember.user_id)).where(TripMember.trip_id == trip_id)
    )).scalar() or 1

    try:
        itinerary = await generate_itinerary(
            destination=rec.destination,
            trip_name=trip.name,
            days=days,
            group_size=group_size,
            db=db,
            trip_id=trip_id,
        )
    except KeyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError:
        raise HTTPException(
            status_code=502,
            detail="The AI response couldn't be read. Please try generating again.",
        )

    if not isinstance(itinerary, list) or not itinerary:
        raise HTTPException(
            status_code=502,
            detail="AI returned no usable itinerary. Try again.",
        )

    rec.itinerary = itinerary
    await db.commit()

    return {"destination": rec.destination, "itinerary": itinerary, "cached": False}