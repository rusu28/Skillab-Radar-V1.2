from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


def _slug(domain: str) -> str:
    return domain.lower().replace(" ", "_")


def _read_domain_csv(csv_dir: Path, domain: str, suffix: str) -> pd.DataFrame:
    path = csv_dir / f"{_slug(domain)}_{suffix}.csv"
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


def build_advanced_outputs(domains: list[str], csv_dir: str | Path, figures_dir: str | Path) -> None:
    csv_path = Path(csv_dir)
    fig_path = Path(figures_dir)
    fig_path.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")

    relevance_frames = []
    gap_frames = []
    trend_frames = []
    for domain in domains:
        rel = _read_domain_csv(csv_path, domain, "skill_relevance")
        gap = _read_domain_csv(csv_path, domain, "skill_gap")
        trend = _read_domain_csv(csv_path, domain, "skill_trends")
        if not rel.empty:
            relevance_frames.append(rel)
        if not gap.empty:
            gap_frames.append(gap)
        if not trend.empty:
            trend_frames.append(trend)

    if not relevance_frames:
        return

    relevance = pd.concat(relevance_frames, ignore_index=True)
    gaps = pd.concat(gap_frames, ignore_index=True) if gap_frames else pd.DataFrame()
    trends = pd.concat(trend_frames, ignore_index=True) if trend_frames else pd.DataFrame()

    _cross_domain_heatmap(relevance, csv_path, fig_path)
    _gap_portfolio(relevance, csv_path, fig_path)
    _gap_heatmap(gaps, csv_path, fig_path)
    _training_alignment(relevance, csv_path, fig_path)
    _capability_family_summary(relevance, csv_path, fig_path)
    _candidate_readiness(domains, csv_path)
    _candidate_readiness_chart(csv_path, fig_path)
    _skill_shock_index(relevance, csv_path, fig_path, len(domains))
    _training_roi_priority(relevance, csv_path, fig_path)
    _career_bridges(domains, csv_path, fig_path)
    _location_coverage_chart(csv_path, fig_path)
    _methodology_table(csv_path)
    if not gaps.empty and not trends.empty:
        _rising_unmet_skills(gaps, trends, csv_path, fig_path)
        _future_risk_quadrant(gaps, trends, csv_path, fig_path)
    _domain_story_summary(domains, csv_path)
    _domain_market_attractiveness(domains, csv_path, fig_path)
    _domain_signal_scoreboard(csv_path, fig_path)
    _insight_cards(domains, csv_path)


def _normalized(series: pd.Series) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce").fillna(0).clip(lower=0)
    max_value = float(values.max())
    if max_value <= 0:
        return values * 0
    return values / max_value


def _cross_domain_heatmap(relevance: pd.DataFrame, csv_dir: Path, fig_dir: Path) -> None:
    top_labels = (
        relevance.sort_values("relevance_index", ascending=False)
        .groupby("domain")
        .head(10)["skill_label"]
        .drop_duplicates()
        .head(35)
        .tolist()
    )
    matrix = (
        relevance[relevance["skill_label"].isin(top_labels)]
        .pivot_table(index="domain", columns="skill_label", values="relevance_index", aggfunc="max", fill_value=0)
    )
    matrix.to_csv(csv_dir / "advanced_cross_domain_skill_heatmap.csv", encoding="utf-8")
    if matrix.empty:
        return
    plt.figure(figsize=(16, 6))
    sns.heatmap(matrix, cmap="YlGnBu", linewidths=0.4, linecolor="white")
    plt.title("Cross-domain skill relevance heatmap")
    plt.xlabel("Skill")
    plt.ylabel("Domain")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_cross_domain_skill_heatmap.png", dpi=170)
    plt.close()


def _gap_portfolio(relevance: pd.DataFrame, csv_dir: Path, fig_dir: Path) -> None:
    portfolio = relevance.copy()
    portfolio["bubble_size"] = 80 + portfolio["course_count"].clip(lower=0) * 12
    portfolio["portfolio_quadrant"] = "balanced"
    portfolio.loc[(portfolio["demand_frequency"] >= 0.25) & (portfolio["supply_frequency"] < 0.10), "portfolio_quadrant"] = "critical shortage"
    portfolio.loc[(portfolio["demand_frequency"] >= 0.25) & (portfolio["supply_frequency"] >= 0.10), "portfolio_quadrant"] = "high demand / available supply"
    portfolio.loc[(portfolio["demand_frequency"] < 0.25) & (portfolio["course_frequency"] >= 0.25), "portfolio_quadrant"] = "training ahead of demand"
    portfolio.to_csv(csv_dir / "advanced_skill_gap_portfolio.csv", index=False, encoding="utf-8")

    plt.figure(figsize=(11, 7))
    sns.scatterplot(
        data=portfolio,
        x="supply_frequency",
        y="demand_frequency",
        hue="domain",
        size="course_count",
        sizes=(40, 450),
        alpha=0.75,
    )
    plt.plot([0, 1], [0, 1], color="#444", linestyle="--", linewidth=1)
    plt.title("Skill portfolio: demand vs workforce supply")
    plt.xlabel("Supply frequency in profiles")
    plt.ylabel("Demand frequency in jobs")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_skill_gap_portfolio.png", dpi=170)
    plt.close()


def _gap_heatmap(gaps: pd.DataFrame, csv_dir: Path, fig_dir: Path) -> None:
    if gaps.empty:
        return
    top_labels = (
        gaps.sort_values("gap_score", ascending=False)
        .groupby("domain")
        .head(8)["skill_label"]
        .drop_duplicates()
        .head(35)
        .tolist()
    )
    matrix = (
        gaps[gaps["skill_label"].isin(top_labels)]
        .pivot_table(index="domain", columns="skill_label", values="gap_score", aggfunc="max", fill_value=0)
    )
    matrix.to_csv(csv_dir / "advanced_gap_heatmap.csv", encoding="utf-8")
    if matrix.empty:
        return
    plt.figure(figsize=(16, 6))
    sns.heatmap(matrix, cmap="OrRd", linewidths=0.4, linecolor="white")
    plt.title("Cross-domain demand/supply gap heatmap")
    plt.xlabel("Skill")
    plt.ylabel("Domain")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_gap_heatmap.png", dpi=170)
    plt.close()


def _training_alignment(relevance: pd.DataFrame, csv_dir: Path, fig_dir: Path) -> None:
    alignment = relevance.copy()
    alignment["training_gap"] = alignment["demand_frequency"] - alignment["course_frequency"]
    alignment["training_misalignment_index"] = alignment["demand_frequency"].clip(lower=0) * alignment["training_gap"].clip(lower=0)
    alignment["alignment_label"] = "aligned"
    alignment.loc[alignment["training_gap"] > 0.25, "alignment_label"] = "under-served by courses"
    alignment.loc[alignment["training_gap"] < -0.25, "alignment_label"] = "over-served by courses"
    alignment.to_csv(csv_dir / "advanced_training_alignment.csv", index=False, encoding="utf-8")

    top = alignment.sort_values("training_gap", ascending=False).groupby("domain").head(8)
    plt.figure(figsize=(12, 7))
    sns.scatterplot(
        data=top,
        x="course_frequency",
        y="demand_frequency",
        hue="alignment_label",
        style="domain",
        s=120,
    )
    plt.plot([0, 1], [0, 1], color="#444", linestyle="--", linewidth=1)
    for row in top.head(20).itertuples():
        plt.text(row.course_frequency + 0.01, row.demand_frequency + 0.01, row.skill_label[:22], fontsize=8)
    plt.title("Training alignment: are courses covering demanded skills?")
    plt.xlabel("Course coverage")
    plt.ylabel("Job demand")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_training_alignment.png", dpi=170)
    plt.close()


def _skill_shock_index(relevance: pd.DataFrame, csv_dir: Path, fig_dir: Path, domain_count: int) -> None:
    shock = relevance.copy()
    shock["training_gap"] = (shock["demand_frequency"] - shock["course_frequency"]).clip(lower=0)
    shock["positive_trend"] = shock["trend_score"].clip(lower=0)
    presence = shock.groupby("skill_uri")["domain"].nunique().rename("cross_domain_presence").reset_index()
    shock = shock.merge(presence, on="skill_uri", how="left")
    domain_denominator = max(float(domain_count), 1.0)
    shock["cross_domain_presence_norm"] = shock["cross_domain_presence"].astype(float) / domain_denominator
    shock["skill_shock_index"] = (
        0.35 * _normalized(shock["gap_score"])
        + 0.30 * _normalized(shock["positive_trend"])
        + 0.25 * _normalized(shock["training_gap"])
        + 0.10 * shock["cross_domain_presence_norm"].clip(lower=0, upper=1)
    ).round(6)
    shock["shock_label"] = "low shock"
    shock.loc[shock["skill_shock_index"] >= 0.45, "shock_label"] = "watchlist"
    shock.loc[shock["skill_shock_index"] >= 0.65, "shock_label"] = "critical bottleneck"
    shock = shock.sort_values("skill_shock_index", ascending=False)
    shock.to_csv(csv_dir / "advanced_skill_shock_index.csv", index=False, encoding="utf-8")

    top = shock.head(20).copy()
    if top.empty:
        return
    top["shock_label_text"] = top["domain"] + " | " + top["skill_label"].astype(str).str.slice(0, 45)
    plt.figure(figsize=(13, 8))
    sns.barplot(data=top, y="shock_label_text", x="skill_shock_index", hue="shock_label")
    plt.title("Skill Shock Index: future bottleneck risk")
    plt.xlabel("Skill Shock Index")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_skill_shock_index.png", dpi=170)
    plt.close()


def _training_roi_priority(relevance: pd.DataFrame, csv_dir: Path, fig_dir: Path) -> None:
    roi = relevance.copy()
    roi["training_gap"] = (roi["demand_frequency"] - roi["course_frequency"]).clip(lower=0)
    roi["positive_trend"] = roi["trend_score"].clip(lower=0)
    roi["training_roi_priority"] = (
        0.40 * _normalized(roi["demand_frequency"])
        + 0.25 * _normalized(roi["gap_score"])
        + 0.20 * _normalized(roi["positive_trend"])
        + 0.15 * _normalized(roi["training_gap"])
    ).round(6)
    roi["roi_label"] = "low priority"
    roi.loc[roi["training_roi_priority"] >= 0.45, "roi_label"] = "medium priority"
    roi.loc[roi["training_roi_priority"] >= 0.65, "roi_label"] = "high priority course investment"
    roi = roi.sort_values("training_roi_priority", ascending=False)
    roi.to_csv(csv_dir / "advanced_training_roi_priority.csv", index=False, encoding="utf-8")

    top = roi.head(20).copy()
    if top.empty:
        return
    top["roi_label_text"] = top["domain"] + " | " + top["skill_label"].astype(str).str.slice(0, 45)
    plt.figure(figsize=(13, 8))
    sns.barplot(data=top, y="roi_label_text", x="training_roi_priority", hue="roi_label")
    plt.title("Training ROI Priority: where course investment matters most")
    plt.xlabel("Training ROI Priority")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_training_roi_priority.png", dpi=170)
    plt.close()


def _capability_family_summary(relevance: pd.DataFrame, csv_dir: Path, fig_dir: Path) -> None:
    family = (
        relevance.groupby(["domain", "capability_family"], as_index=False)
        .agg(
            mean_relevance=("relevance_index", "mean"),
            total_demand=("demand_count", "sum"),
            total_supply=("supply_count", "sum"),
            total_courses=("course_count", "sum"),
            mean_gap=("gap_score", "mean"),
        )
        .sort_values(["domain", "mean_gap", "total_demand"], ascending=[True, False, False])
    )
    family.to_csv(csv_dir / "advanced_capability_family_summary.csv", index=False, encoding="utf-8")

    top = family.groupby("domain").head(6)
    plt.figure(figsize=(13, 8))
    sns.barplot(data=top, y="capability_family", x="mean_gap", hue="domain")
    plt.title("Capability-family shortage summary using ESCO hierarchy")
    plt.xlabel("Mean gap score")
    plt.ylabel("ESCO capability family")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_capability_family_gaps.png", dpi=170)
    plt.close()


def _rising_unmet_skills(gaps: pd.DataFrame, trends: pd.DataFrame, csv_dir: Path, fig_dir: Path) -> None:
    merged = trends.merge(
        gaps[["domain", "skill_uri", "gap_score", "demand_count", "supply_count", "course_count"]],
        on=["domain", "skill_uri"],
        how="inner",
    )
    merged["rising_unmet_score"] = merged["trend_score"].clip(lower=0) * merged["gap_score"].clip(lower=0)
    merged = merged.sort_values("rising_unmet_score", ascending=False)
    merged.to_csv(csv_dir / "advanced_rising_unmet_skills.csv", index=False, encoding="utf-8")
    top = merged.groupby("domain").head(6)
    if top.empty:
        return
    plt.figure(figsize=(12, 7))
    sns.barplot(data=top, y="skill_label", x="rising_unmet_score", hue="domain")
    plt.title("Rising skills that are still under-supplied")
    plt.xlabel("Rising unmet score")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_rising_unmet_skills.png", dpi=170)
    plt.close()


def _future_risk_quadrant(gaps: pd.DataFrame, trends: pd.DataFrame, csv_dir: Path, fig_dir: Path) -> None:
    merged = trends.merge(
        gaps[["domain", "skill_uri", "gap_score", "demand_count", "supply_count", "course_count"]],
        on=["domain", "skill_uri"],
        how="inner",
    )
    merged["future_risk_score"] = merged["trend_score"].clip(lower=0) * merged["gap_score"].clip(lower=0)
    merged["risk_quadrant"] = "monitor"
    merged.loc[(merged["trend_score"] > 0.05) & (merged["gap_score"] > 0.25), "risk_quadrant"] = "rising shortage"
    merged.loc[(merged["trend_score"] <= 0.05) & (merged["gap_score"] > 0.25), "risk_quadrant"] = "current shortage"
    merged.loc[(merged["trend_score"] > 0.05) & (merged["gap_score"] <= 0.25), "risk_quadrant"] = "emerging signal"
    merged = merged.sort_values("future_risk_score", ascending=False)
    merged.to_csv(csv_dir / "advanced_future_risk_quadrant.csv", index=False, encoding="utf-8")

    plt.figure(figsize=(11, 7))
    sns.scatterplot(
        data=merged,
        x="gap_score",
        y="trend_score",
        hue="risk_quadrant",
        style="domain",
        s=110,
        alpha=0.8,
    )
    plt.axhline(0.05, color="#444", linestyle="--", linewidth=1)
    plt.axvline(0.25, color="#444", linestyle="--", linewidth=1)
    for row in merged.head(15).itertuples():
        plt.text(row.gap_score + 0.005, row.trend_score + 0.005, row.skill_label[:20], fontsize=8)
    plt.title("Future risk quadrant: rising demand with limited supply")
    plt.xlabel("Demand/supply gap score")
    plt.ylabel("Trend score")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_future_risk_quadrant.png", dpi=170)
    plt.close()


def _candidate_readiness(domains: list[str], csv_dir: Path) -> None:
    frames = []
    for domain in domains:
        candidates = _read_domain_csv(csv_dir, domain, "candidate_matches")
        if candidates.empty:
            continue
        candidates = candidates.copy()
        max_score = max(float(candidates["candidate_score"].max()), 1e-9)
        max_matches = max(float(candidates["matched_skill_count"].max()), 1.0)
        candidates["candidate_readiness_index"] = (
            0.75 * (candidates["candidate_score"].astype(float) / max_score)
            + 0.25 * (candidates["matched_skill_count"].astype(float) / max_matches)
        ).round(6)
        candidates["readiness_label"] = "developing"
        candidates.loc[candidates["candidate_readiness_index"] >= 0.75, "readiness_label"] = "strong match"
        candidates.loc[candidates["candidate_readiness_index"] < 0.35, "readiness_label"] = "weak match"
        frames.append(candidates.sort_values("candidate_readiness_index", ascending=False))
    if frames:
        pd.concat(frames, ignore_index=True).to_csv(csv_dir / "advanced_candidate_readiness.csv", index=False, encoding="utf-8")


def _candidate_readiness_chart(csv_dir: Path, fig_dir: Path) -> None:
    path = csv_dir / "advanced_candidate_readiness.csv"
    if not path.exists():
        return
    readiness = pd.read_csv(path)
    if readiness.empty:
        return
    top = readiness.sort_values("candidate_readiness_index", ascending=False).groupby("domain").head(5)
    top["candidate_label"] = top["domain"] + " #" + top["profile_id"].astype(str)
    plt.figure(figsize=(12, 7))
    sns.barplot(data=top, y="candidate_label", x="candidate_readiness_index", hue="readiness_label")
    plt.title("Top anonymized candidate readiness by domain")
    plt.xlabel("Candidate readiness index")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_candidate_readiness.png", dpi=170)
    plt.close()


def _split_skill_list(value: object) -> set[str]:
    if pd.isna(value):
        return set()
    return {item.strip() for item in str(value).split("|") if item.strip()}


def _career_bridges(domains: list[str], csv_dir: Path, fig_dir: Path) -> None:
    target_priorities: dict[str, pd.DataFrame] = {}
    for domain in domains:
        relevance = _read_domain_csv(csv_dir, domain, "skill_relevance")
        if relevance.empty:
            continue
        target_priorities[domain] = relevance.sort_values("relevance_index", ascending=False).head(15).copy()

    source_profiles: dict[tuple[str, str], dict[str, object]] = {}
    for domain in domains:
        candidates = _read_domain_csv(csv_dir, domain, "candidate_matches")
        if candidates.empty:
            continue
        for row in candidates.itertuples():
            key = (str(row.source), str(row.source_id))
            skills = _split_skill_list(getattr(row, "matched_skills", ""))
            existing = source_profiles.setdefault(
                key,
                {
                    "profile_id": str(row.profile_id),
                    "source": str(row.source),
                    "source_id": str(row.source_id),
                    "location": "" if pd.isna(getattr(row, "location", "")) else str(getattr(row, "location", "")),
                    "source_domains": set(),
                    "skills": set(),
                },
            )
            existing["source_domains"].add(domain)
            existing["skills"].update(skills)

    rows = []
    for profile in source_profiles.values():
        profile_skills = profile["skills"]
        if not profile_skills:
            continue
        source_domain = sorted(profile["source_domains"])[0]
        for target_domain, priorities in target_priorities.items():
            if target_domain == source_domain:
                continue
            total_weight = float(pd.to_numeric(priorities["relevance_index"], errors="coerce").fillna(0).sum())
            if total_weight <= 0:
                continue
            matched = priorities[priorities["skill_uri"].isin(profile_skills)].copy()
            missing = priorities[~priorities["skill_uri"].isin(profile_skills)].copy()
            score = float(pd.to_numeric(matched["relevance_index"], errors="coerce").fillna(0).sum()) / total_weight
            label = "large gap"
            if score >= 0.35:
                label = "reskillable"
            if score >= 0.65:
                label = "near-ready"
            rows.append({
                "profile_id": profile["profile_id"],
                "source_domain": source_domain,
                "target_domain": target_domain,
                "source": profile["source"],
                "source_id": profile["source_id"],
                "location": profile["location"],
                "career_bridge_score": round(score, 6),
                "bridge_label": label,
                "matched_skill_count": int(len(matched)),
                "matched_skill_labels": " | ".join(matched["skill_label"].astype(str).head(10).tolist()),
                "missing_reskilling_skill_labels": " | ".join(missing["skill_label"].astype(str).head(10).tolist()),
            })

    bridges = pd.DataFrame(rows)
    if bridges.empty:
        bridges = pd.DataFrame(columns=[
            "profile_id",
            "source_domain",
            "target_domain",
            "source",
            "source_id",
            "location",
            "career_bridge_score",
            "bridge_label",
            "matched_skill_count",
            "matched_skill_labels",
            "missing_reskilling_skill_labels",
        ])
        bridges.to_csv(csv_dir / "advanced_career_bridges.csv", index=False, encoding="utf-8")
        return
    bridges = bridges.sort_values(["career_bridge_score", "matched_skill_count"], ascending=[False, False])
    bridges.to_csv(csv_dir / "advanced_career_bridges.csv", index=False, encoding="utf-8")

    top = bridges.head(20).copy()
    top["bridge_text"] = (
        top["source_domain"].astype(str)
        + " -> "
        + top["target_domain"].astype(str)
        + " | profile "
        + top["profile_id"].astype(str)
    )
    plt.figure(figsize=(13, 8))
    sns.barplot(data=top, y="bridge_text", x="career_bridge_score", hue="bridge_label")
    plt.title("Career Bridge: reskilling pathways between domains")
    plt.xlabel("Career Bridge Score")
    plt.ylabel("")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_career_bridges.png", dpi=170)
    plt.close()


def _location_coverage_chart(csv_dir: Path, fig_dir: Path) -> None:
    path = csv_dir / "all_domains_locations.csv"
    if not path.exists():
        return
    locations = pd.read_csv(path)
    if locations.empty:
        return
    top = locations.sort_values(["domain", "job_count"], ascending=[True, False]).groupby("domain").head(8)
    plt.figure(figsize=(12, 7))
    sns.barplot(data=top, y="location_code", x="job_count", hue="domain")
    plt.title("Job location coverage by domain")
    plt.xlabel("Fetched job count")
    plt.ylabel("Location code")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_location_coverage.png", dpi=170)
    plt.close()


def _domain_story_summary(domains: list[str], csv_dir: Path) -> None:
    training = pd.read_csv(csv_dir / "advanced_training_alignment.csv") if (csv_dir / "advanced_training_alignment.csv").exists() else pd.DataFrame()
    readiness = pd.read_csv(csv_dir / "advanced_candidate_readiness.csv") if (csv_dir / "advanced_candidate_readiness.csv").exists() else pd.DataFrame()
    risk = pd.read_csv(csv_dir / "advanced_future_risk_quadrant.csv") if (csv_dir / "advanced_future_risk_quadrant.csv").exists() else pd.DataFrame()
    shock = pd.read_csv(csv_dir / "advanced_skill_shock_index.csv") if (csv_dir / "advanced_skill_shock_index.csv").exists() else pd.DataFrame()
    roi = pd.read_csv(csv_dir / "advanced_training_roi_priority.csv") if (csv_dir / "advanced_training_roi_priority.csv").exists() else pd.DataFrame()
    rows = []
    for domain in domains:
        gap = _read_domain_csv(csv_dir, domain, "skill_gap")
        trends = _read_domain_csv(csv_dir, domain, "skill_trends")
        top_gap = gap.iloc[0] if not gap.empty else None
        rising_trends = trends[
            (trends["trend_label"] == "rising")
            & (pd.to_numeric(trends["total_monthly_mentions"], errors="coerce").fillna(0) > 0)
        ] if not trends.empty else pd.DataFrame()
        top_trend = rising_trends.sort_values(["trend_score", "total_monthly_mentions"], ascending=[False, False]).iloc[0] if not rising_trends.empty else None
        domain_training = training[training["domain"] == domain].sort_values("training_misalignment_index", ascending=False) if not training.empty else pd.DataFrame()
        domain_readiness = readiness[readiness["domain"] == domain].sort_values("candidate_readiness_index", ascending=False) if not readiness.empty else pd.DataFrame()
        domain_risk = risk[risk["domain"] == domain].sort_values("future_risk_score", ascending=False) if not risk.empty else pd.DataFrame()
        domain_shock = shock[shock["domain"] == domain].sort_values("skill_shock_index", ascending=False) if not shock.empty else pd.DataFrame()
        domain_roi = roi[roi["domain"] == domain].sort_values("training_roi_priority", ascending=False) if not roi.empty else pd.DataFrame()
        rows.append({
            "domain": domain,
            "top_gap_skill": "" if top_gap is None else top_gap["skill_label"],
            "top_gap_score": 0 if top_gap is None else top_gap["gap_score"],
            "top_rising_skill": "" if top_trend is None else top_trend["skill_label"],
            "top_trend_score": 0 if top_trend is None else top_trend["trend_score"],
            "top_training_gap_skill": "" if domain_training.empty else domain_training.iloc[0]["skill_label"],
            "training_misalignment_index": 0 if domain_training.empty else domain_training.iloc[0]["training_misalignment_index"],
            "top_future_risk_skill": "" if domain_risk.empty else domain_risk.iloc[0]["skill_label"],
            "future_risk_score": 0 if domain_risk.empty else domain_risk.iloc[0]["future_risk_score"],
            "top_skill_shock_skill": "" if domain_shock.empty else domain_shock.iloc[0]["skill_label"],
            "skill_shock_index": 0 if domain_shock.empty else domain_shock.iloc[0]["skill_shock_index"],
            "top_training_roi_skill": "" if domain_roi.empty else domain_roi.iloc[0]["skill_label"],
            "training_roi_priority": 0 if domain_roi.empty else domain_roi.iloc[0]["training_roi_priority"],
            "best_candidate_profile_id": "" if domain_readiness.empty else domain_readiness.iloc[0]["profile_id"],
            "candidate_readiness_index": 0 if domain_readiness.empty else domain_readiness.iloc[0]["candidate_readiness_index"],
        })
    pd.DataFrame(rows).to_csv(csv_dir / "domain_story_summary.csv", index=False, encoding="utf-8")


def _domain_signal_scoreboard(csv_dir: Path, fig_dir: Path) -> None:
    story_path = csv_dir / "domain_story_summary.csv"
    if not story_path.exists():
        return
    story = pd.read_csv(story_path)
    if story.empty:
        return
    scoreboard = story[[
        "domain",
        "top_gap_score",
        "top_trend_score",
        "training_misalignment_index",
        "future_risk_score",
        "candidate_readiness_index",
    ]].copy()
    for column in scoreboard.columns:
        if column != "domain":
            max_value = max(float(scoreboard[column].max()), 1e-9)
            scoreboard[column] = (scoreboard[column].astype(float) / max_value).round(6)
    scoreboard.to_csv(csv_dir / "advanced_domain_signal_scoreboard.csv", index=False, encoding="utf-8")

    plot_df = scoreboard.melt(id_vars="domain", var_name="signal", value_name="normalized_score")
    plt.figure(figsize=(12, 7))
    sns.barplot(data=plot_df, x="normalized_score", y="domain", hue="signal")
    plt.title("Domain signal scoreboard")
    plt.xlabel("Normalized score")
    plt.ylabel("Domain")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_domain_signal_scoreboard.png", dpi=170)
    plt.close()


def _domain_market_attractiveness(domains: list[str], csv_dir: Path, fig_dir: Path) -> None:
    summary = pd.read_csv(csv_dir / "all_domains_summary.csv") if (csv_dir / "all_domains_summary.csv").exists() else pd.DataFrame()
    readiness = pd.read_csv(csv_dir / "advanced_candidate_readiness.csv") if (csv_dir / "advanced_candidate_readiness.csv").exists() else pd.DataFrame()
    roi = pd.read_csv(csv_dir / "advanced_training_roi_priority.csv") if (csv_dir / "advanced_training_roi_priority.csv").exists() else pd.DataFrame()
    rows = []
    for domain in domains:
        relevance = _read_domain_csv(csv_dir, domain, "skill_relevance")
        trends = _read_domain_csv(csv_dir, domain, "skill_trends")
        locations = _read_domain_csv(csv_dir, domain, "locations")
        if relevance.empty:
            continue
        top = relevance.head(15).copy()
        domain_summary = summary[summary["domain"] == domain] if not summary.empty else pd.DataFrame()
        jobs_fetched = float(domain_summary.iloc[0]["jobs_fetched"]) if not domain_summary.empty else float(relevance["demand_count"].sum())
        location_count = float(locations["location_code"].nunique()) if not locations.empty and "location_code" in locations else 0.0
        positive_trend = pd.to_numeric(trends["trend_score"], errors="coerce").fillna(0).clip(lower=0) if not trends.empty else pd.Series(dtype=float)
        trend_values = pd.to_numeric(trends["trend_score"], errors="coerce").fillna(0) if not trends.empty else pd.Series(dtype=float)
        readiness_domain = readiness[readiness["domain"] == domain] if not readiness.empty else pd.DataFrame()

        rows.append({
            "domain": domain,
            "_jobs_fetched": jobs_fetched,
            "_location_count": location_count,
            "_top_demand_mean": float(pd.to_numeric(top["demand_frequency"], errors="coerce").fillna(0).mean()),
            "_trend_volatility": float(trend_values.std()) if len(trend_values) > 1 else 0.0,
            "_positive_trend_mean": float(positive_trend.mean()) if not positive_trend.empty else 0.0,
            "_accessibility_raw": float((1 - pd.to_numeric(top["gap_score"], errors="coerce").fillna(0).clip(0, 1)).mean()),
            "_training_support_raw": float(pd.to_numeric(top["course_frequency"], errors="coerce").fillna(0).clip(0, 1).mean()),
            "_candidate_fit_raw": float(pd.to_numeric(readiness_domain["candidate_readiness_index"], errors="coerce").fillna(0).head(10).mean()) if not readiness_domain.empty else 0.0,
            "_avg_gap": float(pd.to_numeric(top["gap_score"], errors="coerce").fillna(0).mean()),
        })

    market = pd.DataFrame(rows)
    if market.empty:
        market.to_csv(csv_dir / "advanced_domain_market_attractiveness.csv", index=False, encoding="utf-8")
        return

    market["demand_strength"] = (0.55 * _normalized(market["_jobs_fetched"]) + 0.45 * _normalized(market["_top_demand_mean"])).round(6)
    market["stability_score"] = (
        0.50 * (1 - _normalized(market["_trend_volatility"]))
        + 0.25 * _normalized(market["_positive_trend_mean"])
        + 0.25 * _normalized(market["_location_count"])
    ).clip(lower=0, upper=1).round(6)
    market["accessibility_score"] = pd.to_numeric(market["_accessibility_raw"], errors="coerce").fillna(0).clip(0, 1).round(6)
    market["training_support_score"] = _normalized(market["_training_support_raw"]).round(6)
    market["candidate_market_fit"] = pd.to_numeric(market["_candidate_fit_raw"], errors="coerce").fillna(0).clip(0, 1).round(6)
    market["domain_opportunity_score"] = (
        0.30 * market["demand_strength"]
        + 0.20 * market["stability_score"]
        + 0.20 * market["accessibility_score"]
        + 0.15 * market["training_support_score"]
        + 0.15 * market["candidate_market_fit"]
    ).round(6)

    market["recommendation_label"] = "promising with reskilling needed"
    market.loc[(market["domain_opportunity_score"] >= 0.65) & (market["accessibility_score"] >= 0.55), "recommendation_label"] = "very attractive"
    market.loc[(market["domain_opportunity_score"] >= 0.65) & (market["accessibility_score"] < 0.55), "recommendation_label"] = "attractive but competitive"
    market.loc[(market["stability_score"] < 0.35) | (market["training_support_score"] < 0.20), "recommendation_label"] = "risky / training gap"

    top_roi = roi.sort_values("training_roi_priority", ascending=False).groupby("domain").head(1) if not roi.empty else pd.DataFrame()
    roi_lookup = {row.domain: row.skill_label for row in top_roi.itertuples()} if not top_roi.empty else {}
    market["top_reason"] = market.apply(
        lambda row: f"Demand {row.demand_strength:.2f}, stability {row.stability_score:.2f}, candidate fit {row.candidate_market_fit:.2f}.",
        axis=1,
    )
    market["main_risk"] = market.apply(
        lambda row: (
            f"Training support is weak; priority skill: {roi_lookup.get(row.domain, 'not available')}."
            if row.training_support_score < 0.35
            else f"Accessibility score {row.accessibility_score:.2f}; reskilling may still be needed."
        ),
        axis=1,
    )

    output_columns = [
        "domain",
        "demand_strength",
        "stability_score",
        "accessibility_score",
        "training_support_score",
        "candidate_market_fit",
        "domain_opportunity_score",
        "recommendation_label",
        "top_reason",
        "main_risk",
    ]
    market = market.sort_values("domain_opportunity_score", ascending=False)
    market[output_columns].to_csv(csv_dir / "advanced_domain_market_attractiveness.csv", index=False, encoding="utf-8")

    plt.figure(figsize=(12, 7))
    sns.barplot(data=market, y="domain", x="domain_opportunity_score", hue="recommendation_label")
    plt.title("Domain Market Attractiveness: API-only opportunity proxy")
    plt.xlabel("Domain Opportunity Score")
    plt.ylabel("Domain")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_domain_market_attractiveness.png", dpi=170)
    plt.close()

    radar_columns = ["demand_strength", "stability_score", "accessibility_score", "training_support_score", "candidate_market_fit"]
    radar = market.set_index("domain")[radar_columns]
    plt.figure(figsize=(11, 6))
    sns.heatmap(radar, cmap="YlGnBu", annot=True, fmt=".2f", linewidths=0.4, linecolor="white", vmin=0, vmax=1)
    plt.title("Domain choice radar: demand, stability, access, training, fit")
    plt.xlabel("Signal")
    plt.ylabel("Domain")
    plt.tight_layout()
    plt.savefig(fig_dir / "advanced_domain_choice_radar.png", dpi=170)
    plt.close()


def _methodology_table(csv_dir: Path) -> None:
    rows = [
        {"metric": "Demand frequency", "formula": "skill job count / max skill job count in domain", "interpretation": "Relative employer demand inside a domain."},
        {"metric": "Supply frequency", "formula": "skill profile count / max skill profile count in domain", "interpretation": "Relative workforce supply inside a domain."},
        {"metric": "Course frequency", "formula": "skill course count / max skill course count in domain", "interpretation": "Relative training coverage."},
        {"metric": "Gap score", "formula": "max(0, demand_frequency - supply_frequency)", "interpretation": "Skills demanded more than they are supplied."},
        {"metric": "Trend score", "formula": "0.6 * normalized monthly slope + 0.4 * recent-vs-early delta", "interpretation": "Positive values indicate rising demand."},
        {"metric": "Relevance index", "formula": "0.45 demand + 0.25 shortage + 0.20 trend + 0.10 course coverage", "interpretation": "Composite ranking used for domain skill priority."},
        {"metric": "Training Misalignment Index", "formula": "demand_frequency * max(0, demand_frequency - course_frequency)", "interpretation": "Demanded skills that courses do not cover enough."},
        {"metric": "Future Risk Score", "formula": "max(0, trend_score) * max(0, gap_score)", "interpretation": "Skills that are both rising and under-supplied."},
        {"metric": "Candidate Readiness Index", "formula": "0.75 normalized candidate score + 0.25 normalized matched skill count", "interpretation": "Explainable readiness of a profile for a domain."},
        {"metric": "Skill Shock Index", "formula": "0.35 gap + 0.30 positive trend + 0.25 training gap + 0.10 cross-domain presence", "interpretation": "Future bottleneck risk across demand, supply, trend, and training response."},
        {"metric": "Career Bridge Score", "formula": "matched target-domain priority skill weight / total target-domain priority skill weight", "interpretation": "How close a profile is to reskilling into another domain."},
        {"metric": "Training ROI Priority", "formula": "0.40 demand + 0.25 gap + 0.20 positive trend + 0.15 training gap", "interpretation": "Where new or improved courses would likely have the highest labour-market value."},
        {"metric": "Domain Opportunity Score", "formula": "0.30 demand strength + 0.20 stability + 0.20 accessibility + 0.15 training support + 0.15 candidate fit", "interpretation": "API-only market attractiveness proxy, not real salary or income data."},
        {"metric": "Domain Signal Scoreboard", "formula": "Per-domain max-normalized gap, trend, training, risk, and readiness signals", "interpretation": "Compact cross-domain comparison for the dashboard."},
    ]
    pd.DataFrame(rows).to_csv(csv_dir / "methodology_table.csv", index=False, encoding="utf-8")


def _insight_cards(domains: list[str], csv_dir: Path) -> None:
    story_path = csv_dir / "domain_story_summary.csv"
    if not story_path.exists():
        return
    story = pd.read_csv(story_path)
    rows = []
    for row in story.itertuples():
        rows.extend([
            {
                "domain": row.domain,
                "insight_type": "skill gap",
                "headline": f"{row.domain}: strongest shortage signal is '{row.top_gap_skill}'.",
                "evidence": f"Gap score {float(row.top_gap_score):.3f}. Source: {row.domain.lower().replace(' ', '_')}_skill_gap.csv.",
                "figure": f"{row.domain.lower().replace(' ', '_')}_skill_gap.png",
            },
            {
                "domain": row.domain,
                "insight_type": "future risk",
                "headline": f"{row.domain}: '{row.top_future_risk_skill}' is the top rising unmet skill.",
                "evidence": f"Future risk score {float(row.future_risk_score):.3f}. Source: advanced_future_risk_quadrant.csv.",
                "figure": "advanced_future_risk_quadrant.png",
            },
            {
                "domain": row.domain,
                "insight_type": "training alignment",
                "headline": f"{row.domain}: courses are least aligned for '{row.top_training_gap_skill}'.",
                "evidence": f"Training misalignment index {float(row.training_misalignment_index):.3f}. Source: advanced_training_alignment.csv.",
                "figure": "advanced_training_alignment.png",
            },
            {
                "domain": row.domain,
                "insight_type": "candidate fit",
                "headline": f"{row.domain}: best anonymized candidate profile is {row.best_candidate_profile_id}.",
                "evidence": f"Candidate readiness index {float(row.candidate_readiness_index):.3f}. Source: advanced_candidate_readiness.csv.",
                "figure": "",
            },
        ])
    pd.DataFrame(rows).to_csv(csv_dir / "insight_cards.csv", index=False, encoding="utf-8")
