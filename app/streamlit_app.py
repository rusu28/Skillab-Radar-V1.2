from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st


CSV_DIR = Path("results/csv")
FIGURES_DIR = Path("results/figures")


def slug(domain: str) -> str:
    return domain.lower().replace(" ", "_")


@st.cache_data
def read_csv(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    return pd.read_csv(path)


st.set_page_config(page_title="SKILLAB Skill Radar", layout="wide")
st.title("SKILLAB Skill Radar")
st.caption("Demand, trends, and candidate fit from SKILLAB Tracker API data.")

summary = read_csv(CSV_DIR / "all_domains_summary.csv")
if summary.empty:
    st.warning("No generated CSVs found. Run: python -m src.pipeline --config config.yaml")
    st.stop()

insights = read_csv(CSV_DIR / "insight_cards.csv")
story = read_csv(CSV_DIR / "domain_story_summary.csv")
methodology = read_csv(CSV_DIR / "methodology_table.csv")
training_alignment = read_csv(CSV_DIR / "advanced_training_alignment.csv")
future_risk = read_csv(CSV_DIR / "advanced_future_risk_quadrant.csv")
candidate_readiness = read_csv(CSV_DIR / "advanced_candidate_readiness.csv")
skill_shock = read_csv(CSV_DIR / "advanced_skill_shock_index.csv")
career_bridges = read_csv(CSV_DIR / "advanced_career_bridges.csv")
training_roi = read_csv(CSV_DIR / "advanced_training_roi_priority.csv")
market_attractiveness = read_csv(CSV_DIR / "advanced_domain_market_attractiveness.csv")

domain = st.sidebar.selectbox("Domain", summary["domain"].tolist())
domain_slug = slug(domain)

relevance = read_csv(CSV_DIR / f"{domain_slug}_skill_relevance.csv")
gap = read_csv(CSV_DIR / f"{domain_slug}_skill_gap.csv")
trends = read_csv(CSV_DIR / f"{domain_slug}_skill_trends.csv")
candidates = read_csv(CSV_DIR / f"{domain_slug}_candidate_matches.csv")
locations = read_csv(CSV_DIR / f"{domain_slug}_locations.csv")

row = summary[summary["domain"] == domain].iloc[0]
metric_cols = st.columns(4)
metric_cols[0].metric("Jobs fetched", int(row["jobs_fetched"]))
metric_cols[1].metric("Profiles fetched", int(row["profiles_fetched"]))
metric_cols[2].metric("Courses fetched", int(row["courses_fetched"]))
metric_cols[3].metric("Top candidate score", round(float(row["top_candidate_score"]), 3))
st.caption(
    "Top candidate score = weighted overlap between an anonymized profile's skills and the selected domain's highest-priority skills. "
    "A higher score means the profile covers more of the skills that are demanded, rising, or scarce in that domain."
)
with st.expander("Metric quick guide", expanded=False):
    st.markdown(
        """
        - **Jobs fetched**: job adverts returned by the Tracker API for the selected domain; this is the demand sample.
        - **Profiles fetched**: anonymized profile records returned by the Tracker API; this is the supply sample.
        - **Courses fetched**: course records returned by the Tracker API; this is the training/upskilling sample.
        - **Gap score**: high when job demand for a skill is stronger than profile supply.
        - **Trend score**: positive means rising demand, negative means cooling demand, based on available job dates.
        - **Training misalignment**: high when jobs demand a skill but courses cover it weakly.
        - **Skill Shock Index**: high when a skill is rising, under-supplied, weakly covered by courses, and relevant across domains.
        - **Career Bridge Score**: how close an anonymized profile is to another domain's priority skills.
        - **Domain Opportunity Score**: API-only market attractiveness proxy; it is not salary data.
        """
    )

tab_overview, tab_gap, tab_trends, tab_candidates, tab_geo, tab_advanced, tab_method = st.tabs([
    "Overview",
    "Demand/Supply Gap",
    "Hot & Cooling Skills",
    "Candidate Fit",
    "Locations",
    "Advanced Studies",
    "Methodology",
])

with tab_overview:
    st.subheader("Overview: Generated Findings")
    if insights.empty:
        st.info("Run the pipeline again to generate insight cards.")
    else:
        for item in insights.head(5).itertuples():
            st.markdown(f"**{item.headline}**")
            st.caption(item.evidence)

    st.subheader("How to Read the Dashboard")
    st.markdown(
        """
        1. **Demand/Supply Gap:** skills employers ask for more than profiles supply.
        2. **Hot & Cooling Skills:** skills whose demand changes over time.
        3. **Candidate Fit:** anonymized profile matching based on weighted skill overlap.
        4. **Advanced Studies:** cross-domain charts, training alignment, future risk, and ESCO family gaps.
        """
    )

    if not story.empty:
        st.subheader("Domain Story Summary")
        st.dataframe(story, use_container_width=True)

    if not market_attractiveness.empty:
        st.subheader("Best Domains to Enter Based on API Signals")
        st.caption(
            "This is an API-only opportunity proxy, not salary data. "
            "It combines demand, stability, skill accessibility, training support, and candidate fit."
        )
        st.bar_chart(market_attractiveness.set_index("domain")[["domain_opportunity_score"]])
        st.dataframe(
            market_attractiveness[[
                "domain",
                "domain_opportunity_score",
                "recommendation_label",
                "top_reason",
                "main_risk",
            ]],
            use_container_width=True,
        )

    st.subheader("Three Signals the Jury Can Read Quickly")
    signal_cols = st.columns(3)
    with signal_cols[0]:
        if not future_risk.empty:
            top_risk = future_risk.sort_values("future_risk_score", ascending=False).head(8)
            st.markdown("**Future risk**")
            st.bar_chart(top_risk.set_index("skill_label")[["future_risk_score"]])
    with signal_cols[1]:
        if not training_alignment.empty:
            top_training = training_alignment.sort_values("training_misalignment_index", ascending=False).head(8)
            st.markdown("**Training misalignment**")
            st.bar_chart(top_training.set_index("skill_label")[["training_misalignment_index"]])
    with signal_cols[2]:
        if not candidate_readiness.empty:
            top_candidates = candidate_readiness.sort_values("candidate_readiness_index", ascending=False).head(8)
            st.markdown("**Candidate readiness**")
            st.bar_chart(top_candidates.set_index("domain")[["candidate_readiness_index"]])

    col_a, col_b = st.columns(2)
    with col_a:
        heatmap = FIGURES_DIR / "advanced_cross_domain_skill_heatmap.png"
        if heatmap.exists():
            st.image(str(heatmap), caption="Cross-domain skill relevance", use_container_width=True)
        gap_heatmap = FIGURES_DIR / "advanced_gap_heatmap.png"
        if gap_heatmap.exists():
            st.image(str(gap_heatmap), caption="Cross-domain demand/supply gaps", use_container_width=True)
    with col_b:
        portfolio = FIGURES_DIR / "advanced_skill_gap_portfolio.png"
        if portfolio.exists():
            st.image(str(portfolio), caption="Demand vs supply portfolio", use_container_width=True)
        scoreboard = FIGURES_DIR / "advanced_domain_signal_scoreboard.png"
        if scoreboard.exists():
            st.image(str(scoreboard), caption="Domain signal scoreboard", use_container_width=True)

with tab_gap:
    st.subheader("Top Skill Relevance")
    st.caption("Relevance combines demand, shortage, trend, and course coverage into a single priority score.")
    top_rel = relevance.head(15).set_index("skill_label")
    st.bar_chart(top_rel[["relevance_index", "demand_frequency", "supply_frequency"]])
    st.dataframe(relevance.head(50), use_container_width=True)

    st.subheader("Largest Demand/Supply Gaps")
    st.caption("These are skills where the API job sample asks for more than the API profile sample appears to supply.")
    top_gap = gap.head(15).set_index("skill_label")
    st.bar_chart(top_gap[["gap_score"]])

with tab_trends:
    st.subheader("Rising and Cooling Skills")
    st.caption("Trend uses monthly job upload dates where present. Positive values are rising skills; negative values are cooling skills.")
    trend_view = trends[trends["trend_label"].isin(["rising", "cooling"])].head(30)
    if trend_view.empty:
        st.info("No strong rising/cooling signal in the fetched sample.")
    else:
        st.bar_chart(trend_view.set_index("skill_label")[["trend_score"]])
    st.dataframe(trends, use_container_width=True)

with tab_candidates:
    st.subheader("Optimal Candidate Detection")
    st.markdown(
        """
        **What the score means:** each domain has a ranked set of priority skills. A candidate receives credit when their
        profile contains those skills; matches to more important skills count more. The dashboard also shows missing
        priority skills, so the score is explainable rather than a black-box hiring decision.
        """
    )
    st.dataframe(candidates, use_container_width=True)
    domain_ready = candidate_readiness[candidate_readiness["domain"] == domain] if not candidate_readiness.empty else pd.DataFrame()
    if not domain_ready.empty:
        st.subheader("Candidate Readiness Index")
        st.bar_chart(domain_ready.head(15).set_index("profile_id")[["candidate_readiness_index"]])
        st.dataframe(
            domain_ready[[
                "profile_id",
                "candidate_readiness_index",
                "readiness_label",
                "candidate_score",
                "matched_skill_count",
                "matched_skill_labels",
                "missing_priority_skill_labels",
            ]].head(25),
            use_container_width=True,
        )
    st.caption("Scores are explainable weighted overlaps with the domain's top demanded and rising skills.")
    domain_bridges = career_bridges[career_bridges["target_domain"] == domain] if not career_bridges.empty else pd.DataFrame()
    if not domain_bridges.empty:
        st.subheader("Career Bridge / Reskilling Pathways")
        st.caption(
            "These rows show profiles from other domains that are closest to this domain. "
            "Missing reskilling skills are the suggested upskilling path."
        )
        st.bar_chart(domain_bridges.head(12).set_index("profile_id")[["career_bridge_score"]])
        st.dataframe(
            domain_bridges[[
                "profile_id",
                "source_domain",
                "target_domain",
                "career_bridge_score",
                "bridge_label",
                "matched_skill_labels",
                "missing_reskilling_skill_labels",
            ]].head(25),
            use_container_width=True,
        )

with tab_geo:
    st.subheader("Job Location Coverage")
    st.caption("Locations are shown only where the Tracker API returned location/country fields for the fetched job records.")
    if locations.empty:
        st.info("No location data found.")
    else:
        st.bar_chart(locations.set_index("location_code")[["job_count"]])
        st.dataframe(locations, use_container_width=True)

with tab_advanced:
    st.subheader("Cross-Domain and Innovation Studies")
    advanced_files = [
        ("Cross-domain skill heatmap", "advanced_cross_domain_skill_heatmap.png", "advanced_cross_domain_skill_heatmap.csv"),
        ("Cross-domain gap heatmap", "advanced_gap_heatmap.png", "advanced_gap_heatmap.csv"),
        ("Demand vs supply portfolio", "advanced_skill_gap_portfolio.png", "advanced_skill_gap_portfolio.csv"),
        ("Training alignment", "advanced_training_alignment.png", "advanced_training_alignment.csv"),
        ("Skill Shock Index", "advanced_skill_shock_index.png", "advanced_skill_shock_index.csv"),
        ("Career Bridge / Reskilling Pathways", "advanced_career_bridges.png", "advanced_career_bridges.csv"),
        ("Training ROI Priority", "advanced_training_roi_priority.png", "advanced_training_roi_priority.csv"),
        ("Domain Market Attractiveness", "advanced_domain_market_attractiveness.png", "advanced_domain_market_attractiveness.csv"),
        ("Domain Choice Radar", "advanced_domain_choice_radar.png", "advanced_domain_market_attractiveness.csv"),
        ("ESCO capability-family shortages", "advanced_capability_family_gaps.png", "advanced_capability_family_summary.csv"),
        ("Rising unmet skills", "advanced_rising_unmet_skills.png", "advanced_rising_unmet_skills.csv"),
        ("Future risk quadrant", "advanced_future_risk_quadrant.png", "advanced_future_risk_quadrant.csv"),
        ("Candidate readiness", "advanced_candidate_readiness.png", "advanced_candidate_readiness.csv"),
        ("Location coverage", "advanced_location_coverage.png", "all_domains_locations.csv"),
        ("Domain signal scoreboard", "advanced_domain_signal_scoreboard.png", "advanced_domain_signal_scoreboard.csv"),
        ("Domain story summary", "", "domain_story_summary.csv"),
        ("Insight cards", "", "insight_cards.csv"),
        ("Methodology table", "", "methodology_table.csv"),
    ]
    selected = st.selectbox("Study", [item[0] for item in advanced_files])
    figure_name = next(item[1] for item in advanced_files if item[0] == selected)
    csv_name = next(item[2] for item in advanced_files if item[0] == selected)
    figure_path = FIGURES_DIR / figure_name
    if figure_name and figure_path.exists():
        st.image(str(figure_path), use_container_width=True)
    data = read_csv(CSV_DIR / csv_name)
    if selected == "Domain Market Attractiveness":
        st.caption(
            "This is an API-only income/opportunity proxy. Salary is not exposed by the Tracker API, "
            "so the score infers attractiveness from demand, stability, accessibility, training support, and candidate fit."
        )
    if not data.empty:
        st.dataframe(data.head(100), use_container_width=True)

    st.subheader("Quick Comparison Tables")
    comp_a, comp_b, comp_c = st.columns(3)
    with comp_a:
        if not skill_shock.empty:
            st.markdown("**Top skill shocks**")
            st.dataframe(
                skill_shock[["domain", "skill_label", "shock_label", "gap_score", "trend_score", "training_gap", "skill_shock_index"]]
                .sort_values("skill_shock_index", ascending=False)
                .head(15),
                use_container_width=True,
            )
    with comp_b:
        if not training_roi.empty:
            st.markdown("**Top training ROI priorities**")
            st.dataframe(
                training_roi[["domain", "skill_label", "training_roi_priority", "roi_label", "demand_frequency", "gap_score", "course_frequency"]]
                .sort_values("training_roi_priority", ascending=False)
                .head(15),
                use_container_width=True,
            )
    with comp_c:
        if not market_attractiveness.empty:
            st.markdown("**Domain opportunity ranking**")
            st.dataframe(
                market_attractiveness[["domain", "domain_opportunity_score", "recommendation_label", "main_risk"]]
                .sort_values("domain_opportunity_score", ascending=False)
                .head(15),
                use_container_width=True,
            )

with tab_method:
    st.markdown(
        """
        **Pitch framing:** Skill Radar turns SKILLAB Tracker into a decision dashboard for labour-market intelligence:
        what employers ask for, what workers offer, what is changing, and who is the best match.

        **Data source:** all job, profile, and course records come from the SKILLAB Tracker API.

        **Metadata source:** ESCO/ISCO mapping files are used for labels and hierarchy enrichment only.

        **Metrics:** demand frequency, supply frequency, course coverage, trend slope, demand/supply shortage, weighted candidate overlap, cross-domain heatmaps, training alignment, ESCO family shortages, and rising unmet skills.

        **Top candidate score:** the best raw profile-match score found in the selected domain. It is computed from the
        share of domain-priority skill weight covered by a profile. The separate Candidate Readiness Index normalizes that
        score within a domain and blends it with the number of matched priority skills.
        """
    )
    if not methodology.empty:
        st.dataframe(methodology, use_container_width=True)
