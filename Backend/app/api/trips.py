from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.trip import Trip, TripMember
from app.models.user import User
from app.models.invite import PendingInvite
from app.firebase import get_current_user
from app.services.email_service import send_trip_invite
import uuid

router = APIRouter(prefix="/trips", tags=["trips"])

class TripCreate(BaseModel):
    name: str
    destination: Optional[str] = None
    trip_date: Optional[datetime] = None
    description: Optional[str] = None

@router.post("/create")
async def create_trip(
    trip_data: TripCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # check user exists
    result = await db.execute(
        select(User).where(User.id == current_user["uid"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Register first")

    # create trip
    trip_id = str(uuid.uuid4())
    new_trip = Trip(
    id=trip_id,
    name=trip_data.name,
    destination=trip_data.destination,
    trip_date=trip_data.trip_date,
    description=trip_data.description,
    creator_id=current_user["uid"]
)
    db.add(new_trip)

    # add creator as first member
    member = TripMember(
        id=str(uuid.uuid4()),
        trip_id=trip_id,
        user_id=current_user["uid"],
        is_admin=True
    )
    db.add(member)
    await db.commit()
    await db.refresh(new_trip)

    return {"message": "Trip created successfully", "trip_id": new_trip.id}

@router.get("/my-trips")
async def get_my_trips(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # return all trips the user is a member of (not just created)
    result = await db.execute(
        select(Trip)
        .join(TripMember, TripMember.trip_id == Trip.id)
        .where(TripMember.user_id == current_user["uid"])
        .order_by(Trip.trip_date)
    )
    trips = result.scalars().all()

    now = datetime.now(timezone.utc)
    upcoming, previous = [], []
    for trip in trips:
        trip_date = trip.trip_date
        # guard against naive datetimes from the DB
        if trip_date and trip_date.tzinfo is None:
            trip_date = trip_date.replace(tzinfo=timezone.utc)
        bucket = previous if (trip_date and trip_date < now) else upcoming
        bucket.append({
            "id": trip.id,
            "name": trip.name,
            "destination": trip.destination,
            "trip_date": trip.trip_date.isoformat() if trip.trip_date else None,
            "description": trip.description,
            "status": trip.status.value if trip.status else None,
            "creator_id": trip.creator_id,
        })

    return {"upcoming": upcoming, "previous": previous}

@router.get("/{trip_id}")
async def get_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(Trip)
        .options(selectinload(Trip.members).selectinload(TripMember.user))
        .where(Trip.id == trip_id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    members = []
    for member in trip.members:
        members.append({
            "id": member.id,
            "user_id": member.user_id,
            "name": member.user.name if member.user else None,
            "email": member.user.email if member.user else None,
            "is_admin": member.is_admin,
            "joined_at": member.joined_at.isoformat() if member.joined_at else None,
        })

    # still-pending invites (people invited but not yet registered/joined)
    pending_result = await db.execute(
        select(PendingInvite).where(PendingInvite.trip_id == trip_id)
    )
    pending_invites = [
        {"email": p.email, "created_at": p.created_at.isoformat() if p.created_at else None}
        for p in pending_result.scalars().all()
    ]

    return {
        "id": trip.id,
        "name": trip.name,
        "destination": trip.destination,
        "trip_date": trip.trip_date.isoformat() if trip.trip_date else None,
        "description": trip.description,
        "status": trip.status.value if trip.status else None,
        "creator_id": trip.creator_id,
        "created_at": trip.created_at.isoformat() if trip.created_at else None,
        "updated_at": trip.updated_at.isoformat() if trip.updated_at else None,
        "members": members,
        "member_count": len(members),
        "pending_invites": pending_invites,
    }


@router.post("/{trip_id}/join")
async def join_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Join a trip via a shared link. Any signed-in user who has the link can
    join (the trip id is an unguessable UUID). Idempotent: if already a member,
    it just returns success."""
    trip = (await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )).scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # already a member? nothing to do.
    existing = (await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"],
        )
    )).scalar_one_or_none()
    if existing:
        return {"message": "Already a member", "trip_id": trip_id, "joined": False}

    db.add(TripMember(
        id=str(uuid.uuid4()),
        trip_id=trip_id,
        user_id=current_user["uid"],
        is_admin=False,
    ))

    # clean up any pending email-invite for this user (link join supersedes it)
    user = (await db.execute(
        select(User).where(User.id == current_user["uid"])
    )).scalar_one_or_none()
    if user and user.email:
        for inv in (await db.execute(
            select(PendingInvite).where(
                PendingInvite.trip_id == trip_id,
                PendingInvite.email == user.email.lower(),
            )
        )).scalars().all():
            await db.delete(inv)

    await db.commit()
    return {"message": "Joined trip", "trip_id": trip_id, "joined": True, "trip_name": trip.name}


@router.post("/{trip_id}/invite")
async def invite_member(
    trip_id: str,
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # check trip exists
    result = await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # check if requester is an admin of this trip
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
        raise HTTPException(status_code=403, detail="Only the trip admin can invite members")

    # inviter info for the email
    inviter_result = await db.execute(
        select(User).where(User.id == current_user["uid"])
    )
    inviter = inviter_result.scalar_one_or_none()
    inviter_name = inviter.name if inviter else "A friend"

    # normalize email so case differences don't break invite matching
    email = (email or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required")

    # find user by email
    user_result = await db.execute(
        select(User).where(User.email == email)
    )
    invited_user = user_result.scalar_one_or_none()

    if invited_user:
        # check already member
        existing = await db.execute(
            select(TripMember).where(
                TripMember.trip_id == trip_id,
                TripMember.user_id == invited_user.id
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Already a member")

        # add member
        new_member = TripMember(
            id=str(uuid.uuid4()),
            trip_id=trip_id,
            user_id=invited_user.id,
            is_admin=False
        )
        db.add(new_member)
        await db.commit()

        # notify by email
        await send_trip_invite(
            to_email=email,
            inviter_name=inviter_name,
            trip_name=trip.name,
            trip_id=trip_id
        )

        return {"message": f"{email} added to trip and notified by email"}

    # unregistered user \u2014 create a pending invite
    existing_invite = await db.execute(
        select(PendingInvite).where(
            PendingInvite.trip_id == trip_id,
            PendingInvite.email == email
        )
    )
    if existing_invite.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Invite already pending for this email")

    invite = PendingInvite(
        id=str(uuid.uuid4()),
        trip_id=trip_id,
        email=email,
        invited_by=current_user["uid"]
    )
    db.add(invite)
    await db.commit()

    await send_trip_invite(
        to_email=email,
        inviter_name=inviter_name,
        trip_name=trip.name,
        trip_id=trip_id
    )

    return {
        "message": f"Invite sent to {email} \u2014 they will join the trip automatically after registering"
    }


@router.delete("/{trip_id}/leave")
async def leave_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Remove yourself from a trip. The trip creator cannot leave (that would
    orphan the trip) — they'd need to delete it or transfer ownership, which
    is out of scope here."""
    trip = (await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )).scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    if trip.creator_id == current_user["uid"]:
        raise HTTPException(
            status_code=400,
            detail="The trip creator can't leave their own trip."
        )

    member = (await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="You're not a member of this trip")

    await db.delete(member)
    await db.commit()
    return {"message": "You have left the trip"}


@router.delete("/{trip_id}/invite")
async def cancel_invite(
    trip_id: str,
    email: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """Admin cancels a still-pending invite (for someone who hasn't registered
    yet). Once a person has registered and joined, use remove/leave instead."""
    trip = (await db.execute(
        select(Trip).where(Trip.id == trip_id)
    )).scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")

    # only an admin of this trip can cancel invites
    member = (await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"]
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a trip member")
    if not member.is_admin:
        raise HTTPException(status_code=403, detail="Only the trip admin can cancel invites")

    email = (email or "").strip().lower()
    invite = (await db.execute(
        select(PendingInvite).where(
            PendingInvite.trip_id == trip_id,
            PendingInvite.email == email
        )
    )).scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=404, detail="No pending invite for that email")

    await db.delete(invite)
    await db.commit()
    return {"message": f"Pending invite for {email} cancelled"}
