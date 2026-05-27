from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .esco import EscoMapper


@dataclass(frozen=True)
class EntityBundle:
    jobs: list[dict[str, Any]]
    profiles: list[dict[str, Any]]
    courses: list[dict[str, Any]]


def skill_counter(items: list[dict[str, Any]]) -> Counter[str]:
    counter: Counter[str] = Counter()
    for item in items:
        counter.update(set(item.get("skills") or []))
    return counter


def normalized(value: float, max_value: float) -> float:
    if max_value <= 0:
        return 0.0
    return float(value) / float(max_value)


def monthly_skill_counts(jobs: list[dict[str, Any]]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for job in jobs:
        upload_date = job.get("upload_date")
        if not upload_date:
            continue
        month = pd.to_datetime(upload_date, errors="coerce")
        if pd.isna(month):
            continue
        month_key = month.to_period("M").to_timestamp()
        for skill in set(job.get("skills") or []):
            rows.append({"month": month_key, "skill_uri": skill})
    if not rows:
        return pd.DataFrame(columns=["month", "skill_uri", "count"])
    return pd.DataFrame(rows).groupby(["month", "skill_uri"], as_index=False).size().rename(columns={"size": "count"})


def trend_table(domain: str, jobs: list[dict[str, Any]], esco: EscoMapper, top_skills: set[str], recent_months: int = 3) -> pd.DataFrame:
    monthly = monthly_skill_counts(jobs)
    if monthly.empty:
        return pd.DataFrame(columns=["domain", "skill_uri", "skill_label", "trend_score", "trend_label"])

    all_months = sorted(monthly["month"].unique())
    rows = []
    for skill in top_skills:
        series = monthly[monthly["skill_uri"] == skill].set_index("month")["count"].reindex(all_months, fill_value=0)
        values = series.to_numpy(dtype=float)
        if len(values) <= 1 or values.max() == 0:
            slope = 0.0
            recent_delta = 0.0
        else:
            x = np.arange(len(values), dtype=float)
            slope = float(np.polyfit(x, values / values.max(), 1)[0])
            early = values[:recent_months].mean() if len(values) >= recent_months else values[:1].mean()
            recent = values[-recent_months:].mean() if len(values) >= recent_months else values[-1:].mean()
            recent_delta = float((recent - early) / max(values.max(), 1.0))
        score = round(0.6 * slope + 0.4 * recent_delta, 6)
        label = "rising" if score > 0.05 else "cooling" if score < -0.05 else "stable"
        rows.append({
            "domain": domain,
            "skill_uri": skill,
            "skill_label": esco.skill_label(skill),
            "capability_family": esco.capability_family(skill),
            "trend_score": score,
            "trend_label": label,
            "months_observed": len(all_months),
            "total_monthly_mentions": int(values.sum()),
        })
    return pd.DataFrame(rows).sort_values(["trend_score", "total_monthly_mentions"], ascending=[False, False])


def relevance_and_gap_tables(
    domain: str,
    bundle: EntityBundle,
    esco: EscoMapper,
    weights: dict[str, float],
    top_n: int,
    recent_months: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    demand = skill_counter(bundle.jobs)
    supply = skill_counter(bundle.profiles)
    courses = skill_counter(bundle.courses)
    skill_universe = set(demand) | set(supply) | set(courses)

    top_skills_ordered: list[str] = []
    for skill, _ in demand.most_common(top_n):
        if skill not in top_skills_ordered:
            top_skills_ordered.append(skill)
    for skill, _ in supply.most_common(max(10, top_n // 2)):
        if skill not in top_skills_ordered:
            top_skills_ordered.append(skill)
    top_skills = set(top_skills_ordered[: max(top_n, len(demand.most_common(top_n)))])
    trends = trend_table(domain, bundle.jobs, esco, top_skills, recent_months=recent_months)
    trend_lookup = {row.skill_uri: float(row.trend_score) for row in trends.itertuples()}

    max_demand = max(demand.values(), default=0)
    max_supply = max(supply.values(), default=0)
    max_courses = max(courses.values(), default=0)
    rows = []
    for skill in skill_universe:
        d = demand.get(skill, 0)
        s = supply.get(skill, 0)
        c = courses.get(skill, 0)
        demand_norm = normalized(d, max_demand)
        supply_norm = normalized(s, max_supply)
        course_norm = normalized(c, max_courses)
        shortage = max(0.0, demand_norm - supply_norm)
        trend_raw = trend_lookup.get(skill, 0.0)
        trend_norm = max(0.0, min(1.0, (trend_raw + 0.2) / 0.4))
        relevance = (
            weights["demand"] * demand_norm
            + weights["shortage"] * shortage
            + weights["trend"] * trend_norm
            + weights["course_coverage"] * course_norm
        )
        rows.append({
            "domain": domain,
            "skill_uri": skill,
            "skill_label": esco.skill_label(skill),
            "capability_family": esco.capability_family(skill),
            "demand_count": d,
            "supply_count": s,
            "course_count": c,
            "demand_frequency": round(demand_norm, 6),
            "supply_frequency": round(supply_norm, 6),
            "course_frequency": round(course_norm, 6),
            "gap_score": round(shortage, 6),
            "trend_score": round(trend_raw, 6),
            "relevance_index": round(relevance, 6),
        })

    relevance = pd.DataFrame(rows).sort_values("relevance_index", ascending=False)
    gap = relevance.sort_values(["gap_score", "demand_count"], ascending=[False, False]).copy()
    return relevance.head(top_n), gap.head(top_n), trends


def candidate_matches(
    domain: str,
    profiles: list[dict[str, Any]],
    relevance: pd.DataFrame,
    esco: EscoMapper,
    top_n: int,
) -> pd.DataFrame:
    target = relevance.head(25).copy()
    weights = dict(zip(target["skill_uri"], target["relevance_index"]))
    target_skills = set(weights)
    rows = []
    for profile in profiles:
        profile_skills = set(profile.get("skills") or [])
        if not profile_skills:
            continue
        matched = sorted(target_skills & profile_skills, key=lambda s: weights.get(s, 0), reverse=True)
        if not matched:
            continue
        missing = sorted(target_skills - profile_skills, key=lambda s: weights.get(s, 0), reverse=True)[:10]
        score = sum(weights.get(skill, 0.0) for skill in matched) / max(sum(weights.values()), 1e-9)
        rows.append({
            "domain": domain,
            "profile_id": profile.get("id"),
            "source": profile.get("source"),
            "source_id": profile.get("source_id"),
            "location": profile.get("location") or profile.get("user_location") or profile.get("country"),
            "candidate_score": round(float(score), 6),
            "matched_skill_count": len(matched),
            "matched_skills": " | ".join(matched[:15]),
            "matched_skill_labels": " | ".join(esco.skill_label(skill) for skill in matched[:15]),
            "missing_priority_skills": " | ".join(missing),
            "missing_priority_skill_labels": " | ".join(esco.skill_label(skill) for skill in missing),
        })
    columns = [
        "domain",
        "profile_id",
        "source",
        "source_id",
        "location",
        "candidate_score",
        "matched_skill_count",
        "matched_skills",
        "matched_skill_labels",
        "missing_priority_skills",
        "missing_priority_skill_labels",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)
    return pd.DataFrame(rows, columns=columns).sort_values(["candidate_score", "matched_skill_count"], ascending=[False, False]).head(top_n)


def duplicate_report(domain: str, entity: str, items: list[dict[str, Any]]) -> dict[str, Any]:
    seen: set[tuple[Any, Any]] = set()
    duplicates = 0
    for item in items:
        key = (item.get("source"), item.get("source_id"))
        if key in seen:
            duplicates += 1
        else:
            seen.add(key)
    return {"domain": domain, "entity": entity, "records": len(items), "duplicate_source_source_id": duplicates}


def location_summary(domain: str, jobs: list[dict[str, Any]]) -> pd.DataFrame:
    counter: Counter[str] = Counter()
    for job in jobs:
        code = job.get("location_code") or job.get("location") or "Unknown"
        counter[str(code)] += 1
    return pd.DataFrame([
        {"domain": domain, "location_code": location, "job_count": count}
        for location, count in counter.most_common(30)
    ])
