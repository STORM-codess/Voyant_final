import json
from app.services.model_gateway import gateway
from app.services.prompts import get_prompt
from app.services.eval_service import evaluate_recommendations


async def generate_recommendations(
    trip_name: str,
    form_data: dict,
    db=None,
    trip_id: str = None,
    prompt_version: str = None,
    start_at: int = 0,
) -> list:
    """Generate AI recommendations from aggregated form responses.

    After a successful generation, the raw output is scored by the eval harness
    and the score is written back onto the AICall row that produced it. This is
    what lets prompt versions be compared on output quality, not just cost.
    """
    template = get_prompt("recommendations", prompt_version)
    prompt = template.render({"trip_name": trip_name, "form_data": form_data})

    holder = {}
    raw = await gateway.complete(
        prompt=prompt, temperature=0.7, max_tokens=4000,
        db=db, feature="recommendations", trip_id=trip_id,
        prompt_version=template.version, result_holder=holder, start_at=start_at,
    )
    parsed = gateway.parse_json(raw)

    # score output quality and attach it to the call row (best-effort)
    if db is not None and holder.get("call_id"):
        try:
            result = evaluate_recommendations(parsed, form_data=form_data)
            from app.models.ai_call import AICall
            call = await db.get(AICall, holder["call_id"])
            if call is not None:
                call.eval_score = result.score
                call.eval_checks = json.dumps(result.as_dict())
                await db.flush()
        except Exception:
            pass  # eval is observability; never break the user-facing result

    return parsed


async def generate_itinerary(
    destination: str,
    trip_name: str,
    days: int = 5,
    group_size: int = 1,
    db=None,
    trip_id: str = None,
    prompt_version: str = None,
) -> list:
    """Generate a day-by-day itinerary for ONE chosen destination.

    Runs through the same model gateway (so it's logged to ai_calls with the
    'itinerary' feature + prompt version), keeping cost/latency observable.
    Returns a list of {day, title, items} objects.
    """
    template = get_prompt("itinerary", prompt_version)
    prompt = template.render({
        "destination": destination,
        "trip_name": trip_name,
        "days": days,
        "group_size": group_size,
    })

    holder = {}
    raw = await gateway.complete(
        prompt=prompt, temperature=0.7, max_tokens=4000,
        db=db, feature="itinerary", trip_id=trip_id,
        prompt_version=template.version, result_holder=holder,
    )
    return gateway.parse_json(raw)