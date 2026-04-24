import json
import urllib.request
import urllib.parse

OUTPUT_FILE = "places.json"

CATALOG_URL = "https://opendata.paris.fr/api/v2/catalog/datasets"
SEARCH_QUERY = "musee"
ROWS_PER_PAGE = 50


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

        datasets = data.get("datasets")

        # Ha az API nem azt adja amit várunk, írjuk ki és álljunk meg
        if datasets is None:
            raise Exception("API response does not contain 'datasets'. Response keys: " + str(list(data.keys())))

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

        url = f"https://opendata.paris.fr/api/v2/catalog/datasets/{dataset_id}/records?" + urllib.parse.urlencode(params)

        data = fetch_json(url)

        records = data.get("records")
        if records is None:
            raise Exception("API response does not contain 'records'. Response keys: " + str(list(data.keys())))

        if not records:
            break

        all_records.extend(records)
        offset += limit

        print(f"Fetched {len(all_records)} records...")

        if len(records) < limit:
            break

    return all_records


def main():
    dataset_id, dataset_title = find_dataset()
    records = fetch_records(dataset_id)

    places = []

    for r in records:
        f = r.get("record", {}).get("fields", {})

        place = {
            "name": safe(f.get("nom_du_lieu") or f.get("name") or f.get("title")),
            "type": safe(f.get("type") or f.get("categorie") or f.get("type_de_lieu") or "Museum"),
            "address": safe(f.get("adresse") or f.get("address") or f.get("adresse_complete")),
            "postcode": safe(f.get("code_postal") or f.get("postcode")),
            "city": safe(f.get("ville") or "Paris"),
            "website": safe(f.get("site_web") or f.get("url") or f.get("link")),
            "description": safe(f.get("description") or f.get("presentation") or f.get("resume")),
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
