from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, Integer
from app.database import get_db
from app.models.ai_call import AICall
from app.models.trip import TripMember
from app.firebase import get_current_user

router = APIRouter(prefix="/ai-metrics", tags=["ai-metrics"])


@router.get("/summary")
async def usage_summary(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Overall AI usage: totals plus a per-model breakdown."""
    totals = (await db.execute(
        select(
            func.count(AICall.id),
            func.sum(AICall.total_tokens),
            func.sum(AICall.estimated_cost_usd),
        )
    )).one()

    success_count = (await db.execute(
        select(func.count(AICall.id)).where(AICall.success == True)
    )).scalar() or 0

    per_model_rows = (await db.execute(
        select(
            AICall.model,
            func.count(AICall.id),
            func.sum(AICall.total_tokens),
            func.sum(AICall.estimated_cost_usd),
            func.avg(AICall.latency_ms),
        ).group_by(AICall.model)
    )).all()

    total_calls = totals[0] or 0
    return {
        "total_calls": total_calls,
        "successful_calls": success_count,
        "success_rate": round(success_count / total_calls, 3) if total_calls else None,
        "total_tokens": int(totals[1] or 0),
        "total_estimated_cost_usd": round(float(totals[2] or 0), 6),
        "per_model": [
            {
                "model": r[0],
                "calls": r[1],
                "tokens": int(r[2] or 0),
                "estimated_cost_usd": round(float(r[3] or 0), 6),
                "avg_latency_ms": round(float(r[4] or 0), 1),
            }
            for r in per_model_rows
        ],
    }


@router.get("/trip/{trip_id}")
async def usage_for_trip(
    trip_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """AI cost/usage scoped to one trip. Restricted to trip members."""
    member = (await db.execute(
        select(TripMember).where(
            TripMember.trip_id == trip_id,
            TripMember.user_id == current_user["uid"],
        )
    )).scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not a trip member")

    rows = (await db.execute(
        select(AICall).where(AICall.trip_id == trip_id).order_by(AICall.created_at)
    )).scalars().all()

    return {
        "trip_id": trip_id,
        "calls": len(rows),
        "total_tokens": sum(r.total_tokens or 0 for r in rows),
        "total_estimated_cost_usd": round(sum(r.estimated_cost_usd or 0 for r in rows), 6),
        "details": [
            {
                "model": r.model,
                "feature": r.feature,
                "success": r.success,
                "fallback_position": r.fallback_position,
                "latency_ms": r.latency_ms,
                "total_tokens": r.total_tokens,
                "estimated_cost_usd": r.estimated_cost_usd,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }


# ── Layer 3: extended reporting ──────────────────────────────────────

from datetime import datetime, timezone, timedelta


def _window_clause(days: int):
    """Return a SQLAlchemy filter for 'created within the last N days', or None."""
    if not days or days <= 0:
        return None
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    return AICall.created_at >= cutoff


@router.get("/by-prompt-version")
async def usage_by_prompt_version(
    days: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Per-prompt-version breakdown — the bridge to A/B testing.
    Optional ?days=N limits to the last N days."""
    stmt = select(
        AICall.prompt_version,
        func.count(AICall.id),
        func.sum(func.cast(AICall.success, Integer)),
        func.sum(AICall.total_tokens),
        func.sum(AICall.estimated_cost_usd),
        func.avg(AICall.latency_ms),
        func.avg(AICall.eval_score),
    ).group_by(AICall.prompt_version)

    clause = _window_clause(days)
    if clause is not None:
        stmt = stmt.where(clause)

    rows = (await db.execute(stmt)).all()
    out = []
    for version, calls, successes, tokens, cost, avg_latency, avg_eval in rows:
        calls = calls or 0
        successes = successes or 0
        out.append({
            "prompt_version": version,
            "calls": calls,
            "successful_calls": successes,
            "success_rate": round(successes / calls, 3) if calls else None,
            "total_tokens": int(tokens or 0),
            "avg_tokens_per_call": round((tokens or 0) / calls, 1) if calls else None,
            "total_estimated_cost_usd": round(float(cost or 0), 6),
            "avg_cost_per_call_usd": round(float(cost or 0) / calls, 6) if calls else None,
            "avg_latency_ms": round(float(avg_latency or 0), 1),
            "avg_eval_score": round(float(avg_eval), 3) if avg_eval is not None else None,
        })
    return {"window_days": days or "all", "by_prompt_version": out}


@router.get("/reliability")
async def reliability(
    days: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Failure + fallback health: how often the primary model fails and a
    fallback has to carry the request."""
    clause = _window_clause(days)

    base = select(
        func.count(AICall.id),
        func.sum(func.cast(AICall.success, Integer)),
    )
    if clause is not None:
        base = base.where(clause)
    total_attempts, successes = (await db.execute(base)).one()
    total_attempts = total_attempts or 0
    successes = successes or 0

    # successful calls broken down by which fallback position carried them
    pos_stmt = select(
        AICall.fallback_position, func.count(AICall.id)
    ).where(AICall.success == True).group_by(AICall.fallback_position)
    if clause is not None:
        pos_stmt = pos_stmt.where(clause)
    pos_rows = (await db.execute(pos_stmt)).all()
    by_position = {int(p): c for p, c in pos_rows if p is not None}

    served_by_primary = by_position.get(0, 0)
    served_by_fallback = sum(c for p, c in by_position.items() if p > 0)

    return {
        "window_days": days or "all",
        "total_attempts": total_attempts,
        "successful_attempts": successes,
        "failed_attempts": total_attempts - successes,
        "served_by_primary": served_by_primary,
        "served_by_fallback": served_by_fallback,
        "fallback_rate": round(
            served_by_fallback / (served_by_primary + served_by_fallback), 3
        ) if (served_by_primary + served_by_fallback) else None,
        "successful_by_position": by_position,
    }


@router.get("/cost-efficiency")
async def cost_efficiency(
    days: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Per-model cost efficiency — the data behind 'cost optimization'.
    Shows cost-per-1k-tokens and avg latency so you can decide which model
    to route simple vs complex tasks to."""
    clause = _window_clause(days)
    stmt = select(
        AICall.model,
        func.count(AICall.id),
        func.sum(AICall.total_tokens),
        func.sum(AICall.estimated_cost_usd),
        func.avg(AICall.latency_ms),
    ).where(AICall.success == True).group_by(AICall.model)
    if clause is not None:
        stmt = stmt.where(clause)

    rows = (await db.execute(stmt)).all()
    out = []
    for model, calls, tokens, cost, avg_latency in rows:
        tokens = int(tokens or 0)
        cost = float(cost or 0)
        out.append({
            "model": model,
            "successful_calls": calls,
            "total_tokens": tokens,
            "total_estimated_cost_usd": round(cost, 6),
            "cost_per_1k_tokens_usd": round((cost / tokens) * 1000, 6) if tokens else None,
            "avg_latency_ms": round(float(avg_latency or 0), 1),
        })
    out.sort(key=lambda x: (x["cost_per_1k_tokens_usd"] or 0))
    return {"window_days": days or "all", "models_cheapest_first": out}

# ── public showcase metrics (NO AUTH) ────────────────────────────────
# Curated, aggregate-only numbers for the public "How our AI works" page.
# Deliberately excludes anything per-trip, per-user, or call-level — only
# system-health aggregates that are safe to show a logged-out visitor.

@router.get("/public")
async def public_metrics(db: AsyncSession = Depends(get_db)):
    # totals
    totals = (await db.execute(
        select(
            func.count(AICall.id),
            func.sum(AICall.total_tokens),
            func.sum(func.cast(AICall.success, Integer)),
            func.avg(AICall.latency_ms),
            func.avg(AICall.eval_score),
        )
    )).one()
    total_calls = totals[0] or 0
    total_tokens = int(totals[1] or 0)
    successes = totals[2] or 0
    avg_latency_ms = round(float(totals[3] or 0), 1)
    avg_eval = round(float(totals[4]), 3) if totals[4] is not None else None

    # per-model usage split (names + share only — no raw cost)
    model_rows = (await db.execute(
        select(AICall.model, func.count(AICall.id), func.avg(AICall.latency_ms))
        .group_by(AICall.model)
    )).all()
    per_model = [
        {
            "model": m,
            "calls": c,
            "share": round(c / total_calls, 3) if total_calls else None,
            "avg_latency_ms": round(float(lat or 0), 1),
        }
        for m, c, lat in model_rows
    ]

    # fallback health (which position served successful calls)
    pos_rows = (await db.execute(
        select(AICall.fallback_position, func.count(AICall.id))
        .where(AICall.success == True).group_by(AICall.fallback_position)
    )).all()
    by_position = {int(p): c for p, c in pos_rows if p is not None}
    served_primary = by_position.get(0, 0)
    served_fallback = sum(c for p, c in by_position.items() if p > 0)
    served_total = served_primary + served_fallback

    # per-prompt-version eval + cost (the A/B story)
    pv_rows = (await db.execute(
        select(
            AICall.prompt_version,
            func.count(AICall.id),
            func.avg(AICall.eval_score),
            func.avg(AICall.estimated_cost_usd),
        ).group_by(AICall.prompt_version)
    )).all()
    prompt_versions = [
        {
            "prompt_version": v,
            "calls": c,
            "avg_eval_score": round(float(ev), 3) if ev is not None else None,
            "avg_cost_per_call_usd": round(float(cost or 0), 6),
        }
        for v, c, ev, cost in pv_rows if v is not None
    ]

    return {
        "total_calls": total_calls,
        "success_rate": round(successes / total_calls, 3) if total_calls else None,
        "total_tokens": total_tokens,
        "avg_latency_ms": avg_latency_ms,
        "avg_eval_score": avg_eval,
        "served_by_primary": served_primary,
        "served_by_fallback": served_fallback,
        "fallback_rate": round(served_fallback / served_total, 3) if served_total else None,
        "per_model": per_model,
        "prompt_versions": prompt_versions,
    }