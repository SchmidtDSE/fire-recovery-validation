import re, requests, pandas as pd, time
from datetime import datetime, timedelta

API_URL = "https://burnseverity.cr.usgs.gov/baer/api/form/baer-downloads"
DATE_TOLERANCE_DAYS = 30  # how close ignition dates need to be

jobs = pd.read_csv("fire_processing_jobs.csv")

def extract_year(s):
    m = re.search(r"_(\d{4})-", str(s))
    return int(m.group(1)) if m else None

def extract_date(s):
    m = re.search(r"_(\d{4}-\d{2}-\d{2})_", str(s))
    return datetime.strptime(m.group(1), "%Y-%m-%d") if m else None

jobs["year"] = jobs["fire_event_name"].apply(extract_year)
jobs["ignition_date"] = jobs["fire_event_name"].apply(extract_date)
fires = jobs[["fire_name","year","ignition_date"]].drop_duplicates(subset=["fire_name","year"]).dropna()
fires = fires[fires["year"] > 2000].reset_index(drop=True)

# Fetch BAER catalogue for all years
years = sorted(fires["year"].unique())
catalogue = []
for year in years:
    r = requests.get(API_URL, params={"year": int(year)}, timeout=30)
    for region in r.json()["data"]["items"]:
        if isinstance(region, dict):
            for fire in region.get("items", []):
                fire["_year"] = int(year)
                catalogue.append(fire)
    time.sleep(0.3)

ca_cat = [f for f in catalogue if f.get("field_state") == "California"]
print(f"CA BAER records across all years: {len(ca_cat)}")

def normalize(n):
    return re.sub(r"[^a-z0-9 ]", "", str(n).lower()).strip()

def words(n):
    return set(normalize(n).split())

def name_match(baer_name, target_name):
    b_words = words(baer_name)
    t_words = words(target_name)
    # all words in target must appear in baer name (handles multi-word like "ELK TRAIL")
    return t_words.issubset(b_words) or normalize(target_name) in normalize(baer_name)

def parse_baer_date(d):
    try:
        return datetime.strptime(d, "%m/%d/%Y")
    except Exception:
        return None

matched, missed = [], []
for _, row in fires.iterrows():
    target_name = row["fire_name"]
    target_year = int(row["year"])
    target_date = row["ignition_date"]

    # Step 1: filter CA + year
    pool = [f for f in ca_cat if f["_year"] == target_year]

    # Step 2: name match
    name_cands = [f for f in pool if name_match(f.get("fire_name",""), target_name)]

    # Step 3: date proximity (if we have candidates and a date)
    if name_cands and target_date:
        date_cands = []
        for f in name_cands:
            bd = parse_baer_date(f.get("ignition_date",""))
            if bd and abs((bd - target_date).days) <= DATE_TOLERANCE_DAYS:
                date_cands.append((abs((bd - target_date).days), f))
        if date_cands:
            date_cands.sort(key=lambda x: x[0])
            best_days, best = date_cands[0]
            has_sbs = bool(best.get("soil_burn_file_url"))
            has_pre = bool(best.get("preliminary_file_url"))
            matched.append({
                "our_name": target_name,
                "year": target_year,
                "our_date": target_date.date(),
                "baer_name": best["fire_name"],
                "baer_date": best.get("ignition_date"),
                "date_diff_days": best_days,
                "name_candidates": len(name_cands),
                "sbs": has_sbs,
                "preliminary": has_pre,
                "sbs_url": best.get("soil_burn_file_url",""),
            })
            continue
        elif name_cands:
            # name matched but date is off — report separately
            bd = parse_baer_date(name_cands[0].get("ignition_date",""))
            diff = abs((bd - target_date).days) if bd and target_date else "?"
            missed.append({"fire": target_name, "year": target_year, "reason": f"name match but date diff={diff}d > {DATE_TOLERANCE_DAYS}d", "baer_name": name_cands[0]["fire_name"], "baer_date": name_cands[0].get("ignition_date")})
            continue

    missed.append({"fire": target_name, "year": target_year, "reason": "no name match in CA", "baer_name": "", "baer_date": ""})

print(f"\nMATCHED ({len(matched)}):")
for m in matched:
    sbs = "SBS" if m["sbs"] else ("PRE" if m["preliminary"] else "none")
    print(f"  {m['our_name']} ({m['year']}) -> {m['baer_name']} | our={m['our_date']} baer={m['baer_date']} diff={m['date_diff_days']}d | {sbs}")

print(f"\nNOT FOUND ({len(missed)}):")
for m in missed:
    print(f"  {m['fire']} ({m['year']}): {m['reason']}" + (f" -> {m['baer_name']} baer_date={m['baer_date']}" if m['baer_name'] else ""))

# Show all CA BAER records for reference
print(f"\n=== ALL CA FIRES IN BAER (for manual cross-ref) ===")
for year in years:
    pool = [f for f in ca_cat if f["_year"] == year]
    if pool:
        print(f"\n{int(year)}:")
        for f in pool:
            sbs = "SBS" if f.get("soil_burn_file_url") else "   "
            print(f"  [{sbs}] {f['fire_name']} | {f.get('ignition_date','')} | {f.get('administrative_unit','')}")
