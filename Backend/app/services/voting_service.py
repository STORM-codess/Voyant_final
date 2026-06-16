import random
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vote import Vote, VoteSession, VoteOption

REVOTE_EXTENSION_HOURS = 24

# \u2500\u2500\u2500 Ballot helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

async def get_session_ballots(session_id: str, db: AsyncSession) -> list:
    """Get all ballots for a session. Each ballot is an ordered list of option ids (first = top choice)."""
    result = await db.execute(
        select(Vote).where(Vote.session_id == session_id)
    )
    votes = result.scalars().all()
    return [vote.rankings or [] for vote in votes]

async def get_session_option_ids(session_id: str, db: AsyncSession) -> list:
    """Get all option ids for a session"""
    result = await db.execute(
        select(VoteOption).where(VoteOption.session_id == session_id)
    )
    return [option.id for option in result.scalars().all()]

def count_first_choices(ballots: list, active_options: list) -> dict:
    """Count each ballot's highest-ranked option that is still active"""
    counts = {option_id: 0 for option_id in active_options}
    for ballot in ballots:
        for option_id in ballot:
            if option_id in counts:
                counts[option_id] += 1
                break
    return counts

# \u2500\u2500\u2500 Instant-runoff (ranked-choice) counting \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def run_instant_runoff(ballots: list, option_ids: list) -> tuple:
    """
    Ranked-choice voting using instant-runoff:
    1. Count first choices
    2. If an option has a majority (>50%), it wins
    3. Otherwise eliminate the option(s) with the fewest votes and redistribute
    4. Repeat until a winner emerges or all remaining options are tied

    Returns (winner_id, is_tie, tied_ids, rounds)
    rounds is a list of per-round count breakdowns for transparency.
    """
    active = list(option_ids)
    rounds = []
    round_number = 1

    valid_ballots = [ballot for ballot in ballots if ballot]
    if not valid_ballots or not active:
        return None, False, [], rounds

    while True:
        counts = count_first_choices(valid_ballots, active)
        total = sum(counts.values())
        round_info = {"round": round_number, "counts": dict(counts)}
        rounds.append(round_info)

        if total == 0:
            return None, True, list(active), rounds

        # majority winner?
        for option_id, count in counts.items():
            if count * 2 > total:
                return option_id, False, [], rounds

        if len(active) == 1:
            return active[0], False, [], rounds

        # find lowest-ranked option(s) to eliminate
        min_votes = min(counts.values())
        lowest = [option_id for option_id, count in counts.items() if count == min_votes]

        if len(lowest) == len(active):
            # all remaining options are tied
            return None, True, list(active), rounds

        for option_id in lowest:
            active.remove(option_id)
        round_info["eliminated"] = lowest
        round_number += 1

# \u2500\u2500\u2500 Session closing \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

async def close_session(session: VoteSession, db: AsyncSession) -> dict:
    """
    Run ranked-choice counting and close (or move to revote) a session.
    Tie handling: the first tie starts a revote (ballots cleared, deadline
    extended); a tie after the revote is broken randomly.
    """
    ballots = await get_session_ballots(session.id, db)
    option_ids = await get_session_option_ids(session.id, db)
    winner_id, is_tie, tied_ids, rounds = run_instant_runoff(ballots, option_ids)

    if is_tie:
        if session.status == "revote":
            # still tied after revote \u2014 break randomly
            winner_id = pick_random_winner(tied_ids)
            session.winner_option_id = winner_id
            session.status = "closed"
            session.is_random_winner = True
            await db.commit()
            return {
                "status": "closed",
                "winner_option_id": winner_id,
                "is_random": True,
                "tied_options": tied_ids,
                "rounds": rounds
            }

        # first tie \u2014 start revote with fresh ballots and an extended deadline
        votes_result = await db.execute(
            select(Vote).where(Vote.session_id == session.id)
        )
        for vote in votes_result.scalars().all():
            await db.delete(vote)

        new_deadline = datetime.now(timezone.utc) + timedelta(hours=REVOTE_EXTENSION_HOURS)
        session.status = "revote"
        session.deadline = new_deadline
        session.revote_deadline = new_deadline
        await db.commit()
        return {
            "status": "revote",
            "tied_options": tied_ids,
            "deadline": new_deadline,
            "rounds": rounds
        }

    if winner_id is None:
        # no ballots were cast
        if session.status == "revote" and option_ids:
            # revote got no ballots \u2014 break the original tie randomly
            winner_id = pick_random_winner(option_ids)
            session.winner_option_id = winner_id
            session.is_random_winner = True
        session.status = "closed"
        await db.commit()
        return {
            "status": "closed",
            "winner_option_id": winner_id,
            "is_random": bool(session.is_random_winner),
            "rounds": rounds
        }

    session.winner_option_id = winner_id
    session.status = "closed"
    session.is_random_winner = False
    await db.commit()
    return {
        "status": "closed",
        "winner_option_id": winner_id,
        "is_random": False,
        "rounds": rounds
    }

async def auto_close_if_expired(session: VoteSession, db: AsyncSession) -> bool:
    """
    Lazily close sessions whose deadline has passed.
    Returns True if the session changed state.
    """
    if session.status == "closed":
        return False
    if not is_deadline_passed(session.deadline):
        return False
    await close_session(session, db)
    return True

# \u2500\u2500\u2500 Utilities \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def pick_random_winner(tied_ids: list) -> str:
    """Randomly pick from tied options"""
    return random.choice(tied_ids)

def is_deadline_passed(deadline: datetime) -> bool:
    """Check if deadline has passed"""
    now = datetime.now(timezone.utc)
    if deadline.tzinfo is None:
        deadline = deadline.replace(tzinfo=timezone.utc)
    return now > deadline
