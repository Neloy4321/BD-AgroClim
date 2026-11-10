#!/usr/bin/env python3
"""Build a per-station historical-site verification queue, WITHOUT certifying sites."""
from __future__ import annotations

import csv
import json
import math
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
ALIASES = {
    "Ambagan (Ctg)": "Chittagong Ambagan",
    "Barisal": "Barishal",
    "Bogra": "Bogura",
    "Comilla": "Cumilla",
    "Saidpur": "Syedpur",
}


def read_csv(path: Path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def haversine_km(lat_a: float, lon_a: float, lat_b: float, lon_b: float) -> float:
    x1, x2 = map(math.radians, [lat_a, lat_b])
    a = math.sin((x2 - x1) / 2) ** 2 + math.cos(x1) * math.cos(x2) * math.sin(
        math.radians(lon_b - lon_a) / 2) ** 2
    return 2 * 6371.0088 * math.asin(math.sqrt(a))


def generate(metadata: Path, current_bamis: Path, out_csv: Path, out_json: Path) -> dict:
    original = read_csv(metadata)
    bamis_rows = read_csv(current_bamis)
    match = {r["official_station"].casefold(): r for r in bamis_rows}
    output = []
    counts = Counter()
    for r in original:
        guessed = ALIASES.get(r["station_name"], r["station_name"])
        present = match.get(guessed.casefold())
        old_lat, old_lon = float(r["lat"]), float(r["lon"])
        distance = None
        if present:
            distance = haversine_km(old_lat, old_lon, float(present["official_lat"]),
                                    float(present["official_lon"]))
            if distance > 5:
                priority = "P0_current_difference_over_5km"
            elif distance > 1:
                priority = "P1_current_difference_over_1km"
            else:
                priority = "P2_historical_date_and_identity_needed"
        else:
            priority = "P0_no_unambiguous_current_site_name_match"
        counts[priority] += 1
        wmo_raw = r.get("wmo_id", "")
        wmo = str(int(float(wmo_raw))) if wmo_raw else ""
        output.append({
            "author_station": r["station_name"],
            "author_wmo_id_unverified": wmo,
            "author_lat_draft": r["lat"],
            "author_lon_draft": r["lon"],
            "bamis_current_station_name_assumed_match": present["official_station"] if present else "",
            "bamis_current_lat": present["official_lat"] if present else "",
            "bamis_current_lon": present["official_lon"] if present else "",
            "draft_to_current_distance_km": round(distance, 3) if distance is not None else "",
            "verification_priority": priority,
            "historical_2000_2023_wmo_match_verified": "NO",
            "historical_2000_2023_site_moves_verified": "NO",
            "bamis_current_snapshot_url": "https://www.bamis.gov.bd/en/bmd/observed/table/",
            "wmo_history_candidate": "https://oscar.wmo.int/surface/",
            "author_action_requested": "BMD archival station metadata/site history, station code and operating dates",
        })
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)
    summary = {
        "author_stations": len(original),
        "public_current_bamis_snapshot_stations": len(bamis_rows),
        "matched_current_names_alias_assumption_only": sum(bool(x["bamis_current_station_name_assumed_match"]) for x in output),
        "priority_counts": dict(counts),
        "status": "2026 station coordinates ONLY; historical station coordinates unverified",
    }
    out_json.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


if __name__ == "__main__":
    print(json.dumps(generate(
        HERE / "station_metadata_author_draft.csv",
        HERE / "bamis_station_coordinates_public_2026.csv",
        HERE / "station_historical_source_queue.csv",
        HERE / "station_queue_summary.json",
    ), indent=2))
