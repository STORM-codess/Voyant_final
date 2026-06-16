"""Integration tests for ranked-choice voting sessions."""
from tests.helpers import register_user, create_trip, add_member


async def setup_trip_with_members(client, as_user, member_count=2):
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")
    members = []
    for i in range(member_count):
        uid = f"member-{i}"
        await add_member(client, as_user, "creator", trip_id, uid)
        members.append(uid)
    return trip_id, members


async def create_session(client, as_user, trip_id, options=None, deadline_hours=24.0):
    as_user("creator")
    response = await client.post(f"/votes/{trip_id}/create-session", json={
        "title": "Destination",
        "options": options or ["Goa", "Manali", "Jaipur"],
        "deadline_hours": deadline_hours,
    })
    assert response.status_code == 200, response.text
    data = response.json()
    return data["session_id"], {o["text"]: o["id"] for o in data["options"]}


async def cast(client, as_user, uid, trip_id, session_id, rankings):
    as_user(uid)
    return await client.post(
        f"/votes/{trip_id}/cast", json={"session_id": session_id, "rankings": rankings}
    )


async def test_create_session_rules(client, as_user):
    trip_id, members = await setup_trip_with_members(client, as_user, 1)

    # non-creator cannot create a session
    as_user(members[0])
    response = await client.post(f"/votes/{trip_id}/create-session", json={
        "title": "X", "options": ["a", "b"], "deadline_hours": 1,
    })
    assert response.status_code == 403

    # needs at least 2 options
    as_user("creator")
    response = await client.post(f"/votes/{trip_id}/create-session", json={
        "title": "X", "options": ["a"], "deadline_hours": 1,
    })
    assert response.status_code == 400


async def test_cast_and_update_ballot(client, as_user):
    trip_id, members = await setup_trip_with_members(client, as_user, 1)
    session_id, ids = await create_session(client, as_user, trip_id)

    response = await cast(client, as_user, members[0], trip_id, session_id, [ids["Goa"], ids["Manali"]])
    assert response.status_code == 200
    assert "cast" in response.json()["message"]

    response = await cast(client, as_user, members[0], trip_id, session_id, [ids["Manali"]])
    assert response.status_code == 200
    assert "updated" in response.json()["message"]

    as_user(members[0])
    response = await client.get(f"/votes/{trip_id}/sessions")
    session = response.json()["sessions"][0]
    assert session["user_rankings"] == [ids["Manali"]]
    assert session["total_ballots"] == 1


async def test_ballot_validation(client, as_user):
    trip_id, members = await setup_trip_with_members(client, as_user, 1)
    session_id, ids = await create_session(client, as_user, trip_id)

    # empty rankings
    response = await cast(client, as_user, members[0], trip_id, session_id, [])
    assert response.status_code == 400

    # duplicate options in ballot
    response = await cast(client, as_user, members[0], trip_id, session_id, [ids["Goa"], ids["Goa"]])
    assert response.status_code == 400

    # option id from another session / invalid
    response = await cast(client, as_user, members[0], trip_id, session_id, ["bogus-option"])
    assert response.status_code == 400

    # non-member cannot vote
    as_user("nobody")
    response = await client.post(
        f"/votes/{trip_id}/cast", json={"session_id": session_id, "rankings": [ids["Goa"]]}
    )
    assert response.status_code == 403


async def test_irv_majority_winner(client, as_user):
    trip_id, members = await setup_trip_with_members(client, as_user, 2)
    session_id, ids = await create_session(client, as_user, trip_id, options=["Goa", "Manali"])

    await cast(client, as_user, "creator", trip_id, session_id, [ids["Goa"], ids["Manali"]])
    await cast(client, as_user, members[0], trip_id, session_id, [ids["Goa"], ids["Manali"]])
    await cast(client, as_user, members[1], trip_id, session_id, [ids["Manali"], ids["Goa"]])

    as_user("creator")
    response = await client.post(f"/votes/{trip_id}/close/{session_id}")
    data = response.json()
    assert data["status"] == "closed"
    assert data["winner_option_id"] == ids["Goa"]
    assert data["is_random"] is False


async def test_irv_elimination_redistributes_votes(client, as_user):
    trip_id, members = await setup_trip_with_members(client, as_user, 4)
    session_id, ids = await create_session(client, as_user, trip_id, options=["A", "B", "C"])
    a, b, c = ids["A"], ids["B"], ids["C"]

    voters = ["creator"] + members
    ballots = [[a, b], [a, c], [b, a], [b, c], [c, b]]
    for voter, ballot in zip(voters, ballots):
        response = await cast(client, as_user, voter, trip_id, session_id, ballot)
        assert response.status_code == 200

    as_user("creator")
    response = await client.post(f"/votes/{trip_id}/close/{session_id}")
    data = response.json()
    assert data["status"] == "closed"
    # C is eliminated first; its vote transfers to B, giving B the majority
    assert data["winner_option_id"] == b
    assert data["rounds"][0]["eliminated"] == [c]


async def test_tie_revote_then_random(client, as_user):
    trip_id, members = await setup_trip_with_members(client, as_user, 1)
    session_id, ids = await create_session(client, as_user, trip_id, options=["A", "B"])

    await cast(client, as_user, "creator", trip_id, session_id, [ids["A"]])
    await cast(client, as_user, members[0], trip_id, session_id, [ids["B"]])

    as_user("creator")
    response = await client.post(f"/votes/{trip_id}/close/{session_id}")
    data = response.json()
    assert data["status"] == "revote"
    assert set(data["tied_options"]) == {ids["A"], ids["B"]}

    # ballots are cleared for the revote
    response = await client.get(f"/votes/{trip_id}/sessions")
    session = response.json()["sessions"][0]
    assert session["status"] == "revote"
    assert session["total_ballots"] == 0

    # same tie again — broken randomly this time
    await cast(client, as_user, "creator", trip_id, session_id, [ids["A"]])
    await cast(client, as_user, members[0], trip_id, session_id, [ids["B"]])
    as_user("creator")
    response = await client.post(f"/votes/{trip_id}/close/{session_id}")
    data = response.json()
    assert data["status"] == "closed"
    assert data["is_random"] is True
    assert data["winner_option_id"] in {ids["A"], ids["B"]}


async def test_auto_close_after_deadline(client, as_user):
    trip_id, members = await setup_trip_with_members(client, as_user, 1)
    session_id, ids = await create_session(client, as_user, trip_id, deadline_hours=-1)

    # casting after the deadline lazily closes the session
    response = await cast(client, as_user, members[0], trip_id, session_id, [ids["Goa"]])
    assert response.status_code == 400
    assert "closed" in response.json()["detail"]

    as_user(members[0])
    response = await client.get(f"/votes/{trip_id}/sessions")
    assert response.json()["sessions"][0]["status"] == "closed"


async def test_results_and_final_plan(client, as_user):
    trip_id, members = await setup_trip_with_members(client, as_user, 1)
    session_id, ids = await create_session(client, as_user, trip_id, options=["A", "B"])

    await cast(client, as_user, "creator", trip_id, session_id, [ids["A"], ids["B"]])
    await cast(client, as_user, members[0], trip_id, session_id, [ids["A"], ids["B"]])

    as_user("creator")
    await client.post(f"/votes/{trip_id}/close/{session_id}")

    response = await client.get(f"/votes/{trip_id}/results")
    data = response.json()
    assert data["total_decisions"] == 1
    assert data["final_plan"][0]["winner"] == "A"

    response = await client.post(f"/votes/{trip_id}/send-final-plan")
    assert response.status_code == 200
    assert len(response.json()["members_notified"]) == 2
