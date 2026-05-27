# Skill Radar notebooks

These notebooks mirror the Streamlit dashboard for reviewers who prefer notebooks or cannot run Streamlit.

## Recommended order

- `run_pipeline_optional.ipynb` - optional live refresh from the SKILLAB Tracker API through the existing pipeline.
- `overview.ipynb` - mirrors the Streamlit Overview tab.
- `demand_supply_gap.ipynb` - mirrors Demand/Supply Gap.
- `hot_cooling_skills.ipynb` - mirrors Hot & Cooling Skills.
- `candidate_fit.ipynb` - mirrors Candidate Fit and Career Bridge.
- `locations.ipynb` - mirrors Locations.
- `advanced_studies.ipynb` - mirrors Advanced Studies.
- `methodology.ipynb` - mirrors Methodology.

## Fast mode

Run the notebooks directly after generated outputs exist:

```powershell
python -m src.pipeline --config config.yaml
jupyter notebook notebooks
```

## Live API mode

Open `run_pipeline_optional.ipynb` and run it first. It calls:

```powershell
python -m src.pipeline --config config.yaml
```

That refreshes API-derived CSVs and figures using the same cache/config as the main project.

All labour-market data still comes from the SKILLAB Tracker API. ESCO/ISCO files are metadata only.
