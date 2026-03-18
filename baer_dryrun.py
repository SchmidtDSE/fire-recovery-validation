import re, requests, pandas as pd, time

API_URL = "https://burnseverity.cr.usgs.gov/baer/api/form/baer-downloads"

jobs = pd.read_csv("fire_processing_jobs.csv")
jobs = jobs.dropna(subset=["fire_name", "fire_event_name"])

def extract_year(event_name):
    m = re.search(r"_(\d{4})-", str(event_name))
    return int(m.group(1)) if m else None

jobs["year"] = jobs["fire_event_name"].apply(extract_year)
fires = jobs[["fire_name","year"]].dropna().drop_duplicates().reset_index(drop=True)
print(f"Unique fires: {len(fires)}")

years = sorted(fires["year"].unique())
catalogue = []
for year in years:
    r = requests.get(API_URL, params={"year": int(year)}, timeout=30)
    data = r.json()["data"]["items"]
    for region in data:
        if isinstance(region, dict):
            for fire in region.get("items", []):
                fire["_year"] = int(year)
                catalogue.append(fire)
    time.sleep(0.3)

print(f"BAER records fetched: {len(catalogue)}")

def normalize(n):
    return re.sub(r"\s+", " ", str(n).lower().strip())

def name_match(baer_name, target_name):
    b, t = normalize(baer_name), normalize(target_name)
    return t in b or b.startswith(t)

matched, missed = [], []
for _, row in fires.iterrows():
    cands = [
        f for f in catalogue
        if f["_year"] == int(row["year"]) and name_match(f.get("fire_name",""), row["fire_name"])
    ]
    if cands:
        has_sbs   = bool(cands[0].get("soil_burn_file_url"))
        has_prelim = bool(cands[0].get("preliminary_file_url"))
        matched.append((row["fire_name"], int(row["year"]), cands[0]["fire_name"], len(cands), has_sbs, has_prelim))
    else:
        missed.append((row["fire_name"], int(row["year"])))

print(f"\nMATCHED ({len(matched)}):")
for m in matched:
    sbs = "SBS+PRE" if m[4] and m[5] else ("SBS" if m[4] else ("PRE" if m[5] else "none"))
    multi = f"  [!{m[3]} matches]" if m[3] > 1 else ""
    print(f"  {m[0]} ({m[1]}) -> {m[2]} | {sbs}{multi}")

print(f"\nNOT FOUND ({len(missed)}):")
for m in missed:
    print(f"  {m[0]} ({m[1]})")
