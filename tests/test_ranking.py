"""Picking the right TMDB hit. Regression: 'Euforia' must resolve to Euphoria."""
import pytest

from app.ranking import EXACT, NONE, PARTIAL, PREFIX, best_match, fold, match_tier

# Real TMDB payload for query 'Euforia', language pl-PL, in TMDB's own order.
EUFORIA_RESULTS = [
    {"id": 1, "name": "Eufòria", "original_name": "Eufòria",
     "popularity": 7.3992, "vote_count": 2},
    {"id": 2, "name": "Eufòria Street Dance", "original_name": "Eufòria Street Dance",
     "popularity": 1.5771, "vote_count": 0},
    {"id": 3, "name": "Eufòria Dance Kids", "original_name": "Eufòria Dance Kids",
     "popularity": 1.1813, "vote_count": 0},
    {"id": 4, "name": "Euforia", "original_name": "Euphoria",
     "popularity": 81.385, "vote_count": 11119},
]


class TestFold:
    @pytest.mark.parametrize("raw,expected", [
        ("Eufòria", "euforia"),
        ("EUFORIA", "euforia"),
        ("  Psi   Patrol ", "psi patrol"),
        ("Pokémon", "pokemon"),
        (None, ""),
        ("", ""),
    ])
    def test_folds(self, raw, expected):
        assert fold(raw) == expected


class TestMatchTier:
    def test_exact_ignores_accents_and_case(self):
        assert match_tier("euforia", "Eufòria") == EXACT

    def test_exact_on_original_name(self):
        assert match_tier("Euphoria", "Euforia", "Euphoria") == EXACT

    def test_prefix(self):
        assert match_tier("Psi", "Psi Patrol") == PREFIX

    def test_partial(self):
        assert match_tier("Patrol", "Psi Patrol") == PARTIAL

    def test_unrelated(self):
        assert match_tier("Euforia", "Breaking Bad") == NONE

    def test_blank_query(self):
        assert match_tier("", "Anything") == NONE


class TestBestMatch:
    def test_prefers_popular_over_tmdb_order(self):
        """The bug: results[0] was the Catalan show, not HBO's Euphoria."""
        assert best_match(EUFORIA_RESULTS, "Euforia")["id"] == 4

    def test_exact_beats_more_popular_partial(self):
        results = [
            {"id": 1, "name": "Patrol Squad", "popularity": 900.0, "vote_count": 5000},
            {"id": 2, "name": "Psi Patrol", "popularity": 1.0, "vote_count": 1},
        ]
        assert best_match(results, "Psi Patrol")["id"] == 2

    def test_vote_count_breaks_popularity_tie(self):
        results = [
            {"id": 1, "name": "Show", "popularity": 5.0, "vote_count": 10},
            {"id": 2, "name": "Show", "popularity": 5.0, "vote_count": 99},
        ]
        assert best_match(results, "Show")["id"] == 2

    @pytest.mark.parametrize("results", [[], None, ["nonsense", 42], [{"name": "no id"}]])
    def test_unusable_input_returns_none(self, results):
        assert best_match(results, "Euforia") is None

    def test_skips_malformed_entries_but_keeps_good_ones(self):
        results = [None, "x", {"name": "no id"}, {"id": 7, "name": "Euforia"}]
        assert best_match(results, "Euforia")["id"] == 7

    def test_missing_numeric_fields_do_not_crash(self):
        results = [{"id": 1, "name": "Euforia"},
                   {"id": 2, "name": "Euforia", "popularity": "bogus", "vote_count": True}]
        assert best_match(results, "Euforia")["id"] in (1, 2)
