"""Integration tests for AI recommendations with a stubbed model gateway."""
from tests.helpers import register_user, create_trip


async def test_generate_and_fetch_recommendations(client, as_user, template_id, monkeypatch):
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")

    # create + publish form, submit one response
    response = await client.post(
        f"/forms/{trip_id}/create", json={"template_id": template_id, "title": "Prefs"}
    )
    assert response.status_code == 200
    await client.post(f"/forms/{trip_id}/publish")

    response = await client.get(f"/forms/{trip_id}/form")
    q_choice = next(
        q for q in response.json()["questions"] if q["question_type"] == "single_choice"
    )
    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": q_choice["id"], "answer_options": ["Low"]}]
    })
    assert response.status_code == 200

    # stub the AI call — no real model is hit in tests
    async def fake_generate(trip_name, form_data):
        assert form_data["group_size"] == 1
        return [{
            "destination": "Goa",
            "reasoning": "Matches the group's low budget preference",
            "best_activities": ["beach", "surfing"],
            "estimated_budget": {"hotel_per_night": "1500 - 3000"},
            "best_time_to_visit": "November - February",
            "match_score": 88,
        }]

    monkeypatch.setattr("app.api.recommendations.generate_recommendations", fake_generate)

    response = await client.post(f"/recommendations/{trip_id}/generate")
    assert response.status_code == 200
    assert response.json()["version"] == 1

    response = await client.get(f"/recommendations/{trip_id}")
    data = response.json()
    assert data["total_recommendations"] == 1
    assert data["recommendations_by_version"]["1"][0]["destination"] == "Goa"


async def test_generate_requires_form_responses(client, as_user):
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")

    response = await client.post(f"/recommendations/{trip_id}/generate")
    assert response.status_code == 400


async def test_completed_form_still_feeds_ai(client, as_user, template_id, monkeypatch):
    """Regression: a form that flipped to 'completed' (all members answered)
    must still be read by the AI. The old code only looked at 'published' forms."""
    await register_user(client, as_user, "creator")
    trip_id = await create_trip(client, as_user, "creator")

    await client.post(
        f"/forms/{trip_id}/create", json={"template_id": template_id, "title": "Prefs"}
    )
    await client.post(f"/forms/{trip_id}/publish")

    response = await client.get(f"/forms/{trip_id}/form")
    q_choice = next(
        q for q in response.json()["questions"] if q["question_type"] == "single_choice"
    )
    # single member submitting flips the form to 'completed'
    await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": q_choice["id"], "answer_options": ["Low"]}]
    })

    captured = {}

    async def fake_generate(trip_name, form_data):
        captured["form_data"] = form_data
        return [{"destination": "Goa", "reasoning": "fits", "best_activities": [],
                 "hotels": ["Beach Resort"], "estimated_budget": {}}]

    monkeypatch.setattr("app.api.recommendations.generate_recommendations", fake_generate)

    response = await client.post(f"/recommendations/{trip_id}/generate")
    assert response.status_code == 200, response.text
    # the AI actually received the answers from the completed form
    assert captured["form_data"]["answers"]
    assert captured["form_data"]["total_responses"] == 1
