"""Shared helpers for integration tests."""

from datetime import datetime, timedelta, timezone


async def register_user(client, as_user, uid, name=None, email=None):
    as_user(uid)
    return await client.post(
        "/users/register",
        json={"name": name or uid, "email": email or f"{uid}@example.com"},
    )


async def create_trip(client, as_user, uid, name="Test Trip"):
    as_user(uid)
    trip_date = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    response = await client.post(
        "/trips/create",
        json={"name": name, "destination": "Goa", "trip_date": trip_date},
    )
    assert response.status_code == 200, response.text
    return response.json()["trip_id"]


async def add_member(client, as_user, creator_uid, trip_id, member_uid):
    """Register a user and invite them to the trip (registered-user path)."""
    response = await register_user(client, as_user, member_uid)
    assert response.status_code == 200, response.text
    as_user(creator_uid)
    response = await client.post(
        f"/trips/{trip_id}/invite", params={"email": f"{member_uid}@example.com"}
    )
    assert response.status_code == 200, response.text
