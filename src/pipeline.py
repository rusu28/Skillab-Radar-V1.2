from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import pandas as pd

from .advanced_analytics import build_advanced_outputs
from .config import load_config
from .esco import EscoMapper
from .figures import save_domain_figures
from .metrics import EntityBundle, candidate_matches, duplicate_report, location_summary, relevance_and_gap_tables
from .skillab_client import SkillabClient
from .submission import build_submission_package


def domain_slug(domain: str) -> str:
    return domain.lower().replace(" ", "_")


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def remove_generic_rankings(df: pd.DataFrame, patterns: list[str]) -> pd.DataFrame:
    if df.empty or not patterns:
        return df
    labels = df["skill_label"].fillna("").str.lower()
    mask = pd.Series(False, index=df.index)
    for pattern in patterns:
        mask = mask | labels.str.contains(pattern.lower(), regex=False)
    return df[~mask].copy()


def remove_zero_mention_trends(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "total_monthly_mentions" not in df:
        return df
    mentions = pd.to_numeric(df["total_monthly_mentions"], errors="coerce").fillna(0)
    return df[mentions > 0].copy()


def top_rising_skill(trends: pd.DataFrame) -> str:
    if trends.empty:
        return ""
    rising = trends[
        (trends["trend_label"] == "rising")
        & (pd.to_numeric(trends["trend_score"], errors="coerce").fillna(0) > 0.05)
        & (pd.to_numeric(trends["total_monthly_mentions"], errors="coerce").fillna(0) >= 2)
    ].copy()
    if rising.empty:
        return ""
    return str(rising.sort_values(["trend_score", "total_monthly_mentions"], ascending=[False, False]).iloc[0]["skill_label"])


def _text_from_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_text_from_value(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_text_from_value(v) for v in value)
    return str(value)


def _keyword_hits(text: str, keywords: list[str]) -> int:
    lowered = text.lower()
    hits = 0
    for keyword in keywords:
        key = keyword.lower().strip()
        if not key:
            continue
        if " " in key:
            if key in lowered:
                hits += 1
        elif re.search(rf"(?<![a-z0-9+.#-]){re.escape(key)}(?![a-z0-9+.#-])", lowered):
            hits += 1
    return hits


def domain_match_score(item: dict[str, Any], keywords: list[str], esco: EscoMapper) -> float:
    text_fields = [
        item.get("title"),
        item.get("description"),
        item.get("type"),
        item.get("organization"),
        item.get("location"),
        item.get("sectors"),
        item.get("occupations"),
    ]
    text = " ".join(_text_from_value(value) for value in text_fields)
    skill_text = " ".join(
        f"{esco.skill_label(skill)} {esco.capability_family(skill)}"
        for skill in set(item.get("skills") or [])
    )
    text_hits = _keyword_hits(text, keywords)
    skill_hits = _keyword_hits(skill_text, keywords)
    score = min(1.0, (text_hits * 0.25) + (skill_hits * 0.15))
    return round(score, 6)


def filter_domain_items(
    domain: str,
    endpoint: str,
    items: list[dict[str, Any]],
    keywords: list[str],
    esco: EscoMapper,
    threshold: float,
    min_records: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    scored = []
    for item in items:
        enriched = dict(item)
        enriched["domain_match_score"] = domain_match_score(enriched, keywords, esco)
        scored.append(enriched)
    filtered = [item for item in scored if float(item["domain_match_score"]) >= threshold]
    fallback = len(filtered) < min_records
    selected = scored if fallback else filtered
    return selected, {
        "domain": domain,
        "endpoint": endpoint,
        "records_before_filter": len(items),
        "records_after_filter": len(selected),
        "domain_filter_threshold": threshold,
        "domain_filter_fallback": fallback,
        "mean_domain_match_score": round(sum(float(item["domain_match_score"]) for item in scored) / max(len(scored), 1), 6),
    }


def generic_leakage_count(df: pd.DataFrame, patterns: list[str]) -> int:
    if df.empty or "skill_label" not in df or not patterns:
        return 0
    labels = df["skill_label"].fillna("").str.lower()
    mask = pd.Series(False, index=df.index)
    for pattern in patterns:
        mask = mask | labels.str.contains(pattern.lower(), regex=False)
    return int(mask.sum())


def quality_row(
    domain: str,
    relevance: pd.DataFrame,
    gap: pd.DataFrame,
    trends: pd.DataFrame,
    candidates: pd.DataFrame,
    duplicate_rows: list[dict[str, Any]],
    filter_stats: list[dict[str, Any]],
    excluded: list[str],
) -> dict[str, Any]:
    rising = top_rising_skill(trends)
    top_rising_valid = bool(rising)
    domain_duplicates = sum(int(row["duplicate_source_source_id"]) for row in duplicate_rows if row["domain"] == domain)
    domain_filter_fallbacks = [
        row["endpoint"] for row in filter_stats
        if row["domain"] == domain and row.get("domain_filter_fallback")
    ]
    return {
        "domain": domain,
        "relevance_rows": len(relevance),
        "gap_rows": len(gap),
        "trend_rows": len(trends),
        "candidate_rows": len(candidates),
        "duplicate_source_source_id": domain_duplicates,
        "empty_skill_labels": int(relevance["skill_label"].fillna("").eq("").sum()) if not relevance.empty else 0,
        "zero_mention_trend_rows": int((pd.to_numeric(trends.get("total_monthly_mentions", pd.Series(dtype=float)), errors="coerce").fillna(0) <= 0).sum()) if not trends.empty else 0,
        "top_rising_skill": rising,
        "top_rising_valid": top_rising_valid,
        "generic_leakage_relevance": generic_leakage_count(relevance, excluded),
        "generic_leakage_gap": generic_leakage_count(gap, excluded),
        "domain_filter_fallbacks": " | ".join(domain_filter_fallbacks),
    }


def run_pipeline(config_path: str, refresh_cache: bool = False) -> None:
    config = load_config(config_path)
    paths = config["paths"]
    tracker = config["tracker"]
    metrics_config = config["metrics"]

    client = SkillabClient(
        api=tracker["api"],
        username=tracker["username"],
        password=tracker["password"],
        cache_dir=paths["cache_dir"],
        timeout=int(tracker["request_timeout_seconds"]),
        pause_seconds=float(tracker["pause_seconds"]),
        use_cache=bool(tracker["use_cache"]),
        refresh_cache=refresh_cache,
        retries=int(tracker.get("request_retries", 3)),
    )
    esco = EscoMapper(paths["esco_skills"], paths.get("esco_occupations"))

    csv_dir = Path(paths["results_csv_dir"])
    raw_dir = Path(paths["raw_dir"])
    provenance_dir = Path(paths["provenance_dir"])
    figure_dir = Path(paths["figures_dir"])
    duplicate_rows = []
    summary_rows = []
    quality_rows = []
    all_locations = []

    for domain, domain_config in config["domains"].items():
        print(f"[{domain}] extracting jobs/profiles/courses")
        slug = domain_slug(domain)
        keywords = list(domain_config["keywords"])
        body = {"keywords": keywords, "keywords_logic": "or"}
        bundle_items = {}
        provenance = {}
        domain_filter_stats = []
        for endpoint in ["jobs", "profiles", "courses"]:
            items, prov = client.fetch_paged(
                endpoint,
                body=body,
                page_size=int(tracker["page_size"]),
                max_pages=int(tracker["max_pages_per_entity"]),
            )
            provenance[endpoint] = prov
            write_json(raw_dir / f"{slug}_{endpoint}.json", items)
            duplicate_rows.append(duplicate_report(domain, endpoint, items))
            filtered_items, filter_stat = filter_domain_items(
                domain=domain,
                endpoint=endpoint,
                items=items,
                keywords=keywords,
                esco=esco,
                threshold=float(metrics_config.get("domain_filter_thresholds", {}).get(endpoint, 0.1)),
                min_records=int(metrics_config.get("domain_filter_min_records", 50)),
            )
            bundle_items[endpoint] = filtered_items
            domain_filter_stats.append(filter_stat)
            provenance[endpoint]["domain_filter"] = filter_stat

        bundle = EntityBundle(
            jobs=bundle_items["jobs"],
            profiles=bundle_items["profiles"],
            courses=bundle_items["courses"],
        )
        relevance, gap, trends = relevance_and_gap_tables(
            domain=domain,
            bundle=bundle,
            esco=esco,
            weights=metrics_config["relevance_weights"],
            top_n=int(metrics_config["top_n_skills"]) * 2,
            recent_months=int(metrics_config["trend_recent_months"]),
        )
        excluded = metrics_config.get("exclude_generic_skill_labels", [])
        top_n_skills = int(metrics_config["top_n_skills"])
        relevance = remove_generic_rankings(relevance, excluded).head(top_n_skills)
        gap = remove_generic_rankings(gap, excluded).head(top_n_skills)
        trends = remove_zero_mention_trends(remove_generic_rankings(trends, excluded)).head(top_n_skills)
        candidates = candidate_matches(domain, bundle.profiles, relevance, esco, top_n=int(metrics_config["top_n_candidates"]))
        locations = location_summary(domain, bundle.jobs)
        all_locations.append(locations)

        relevance.to_csv(csv_dir / f"{slug}_skill_relevance.csv", index=False, encoding="utf-8")
        gap.to_csv(csv_dir / f"{slug}_skill_gap.csv", index=False, encoding="utf-8")
        trends.to_csv(csv_dir / f"{slug}_skill_trends.csv", index=False, encoding="utf-8")
        candidates.to_csv(csv_dir / f"{slug}_candidate_matches.csv", index=False, encoding="utf-8")
        locations.to_csv(csv_dir / f"{slug}_locations.csv", index=False, encoding="utf-8")
        write_json(provenance_dir / f"{slug}_provenance.json", provenance)
        save_domain_figures(domain, relevance, gap, trends, figure_dir)
        quality_rows.append(quality_row(domain, relevance, gap, trends, candidates, duplicate_rows, domain_filter_stats, excluded))

        summary_rows.append({
            "domain": domain,
            "jobs_fetched": len(bundle.jobs),
            "profiles_fetched": len(bundle.profiles),
            "courses_fetched": len(bundle.courses),
            "top_gap_skill": gap.iloc[0]["skill_label"] if not gap.empty else "",
            "top_rising_skill": top_rising_skill(trends),
            "top_candidate_score": candidates.iloc[0]["candidate_score"] if not candidates.empty else 0,
        })

    pd.DataFrame(summary_rows).to_csv(csv_dir / "all_domains_summary.csv", index=False, encoding="utf-8")
    pd.DataFrame(duplicate_rows).to_csv(csv_dir / "data_integrity_duplicates.csv", index=False, encoding="utf-8")
    pd.DataFrame(quality_rows).to_csv(csv_dir / "csv_quality_report.csv", index=False, encoding="utf-8")
    if all_locations:
        pd.concat(all_locations, ignore_index=True).to_csv(csv_dir / "all_domains_locations.csv", index=False, encoding="utf-8")
    build_advanced_outputs(list(config["domains"].keys()), csv_dir, figure_dir)
    build_submission_package(config)
    print(f"Done. CSV outputs are in {csv_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SKILLAB Skill Radar outputs.")
    parser.add_argument("--config", default="config.yaml")
    parser.add_argument("--refresh-cache", action="store_true")
    args = parser.parse_args()
    run_pipeline(args.config, refresh_cache=args.refresh_cache)


if __name__ == "__main__":
    main()
