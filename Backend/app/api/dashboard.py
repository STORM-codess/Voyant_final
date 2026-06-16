from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, distinct
from app.database import get_db
from app.models.trip import Trip, TripMember
from app.models.vote import VoteSession
from app.firebase import get_current_user

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Aggregated headline numbers for the dashboard stat tiles.

    - trips_planned   : trips this user is a member of
    - friends_traveling: distinct OTHER members across those trips
    - decisions_made  : closed vote sessions across those trips (a decided
                        vote = a group decision reached)
    """
    uid = current_user["uid"]

    # trip ids the user belongs to
    trip_ids_result = await db.execute(
        select(TripMember.trip_id).where(TripMember.user_id == uid)
    )
    trip_ids = [row[0] for row in trip_ids_result.all()]

    trips_planned = len(trip_ids)

    if trip_ids:
        # distinct co-travellers (exclude the user themself)
        friends_result = await db.execute(
            select(func.count(distinct(TripMember.user_id))).where(
                TripMember.trip_id.in_(trip_ids),
                TripMember.user_id != uid,
            )
        )
        friends_traveling = friends_result.scalar() or 0

        # decisions = closed vote sessions on those trips
        decisions_result = await db.execute(
            select(func.count(VoteSession.id)).where(
                VoteSession.trip_id.in_(trip_ids),
                VoteSession.status == "closed",
            )
        )
        decisions_made = decisions_result.scalar() or 0
    else:
        friends_traveling = 0
        decisions_made = 0

    return {
        "trips_planned": trips_planned,
        "friends_traveling": friends_traveling,
        "decisions_made": decisions_made,
    }