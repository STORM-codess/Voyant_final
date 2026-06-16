"""Integration tests for the form lifecycle and submission validation."""
from tests.helpers import register_user, create_trip, add_member


async def setup_trip(client, as_user):
    await register_user(client, as_user, "creator")
    return await create_trip(client, as_user, "creator")


async def create_form(client, as_user, trip_id, template_id, title="Preferences"):
    as_user("creator")
    response = await client.post(
        f"/forms/{trip_id}/create", json={"template_id": template_id, "title": title}
    )
    assert response.status_code == 200, response.text
    return response.json()["form_id"]


async def test_form_lifecycle(client, as_user, template_id):
    trip_id = await setup_trip(client, as_user)
    await create_form(client, as_user, trip_id, template_id)

    # edit while draft
    response = await client.put(f"/forms/{trip_id}/edit", json={"title": "Updated"})
    assert response.status_code == 200

    # publish
    response = await client.post(f"/forms/{trip_id}/publish")
    assert response.status_code == 200

    # cannot edit once published
    response = await client.put(f"/forms/{trip_id}/edit", json={"title": "Nope"})
    assert response.status_code == 400

    # get form with questions
    response = await client.get(f"/forms/{trip_id}/form")
    data = response.json()
    assert data["title"] == "Updated"
    assert len(data["questions"]) == 2

    # submit a valid response
    q_choice = next(q for q in data["questions"] if q["question_type"] == "single_choice")
    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": q_choice["id"], "answer_options": ["Low"]}]
    })
    assert response.status_code == 200

    # status reflects the submission
    response = await client.get(f"/forms/{trip_id}/status")
    data = response.json()
    assert data["submitted_count"] == 1
    assert data["all_submitted"] is True


async def test_non_member_cannot_create_form(client, as_user, template_id):
    trip_id = await setup_trip(client, as_user)
    await register_user(client, as_user, "outsider")

    as_user("outsider")
    response = await client.post(
        f"/forms/{trip_id}/create", json={"template_id": template_id, "title": "Nope"}
    )
    assert response.status_code == 403


async def test_trip_member_can_create_new_form_after_previous_one_is_complete(client, as_user, template_id):
    trip_id = await setup_trip(client, as_user)
    await add_member(client, as_user, "creator", trip_id, "friend")

    as_user("creator")
    await create_form(client, as_user, trip_id, template_id, title="First form")
    response = await client.post(f"/forms/{trip_id}/publish")
    assert response.status_code == 200

    response = await client.get(f"/forms/{trip_id}/form")
    questions = response.json()["questions"]
    q_choice = next(q for q in questions if q["question_type"] == "single_choice")

    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": q_choice["id"], "answer_options": ["Low"]}]
    })
    assert response.status_code == 200

    as_user("friend")
    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": q_choice["id"], "answer_options": ["Low"]}]
    })
    assert response.status_code == 200

    response = await client.get(f"/forms/{trip_id}/form")
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    response = await client.post(
        f"/forms/{trip_id}/create", json={"template_id": template_id, "title": "Second form"}
    )
    assert response.status_code == 200


async def test_cannot_create_new_form_while_previous_form_pending(client, as_user, template_id):
    trip_id = await setup_trip(client, as_user)
    await add_member(client, as_user, "creator", trip_id, "friend")

    as_user("creator")
    await create_form(client, as_user, trip_id, template_id, title="First form")
    response = await client.post(f"/forms/{trip_id}/publish")
    assert response.status_code == 200

    response = await client.get(f"/forms/{trip_id}/form")
    questions = response.json()["questions"]
    q_choice = next(q for q in questions if q["question_type"] == "single_choice")

    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": q_choice["id"], "answer_options": ["Low"]}]
    })
    assert response.status_code == 200

    as_user("friend")
    response = await client.post(
        f"/forms/{trip_id}/create", json={"template_id": template_id, "title": "Second form"}
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "Current form must be completed first"


async def test_submit_validation(client, as_user, template_id):
    trip_id = await setup_trip(client, as_user)
    await create_form(client, as_user, trip_id, template_id)
    await client.post(f"/forms/{trip_id}/publish")

    response = await client.get(f"/forms/{trip_id}/form")
    questions = response.json()["questions"]
    q_choice = next(q for q in questions if q["question_type"] == "single_choice")
    q_text = next(q for q in questions if q["question_type"] == "text")

    # missing required question
    response = await client.post(f"/forms/{trip_id}/submit", json={"answers": []})
    assert response.status_code == 422
    assert any("Required question" in e for e in response.json()["detail"]["errors"])

    # unknown question id
    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": "bogus", "answer_text": "hi"}]
    })
    assert response.status_code == 422

    # single_choice with two selected options
    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": q_choice["id"], "answer_options": ["Low", "High"]}]
    })
    assert response.status_code == 422

    # option value not in the question's options
    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [{"question_id": q_choice["id"], "answer_options": ["Medium"]}]
    })
    assert response.status_code == 422

    # valid submission including the optional text question
    response = await client.post(f"/forms/{trip_id}/submit", json={
        "answers": [
            {"question_id": q_choice["id"], "answer_options": ["Low"]},
            {"question_id": q_text["id"], "answer_text": "No notes"},
        ]
    })
    assert response.status_code == 200
