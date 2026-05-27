from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


def build_submission_package(config: dict[str, Any]) -> None:
    csv_dir = Path(config["paths"]["results_csv_dir"])
    figure_dir = Path(config["paths"]["figures_dir"])
    provenance_dir = Path(config["paths"]["provenance_dir"])

    _write_manifest(config, csv_dir, figure_dir, provenance_dir)
    _write_report(csv_dir)
    _write_pitch(csv_dir)


def _read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def _write_manifest(config: dict[str, Any], csv_dir: Path, figure_dir: Path, provenance_dir: Path) -> None:
    files = []
    for root in [csv_dir, figure_dir, provenance_dir, Path("src"), Path("app"), Path("tests"), Path("report"), Path("pitch"), Path("notebooks")]:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.is_file():
                files.append({"path": str(path).replace("\\", "/"), "bytes": path.stat().st_size})

    manifest = {
        "project": "SKILLAB Skill Radar",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reproduction_commands": [
            "python -m src.pipeline --config config.yaml",
            "python -m unittest discover -s tests",
            "streamlit run app/streamlit_app.py",
            "jupyter notebook notebooks",
        ],
        "tracker_api": config["tracker"]["api"],
        "api_entities": ["jobs", "profiles", "courses"],
        "domains": list(config["domains"].keys()),
        "max_pages_per_entity": config["tracker"]["max_pages_per_entity"],
        "labour_market_data_rule": "All job, profile, and course records come from the SKILLAB Tracker API.",
        "metadata_rule": "ESCO/ISCO files are used only for labels and hierarchy enrichment.",
        "generated_files": files,
    }
    out = Path("results/submission_manifest.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")


def _write_report(csv_dir: Path) -> None:
    story = _read_csv(csv_dir / "domain_story_summary.csv")
    methodology = _read_csv(csv_dir / "methodology_table.csv")
    duplicates = _read_csv(csv_dir / "data_integrity_duplicates.csv")
    insights = _read_csv(csv_dir / "insight_cards.csv")
    summary = _read_csv(csv_dir / "all_domains_summary.csv")

    lines = [
        "# SKILLAB Skill Radar Report",
        "",
        "## Executive Summary",
        "",
        "Skill Radar is a reproducible labour-market intelligence workflow built for the SKILLAB Innovation Challenge. It combines Tracker API data from jobs, profiles, and courses to answer practical questions: what skills are demanded, what skills are supplied, which candidates are closest to domain demand, and which domains look most attractive to enter. Version 1.2 adds an API-only Domain Opportunity Score; it is not salary data.",
        "",
        "The project follows the webinar framing of a regional, sectoral, and temporal skill intelligence platform. Jobs are treated as demand, profiles as supply, and courses as training/upskilling coverage. ESCO metadata is used to label skills and group them into capability families.",
        "",
        "## Data and Reproducibility",
        "",
        "All labour-market records are fetched from the SKILLAB Tracker API endpoints `/jobs`, `/profiles`, and `/courses`. Raw responses are cached under `data/cache/` and normalized outputs are written under `results/csv/`.",
        "",
        "Reproduction commands:",
        "",
        "```powershell",
        "python -m src.pipeline --config config.yaml",
        "python -m unittest discover -s tests",
        "streamlit run app/streamlit_app.py",
        "jupyter notebook notebooks",
        "```",
        "",
    ]

    if not summary.empty:
        total_jobs = int(summary["jobs_fetched"].astype(int).sum())
        total_profiles = int(summary["profiles_fetched"].astype(int).sum())
        total_courses = int(summary["courses_fetched"].astype(int).sum())
        lines.extend([
            f"The current bounded run includes {total_jobs} fetched jobs, {total_profiles} fetched profiles, and {total_courses} fetched courses across {len(summary)} domains.",
            "",
        ])

    if not duplicates.empty:
        duplicate_total = int(duplicates["duplicate_source_source_id"].astype(int).sum())
        lines.extend([
            f"Data integrity check: duplicate `(source, source_id)` pairs found in generated extracts: {duplicate_total}.",
            "",
        ])

    lines.extend(["## Methodology", ""])
    if not methodology.empty:
        lines.append("| Metric | Formula | Interpretation |")
        lines.append("| --- | --- | --- |")
        for row in methodology.itertuples():
            lines.append(f"| {row.metric} | `{row.formula}` | {row.interpretation} |")
        lines.append("")

    lines.extend(["## Main Findings", ""])
    if not story.empty:
        for row in story.itertuples():
            lines.extend([
                f"### {row.domain}",
                "",
                f"- Largest skill shortage: **{row.top_gap_skill}** (gap score {float(row.top_gap_score):.3f}).",
                f"- Top rising skill: **{row.top_rising_skill}** (trend score {float(row.top_trend_score):.3f}).",
                f"- Largest training misalignment: **{row.top_training_gap_skill}** (index {float(row.training_misalignment_index):.3f}).",
                f"- Highest future-risk signal: **{row.top_future_risk_skill}** (score {float(row.future_risk_score):.3f}).",
                f"- Highest skill-shock signal: **{row.top_skill_shock_skill}** (index {float(row.skill_shock_index):.3f}).",
                f"- Top training investment priority: **{row.top_training_roi_skill}** (priority {float(row.training_roi_priority):.3f}).",
                f"- Best anonymized candidate profile: **{row.best_candidate_profile_id}** (readiness index {float(row.candidate_readiness_index):.3f}).",
                "",
            ])

    lines.extend([
        "## Evidence Artefacts",
        "",
        "Recommended figures for the jury package:",
        "",
        "- `results/figures/advanced_cross_domain_skill_heatmap.png`",
        "- `results/figures/advanced_skill_gap_portfolio.png`",
        "- `results/figures/advanced_training_alignment.png`",
        "- `results/figures/advanced_skill_shock_index.png`",
        "- `results/figures/advanced_career_bridges.png`",
        "- `results/figures/advanced_training_roi_priority.png`",
        "- `results/figures/advanced_domain_market_attractiveness.png`",
        "- `results/figures/advanced_domain_choice_radar.png`",
        "- `results/figures/advanced_future_risk_quadrant.png`",
        "- `results/figures/advanced_capability_family_gaps.png`",
        "",
    ])

    if not insights.empty:
        lines.extend(["## Insight Cards", ""])
        for row in insights.head(12).itertuples():
            lines.append(f"- **{row.headline}** {row.evidence}")
        lines.append("")

    lines.extend([
        "## Limitations",
        "",
        "- The default run is bounded by `tracker.max_pages_per_entity` so the demo remains fast under API latency.",
        "- Domain extraction uses transparent keyword filters, which can include noisy records.",
        "- Generic cross-domain skills are filtered from presentation rankings, but raw extracts remain cached.",
        "- Candidate matching is explainable skill overlap, not a full hiring model.",
        "",
        "## Conclusion",
        "",
        "Skill Radar packages SKILLAB Tracker data into a reproducible decision dashboard. It goes beyond top-skill charts by combining demand, supply, trend, training coverage, ESCO hierarchy, and explainable candidate matching into one workflow.",
    ])

    Path("report/REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_pitch(csv_dir: Path) -> None:
    story = _read_csv(csv_dir / "domain_story_summary.csv")
    first = story.iloc[0] if not story.empty else None
    example_domain = first["domain"] if first is not None else "IT"
    top_gap = first["top_gap_skill"] if first is not None else "the top shortage skill"
    top_risk = first["top_future_risk_skill"] if first is not None else "the top future-risk skill"

    lines = [
        "# Skill Radar Pitch Script",
        "",
        "## 0:00-0:30 - Problem",
        "",
        "Europe has rich labour-market data, but the hard question is operational: what skills are employers asking for, what does the workforce already offer, and what should education or hiring teams do next?",
        "",
        "## 0:30-1:10 - Solution",
        "",
        "Skill Radar turns SKILLAB Tracker into an explainable decision dashboard. It combines demand from jobs, supply from profiles, and upskilling coverage from courses. It also detects future skill shocks, recommends training investments, explains realistic reskilling pathways between domains, and ranks domains with an API-only opportunity proxy.",
        "",
        "## 1:10-2:00 - Method",
        "",
        "We query only the SKILLAB Tracker API for jobs, profiles, and courses. ESCO/ISCO files are used only as official metadata for skill labels and hierarchy. Every run writes raw cache, CSV tables, figures, and provenance files.",
        "",
        "## 2:00-3:20 - Results",
        "",
        f"Start with {example_domain}. The largest shortage signal is `{top_gap}`. The strongest future-risk signal is `{top_risk}`. Then move to the cross-domain heatmap and the demand-vs-supply portfolio to show that this is not just a list of popular skills; it is a structured market map.",
        "",
        "Recommended figures:",
        "",
        "- `advanced_cross_domain_skill_heatmap.png`",
        "- `advanced_skill_gap_portfolio.png`",
        "- `advanced_training_alignment.png`",
        "- `advanced_skill_shock_index.png`",
        "- `advanced_career_bridges.png`",
        "- `advanced_training_roi_priority.png`",
        "- `advanced_domain_market_attractiveness.png`",
        "- `advanced_domain_choice_radar.png`",
        "- `advanced_future_risk_quadrant.png`",
        "",
        "## 3:20-4:20 - Demo",
        "",
        "Open Streamlit. Start with Overview, then show Domain Market Attractiveness. Explain that salary is not exposed by the Tracker, so we build an API-only attractiveness proxy: a domain is better when demand is strong, trends are stable, required skills are accessible, courses support the gap, and candidates can realistically match. Then use Demand/Supply Gap, Hot & Cooling Skills, Candidate Fit, Locations, and Advanced Studies. If Streamlit is not available, open the mirrored notebooks under `notebooks/`.",
        "",
        "## 4:20-5:00 - Close",
        "",
        "The innovation is the combination: demand, supply, training response, temporal movement, ESCO hierarchy, candidate matching, future shock detection, reskilling pathways, and domain attractiveness in one reproducible workflow. The limitation is that this hackathon run is bounded for speed, and domain attractiveness is a proxy rather than real income, but the same pipeline scales by increasing `max_pages_per_entity`.",
    ]
    Path("pitch/PITCH_OUTLINE.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
