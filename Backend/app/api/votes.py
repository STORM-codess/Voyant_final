from app.services.email_service import send_final_plan
from app.models.user import User
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from datetime import datetime, timezone, timedelta
from typing import Optional
from app.database import get_db
from app.models.vote import Vote, VoteSession, VoteOption
from app.models.trip import Trip, TripMember
from app.firebase import get_current_user
from app.services.voting_service import (
    close_session,
    auto_close_if_expired,
    count_first_choices,
    get_session_ballots,
)
import uuid

router = APIRouter(prefix="/votes", tags=["votes"])

# \u2500\u2500\u2500 Pydantic Schemas \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

class CreateSessionRequest(BaseModel):
    title: str
    description: Optional[str] = None
    options: list[str]          # list of option texts
    deadline_hours: float = 72.0

class CastVoteRequest(BaseModel):
    session_id: str
    rankings: list[str]         # option ids in preference order, first = top choice

# \u2500\u2500\u2500 Routes \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

@router.post("/{trip_id}/create-session")
async def create_vote_session(
    trip_id: str,
    request: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Creator creates a vote session with custom options"""

    # only creator can create sessions
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.creator_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Only trip creator can create vote sessions")

    if len(request.options) < 2:
        raise HTTPException(status_code=400, detail="Need at least 2 options to vote on")

    # create session
    deadline = datetime.now(timezone.utc) + timedelta(hours=request.deadline_hours)
    session = VoteSession(
        id=str(uuid.uuid4()),
        trip_id=trip_id,
        title=request.title,
        description=request.description,
        status="open",
        deadline=deadline,
        created_by=current_user["uid"]
    )
    db.add(session)
    await db.flush()

    # create options
    created_options = []
    for option_text in request.options:
        option = VoteOption(
            id=str(uuid.uuid4()),
            session_id=session.id,
            option_text=option_text
        )
        db.add(option)
        created_options.append({"id": option.id, "text": option_text})

    await db.commit()

    return {
        "message": "Vote session created",
        "session_id": session.id,
        "title": request.title,
        "options": created_options,
        "deadline": deadline,
        "deadline_hours": request.deadline_hours,
        "voting_type": "ranked_choice"
    }

@router.post("/{trip_id}/cast")
async def cast_vote(
    trip_id: str,
    request: CastVoteRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Member casts or updates their ranked ballot"""

    # check member
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    # get session
    session_result = await db.execute(
        select(VoteSession).where(
            VoteSession.id == request.session_id,
            VoteSession.trip_id == trip_id
        )
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Vote session not found")

    # lazily auto-close if the deadline has passed
    await auto_close_if_expired(session, db)
    if session.status == "closed":
        raise HTTPException(status_code=400, detail="Voting is closed")

    # validate ballot
    if not request.rankings:
        raise HTTPException(status_code=400, detail="Rankings cannot be empty")
    if len(set(request.rankings)) != len(request.rankings):
        raise HTTPException(status_code=400, detail="Rankings contain duplicate options")

    options_result = await db.execute(
        select(VoteOption).where(VoteOption.session_id == session.id)
    )
    valid_option_ids = {o.id for o in options_result.scalars().all()}
    invalid = [oid for oid in request.rankings if oid not in valid_option_ids]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid option ids: {invalid}")

    # check if already voted in this session
    existing_vote = await db.execute(
        select(Vote).where(
            Vote.session_id == session.id,
            Vote.user_id == current_user["uid"]
        )
    )
    existing = existing_vote.scalar_one_or_none()

    if existing:
        # update existing ballot
        existing.rankings = request.rankings
        existing.updated_at = datetime.now(timezone.utc)
        await db.commit()
        return {"message": "Ballot updated successfully"}

    # cast new ballot
    new_vote = Vote(
        id=str(uuid.uuid4()),
        session_id=session.id,
        user_id=current_user["uid"],
        rankings=request.rankings
    )
    db.add(new_vote)
    await db.commit()

    return {"message": "Ballot cast successfully"}

@router.post("/{trip_id}/close/{session_id}")
async def close_voting(
    trip_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Creator closes voting \u2014 winner determined by instant-runoff counting"""

    # only creator can close
    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.creator_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Only creator can close voting")

    # get session
    session_result = await db.execute(
        select(VoteSession).where(VoteSession.id == session_id)
    )
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "closed":
        raise HTTPException(status_code=400, detail="Session already closed")

    result = await close_session(session, db)

    if result["status"] == "revote":
        return {
            "message": "Tie detected \u2014 revote started with a fresh deadline. Members must vote again.",
            **result
        }
    return {"message": "Voting closed \u2014 winner decided", **result}

@router.get("/{trip_id}/sessions")
async def get_vote_sessions(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all vote sessions for a trip"""

    # check member
    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    sessions_result = await db.execute(
        select(VoteSession).where(VoteSession.trip_id == trip_id)
    )
    sessions = sessions_result.scalars().all()

    result = []
    for session in sessions:
        # lazily close sessions whose deadline has passed
        await auto_close_if_expired(session, db)

        # get options
        options_result = await db.execute(
            select(VoteOption).where(VoteOption.session_id == session.id)
        )
        options = options_result.scalars().all()

        # first-choice counts for display
        ballots = await get_session_ballots(session.id, db)
        first_choice_counts = count_first_choices(ballots, [o.id for o in options])

        # check if current user voted
        user_vote = await db.execute(
            select(Vote).where(
                Vote.session_id == session.id,
                Vote.user_id == current_user["uid"]
            )
        )
        user_voted = user_vote.scalar_one_or_none()

        result.append({
            "session_id": session.id,
            "title": session.title,
            "description": session.description,
            "status": session.status,
            "deadline": session.deadline,
            "winner_option_id": session.winner_option_id,
            "is_random_winner": session.is_random_winner,
            "voting_type": "ranked_choice",
            "total_ballots": len(ballots),
            "first_choice_counts": first_choice_counts,
            "user_rankings": user_voted.rankings if user_voted else None,
            "options": [
                {
                    "id": o.id,
                    "text": o.option_text,
                    "first_choice_votes": first_choice_counts.get(o.id, 0)
                }
                for o in options
            ]
        })

    return {"trip_id": trip_id, "sessions": result}

@router.post("/{trip_id}/send-final-plan")
async def send_final_plan_email(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Creator sends final plan email to all members"""

    trip_result = await db.execute(select(Trip).where(Trip.id == trip_id))
    trip = trip_result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.creator_id != current_user["uid"]:
        raise HTTPException(status_code=403, detail="Only creator can send final plan")

    # lazily close any expired sessions first
    all_sessions_result = await db.execute(
        select(VoteSession).where(VoteSession.trip_id == trip_id)
    )
    all_sessions = all_sessions_result.scalars().all()
    for session in all_sessions:
        await auto_close_if_expired(session, db)

    sessions = [s for s in all_sessions if s.status == "closed"]
    if not sessions:
        raise HTTPException(status_code=400, detail="No closed vote sessions found")

    final_plan = []
    for session in sessions:
        winner_text = None
        if session.winner_option_id:
            option_result = await db.execute(
                select(VoteOption).where(VoteOption.id == session.winner_option_id)
            )
            winner_option = option_result.scalar_one_or_none()
            if winner_option:
                winner_text = winner_option.option_text
        final_plan.append({
            "title": session.title,
            "winner": winner_text,
            "is_random_winner": session.is_random_winner
        })

    members_result = await db.execute(
        select(TripMember).where(TripMember.trip_id == trip_id)
    )
    members = members_result.scalars().all()

    member_emails = []
    for member in members:
        user_result = await db.execute(
            select(User).where(User.id == member.user_id)
        )
        user = user_result.scalar_one_or_none()
        if user:
            member_emails.append(user.email)

    await send_final_plan(
        members=member_emails,
        trip_name=trip.name,
        final_plan=final_plan
    )

    return {
        "message": f"Final plan sent to {len(member_emails)} members",
        "members_notified": member_emails
    }

@router.get("/{trip_id}/results")
async def get_final_results(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Get all closed session results \u2014 the final plan"""

    member_result = await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )
    if not member_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a trip member")

    # lazily close any expired sessions first
    sessions_result = await db.execute(
        select(VoteSession).where(VoteSession.trip_id == trip_id)
    )
    all_sessions = sessions_result.scalars().all()
    for session in all_sessions:
        await auto_close_if_expired(session, db)

    closed_sessions = [s for s in all_sessions if s.status == "closed"]

    final_plan = []
    for session in closed_sessions:
        winner_text = None
        if session.winner_option_id:
            option_result = await db.execute(
                select(VoteOption).where(VoteOption.id == session.winner_option_id)
            )
            winner_option = option_result.scalar_one_or_none()
            if winner_option:
                winner_text = winner_option.option_text
        final_plan.append({
            "title": session.title,
            "winner": winner_text,
            "is_random_winner": session.is_random_winner
        })

    return {
        "trip_id": trip_id,
        "final_plan": final_plan,
        "total_decisions": len(final_plan)
    }
