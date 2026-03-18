import re, requests, pandas as pd, time

API_URL = "https://burnseverity.cr.usgs.gov/baer/api/form/baer-downloads"

jobs = pd.read_csv("fire_processing_jobs.csv")

def extract_year(event_name):
    m = re.search(r"_(\d{4})-", str(event_name))
    return int(m.group(1)) if m else None

jobs["year"] = jobs["fire_event_name"].apply(extract_year)
fires = jobs[["fire_name","year","fire_event_name"]].drop_duplicates(subset=["fire_name","year"]).dropna()
fires = fires[fires["year"] > 2000]

print("Unique year range:", sorted(fires["year"].unique()))
years = sorted(fires["year"].unique())

catalogue = []
for year in years:
    r = requests.get(API_URL, params={"year": int(year)}, timeout=30)
    j = r.json()
    data = j["data"]["items"]
    for region in data:
        if isinstance(region, dict):
            for fire in region.get("items", []):
                fire["_year"] = int(year)
                fire["_region"] = region.get("title","")
                catalogue.append(fire)
    time.sleep(0.3)

print(f"Total BAER records across all years: {len(catalogue)}")

print("\n=== CA FIRES IN BAER BY YEAR ===")
for year in years:
    ca = [f for f in catalogue if f["_year"] == year and "CA" in str(f.get("field_state",""))]
    if ca:
        print(f"\n--- {year} ---")
        for f in ca:
            sbs = "SBS" if f.get("soil_burn_file_url") else "   "
            pre = "PRE" if f.get("preliminary_file_url") else "   "
            unit = f.get("administrative_unit","")
            print(f"  [{sbs}|{pre}] {f.get('fire_name','')} | {unit}")
    else:
        print(f"\n--- {year}: no CA fires ---")
