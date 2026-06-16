"""
seed_ai_metrics.py — populate the AI-metrics showcase with REAL data.

This does NOT fabricate numbers. It calls the same generate_recommendations /
generate_itinerary functions the app uses, through the real model gateway, so
every resulting ai_calls row is genuine: real model, real latency, real tokens,
real eval score. It just triggers many calls in a loop instead of by hand, and
spreads them across all prompt versions so the A/B comparison has data too.

Run from the backend root (where `app/` lives), with your .env loaded the same
way the server loads it:

    python seed_ai_metrics.py            # default: a sensible spread of calls
    python seed_ai_metrics.py --rounds 8 # more volume

Note: these are real API calls — they consume your provider quota and take time.
Keep volume reasonable. On the free Groq tier a few dozen calls is fine.
"""

import argparse
import asyncio
import random

from app.database import AsyncSessionLocal
from app.services.ai_service import generate_recommendations, generate_itinerary

# A handful of realistic group preference profiles. These mimic what
# get_form_answers_for_ai() produces: a dict the prompt template reads.
SAMPLE_FORMS = [
    {
        "form_title": "Trip preferences",
        "group_size": 4,
        "answers": {
            "Budget per person": ["₹10,000-20,000", "₹10,000-20,000", "₹20,000-40,000"],
            "Trip length": ["5-7 days"],
            "Vibe": ["Relaxing", "Beach", "Food", "Nature & outdoors"],
            "One base or multi-city": ["A couple of stops"],
            "Places to avoid": ["very cold places"],
        },
    },
    {
        "form_title": "Trip preferences",
        "group_size": 3,
        "answers": {
            "Budget per person": ["₹5,000-10,000", "₹10,000-20,000"],
            "Trip length": ["3-4 days"],
            "Vibe": ["Adventure", "Nature & outdoors", "Trekking"],
            "One base or multi-city": ["Multi-city route"],
            "Must do": ["trekking", "river rafting"],
        },
    },
    {
        "form_title": "Trip preferences",
        "group_size": 5,
        "answers": {
            "Budget per person": ["₹20,000-40,000", "₹20,000-40,000", "Above ₹40,000"],
            "Trip length": ["8-12 days"],
            "Vibe": ["Culture & history", "Food", "Nightlife"],
            "One base or multi-city": ["Multi-city route"],
            "Places to avoid": ["already been to Goa"],
        },
    },
    {
        "form_title": "Trip preferences",
        "group_size": 2,
        "answers": {
            "Budget per person": ["Under ₹5,000", "₹5,000-10,000"],
            "Trip length": ["1-2 days"],
            "Vibe": ["Relaxing", "Spiritual"],
            "One base or multi-city": ["Stay in one place"],
        },
    },
]

TRIP_NAMES = ["Goa Reunion", "Himalayan Escape", "Backwaters Trip", "Desert Run",
              "Coastal Roadtrip", "Heritage Tour", "Monsoon Getaway"]

# all three versions so the by-prompt-version / A-B comparison populates
PROMPT_VERSIONS = ["recommendations_v1", "recommendations_v2", "recommendations_v3"]


async def run(rounds: int, exercise_all_models: bool):
    rec_ok = rec_fail = itin_ok = itin_fail = 0

    # Build a deterministic per-round model plan so the fallbacks ALWAYS get a
    # few genuine calls regardless of round count or luck. Target ~88/8/4:
    # ~1 in 11 rounds → 70B, ~1 in 22 → gemini, everything else → primary.
    plan = [0] * rounds
    if exercise_all_models and rounds >= 4:
        # at least 2 on the 70B and 1 on gemini, scaling gently with volume
        n70 = max(2, rounds // 11)
        ngem = max(1, rounds // 22)
        # place them at spread-out indices so they're not all bunched
        idxs = list(range(rounds))
        random.shuffle(idxs)
        for i in idxs[:n70]:
            plan[i] = 1
        for i in idxs[n70:n70 + ngem]:
            plan[i] = 2

    for r in range(rounds):
        form = random.choice(SAMPLE_FORMS)
        trip_name = random.choice(TRIP_NAMES)
        version = PROMPT_VERSIONS[r % len(PROMPT_VERSIONS)]  # rotate evenly
        start_at = plan[r]

        # each call gets its own session (mirrors a real request)
        async with AsyncSessionLocal() as db:
            try:
                recs = await generate_recommendations(
                    trip_name=trip_name,
                    form_data=form,
                    db=db,
                    trip_id=None,            # not tied to a real trip; metrics still log
                    prompt_version=version,
                    start_at=start_at,
                )
                await db.commit()
                rec_ok += 1
                tier = ["primary 8B", "fallback 70B", "gemini"][start_at]
                print(f"[{r+1}/{rounds}] recs ok  · {version:<20} · {tier:<13} · {len(recs)} destinations")

                # for some rounds, also generate an itinerary for the top pick
                if recs and r % 2 == 0:
                    top = recs[0].get("destination", "Goa")
                    async with AsyncSessionLocal() as db2:
                        try:
                            itin = await generate_itinerary(
                                destination=top,
                                trip_name=trip_name,
                                days=random.choice([4, 5, 7]),
                                group_size=form["group_size"],
                                db=db2,
                                trip_id=None,
                            )
                            await db2.commit()
                            itin_ok += 1
                            print(f"            itinerary ok · {top} · {len(itin)} days")
                        except Exception as e:
                            itin_fail += 1
                            print(f"            itinerary FAILED · {e}")
            except Exception as e:
                rec_fail += 1
                print(f"[{r+1}/{rounds}] recs FAILED · {version} · {e}")

        # be gentle on rate limits
        await asyncio.sleep(1.5)

    print("\n──────── done ────────")
    print(f"recommendations: {rec_ok} ok, {rec_fail} failed")
    print(f"itineraries:     {itin_ok} ok, {itin_fail} failed")
    print("All logged to ai_calls — refresh the 'How our AI works' page to see them.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", type=int, default=12,
                    help="how many recommendation calls to make (default 12)")
    ap.add_argument("--all-models", action="store_true",
                    help="distribute REAL calls across all 3 gateway models "
                         "(primary/fallback/gemini) so the model breakdown shows all three")
    args = ap.parse_args()
    asyncio.run(run(args.rounds, args.all_models))