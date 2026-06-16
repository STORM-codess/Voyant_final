"""
Live AI-pipeline smoke test for the features added this session
(Layers 1-4: gateway instrumentation, prompt versioning, eval harness, A/B).

Unlike the pytest suite (which stubs the providers), this calls the REAL model
gateway with your actual GROQ_API_KEY / GEMINI_API_KEY and writes to your real
database. Use it to confirm the whole AI chain works against live providers.

Run from the backend root, with your venv active and .env in place:
    python check_ai_pipeline.py

It does NOT require the web server to be running. It talks to the services
directly. It creates a few AICall rows (and runs real model calls, which use a
little quota), but creates no trips/users.
"""
import asyncio
import json

from app.database import AsyncSessionLocal
from app.services.ai_service import generate_recommendations
from app.services.eval_service import evaluate_recommendations
from app.services.prompts import list_prompts, get_prompt
from app.models.ai_call import AICall
from sqlalchemy import select, desc


SAMPLE_FORM_DATA = {
    "form_title": "Preferences",
    "group_size": 4,
    "total_responses": 4,
    "answers": {
        "What is your budget per day?": ["₹1000-2000", "₹2000-5000", "₹1000-2000"],
        "What vibe are you looking for?": ["Adventure", "Nature", "Relaxing", "Adventure"],
        "How do you prefer to travel?": ["Train", "Flight", "Road trip"],
        "How many days can you take off?": ["3-4 days", "5-7 days"],
        "Places you have already visited?": ["Goa", "Manali"],
        "What is your food preference?": ["Vegetarian", "No preference"],
    },
}


def _line(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)


async def main():
    _line("1. Prompt registry (Layer 2)")
    for p in list_prompts():
        mark = " [default]" if p["is_default"] else ""
        print(f"  - {p['version']}{mark}: {p['description']}")

    async with AsyncSessionLocal() as db:
        # run each registered recommendations prompt version for real
        versions = [p["version"] for p in list_prompts() if p["feature"] == "recommendations"]
        scores = {}

        for version in versions:
            _line(f"2. Live generation with {version} (Layers 1, 2, 4)")
            try:
                parsed = await generate_recommendations(
                    trip_name="Friends Trip",
                    form_data=SAMPLE_FORM_DATA,
                    db=db,
                    trip_id=None,
                    prompt_version=version,
                )
                ev = evaluate_recommendations(parsed, form_data=SAMPLE_FORM_DATA)
                scores[version] = ev.score
                print(f"  returned {len(parsed) if isinstance(parsed, list) else 'N/A'} destinations")
                print(f"  eval score: {ev.score:.3f}")
                print(f"  checks: {json.dumps(ev.checks)}")
                if ev.notes:
                    print("  notes:")
                    for n in ev.notes:
                        print(f"    - {n}")
            except Exception as e:
                print(f"  FAILED: {e}")
                scores[version] = None

        await db.commit()

        _line("3. A/B comparison (Layer 4)")
        valid = {k: v for k, v in scores.items() if v is not None}
        if len(valid) >= 2:
            winner = max(valid, key=valid.get)
            for v, s in valid.items():
                print(f"  {v}: {s:.3f}")
            print(f"  -> winner: {winner}")
        else:
            print("  not enough successful generations to compare")

        _line("4. Instrumentation check (Layer 1)")
        rows = (await db.execute(
            select(AICall).order_by(desc(AICall.created_at)).limit(10)
        )).scalars().all()
        print(f"  most recent {len(rows)} ai_calls rows:")
        for r in rows:
            print(f"    {r.model:<22} ok={r.success} pos={r.fallback_position} "
                  f"tokens={r.total_tokens} cost=${r.estimated_cost_usd} "
                  f"eval={r.eval_score} version={r.prompt_version}")

    print("\nDone. If you saw destinations, eval scores, and ai_calls rows above, "
          "the full AI pipeline is working against live providers.")


if __name__ == "__main__":
    asyncio.run(main())