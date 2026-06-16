"""
Evaluation harness for recommendation output quality.

These are DETERMINISTIC checks: given a raw model response, they score how well
it conforms to what we asked for (valid JSON, exactly 10 items, required fields,
sane values, no duplicates, respects exclusions). No LLM call, no cost, instant —
which is exactly what makes them usable as automated quality gates and as the
comparison metric for prompt A/B testing.

Each check contributes to a 0..1 score. The result also lists which checks passed
so failures are debuggable, not just a number.

LLM-as-judge scoring (subjective quality) could be added later as an additional
async check; the structure here leaves room for that without changing callers.
"""
from dataclasses import dataclass, field

EXPECTED_COUNT = 10
REQUIRED_FIELDS = ["destination", "reasoning", "best_activities", "estimated_budget"]


@dataclass
class EvalResult:
    score: float                      # 0..1 overall
    checks: dict = field(default_factory=dict)   # check_name -> bool/number
    notes: list = field(default_factory=list)    # human-readable findings

    def as_dict(self):
        return {"score": round(self.score, 3), "checks": self.checks, "notes": self.notes}


def evaluate_recommendations(parsed, form_data: dict = None) -> EvalResult:
    """Score a parsed recommendations list (already JSON-decoded).

    form_data is optional context used for the 'respects exclusions' check
    (places members said they'd already visited or want to avoid).
    """
    checks = {}
    notes = []

    # 1. is it a list at all?
    is_list = isinstance(parsed, list)
    checks["is_list"] = is_list
    if not is_list:
        notes.append("Output is not a JSON array.")
        return EvalResult(score=0.0, checks=checks, notes=notes)

    count = len(parsed)
    checks["item_count"] = count

    # 2. correct number of items (partial credit near the target)
    checks["count_exact"] = (count == EXPECTED_COUNT)
    if count != EXPECTED_COUNT:
        notes.append(f"Expected {EXPECTED_COUNT} items, got {count}.")

    # 3. every item is a dict with required fields present and non-empty
    well_formed = 0
    for i, item in enumerate(parsed):
        if not isinstance(item, dict):
            notes.append(f"Item {i} is not an object.")
            continue
        missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
        if missing:
            notes.append(f"Item {i} missing/empty fields: {missing}")
        else:
            well_formed += 1
    field_completeness = well_formed / count if count else 0.0
    checks["field_completeness"] = round(field_completeness, 3)

    # 4. no duplicate destinations
    names = [
        str(item.get("destination", "")).strip().lower()
        for item in parsed if isinstance(item, dict)
    ]
    non_empty = [n for n in names if n]
    unique_ratio = (len(set(non_empty)) / len(non_empty)) if non_empty else 0.0
    checks["no_duplicates"] = (unique_ratio == 1.0)
    if unique_ratio < 1.0:
        notes.append("Duplicate destinations found.")

    # 5. match_score values, when present, are sane (0..100)
    scores_seen = 0
    scores_valid = 0
    for item in parsed:
        if isinstance(item, dict) and "match_score" in item:
            scores_seen += 1
            try:
                v = float(item["match_score"])
                if 0 <= v <= 100:
                    scores_valid += 1
            except (TypeError, ValueError):
                pass
    checks["match_scores_valid"] = (
        round(scores_valid / scores_seen, 3) if scores_seen else None
    )

    # 6. respects exclusions (visited / avoided places mentioned in answers)
    excluded_hits = 0
    if form_data:
        answers = form_data.get("answers", {})
        excluded_terms = []
        for q, vals in answers.items():
            ql = str(q).lower()
            if "visited" in ql or "avoid" in ql:
                for v in (vals if isinstance(vals, list) else [vals]):
                    for token in str(v).replace(",", " ").split():
                        token = token.strip().lower()
                        if len(token) >= 3:
                            excluded_terms.append(token)
        for n in non_empty:
            if any(term in n for term in excluded_terms):
                excluded_hits += 1
        checks["respects_exclusions"] = (excluded_hits == 0)
        if excluded_hits:
            notes.append(f"{excluded_hits} recommendation(s) match excluded places.")
    else:
        checks["respects_exclusions"] = None

    # ── weighted score ───────────────────────────────────────────────
    # weights chosen to reward the things that matter most: well-formed,
    # complete items and correct count. Exclusion respect is a bonus when
    # we have the context to judge it.
    score = 0.0
    score += 0.35 * field_completeness
    score += 0.25 * (1.0 if checks["count_exact"] else max(0.0, 1 - abs(count - EXPECTED_COUNT) / EXPECTED_COUNT))
    score += 0.20 * (1.0 if checks["no_duplicates"] else unique_ratio)
    if checks["match_scores_valid"] is not None:
        score += 0.10 * checks["match_scores_valid"]
    else:
        score += 0.10  # no scores to fault
    if checks["respects_exclusions"] is None:
        score += 0.10
    else:
        score += 0.10 * (1.0 if checks["respects_exclusions"] else 0.0)

    return EvalResult(score=score, checks=checks, notes=notes)