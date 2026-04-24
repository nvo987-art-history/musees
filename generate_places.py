import json
import urllib.request
import urllib.parse

OUTPUT_FILE = "places.json"

DOMAIN = "opendata.paris.fr"
SEARCH_QUERY = "lieux culturels"

CATALOG_URL = f"https://{DOMAIN}/api/explore/v2.1/catalog/datasets"
ROWS_PER_PAGE = 100


def safe(val):
    if val is None:
        return ""
    return str(val).strip()


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (NVO987 OpenData Bot)"}
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read().decode("utf-8"))


def find_dataset():
    print("Searching dataset catalog...")

    offset = 0

    while True:
        params = {
            "q": SEARCH_QUERY,
            "limit": ROWS_PER_PAGE,
            "offset": offset
        }

        url = CATALOG_URL + "?" + urllib.parse.urlencode(params)
        data = fetch_json(url)

        datasets = data.get("results", [])
        total_count = data.get("total_count", 0)

        if not datasets:
            break

        for ds in datasets:
            dataset_id = ds.get("dataset_id", "")
            title = ds.get("metas", {}).get("default", {}).get("title", "")

            if dataset_id and title:
                print("Dataset found:", title)
                print("Dataset ID:", dataset_id)
                return dataset_id, title

        offset += ROWS_PER_PAGE

        if offset >= total_count:
            break

    raise Exception("Dataset not found in catalog.")


def fetch_records(dataset_id):
    print("Downloading dataset records...")

    all_records = []
    offset = 0
    limit = 100

    while True:
        params = {
            "limit": limit,
            "offset": offset
        }

        url = f"https://{DOMAIN}/api/explore/v2.1/catalog/datasets/{dataset_id}/records?" + urllib.parse.urlencode(params)
        data = fetch_json(url)

        results = data.get("results", [])
        if not results:
            break

        all_records.extend(results)
        offset += limit

        print(f"Fetched {len(all_records)} records...")

        if len(results) < limit:
            break

    return all_records


def main():
    dataset_id, dataset_title = find_dataset()
    records = fetch_records(dataset_id)

    places = []

    for r in records:
        place = {
            "name": safe(r.get("nom_du_lieu") or r.get("name") or r.get("title") or r.get("nom")),
            "type": safe(r.get("type") or r.get("categorie") or r.get("type_de_lieu") or "Lieu culturel"),
            "address": safe(r.get("adresse") or r.get("address") or r.get("adresse_complete")),
            "postcode": safe(r.get("code_postal") or r.get("postcode")),
            "city": safe(r.get("ville") or "Paris"),
            "website": safe(r.get("site_web") or r.get("url") or r.get("link")),
            "description": safe(r.get("description") or r.get("presentation") or r.get("resume")),
        }

        if place["name"]:
            places.append(place)

    final = {
        "source": "Paris Open Data (Ville de Paris)",
        "dataset": dataset_title,
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
