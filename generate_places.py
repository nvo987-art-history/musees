import json
import urllib.request

# ==========================================================
# NVO987.eu – Places generator (Paris Open Data)
# Uses the stable Opendatasoft API v1.0 (records/1.0/search)
# Generates: places.json
# ==========================================================

DATASET_URL = "https://opendata.paris.fr/api/records/1.0/search/?dataset=lieux-culturels&rows=10000"

OUTPUT_FILE = "places.json"


def safe(val):
    if val is None:
        return ""
    return str(val).strip()


def main():
    print("Downloading dataset...")

    req = urllib.request.Request(
        DATASET_URL,
        headers={"User-Agent": "NVO987.eu Places Generator"}
    )

    with urllib.request.urlopen(req) as response:
        raw = response.read()
        data = json.loads(raw)

    records = data.get("records", [])
    places = []

    for r in records:
        f = r.get("fields", {})

        place = {
            "name": safe(f.get("nom_du_lieu") or f.get("name") or f.get("title") or f.get("nom")),
            "type": safe(f.get("type") or f.get("categorie") or f.get("type_du_lieu") or "Lieu culturel"),
            "address": safe(f.get("adresse") or f.get("address") or f.get("adresse_complete")),
            "postcode": safe(f.get("code_postal") or f.get("postcode") or f.get("cp")),
            "city": safe(f.get("ville") or f.get("commune") or "Paris"),
            "website": safe(f.get("site_web") or f.get("url") or f.get("link")),
            "description": safe(f.get("description") or f.get("presentation") or f.get("resume")),
        }

        if place["name"]:
            places.append(place)

    final = {
        "source": "Paris Open Data (Ville de Paris)",
        "dataset": "lieux-culturels",
        "license": "ODbL v1.0",
        "count": len(places),
        "places": places
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_FILE} with {len(places)} places.")


if __name__ == "__main__":
    main()
