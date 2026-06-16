from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.models.trip import TripMember
from app.models.invite import PendingInvite
from app.firebase import get_current_user
import uuid

router = APIRouter(prefix="/users", tags=["users"])

class UserCreate(BaseModel):
    name: str
    email: Optional[str] = None

@router.post("/register")
async def register_user(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    # check if user already exists
    existing = await db.execute(
        select(User).where(User.id == current_user["uid"])
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User already exists")

    # prefer the email verified by Firebase; fall back to the submitted one
    verified_email = (current_user.get("email") or user_data.email or "").strip().lower()
    if not verified_email:
        raise HTTPException(status_code=400, detail="No email available for registration")

    # create new user
    new_user = User(
        id=current_user["uid"],
        email=verified_email,
        name=user_data.name,
    )
    db.add(new_user)
    await db.flush()

    # convert any pending invites for this email into trip memberships
    invites_result = await db.execute(
        select(PendingInvite).where(PendingInvite.email == verified_email)
    )
    invites = invites_result.scalars().all()
    joined_trips = []
    for invite in invites:
        existing_member = await db.execute(
            select(TripMember).where(
                TripMember.trip_id == invite.trip_id,
                TripMember.user_id == new_user.id
            )
        )
        if not existing_member.scalar_one_or_none():
            db.add(TripMember(
                id=str(uuid.uuid4()),
                trip_id=invite.trip_id,
                user_id=new_user.id,
                is_admin=False
            ))
            joined_trips.append(invite.trip_id)
        await db.delete(invite)

    await db.commit()
    await db.refresh(new_user)
    return {
        "message": "User registered successfully",
        "user_id": new_user.id,
        "joined_trips": joined_trips
    }

@router.get("/me")
async def get_me(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    result = await db.execute(
        select(User).where(User.id == current_user["uid"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
