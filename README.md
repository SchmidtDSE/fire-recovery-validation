# Fire Severity Validation — NPS Sentinel-2 Tool

Validates a Sentinel-2-based fire severity tool against reference data for NPS fires in California (2015–2024).

## Overview

The tool computes fire severity indices (dNBR and RBR) from Sentinel-2 imagery via a remote API. This repository validates those outputs against reference burn severity data for NPS park units: Joshua Tree (JTP), Mojave (MNP), Kings Canyon/Sequoia (KNP/SMP/CNP).

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

## Reference Data (BAER / MTBS)

Validation reference data comes from USGS burn severity products:

- **BAER (Burned Area Emergency Response):** Soil burn severity (SBS) maps created 1–7 days after fire containment. Viewer: https://burnseverity.cr.usgs.gov/viewer/?product=BAER

- **MTBS (Monitoring Trends in Burn Severity):** Satellite-derived burn severity with ~2 year processing lag. Accessible via WFS: `https://edcintl.cr.usgs.gov/geoserver/wfs` (layer: `mtbs:burn_severity_fire_polygons`). Usable for fires up to ~2022.

### BAER API (undocumented)

The download page at https://burnseverity.cr.usgs.gov/baer/baer-imagery-support-data-download renders its tables in JavaScript, but the underlying data endpoint is:

```
GET https://burnseverity.cr.usgs.gov/baer/api/form/baer-downloads?year=YYYY
```

Returns JSON with structure `data.items` → list of region objects, each with `items` → list of fire records. Key fields per fire record:

| Field | Example |
|---|---|
| `fire_name` | `"Sentinel (CA 2024)"` |
| `fire_id` | `"CA3661611828020240714"` |
| `ignition_date` | `"07/14/2024"` |
| `field_state` | `"California"` (full name, not abbreviation) |
| `administrative_unit` | `"Joshua Tree National Park"` |
| `soil_burn_file_url` | `https://edcintl.cr.usgs.gov/.../..._sbs.zip` |
| `preliminary_file_url` | `https://edcintl.cr.usgs.gov/.../..._preliminary.zip` |

Filter for California fires with `field_state == "California"` (the field is the full state name).

The `download_baer.py` script automates fetching this API and downloading SBS zips to `baer_downloads/`.

### BAER coverage for our NPS fires

**Key finding (March 2026):** This BAER database is a USFS product — every `administrative_unit` in the catalogue is a National Forest. NPS-managed lands (Joshua Tree NP, Mojave NP, Kings Canyon NP, Channel Islands NP, Santa Monica Mtns NRA) do not appear at all. This is a coverage issue, not a name-matching issue.

Matching was attempted using all three criteria simultaneously (state = California, fuzzy name match, ignition date within 30 days) via `baer_match.py`. Across 182 CA BAER records for years 2016–2024, only 1 apparent match was returned — a false positive (our `BULL` → BAER `Bullfrog`, Inyo National Forest). None of our actual NPS fires have a BAER record.

**Bottom line: BAER (burnseverity.cr.usgs.gov) is the wrong source for NPS fires.** MTBS is the correct alternative for 2015–2022 fires. For 2023–2024, NPS may have internal burn severity assessments — check NPS Fire & Aviation or Data Store directly.

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
