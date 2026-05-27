from __future__ import annotations

import unittest
from tempfile import TemporaryDirectory
from pathlib import Path

import pandas as pd
import yaml

from src.advanced_analytics import build_advanced_outputs
from src.metrics import candidate_matches, monthly_skill_counts, trend_table
from src.pipeline import domain_match_score, quality_row, top_rising_skill


class DummyEsco:
    def skill_label(self, uri: str) -> str:
        return {"s1": "Skill One", "s2": "Skill Two"}.get(uri, uri)

    def capability_family(self, uri: str) -> str:
        return "Family"


class MetricsTest(unittest.TestCase):
    def test_config_has_expanded_domain_keywords(self) -> None:
        with open("config.yaml", "r", encoding="utf-8") as handle:
            config = yaml.safe_load(handle)
        for domain, domain_config in config["domains"].items():
            self.assertGreaterEqual(len(domain_config["keywords"]), 25, f"{domain} should have broad search coverage.")

    def test_monthly_skill_counts(self) -> None:
        jobs = [
            {"upload_date": "2024-01-10", "skills": ["s1", "s2"]},
            {"upload_date": "2024-01-20", "skills": ["s1"]},
            {"upload_date": "2024-02-10", "skills": ["s2"]},
        ]
        result = monthly_skill_counts(jobs)
        self.assertEqual(int(result[result["skill_uri"] == "s1"]["count"].sum()), 2)
        self.assertEqual(int(result[result["skill_uri"] == "s2"]["count"].sum()), 2)

    def test_trend_classifies_rising(self) -> None:
        jobs = []
        for month, count in [("2024-01-01", 1), ("2024-02-01", 3), ("2024-03-01", 8)]:
            jobs.extend({"upload_date": month, "skills": ["s1"]} for _ in range(count))
        result = trend_table("IT", jobs, DummyEsco(), {"s1"}, recent_months=1)
        self.assertEqual(result.iloc[0]["trend_label"], "rising")

    def test_candidate_exact_match_ranks_first(self) -> None:
        relevance = pd.DataFrame([
            {"skill_uri": "s1", "relevance_index": 0.8},
            {"skill_uri": "s2", "relevance_index": 0.2},
        ])
        profiles = [
            {"id": 1, "skills": ["s1", "s2"], "source": "x", "source_id": "1"},
            {"id": 2, "skills": ["s2"], "source": "x", "source_id": "2"},
        ]
        result = candidate_matches("IT", profiles, relevance, DummyEsco(), top_n=2)
        self.assertEqual(int(result.iloc[0]["profile_id"]), 1)
        self.assertGreater(float(result.iloc[0]["candidate_score"]), float(result.iloc[1]["candidate_score"]))

    def test_top_rising_ignores_stable_zero_mention_skills(self) -> None:
        trends = pd.DataFrame([
            {"skill_label": "C++", "trend_score": 0.0, "trend_label": "stable", "total_monthly_mentions": 0},
            {"skill_label": "Skill One", "trend_score": 0.1, "trend_label": "rising", "total_monthly_mentions": 2},
        ])
        self.assertEqual(top_rising_skill(trends), "Skill One")
        self.assertEqual(top_rising_skill(trends.iloc[[0]]), "")

    def test_domain_match_score_accepts_relevant_and_rejects_unrelated(self) -> None:
        keywords = ["software", "python", "database"]
        relevant = {"title": "Python software developer", "description": "Build database applications.", "skills": ["s1"]}
        unrelated = {"title": "Hotel receptionist", "description": "Welcome guests and manage bookings.", "skills": []}
        self.assertGreaterEqual(domain_match_score(relevant, keywords, DummyEsco()), 0.15)
        self.assertLess(domain_match_score(unrelated, keywords, DummyEsco()), 0.15)

    def test_quality_report_flags_invalid_top_rising(self) -> None:
        trends = pd.DataFrame([
            {"skill_label": "C++", "trend_score": 0.0, "trend_label": "stable", "total_monthly_mentions": 0},
        ])
        row = quality_row(
            domain="IT",
            relevance=pd.DataFrame([{"skill_label": "C++"}]),
            gap=pd.DataFrame([{"skill_label": "C++"}]),
            trends=trends,
            candidates=pd.DataFrame(),
            duplicate_rows=[{"domain": "IT", "duplicate_source_source_id": 0}],
            filter_stats=[{"domain": "IT", "endpoint": "jobs", "domain_filter_fallback": True}],
            excluded=[],
        )
        self.assertEqual(row["zero_mention_trend_rows"], 1)
        self.assertFalse(row["top_rising_valid"])
        self.assertEqual(row["domain_filter_fallbacks"], "jobs")

    def test_advanced_innovation_outputs_rank_expected_signals(self) -> None:
        with TemporaryDirectory() as tmp:
            csv_dir = Path(tmp) / "csv"
            fig_dir = Path(tmp) / "figures"
            csv_dir.mkdir()
            fig_dir.mkdir()
            pd.DataFrame([
                {
                    "domain": "IT",
                    "skill_uri": "s1",
                    "skill_label": "Skill One",
                    "capability_family": "Family",
                    "demand_count": 10,
                    "supply_count": 0,
                    "course_count": 0,
                    "demand_frequency": 1.0,
                    "supply_frequency": 0.0,
                    "course_frequency": 0.0,
                    "gap_score": 1.0,
                    "trend_score": 0.5,
                    "relevance_index": 1.0,
                },
                {
                    "domain": "IT",
                    "skill_uri": "s2",
                    "skill_label": "Skill Two",
                    "capability_family": "Family",
                    "demand_count": 4,
                    "supply_count": 4,
                    "course_count": 4,
                    "demand_frequency": 0.4,
                    "supply_frequency": 0.4,
                    "course_frequency": 0.4,
                    "gap_score": 0.0,
                    "trend_score": 0.0,
                    "relevance_index": 0.2,
                },
            ]).to_csv(csv_dir / "it_skill_relevance.csv", index=False)
            pd.DataFrame([
                {"domain": "IT", "skill_uri": "s1", "skill_label": "Skill One", "capability_family": "Family", "trend_score": 0.5, "trend_label": "rising", "months_observed": 3, "total_monthly_mentions": 10},
                {"domain": "IT", "skill_uri": "s2", "skill_label": "Skill Two", "capability_family": "Family", "trend_score": 0.0, "trend_label": "stable", "months_observed": 3, "total_monthly_mentions": 4},
            ]).to_csv(csv_dir / "it_skill_trends.csv", index=False)
            pd.DataFrame([
                {"domain": "IT", "skill_uri": "s1", "skill_label": "Skill One", "capability_family": "Family", "demand_count": 10, "supply_count": 0, "course_count": 0, "demand_frequency": 1.0, "supply_frequency": 0.0, "course_frequency": 0.0, "gap_score": 1.0, "trend_score": 0.5, "relevance_index": 1.0},
                {"domain": "IT", "skill_uri": "s2", "skill_label": "Skill Two", "capability_family": "Family", "demand_count": 4, "supply_count": 4, "course_count": 4, "demand_frequency": 0.4, "supply_frequency": 0.4, "course_frequency": 0.4, "gap_score": 0.0, "trend_score": 0.0, "relevance_index": 0.2},
            ]).to_csv(csv_dir / "it_skill_gap.csv", index=False)
            pd.DataFrame([
                {"domain": "Other", "skill_uri": "s1", "skill_label": "Skill One", "capability_family": "Family", "demand_count": 6, "supply_count": 0, "course_count": 0, "demand_frequency": 0.8, "supply_frequency": 0.0, "course_frequency": 0.0, "gap_score": 0.8, "trend_score": 0.3, "relevance_index": 0.8},
            ]).to_csv(csv_dir / "other_skill_relevance.csv", index=False)
            pd.DataFrame([
                {"domain": "IT", "profile_id": 1, "source": "x", "source_id": "1", "location": "", "candidate_score": 1.0, "matched_skill_count": 1, "matched_skills": "s1", "matched_skill_labels": "Skill One", "missing_priority_skills": "", "missing_priority_skill_labels": ""},
            ]).to_csv(csv_dir / "it_candidate_matches.csv", index=False)

            build_advanced_outputs(["IT", "Other"], csv_dir, fig_dir)
            shock = pd.read_csv(csv_dir / "advanced_skill_shock_index.csv")
            roi = pd.read_csv(csv_dir / "advanced_training_roi_priority.csv")
            bridges = pd.read_csv(csv_dir / "advanced_career_bridges.csv")
            self.assertEqual(shock.iloc[0]["skill_uri"], "s1")
            self.assertEqual(roi.iloc[0]["skill_uri"], "s1")
            self.assertGreater(float(bridges.iloc[0]["career_bridge_score"]), 0)

    def test_domain_market_attractiveness_prefers_accessible_stable_domain(self) -> None:
        with TemporaryDirectory() as tmp:
            csv_dir = Path(tmp) / "csv"
            fig_dir = Path(tmp) / "figures"
            csv_dir.mkdir()
            fig_dir.mkdir()
            pd.DataFrame([
                {"domain": "Good", "jobs_fetched": 100, "profiles_fetched": 100, "courses_fetched": 100, "top_gap_skill": "s1", "top_rising_skill": "s1", "top_candidate_score": 1.0},
                {"domain": "Bad", "jobs_fetched": 100, "profiles_fetched": 100, "courses_fetched": 100, "top_gap_skill": "s2", "top_rising_skill": "s2", "top_candidate_score": 0.1},
            ]).to_csv(csv_dir / "all_domains_summary.csv", index=False)
            pd.DataFrame([
                {"domain": "Good", "skill_uri": "s1", "skill_label": "Skill One", "capability_family": "Family", "demand_count": 10, "supply_count": 8, "course_count": 8, "demand_frequency": 0.9, "supply_frequency": 0.7, "course_frequency": 0.8, "gap_score": 0.2, "trend_score": 0.05, "relevance_index": 0.9},
                {"domain": "Bad", "skill_uri": "s2", "skill_label": "Skill Two", "capability_family": "Family", "demand_count": 10, "supply_count": 0, "course_count": 0, "demand_frequency": 0.9, "supply_frequency": 0.0, "course_frequency": 0.0, "gap_score": 0.9, "trend_score": 0.8, "relevance_index": 0.9},
            ]).query("domain == 'Good'").to_csv(csv_dir / "good_skill_relevance.csv", index=False)
            pd.DataFrame([
                {"domain": "Good", "skill_uri": "s1", "skill_label": "Skill One", "capability_family": "Family", "demand_count": 10, "supply_count": 8, "course_count": 8, "demand_frequency": 0.9, "supply_frequency": 0.7, "course_frequency": 0.8, "gap_score": 0.2, "trend_score": 0.05, "relevance_index": 0.9},
            ]).to_csv(csv_dir / "good_skill_gap.csv", index=False)
            pd.DataFrame([
                {"domain": "Good", "skill_uri": "s1", "skill_label": "Skill One", "capability_family": "Family", "trend_score": 0.02, "trend_label": "stable", "months_observed": 3, "total_monthly_mentions": 10},
            ]).to_csv(csv_dir / "good_skill_trends.csv", index=False)
            pd.DataFrame([
                {"domain": "Bad", "skill_uri": "s2", "skill_label": "Skill Two", "capability_family": "Family", "demand_count": 10, "supply_count": 0, "course_count": 0, "demand_frequency": 0.9, "supply_frequency": 0.0, "course_frequency": 0.0, "gap_score": 0.9, "trend_score": 0.8, "relevance_index": 0.9},
            ]).to_csv(csv_dir / "bad_skill_relevance.csv", index=False)
            pd.DataFrame([
                {"domain": "Bad", "skill_uri": "s2", "skill_label": "Skill Two", "capability_family": "Family", "demand_count": 10, "supply_count": 0, "course_count": 0, "demand_frequency": 0.9, "supply_frequency": 0.0, "course_frequency": 0.0, "gap_score": 0.9, "trend_score": 0.8, "relevance_index": 0.9},
            ]).to_csv(csv_dir / "bad_skill_gap.csv", index=False)
            pd.DataFrame([
                {"domain": "Bad", "skill_uri": "s2", "skill_label": "Skill Two", "capability_family": "Family", "trend_score": 0.8, "trend_label": "rising", "months_observed": 3, "total_monthly_mentions": 10},
            ]).to_csv(csv_dir / "bad_skill_trends.csv", index=False)
            pd.DataFrame([
                {"domain": "Good", "profile_id": 1, "source": "x", "source_id": "1", "location": "", "candidate_score": 1.0, "matched_skill_count": 1, "matched_skills": "s1", "matched_skill_labels": "Skill One", "missing_priority_skills": "", "missing_priority_skill_labels": ""},
                {"domain": "Bad", "profile_id": 2, "source": "x", "source_id": "2", "location": "", "candidate_score": 0.1, "matched_skill_count": 0, "matched_skills": "", "matched_skill_labels": "", "missing_priority_skills": "s2", "missing_priority_skill_labels": "Skill Two"},
            ]).query("domain == 'Good'").to_csv(csv_dir / "good_candidate_matches.csv", index=False)
            pd.DataFrame([
                {"domain": "Bad", "profile_id": 2, "source": "x", "source_id": "2", "location": "", "candidate_score": 0.1, "matched_skill_count": 0, "matched_skills": "", "matched_skill_labels": "", "missing_priority_skills": "s2", "missing_priority_skill_labels": "Skill Two"},
            ]).to_csv(csv_dir / "bad_candidate_matches.csv", index=False)

            build_advanced_outputs(["Good", "Bad"], csv_dir, fig_dir)
            market = pd.read_csv(csv_dir / "advanced_domain_market_attractiveness.csv")
            self.assertEqual(market.iloc[0]["domain"], "Good")


if __name__ == "__main__":
    unittest.main()
