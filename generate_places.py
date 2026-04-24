import json
import urllib.request
import urllib.parse

DATASET = "lieux-culturels"
BASE_URL = f"https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/{DATASET}/records"
OUTPUT_FILE = "places.json"

LIMIT = 100
MAX_TOTAL = 10000  # biztonsági limit (ne töltsön végtelenül)

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
        headers={"User-Agent": "Mozilla/5.0 (NVO987.eu bot)"}
    )

    with urllib.request.urlopen(req) as response:
        raw = response.read()
        return json.loads(raw)

def main():
    print("Downloading dataset (paginated)...")

    offset = 0
    places = []

    while True:
        print(f"Fetching offset={offset} ...")
        data = fetch_page(offset)

        results = data.get("results", [])
        if not results:
            break

        for r in results:
            place = {
                "name": safe(r.get("nom_du_lieu") or r.get("name") or r.get("title")),
                "type": safe(r.get("type") or r.get("categorie") or r.get("categorie_du_lieu")),
                "address": safe(r.get("adresse") or r.get("address")),
                "postcode": safe(r.get("code_postal") or r.get("postcode")),
                "city": safe(r.get("ville") or "Paris"),
                "website": safe(r.get("site_web") or r.get("url") or r.get("link")),
                "description": safe(r.get("description") or r.get("presentation")),
                "latitude": r.get("geo_point_2d", {}).get("lat") if isinstance(r.get("geo_point_2d"), dict) else "",
                "longitude": r.get("geo_point_2d", {}).get("lon") if isinstance(r.get("geo_point_2d"), dict) else ""
            }

            if place["name"]:
                places.append(place)

        offset += LIMIT

        if offset >= MAX_TOTAL:
            print("Reached MAX_TOTAL limit, stopping.")
            break

    final = {
        "source": "Paris Open Data (Ville de Paris)",
        "dataset": DATASET,
        "license": "ODbL v1.0",
        "count": len(places),
        "places": places
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_FILE} with {len(places)} places.")

if __name__ == "__main__":
    main()
