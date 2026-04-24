import json
import urllib.request
import urllib.parse

# ==========================================================
# NVO987.eu – Places generator
# Paris Open Data (Opendatasoft API v2.1)
# Generates: places.json
# License: ODbL v1.0 (dataset license remains with source)
# ==========================================================

DATASET_NAME = "lieux-culturels"
BASE_URL = "https://opendata.paris.fr/api/explore/v2.1/catalog/datasets"

# Limit max (Opendatasoft often allows up to 100 per request, so we paginate)
PAGE_LIMIT = 100
MAX_TOTAL = 10000

OUTPUT_FILE = "places.json"


def safe(val):
    if val is None:
        return ""
    return str(val).strip()


def fetch_page(offset=0):
    url = f"{BASE_URL}/{urllib.parse.quote(DATASET_NAME)}/records?limit={PAGE_LIMIT}&offset={offset}"

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "NVO987.eu Places Generator (Python urllib)"
        }
    )

    with urllib.request.urlopen(req) as response:
        raw = response.read()
        return json.loads(raw)


def main():
    print("Downloading dataset (paginated)...")

    all_results = []
    offset = 0

    while True:
        print(f"Fetching offset={offset} ...")
        data = fetch_page(offset)

        results = data.get("results", [])
        if not results:
            break

        all_results.extend(results)
        offset += PAGE_LIMIT

        if offset >= MAX_TOTAL:
            break

    places = []

    for f in all_results:
        # Opendatasoft v2.1 already gives fields directly in each "result"
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
        "dataset": DATASET_NAME,
        "license": "ODbL v1.0",
        "count": len(places),
        "places": places
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_FILE} with {len(places)} places.")


if __name__ == "__main__":
    main()
