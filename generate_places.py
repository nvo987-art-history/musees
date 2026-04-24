import json
import urllib.request

DATASET_URL = "https://opendata.paris.fr/api/records/1.0/search/?dataset=lieux-culturels&rows=10000"

OUTPUT_FILE = "places.json"

def safe(val):
    if val is None:
        return ""
    return str(val).strip()

def main():
    print("Downloading dataset...")
    with urllib.request.urlopen(DATASET_URL) as response:
        raw = response.read()
        data = json.loads(raw)

    records = data.get("records", [])

    places = []

    for r in records:
        f = r.get("fields", {})

        place = {
            "name": safe(f.get("nom_du_lieu") or f.get("name") or f.get("title")),
            "type": safe(f.get("type") or f.get("categorie") or "Lieu culturel"),
            "address": safe(f.get("adresse") or f.get("address")),
            "postcode": safe(f.get("code_postal") or f.get("postcode")),
            "city": safe(f.get("ville") or "Paris"),
            "website": safe(f.get("site_web") or f.get("url") or f.get("link")),
            "description": safe(f.get("description") or f.get("presentation")),
        }

        if place["name"]:
            places.append(place)

    final = {
        "source": "Paris Open Data (Ville de Paris)",
        "license": "ODbL v1.0",
        "count": len(places),
        "places": places
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_FILE} with {len(places)} places.")

if __name__ == "__main__":
    main()
