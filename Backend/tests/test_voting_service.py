"""Unit tests for the ranked-choice (instant-runoff) voting logic."""
from datetime import datetime, timezone, timedelta

from app.services.voting_service import (
    count_first_choices,
    run_instant_runoff,
    pick_random_winner,
    is_deadline_passed,
)


class TestCountFirstChoices:
    def test_counts_top_choices(self):
        ballots = [["a", "b"], ["a", "c"], ["b", "a"]]
        counts = count_first_choices(ballots, ["a", "b", "c"])
        assert counts == {"a": 2, "b": 1, "c": 0}

    def test_skips_eliminated_options(self):
        # "c" has been eliminated — votes fall through to the next preference
        ballots = [["c", "a"], ["c", "b"]]
        counts = count_first_choices(ballots, ["a", "b"])
        assert counts == {"a": 1, "b": 1}

    def test_exhausted_ballot_counts_nothing(self):
        ballots = [["c"]]
        counts = count_first_choices(ballots, ["a", "b"])
        assert counts == {"a": 0, "b": 0}


class TestInstantRunoff:
    def test_majority_in_first_round(self):
        ballots = [["a", "b"], ["a", "b"], ["b", "a"]]
        winner, is_tie, tied, rounds = run_instant_runoff(ballots, ["a", "b"])
        assert winner == "a"
        assert is_tie is False
        assert len(rounds) == 1

    def test_elimination_and_redistribution(self):
        # Round 1: a=2, b=2, c=1 — no majority, c eliminated
        # Round 2: c's ballot transfers to b — b wins 3-2
        ballots = [
            ["a", "b"], ["a", "c"],
            ["b", "a"], ["b", "c"],
            ["c", "b"],
        ]
        winner, is_tie, tied, rounds = run_instant_runoff(ballots, ["a", "b", "c"])
        assert winner == "b"
        assert is_tie is False
        assert rounds[0]["eliminated"] == ["c"]

    def test_all_remaining_tied(self):
        ballots = [["a", "b"], ["b", "a"]]
        winner, is_tie, tied, rounds = run_instant_runoff(ballots, ["a", "b"])
        assert winner is None
        assert is_tie is True
        assert set(tied) == {"a", "b"}

    def test_no_ballots(self):
        winner, is_tie, tied, rounds = run_instant_runoff([], ["a", "b"])
        assert winner is None
        assert is_tie is False

    def test_single_option(self):
        winner, is_tie, tied, rounds = run_instant_runoff([["a"]], ["a"])
        assert winner == "a"

    def test_exhausted_ballots_can_lead_to_tie(self):
        # Round 1: a=2, b=1, c=2 — b eliminated, its ballot is exhausted
        # Round 2: a=2, c=2 — tie between remaining options
        ballots = [["a", "b"], ["a"], ["b"], ["c"], ["c"]]
        winner, is_tie, tied, rounds = run_instant_runoff(ballots, ["a", "b", "c"])
        assert winner is None
        assert is_tie is True
        assert set(tied) == {"a", "c"}


class TestUtilities:
    def test_pick_random_winner(self):
        assert pick_random_winner(["a", "b"]) in {"a", "b"}

    def test_deadline_passed_aware(self):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        assert is_deadline_passed(past) is True
        assert is_deadline_passed(future) is False

    def test_deadline_passed_naive(self):
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        assert is_deadline_passed(past) is True
