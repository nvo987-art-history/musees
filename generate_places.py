import json
import urllib.request

OUTPUT_FILE = "places.json"

CATALOG_URL = "https://opendata.paris.fr/api/v2/catalog/datasets"


def safe(val):
    if val is None:
        return ""
    return str(val).strip()


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "NVO987.eu Places Generator"}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def find_dataset():
    print("Searching dataset catalog (paginated)...")

    offset = 0
    limit = 100

    while True:
        url = f"{CATALOG_URL}?limit={limit}&offset={offset}"
        data = fetch_json(url)

        datasets = data.get("datasets", [])
        if not datasets:
            break

        for d in datasets:
            dataset_id = d.get("dataset_id", "")
            metas = d.get("metas", {}) or {}
            title = safe(metas.get("title")).lower()

            # This is flexible: will match "Lieux culturels", "Lieux culturels - équipements", etc.
            if "lieux" in title and "culture" in title:
                print("Found dataset:", dataset_id)
                print("Title:", title)
                return dataset_id

        offset += limit

    return None


def main():
    dataset_id = find_dataset()
    if not dataset_id:
        raise Exception("Dataset not found in catalog (lieux culturels).")

    print("Downloading dataset records...")

    records_url = f"https://opendata.paris.fr/api/records/1.0/search/?dataset={dataset_id}&rows=10000"
    data = fetch_json(records_url)

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
        "dataset_id": dataset_id,
        "license": "ODbL v1.0",
        "count": len(places),
        "places": places
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_FILE} with {len(places)} places.")


if __name__ == "__main__":
    main()
