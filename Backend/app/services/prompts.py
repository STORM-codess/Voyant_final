"""
Versioned prompt registry.

Prompts live in code (not the database) so they are version-controlled with git,
deploy atomically with the code that depends on them, and cannot be mutated at
runtime. Each prompt version has a stable id (e.g. "recommendations_v1") that the
gateway records on every AICall — which is what makes prompt A/B testing and
per-version evaluation possible later.

To add a new version: add a new PromptTemplate to the relevant list with a bumped
version id. Never edit an existing version's text in place — that breaks the
historical link between logged calls and the prompt that produced them. Bump
instead, and (optionally) point DEFAULT_VERSIONS at the new one.
"""
import json
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PromptTemplate:
    version: str                 # stable id, e.g. "recommendations_v1"
    feature: str                 # which feature this prompt serves
    description: str             # short note on what's distinctive about this version
    render: Callable[[dict], str]  # builds the final prompt string from context


# ── recommendations prompts ─────────────────────────────────────────

def _render_recommendations_v1(ctx: dict) -> str:
    trip_name = ctx.get("trip_name", "Trip")
    form_data = ctx.get("form_data", {})
    return f"""
You are a professional travel planner for Indian destinations.

Trip Name: {trip_name}
Group Size: {form_data.get('group_size', 1)} people
Form Title: {form_data.get('form_title', 'Trip Planning')}

Group Responses Summary:
{json.dumps(form_data.get('answers', {}), indent=2)}

Based on the group responses above, recommend the TOP 10 Indian destinations.

Respond ONLY with a JSON array of exactly 10 objects. No extra text. Format:
[
  {{
    "destination": "destination name",
    "reasoning": "2-3 sentences explaining why this suits the group based on their responses",
    "best_activities": ["activity1", "activity2", "activity3"],
    "hotels": ["hotel suggestion 1", "hotel suggestion 2"],
    "estimated_budget": {{
      "hotel_per_night": "₹X - ₹Y",
      "transport_from_major_city": "₹X - ₹Y"
    }},
    "best_time_to_visit": "month range",
    "match_score": 85
  }}
]
"""


def _render_recommendations_v2(ctx: dict) -> str:
    """v2: more explicit instructions to use group consensus and avoid repeats /
    avoided places; asks the model to weigh shared preferences over outliers."""
    trip_name = ctx.get("trip_name", "Trip")
    form_data = ctx.get("form_data", {})
    return f"""
You are an expert Indian travel planner helping a GROUP reach consensus.

Trip: {trip_name}
Group size: {form_data.get('group_size', 1)} people

Here are the combined preferences collected from every group member. Some answers
appear multiple times — treat repeated answers as stronger group signals, and
favour destinations that satisfy the SHARED preferences rather than any single
member's outlier choice. If members listed places already visited or places to
avoid, do not recommend those.

Group responses:
{json.dumps(form_data.get('answers', {}), indent=2)}

Recommend the TOP 10 Indian destinations for THIS group.

Respond ONLY with a JSON array of exactly 10 objects, ordered best match first.
No extra text. Format:
[
  {{
    "destination": "destination name",
    "reasoning": "2-3 sentences citing the specific group preferences this satisfies",
    "best_activities": ["activity1", "activity2", "activity3"],
    "hotels": ["hotel suggestion 1", "hotel suggestion 2"],
    "estimated_budget": {{
      "hotel_per_night": "₹X - ₹Y",
      "transport_from_major_city": "₹X - ₹Y"
    }},
    "best_time_to_visit": "month range",
    "match_score": 85
  }}
]
"""


def _render_recommendations_v3(ctx: dict) -> str:
    """v3: returns trip *concepts*, each of which may be a single base OR a
    multi-city route sized to the trip's length. Keeps the same required
    fields as v1/v2 (so the eval harness still applies) and adds an optional
    `stops` array describing the route."""
    trip_name = ctx.get("trip_name", "Trip")
    form_data = ctx.get("form_data", {})
    return f"""
You are an expert Indian travel planner helping a GROUP reach consensus.

Trip: {trip_name}
Group size: {form_data.get('group_size', 1)} people

Combined preferences from every group member (repeated answers = stronger group
signals; favour SHARED preferences over any one member's outlier). If members
listed places already visited or to avoid, do not recommend those.

Group responses:
{json.dumps(form_data.get('answers', {}), indent=2)}

Recommend the TOP 10 trip OPTIONS for THIS group. IMPORTANT: an option can be
either a single base (stay in one place the whole trip) OR a multi-city route
(2-4 nearby places covered in one trip), whichever genuinely suits the group's
trip length and pace. Size routes sensibly to the trip duration — do not cram
too many stops into a short trip. For a single-base option, return an empty
"stops" list.

Respond ONLY with a JSON array of exactly 10 objects, best match first. No extra
text. Format:
[
  {{
    "destination": "a clear label — for a route use 'Region: A → B → C', for a single base just the place name",
    "stops": [
      {{ "place": "place name", "nights": 2, "highlights": ["thing1", "thing2"] }}
    ],
    "reasoning": "2-3 sentences citing the specific group preferences this satisfies, and why this structure (single base vs route) fits the trip length",
    "best_activities": ["activity1", "activity2", "activity3"],
    "hotels": ["hotel/area suggestion 1", "hotel/area suggestion 2"],
    "estimated_budget": {{
      "hotel_per_night": "₹X - ₹Y",
      "transport": "₹X - ₹Y"
    }},
    "best_time_to_visit": "month range",
    "match_score": 85
  }}
]
"""


RECOMMENDATIONS_PROMPTS = {
    "recommendations_v1": PromptTemplate(
        version="recommendations_v1",
        feature="recommendations",
        description="Baseline: straightforward top-10 from aggregated answers.",
        render=_render_recommendations_v1,
    ),
    "recommendations_v2": PromptTemplate(
        version="recommendations_v2",
        feature="recommendations",
        description="Consensus-weighted: emphasises shared preferences, excludes visited/avoided places.",
        render=_render_recommendations_v2,
    ),
    "recommendations_v3": PromptTemplate(
        version="recommendations_v3",
        feature="recommendations",
        description="Trip-concepts: each option may be a single base OR a multi-city route sized to the trip length.",
        render=_render_recommendations_v3,
    ),
}


# ── itinerary prompts ───────────────────────────────────────────────

def _render_itinerary_v1(ctx: dict) -> str:
    """Build a day-by-day itinerary for ONE already-chosen destination.
    Context: destination, trip_name, days (trip length), group_size."""
    destination = ctx.get("destination", "the destination")
    trip_name = ctx.get("trip_name", "Trip")
    days = ctx.get("days", 5)
    group_size = ctx.get("group_size", 1)
    return f"""
You are an expert Indian travel planner building a day-by-day itinerary.

Trip: {trip_name}
Destination: {destination}
Group size: {group_size} people
Length: {days} days

Create a realistic {days}-day itinerary for this group at {destination}.
Keep each day's plan practical (geographically sensible, not over-packed) and
suited to a group of friends.

Respond ONLY with a JSON array of exactly {days} objects, one per day, in order.
No extra text. Format:
[
  {{
    "day": 1,
    "title": "short title for the day",
    "items": ["activity 1", "activity 2", "activity 3"]
  }}
]
"""


ITINERARY_PROMPTS = {
    "itinerary_v1": PromptTemplate(
        version="itinerary_v1",
        feature="itinerary",
        description="Day-by-day plan for a single chosen destination.",
        render=_render_itinerary_v1,
    ),
}


# ── registry access ─────────────────────────────────────────────────

# all prompts, keyed by version id
REGISTRY = {**RECOMMENDATIONS_PROMPTS, **ITINERARY_PROMPTS}

# the version each feature uses by default (point here to roll out a new version)
DEFAULT_VERSIONS = {
    "recommendations": "recommendations_v3",
    "itinerary": "itinerary_v1",
}


def get_prompt(feature: str, version: str = None) -> PromptTemplate:
    """Return a prompt template by version, or the feature's default version."""
    if version is None:
        version = DEFAULT_VERSIONS.get(feature)
    if version not in REGISTRY:
        raise KeyError(f"Unknown prompt version: {version!r}")
    return REGISTRY[version]


def list_prompts() -> list:
    """Metadata for every registered prompt version (for the API / tester)."""
    return [
        {
            "version": p.version,
            "feature": p.feature,
            "description": p.description,
            "is_default": DEFAULT_VERSIONS.get(p.feature) == p.version,
        }
        for p in REGISTRY.values()
    ]