"""
Download BAER Soil Burn Severity data for fires in fire_processing_jobs.csv.

Matches fires by name and year against the BAER API at:
  https://burnseverity.cr.usgs.gov/baer/api/form/baer-downloads?year=YYYY

Downloads soil burn severity .zip files into baer_downloads/<fire_name>_<year>/
Logs all matches and misses to baer_download_log.csv.
"""

import re
import time
import requests
import pandas as pd
from pathlib import Path

API_URL = "https://burnseverity.cr.usgs.gov/baer/api/form/baer-downloads"
OUT_DIR = Path("baer_downloads")
OUT_DIR.mkdir(exist_ok=True)

# --- Load fire list -----------------------------------------------------------
jobs = pd.read_csv("fire_processing_jobs.csv")
jobs = jobs.dropna(subset=["fire_name", "fire_event_name"])

# Extract unique (fire_name, year) pairs from fire_event_name (e.g. YORK_2023-07-28_5)
def extract_year(event_name):
    m = re.search(r"_(\d{4})-", str(event_name))
    return int(m.group(1)) if m else None

jobs["year"] = jobs["fire_event_name"].apply(extract_year)
fires = (
    jobs[["fire_name", "year"]]
    .dropna()
    .drop_duplicates()
    .reset_index(drop=True)
)
print(f"Unique fires to match: {len(fires)}")

# --- Fetch BAER catalogue for each relevant year ------------------------------
years_needed = sorted(fires["year"].unique())
catalogue = []  # list of dicts with fire metadata + download URLs

for year in years_needed:
    print(f"Fetching BAER catalogue for {year}...")
    try:
        r = requests.get(API_URL, params={"year": year}, timeout=30)
        r.raise_for_status()
        data = r.json()["data"]["items"]
        for region in data:
            if not isinstance(region, dict):
                continue
            for fire in region.get("items", []):
                fire["_region"] = region["title"]
                fire["_year"] = year
                catalogue.append(fire)
        time.sleep(0.5)
    except Exception as e:
        print(f"  ERROR fetching {year}: {e}")

print(f"Total BAER records fetched: {len(catalogue)}")

# --- Match fires --------------------------------------------------------------
def normalize(name):
    """Lowercase, strip, collapse spaces for fuzzy matching."""
    return re.sub(r"\s+", " ", str(name).lower().strip())

def name_match(baer_name, target_name):
    """Check if target fire name appears in the BAER fire name."""
    b = normalize(baer_name)
    t = normalize(target_name)
    return t in b or b.startswith(t)

log = []
for _, row in fires.iterrows():
    fire_name = row["fire_name"]
    year = int(row["year"])

    candidates = [
        f for f in catalogue
        if f["_year"] == year and name_match(f.get("fire_name", ""), fire_name)
    ]

    if not candidates:
        log.append({
            "fire_name": fire_name, "year": year,
            "matched": False, "baer_name": None,
            "sbs_url": None, "downloaded": False, "notes": "No match found"
        })
        print(f"  NO MATCH: {fire_name} ({year})")
        continue

    if len(candidates) > 1:
        note = f"Multiple matches: {[c['fire_name'] for c in candidates]}"
        print(f"  MULTI-MATCH: {fire_name} ({year}) — {note}")
    else:
        note = "OK"

    # Use first match (most cases will be unambiguous)
    match = candidates[0]
    sbs_url = match.get("soil_burn_file_url")
    prelim_url = match.get("preliminary_file_url")

    if not sbs_url and not prelim_url:
        log.append({
            "fire_name": fire_name, "year": year,
            "matched": True, "baer_name": match["fire_name"],
            "sbs_url": None, "downloaded": False,
            "notes": "Matched but no download URLs available"
        })
        print(f"  MATCHED (no SBS url): {fire_name} -> {match['fire_name']}")
        continue

    # Prefer SBS (soil burn severity), fall back to preliminary
    download_url = sbs_url if sbs_url else prelim_url
    url_type = "sbs" if sbs_url else "preliminary"

    # Download
    safe_name = re.sub(r"[^\w]", "_", fire_name)
    out_path = OUT_DIR / f"{safe_name}_{year}_{url_type}.zip"

    if out_path.exists():
        print(f"  SKIP (exists): {out_path.name}")
        log.append({
            "fire_name": fire_name, "year": year,
            "matched": True, "baer_name": match["fire_name"],
            "sbs_url": download_url, "downloaded": True,
            "notes": f"Already downloaded ({url_type})"
        })
        continue

    try:
        print(f"  Downloading {url_type}: {fire_name} ({year}) -> {out_path.name}")
        r = requests.get(download_url, timeout=120, stream=True)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        log.append({
            "fire_name": fire_name, "year": year,
            "matched": True, "baer_name": match["fire_name"],
            "sbs_url": download_url, "downloaded": True,
            "notes": f"Downloaded ({url_type})"
        })
        time.sleep(1)
    except Exception as e:
        log.append({
            "fire_name": fire_name, "year": year,
            "matched": True, "baer_name": match["fire_name"],
            "sbs_url": download_url, "downloaded": False,
            "notes": f"Download error: {e}"
        })
        print(f"  ERROR downloading {fire_name}: {e}")

# --- Save log ----------------------------------------------------------------
log_df = pd.DataFrame(log)
log_df.to_csv("baer_download_log.csv", index=False)
print(f"\nDone. Log saved to baer_download_log.csv")
print(log_df.groupby(["matched", "downloaded"]).size().to_string())
