# Fire Severity Validation — NPS Sentinel-2 Tool

This repository validates DSE's fire severity tool (https://dse-disturbance-toolbox.org/tools/disturbance-severity/) against reference data for NPS fires in California (2015–2024).

## Overview

The tool computes fire severity indices (dNBR and RBR) from Sentinel-2 imagery via a remote API. This repository validates those outputs against reference burn severity data for NPS park units: Joshua Tree (JTP), Mojave (MNP), Kings Canyon/Sequoia (KNP/SMP/CNP).

## Setup

This project uses a conda environment named `burnseverity` (Python 3.13). Environment definitions live in two files:

- **`environment.yml`** — human-readable list of top-level dependencies (edit this to add/remove a package)
- **`conda-lock.yml`** — fully pinned, checksummed lockfile generated from `environment.yml` (this is what actually gets installed; guarantees everyone gets identical package versions, not just "close enough")

### New user (first-time setup)

```bash
conda install -n base -c conda-forge conda-lock   # one-time, installs the conda-lock CLI
conda-lock install --micromamba -n burnseverity conda-lock.yml
conda activate burnseverity
python -m ipykernel install --user --name burnseverity --display-name "burnseverity"  # registers the Jupyter kernel
```

Then select the **burnseverity** kernel when opening any notebook.

### Returning user

If you already have the `burnseverity` env and just pulled changes, only re-run the install step if `conda-lock.yml` changed:

```bash
conda-lock install --micromamba -n burnseverity conda-lock.yml
```

### Updating the environment (adding/upgrading a package)

1. Add the package to `environment.yml`
2. Re-solve and re-lock: `conda-lock -f environment.yml -p osx-arm64 --micromamba`
3. Commit both `environment.yml` and `conda-lock.yml`
4. Re-run the install step above to apply the change locally

The structure we are going for in refactoring is

project/
├── src/
│   ├── __init__.py
│   ├── config.py        # your variables, paths, parameter sets
│   ├── preprocessing.py
│   ├── api.py           # request sending + monitoring
│   └── analysis.py      # COG access, geospatial, plotting
├── notebooks/
│   ├── 01_preprocess.ipynb
│   ├── 02_api_requests.ipynb
│   └── 03_analysis.ipynb
├── reports/             # your .qmd files live here
├── figures/             # saved outputs
├── data/
│   ├── raw/
│   └── processed/
└── environment.yml      # or pyproject.toml

to do for refactoring
- [x] environment.yml + conda-lock.yml for reproducible env (see Setup)
- [ ] get all parameters into config
- [ ] get all functions into scripts
- [ ] flat notebooks for executiong
- [ ] Quarto document for all analyses/ visualisations (can run both R and Python)
- [ ] API class
- [ ] DevContainer/ Docker
- [ ] `fire_event_name` should be wrapped into a function, make sure date_mode is never implicit
- [ ] Homogenize naming conventions for factorial variables

## Workflow

### 1. Preprocessing (`validation_preprocess.ipynb`)
- Loads the full CalFire perimeters shapefile and filters to NPS parks post-2015
- Exports filtered perimeters to `Validation_Fire_Perimeters_2015_2024.shp` (~41 unique fires)
- Submits fire events to the fire severity API for 8 post-fire time windows (5, 10, 15, 21, 30, 45, 60, 90 days)
- Logs job IDs to `fire_processing_jobs.csv`

**API endpoint:** `https://fire-recovery-backend-dev-113009620257.us-central1.run.app/fire-recovery/process/analyze_fire_severity`  
Each request sends a fire bounding box, pre-fire window (21 days prior), and post-fire window. The API returns a `job_id` used to retrieve results.

### 2. Validation check (`validation_check_status.ipynb`)
Checks job completion status and tracks which jobs are still pending.

### 3. Metrics (`validation_metrics.ipynb`)
Computes accuracy metrics (correlation, RMSE, bias) comparing tool outputs to reference burn severity. Outputs saved to:
- `validation_metrics.csv` — tabular results per fire/time window
- `validation_metrics_dnbr.gpkg` / `validation_metrics_rbr.gpkg` — spatial results

### 4. Plots (`validation_plots.ipynb`)
Generates validation figures.

### 5. Reference data (`validation.py`, `validation.R`)
Helper scripts for loading and aligning reference burn severity data.

## Reference Data from BAER (Burned Area Emergency Response)

Validation reference data comes from USGS burn severity products:

**BAER (Burned Area Emergency Response):** Soil burn severity (SBS) maps created 1–7 days after fire containment. Viewer: https://burnseverity.cr.usgs.gov/viewer/?product=BAER

BAER data was manually downloaded for all fires where they are available from the viewer. The resolution of these data is 30 m, while ours is 10, so we'll resample ours to theirs. 

### Name-matching notes

BAER fire names include a state+year suffix, e.g. `"Sentinel (CA 2024)"`. Our `fire_processing_jobs.csv` names are short uppercase tokens (`SENTINEL`). If ever re-attempting BAER matching:
- Filter by `field_state == "California"` (full state name, not abbreviation) before name comparison
- Match on word-level subset: all words in our name must appear in the BAER name
- Validate with ignition date within ~30 days (`ignition_date` field is `MM/DD/YYYY`)
These steps are implemented in `baer_match.py`.

## Fire List

41 unique fires across parks JTP, MNP, KNP, CNP, SMP. Years span 2015–2024. See `fire_processing_jobs.csv` for the full list with job IDs and processing status. Each fire has 8 time-window jobs (5–90 days post-fire).

Notable gap: `KNP Complex` (2021) and a few other large fires had API timeouts for some time windows.

## Key Files

| File | Description |
|---|---|
| `Validation_Fire_Perimeters_2015_2024.shp` | Filtered NPS fire perimeters |
| `California_Fire_Perimeters_(all).shp` | Source CalFire perimeter dataset |
| `fire_processing_jobs.csv` | Job tracking: fire, time window, job ID, status |
| `validation_metrics.csv` | Per-fire accuracy metrics |
| `validation_metrics_dnbr.gpkg` | Spatial dNBR metrics |
| `validation_metrics_rbr.gpkg` | Spatial RBR metrics |
| `Visualization_Metrics.html` | Interactive results visualization |
