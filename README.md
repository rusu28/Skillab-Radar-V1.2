# SKILLAB Skill Radar

Reproducible analytics package for the SKILLAB Innovation Challenge 2026.

It answers three questions from the challenge:

- What is the demand/supply gap per skill?
- Which skills are rising or cooling over time?
- Which anonymized profiles are the best candidates for a domain?

All labour-market entities are fetched from the SKILLAB Tracker API. The ESCO/ISCO Excel files are used only as official metadata for labels and hierarchy.

## Quick Start

### Easiest Windows setup

Double-click `easier_run.bat` for the simplest setup flow. It explains what will be installed/configured, asks for confirmation, then prepares the PC.

For the full command menu, use `harder_run.bat`, then choose:

1. `Setup / auto-configure this PC`
2. `Run pipeline and regenerate outputs`
3. `Start Streamlit dashboard`
4. `Start Jupyter notebooks` if Streamlit is not preferred

Or from PowerShell:

```powershell
.\run.ps1 setup
.\run.ps1 pipeline
.\run.ps1 dashboard
.\run.ps1 notebooks
```

These launchers create a local `.venv`, install requirements, and call `auto_config.py`.
`easier_run.bat` is the main friendly launcher. `harder_run.bat` is the advanced launcher for setup, pipeline, dashboard, notebooks, tests, and full rebuild.

If Python is not installed, install Python 3 from python.org and enable **Add python.exe to PATH** during installation. After that, use `easier_run.bat` again.

### Manual Python setup

1. Configure the project on this PC:

```powershell
python auto_config.py --install-deps --smoke-test
```

The script searches for the ESCO Excel files in the project folder, `data/metadata`, `inputs`, Downloads, and Desktop. If they are somewhere else:

```powershell
python auto_config.py --skills "C:\path\mapping_of_ESCO_skills.xlsx" --occupations "C:\path\mapping_of_ESCO_occupations.xlsx" --install-deps --smoke-test
```

Manual `.env` equivalent:

```env
TRACKER_API=https://skillab-tracker.csd.auth.gr/api
TRACKER_USERNAME=event_public
TRACKER_PASSWORD=PublicOnly2026
ESCO_SKILLS_PATH=C:\Users\NITROPC\Downloads\mapping_of_ESCO_skills.xlsx
ESCO_OCCUPATIONS_PATH=C:\Users\NITROPC\Downloads\mapping_of_ESCO_occupations.xlsx
```

2. Generate cached API extracts, CSVs, and figures:

```powershell
python -m src.pipeline --config config.yaml
```

This single command reproduces the project:

- logs in to the SKILLAB Tracker API
- fetches jobs, profiles, and courses per configured domain
- caches raw API responses under `data/cache/`
- writes raw fetched entities under `data/raw/`
- resolves ESCO labels and capability families from the provided mapping file
- generates all CSV tables under `results/csv/`
- generates all PNG figures under `results/figures/`

For a faster reproducible rerun, keep `tracker.use_cache: true`. To force fresh API calls:

```powershell
python -m src.pipeline --config config.yaml --refresh-cache
```

3. Run tests:

```powershell
python -m unittest discover -s tests
```

4. Run the demo app:

```powershell
pip install -r requirements.txt
streamlit run app/streamlit_app.py
```

5. Optional notebook mirror:

```powershell
jupyter notebook notebooks
```

## Outputs

Generated files are written to:

- `data/cache/`: raw API responses and provenance
- `results/csv/`: analysis tables
- `results/figures/`: PNG figures for dashboard and notebooks
- `results/provenance/`: query metadata

Main outputs:

- `{domain}_skill_relevance.csv`: ranking of the most relevant skills in each domain
- `{domain}_skill_gap.csv`: demand/supply shortage ranking
- `{domain}_skill_trends.csv`: rising, stable, and cooling skills from job upload dates
- `{domain}_candidate_matches.csv`: explainable profile-to-domain candidate matching
- `advanced_cross_domain_skill_heatmap.csv`: cross-domain skill specialization matrix
- `advanced_gap_heatmap.csv`: cross-domain demand/supply shortage matrix
- `advanced_skill_gap_portfolio.csv`: demand/supply/course portfolio study
- `advanced_training_alignment.csv`: whether courses cover demanded skills
- `advanced_skill_shock_index.csv`: future skill bottleneck risk
- `advanced_career_bridges.csv`: reskilling pathways between domains
- `advanced_training_roi_priority.csv`: highest-value course investment priorities
- `advanced_domain_market_attractiveness.csv`: domain opportunity ranking from API-only signals
- `advanced_capability_family_summary.csv`: ESCO hierarchy-based shortage families
- `advanced_rising_unmet_skills.csv`: rising skills that are still under-supplied
- `advanced_future_risk_quadrant.csv`: quadrant study for rising skills with shortage risk
- `advanced_candidate_readiness.csv`: explainable candidate readiness index
- `advanced_domain_signal_scoreboard.csv`: normalized cross-domain comparison across major signals
- `domain_story_summary.csv`: one-row narrative summary per domain
- `insight_cards.csv`: presentation-ready evidence cards
- `methodology_table.csv`: formulas and interpretation for reviewers

Expected default run:

- 5 configured domains
- 3 entity types per domain: jobs, profiles, courses
- bounded extraction controlled by `tracker.max_pages_per_entity`
- CSVs and PNG figures regenerated by one pipeline command

## dashboard

Run the local dashboard:

```powershell
streamlit run app/streamlit_app.py
```

Portable launcher equivalent:

```powershell
.\run.ps1 dashboard
```

Open `http://localhost:8501` and start with the `Overview` tab. The recommended live demo path is:

1. Demand/Supply Gap
2. Hot & Cooling Skills
3. Advanced Studies: Training Alignment and Future Risk Quadrant
4. Candidate Fit
5. Advanced Studies: Domain Market Attractiveness

The Domain Market Attractiveness study does not use salary data. Salary is not exposed by the Tracker API, so the project builds an API-only opportunity proxy from demand, stability, skill accessibility, training support, and candidate fit.

## Notebook fallback

The `notebooks/` folder mirrors the Streamlit tabs for reviewers who prefer notebooks:

- `run_pipeline_optional.ipynb`: optional live refresh from the SKILLAB Tracker API through the existing pipeline
- `overview.ipynb`
- `demand_supply_gap.ipynb`
- `hot_cooling_skills.ipynb`
- `candidate_fit.ipynb`
- `locations.ipynb`
- `advanced_studies.ipynb`
- `methodology.ipynb`

Launch with:

```powershell
jupyter notebook notebooks
```

The notebooks run from generated CSV/PNG outputs by default. If outputs are missing or stale, run `run_pipeline_optional.ipynb` first.

## Presentation

The primary presentation artefacts are the Streamlit dashboard and the reproducible figures in `results/figures/`.
The project focuses on code, API-derived data, CSV outputs, and generated charts.

## Reproducibility

API responses are cached by endpoint, parameters, request body, and page. Re-running the pipeline with the same `config.yaml` reuses cached responses by default, so generated CSVs are deterministic unless `--refresh-cache` is used.

The default `config.yaml` limits extraction to two pages per entity and domain so the demo remains fast. Increase `tracker.max_pages_per_entity` for a larger final run.

