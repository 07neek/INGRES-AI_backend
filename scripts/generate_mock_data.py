"""
The structure (state/district/block, annual extractable resource, extraction,
stage-of-extraction %, category, water levels) mirrors the real fields used in
CGWB's Dynamic Ground Water Resource Assessment and the INGRES portal:

    Category is derived from "Stage of Ground Water Extraction (%)":
        < 70%        -> Safe
        70% - 90%    -> Semi-Critical
        90% - 100%   -> Critical
        > 100%       -> Over-Exploited
        (+ a separate Saline flag for coastal saline-affected blocks)


"""

import json
import random
from pathlib import Path

random.seed(42)

YEARS = [2019, 2020, 2021, 2022, 2023]

# (state, district, block, lat, lon, starting_stage_pct, drift_per_year)
# drift_per_year > 0  => extraction stage rising (worsening) over time
# drift_per_year < 0  => improving over time
BLOCKS = [
    ("Punjab", "Sangrur", "Sangrur",              30.2458, 75.8421, 172.0,  4.0),
    ("Punjab", "Bathinda", "Bathinda",             30.2110, 74.9455, 158.0,  3.0),
    ("Rajasthan", "Jaipur", "Jaipur",               26.9124, 75.7873,  96.0,  2.5),
    ("Rajasthan", "Jodhpur", "Jodhpur",             26.2389, 73.0243, 134.0,  3.5),
    ("Maharashtra", "Wardha", "Wardha",             20.7453, 78.6022,  78.0,  1.8),
    ("Maharashtra", "Nagpur", "Nagpur (Rural)",     21.1458, 79.0882,  52.0,  0.4),
    ("Maharashtra", "Pune", "Haveli",               18.5204, 73.8567,  74.0,  1.2),
    ("Karnataka", "Kolar", "Kolar",                 13.1367, 78.1298, 118.0,  2.2),
    ("Karnataka", "Bengaluru Rural", "Devanahalli", 13.2437, 77.7119,  93.0,  1.9),
    ("Tamil Nadu", "Chennai", "Sholavaram",         13.1281, 80.1786,  92.0,  1.6),
    ("Tamil Nadu", "Coimbatore", "Coimbatore North",11.0168, 76.9558,  76.0,  1.0),
    ("Telangana", "Hyderabad", "Rajendranagar",     17.3220, 78.4083,  71.0,  0.8),
    ("Telangana", "Warangal", "Warangal",           17.9689, 79.5941,  46.0,  0.2),
    ("Uttar Pradesh", "Meerut", "Meerut",           28.9845, 77.7064,  73.0,  1.1),
    ("Uttar Pradesh", "Lucknow", "Lucknow",         26.8467, 80.9462,  55.0,  0.5),
    ("Bihar", "Patna", "Patna Sadar",               25.5941, 85.1376,  48.0, -0.3),
    ("Bihar", "Nalanda", "Bihar Sharif",            25.1985, 85.5241,  44.0, -0.2),
    ("Gujarat", "Mehsana", "Mehsana",                23.5880, 72.3693, 142.0,  2.8),
    ("Gujarat", "Jamnagar", "Jamnagar (Coastal)",    22.4707, 70.0577,  68.0,  0.6),
    ("Andhra Pradesh", "Anantapur", "Anantapur",     14.6819, 77.6006,  97.0,  1.7),
    ("Andhra Pradesh", "Krishna", "Vijayawada Rural",16.5062, 80.6480,  58.0,  0.3),
]

SALINE_BLOCKS = {"Jamnagar (Coastal)"}


def categorize(stage_pct: float, block_name: str) -> str:
    if block_name in SALINE_BLOCKS:
        return "Saline"
    if stage_pct > 100:
        return "Over-Exploited"
    if stage_pct >= 90:
        return "Critical"
    if stage_pct >= 70:
        return "Semi-Critical"
    return "Safe"


def build_record(state, district, block, lat, lon, start_stage, drift):
    yearly = []
    stage = start_stage
    # base recharge tuned so extraction/recharge ratio matches stage_pct
    base_recharge_ham = round(random.uniform(15000, 45000), 1)
    base_rainfall = random.uniform(550, 1100)
    base_level = random.uniform(6.0, 14.0)  # pre-monsoon depth, mbgl

    for i, year in enumerate(YEARS):
        noise = random.uniform(-2.5, 2.5)
        stage_year = max(5.0, stage + drift * i + noise)
        extraction_ham = round(base_recharge_ham * (stage_year / 100), 1)
        rainfall = round(base_rainfall + random.uniform(-80, 80), 1)
        pre_level = round(base_level + (drift * i * 0.08) + random.uniform(-0.4, 0.4), 2)
        post_level = round(pre_level - random.uniform(1.5, 3.5), 2)

        yearly.append({
            "year": year,
            "annual_extractable_resource_ham": base_recharge_ham,
            "annual_ground_water_extraction_ham": extraction_ham,
            "stage_of_extraction_percent": round(stage_year, 1),
            "category": categorize(stage_year, block),
            "rainfall_mm": rainfall,
            "pre_monsoon_level_mbgl": pre_level,
            "post_monsoon_level_mbgl": post_level,
        })

    return {
        "state": state,
        "district": district,
        "block": block,
        "latitude": lat,
        "longitude": lon,
        "yearly": yearly,
    }


def main():
    records = [build_record(*b) for b in BLOCKS]

    payload = {
        "metadata": {
            "title": "INGRES-AI Reference Groundwater Dataset (Sample)",
            "modeled_on": "CGWB Dynamic Ground Water Resource Assessment categories, as surfaced via INGRES / India-WRIS",
            "coverage_years": YEARS,
            "disclaimer": (
                "Synthetic sample data for development and hackathon demo purposes. "
                "NOT official CGWB/INGRES figures. Set USE_LIVE_WATER_API=true with a "
                "valid WATER_DATA_API_KEY and WATER_DATA_RESOURCE_ID to pull live records "
                "from the National Water Data Portal (data.gov.in) or India-WRIS instead."
            ),
        },
        "records": records,
    }

    out_path = Path(__file__).resolve().parent.parent / "app" / "data" / "mock_groundwater.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(records)} blocks x {len(YEARS)} years to {out_path}")


if __name__ == "__main__":
    main()
