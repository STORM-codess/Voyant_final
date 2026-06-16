"""Integration tests for user registration, trips, and the invite flows."""
from tests.helpers import register_user, create_trip, add_member


async def test_register_and_me(client, as_user):
    response = await register_user(client, as_user, "user-1")
    assert response.status_code == 200

    me = await client.get("/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == "user-1@example.com"


async def test_register_duplicate(client, as_user):
    await register_user(client, as_user, "user-1")
    response = await register_user(client, as_user, "user-1")
    assert response.status_code == 400


async def test_create_trip_requires_registration(client, as_user):
    as_user("ghost")
    response = await client.post(
        "/trips/create",
        json={
            "name": "Trip",
            "destination": "Goa",
            "trip_date": "2025-01-01T00:00:00Z",
        },
    )
    assert response.status_code == 404


async def test_my_trips_includes_member_trips(client, as_user):
    """Regression test: /my-trips must include trips the user joined, not only created."""
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")
    await add_member(client, as_user, "creator", trip_id, "friend")

    as_user("friend")
    response = await client.get("/trips/my-trips")
    assert response.status_code == 200
    all_trips = response.json()["upcoming"] + response.json()["previous"]
    assert [t for t in all_trips if t["id"] == trip_id]


async def test_trip_detail_returns_member_names(client, as_user):
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")
    await register_user(client, as_user, "friend")

    as_user("creator")
    response = await client.post(f"/trips/{trip_id}/invite", params={"email": "friend@example.com"})
    assert response.status_code == 200

    as_user("friend")
    trip_response = await client.get(f"/trips/{trip_id}")
    assert trip_response.status_code == 200
    trip = trip_response.json()
    assert "members" in trip
    assert any(m["name"] == "friend" and m["email"] == "friend@example.com" for m in trip["members"])


async def test_invite_registered_user(client, as_user):
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")
    await register_user(client, as_user, "friend")

    as_user("creator")
    response = await client.post(f"/trips/{trip_id}/invite", params={"email": "friend@example.com"})
    assert response.status_code == 200
    assert "added to trip" in response.json()["message"]

    # inviting the same member again fails
    response = await client.post(f"/trips/{trip_id}/invite", params={"email": "friend@example.com"})
    assert response.status_code == 400


async def test_invite_unregistered_user_pending_flow(client, as_user):
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")

    as_user("creator")
    response = await client.post(f"/trips/{trip_id}/invite", params={"email": "newbie@example.com"})
    assert response.status_code == 200
    assert "Invite sent" in response.json()["message"]

    # duplicate pending invite rejected
    response = await client.post(f"/trips/{trip_id}/invite", params={"email": "newbie@example.com"})
    assert response.status_code == 400

    # registration converts the pending invite into a membership
    response = await register_user(client, as_user, "newbie")
    assert response.status_code == 200
    assert response.json()["joined_trips"] == [trip_id]

    response = await client.get("/trips/my-trips")
    all_trips = response.json()["upcoming"] + response.json()["previous"]
    assert [t for t in all_trips if t["id"] == trip_id]


async def test_invite_by_non_member(client, as_user):
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")
    await register_user(client, as_user, "outsider")

    as_user("outsider")
    response = await client.post(f"/trips/{trip_id}/invite", params={"email": "creator@example.com"})
    assert response.status_code == 403


async def test_non_admin_member_cannot_invite(client, as_user):
    """A regular member (not the admin/creator) must not be able to invite others."""
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")
    await add_member(client, as_user, "creator", trip_id, "member")
    await register_user(client, as_user, "target")

    as_user("member")
    response = await client.post(f"/trips/{trip_id}/invite", params={"email": "target@example.com"})
    assert response.status_code == 403
    assert "admin" in response.json()["detail"].lower()
