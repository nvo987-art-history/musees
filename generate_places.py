#!/usr/bin/env python3
# ==========================================================
# FILE: generate_places.py
# NVO987.eu – Carte Culturelle (Paris Open Data)
# Generates places.json for GitHub Pages (static)
#
# Uses Paris Open Data API v2.1 (stable endpoint)
# ==========================================================

import json
import urllib.request
import urllib.parse
import time

OUTPUT_FILE = "places.json"

# ✅ WORKING API v2.1 endpoint (no catalog lookup needed)
BASE_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/lieux-culturels/records"

LIMIT = 100  # max per request (safe value)


def safe(val):
    if val is None:
        return ""
    return str(val).strip()


def fetch_page(offset):
    params = {
        "limit": LIMIT,
        "offset": offset
    }
    url = BASE_URL + "?" + urllib.parse.urlencode(params)

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (NVO987.eu Open Data Generator)",
            "Accept": "application/json"
        }
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        raw = response.read()
        return json.loads(raw)


def normalize_type(raw_type):
    t = (raw_type or "").lower()

    if "musée" in t or "musee" in t:
        return "museum"
    if "galerie" in t:
        return "gallery"
    if "centre" in t or "culturel" in t:
        return "cultural_center"

    return "cultural_place"


def main():
    print("Downloading dataset (Paris Open Data v2.1)...")

    offset = 0
    all_places = []

    while True:
        print(f"Fetching offset={offset} ...")
        data = fetch_page(offset)

        results = data.get("results", [])
        total_count = data.get("total_count", None)

        if not results:
            break

        for f in results:
            name = safe(f.get("nom_du_lieu") or f.get("name") or f.get("title"))
            if not name:
                continue

            raw_type = safe(f.get("type_du_lieu") or f.get("type") or f.get("categorie"))

            place = {
                "name": name,
                "type": normalize_type(raw_type),
                "type_label": raw_type if raw_type else "Lieu culturel",
                "address": safe(f.get("adresse") or f.get("address")),
                "postcode": safe(f.get("code_postal") or f.get("postcode")),
                "city": safe(f.get("ville") or "Paris"),
                "website": safe(f.get("site_web") or f.get("url") or f.get("link")),
                "description": safe(f.get("description") or f.get("presentation")),
            }

            all_places.append(place)

        offset += LIMIT

        if total_count is not None and offset >= total_count:
            break

        time.sleep(0.2)  # small delay to avoid rate-limit issues

    final = {
        "project": "NVO987.eu – Carte Culturelle",
        "source": "Paris Open Data (Ville de Paris)",
        "dataset": "lieux-culturels",
        "license": "ODbL v1.0",
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
        "count": len(all_places),
        "places": all_places
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_FILE} with {len(all_places)} places.")


if __name__ == "__main__":
    main()
