import json
import urllib.request
import urllib.parse
import time

OUTPUT_FILE = "places.json"
SPARQL_URL = "https://query.wikidata.org/sparql"

# Kulturális helyek
# A Louvre miatt az art museum Q207694 is külön szerepel.
CULTURAL_TYPES = [
    "wd:Q33506",      # museum
    "wd:Q207694",     # art museum
    "wd:Q1007870",    # art gallery
    "wd:Q24354",      # theatre
    "wd:Q41253",      # cinema
    "wd:Q7075",       # library
    "wd:Q174782",     # cultural center
    "wd:Q166118",     # opera house
    "wd:Q1060829"     # concert hall
]


def safe(value):
    if value is None:
        return ""
    return str(value).strip()


def fetch_json(req, retries=3):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read().decode(
                    "utf-8",
                    errors="replace"
                )
                return json.loads(raw)

        except Exception as e:
            print(
                f"ERROR: request failed "
                f"(attempt {attempt + 1}): {e}"
            )

            if attempt < retries - 1:
                time.sleep(10)

    raise RuntimeError(
        "Failed to fetch data from Wikidata."
    )


def run_sparql(query):
    post_data = urllib.parse.urlencode({
        "query": query,
        "format": "json"
    }).encode("utf-8")

    headers = {
        "User-Agent": "NVO987 Cultural Map Bot/1.0",
        "Accept": "application/sparql-results+json",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    req = urllib.request.Request(
        SPARQL_URL,
        data=post_data,
        headers=headers,
        method="POST"
    )

    return fetch_json(req)


def main():

    all_results = []

    for cultural_type in CULTURAL_TYPES:

        print("Downloading type:", cultural_type)

        query = f"""
        SELECT DISTINCT
            ?place
            ?placeLabel
            ?lat
            ?lon
            ?cityLabel
            ?website
            ?article
        WHERE {{

            ?place wdt:P31 {cultural_type} .
            ?place wdt:P17 wd:Q142 .

            OPTIONAL {{
                ?place wdt:P625 ?coord .

                BIND(
                    geof:latitude(?coord)
                    AS ?lat
                )

                BIND(
                    geof:longitude(?coord)
                    AS ?lon
                )
            }}

            OPTIONAL {{
                ?place wdt:P131 ?city .
            }}

            OPTIONAL {{
                ?place wdt:P856 ?website .
            }}

            OPTIONAL {{
                ?article schema:about ?place .
                ?article schema:isPartOf
                    <https://fr.wikipedia.org/> .
            }}

            SERVICE wikibase:label {{
                bd:serviceParam
                    wikibase:language "fr,en" .
            }}
        }}
        """

        try:
            data = run_sparql(query)

            results = (
                data
                .get("results", {})
                .get("bindings", [])
            )

            print("Results:", len(results))

            all_results.extend(results)

        except Exception as e:
            print(
                "ERROR downloading",
                cultural_type,
                ":",
                e
            )

        # Ne terheljük túl a Wikidatát
        time.sleep(5)

    print("Raw results:", len(all_results))

    # ID alapján deduplikálunk
    places_by_id = {}

    for r in all_results:

        place_url = safe(
            r.get("place", {}).get("value")
        )

        if not place_url:
            continue

        place_id = place_url.rstrip("/").split("/")[-1]

        lat = r.get("lat", {}).get("value")
        lon = r.get("lon", {}).get("value")

        # Koordináta nélkül nem kell
        if not lat or not lon:
            continue

        name = safe(
            r.get("placeLabel", {}).get("value")
        )

        if not name:
            continue

        # Wikipédia
        wikipedia_url = safe(
            r.get("article", {}).get("value")
        )

        # Hivatalos website
        website = safe(
            r.get("website", {}).get("value")
        )

        city = safe(
            r.get("cityLabel", {}).get("value")
        )

        if place_id not in places_by_id:

            places_by_id[place_id] = {
                "id": place_id,
                "name": name,
                "city": city,
                "lat": float(lat),
                "lon": float(lon),

                # Wikidata URL
                "wikidata": place_url,

                # Wikipédia URL
                "wikipedia": wikipedia_url,

                # Hivatalos website
                "website": website,

                "source": place_url
            }

        else:

            place = places_by_id[place_id]

            # Ha valamelyik lekérdezésből hiányzott,
            # a másikból még megkaphatja.
            if not place["wikipedia"] and wikipedia_url:
                place["wikipedia"] = wikipedia_url

            if not place["website"] and website:
                place["website"] = website

            if not place["city"] and city:
                place["city"] = city

    places = list(places_by_id.values())

    # Név szerint rendezés
    places.sort(
        key=lambda x: x["name"].casefold()
    )

    # --------------------------------------------------
    # Louvre ellenőrzés
    # --------------------------------------------------

    louvre = next(
        (
            p for p in places
            if p["id"] == "Q19675"
        ),
        None
    )

    if louvre:
        print()
        print("Louvre FOUND:")
        print(json.dumps(
            louvre,
            ensure_ascii=False,
            indent=2
        ))
        print()
    else:
        print()
        print("WARNING: Louvre Q19675 not found!")
        print()

    # --------------------------------------------------
    # JSON
    # --------------------------------------------------

    final = {
        "source": "Wikidata (CC0)",
        "license": "CC0 1.0",
        "country": "France",
        "count": len(places),
        "places": places
    }

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            final,
            f,
            ensure_ascii=False,
            indent=2
        )

    print(
        f"Generated {OUTPUT_FILE} "
        f"with {len(places)} places."
    )


if __name__ == "__main__":
    main()
