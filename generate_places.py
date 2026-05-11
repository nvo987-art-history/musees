import json
import urllib.request
import urllib.parse
import time

OUTPUT_FILE = "places.json"
SPARQL_URL = "https://query.wikidata.org/sparql"

# Wikidata kulturális hely típusok (P31 = instance of)
# Museum, art gallery, theatre, cinema, library, cultural center, opera house, concert hall
CULTURAL_TYPES = [
    "wd:Q33506",     # museum
    "wd:Q1007870",   # art gallery
    "wd:Q24354",     # theatre
    "wd:Q41253",     # cinema
    "wd:Q7075",      # library
    "wd:Q174782",    # cultural center
    "wd:Q166118",    # opera house
    "wd:Q1060829"    # concert hall
]


def safe(val):
    if val is None:
        return ""
    return str(val).strip()


def fetch_json(req, retries=5):
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                raw = response.read().decode("utf-8", errors="replace")

                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    print("ERROR: Wikidata response is not valid JSON (attempt", attempt + 1, ")")
                    print(raw[:500])

        except Exception as e:
            print("ERROR: request failed (attempt", attempt + 1, "):", str(e))

        time.sleep(5 * (attempt + 1))

    raise RuntimeError("Failed to fetch valid JSON from Wikidata after retries.")


def run_sparql(query):
    post_data = urllib.parse.urlencode({
        "query": query,
        "format": "json"
    }).encode("utf-8")

    headers = {
        "User-Agent": "Mozilla/5.0 (NVO987 Cultural Map Bot)",
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
        SELECT ?place ?placeLabel ?typeLabel ?lat ?lon ?cityLabel ?website ?description WHERE {{

          ?place wdt:P31 {cultural_type} .
          ?place wdt:P17 wd:Q142 .   # France

          OPTIONAL {{ ?place wdt:P625 ?coord . }}
          BIND(geof:latitude(?coord) AS ?lat)
          BIND(geof:longitude(?coord) AS ?lon)

          OPTIONAL {{ ?place wdt:P131 ?city . }}

          OPTIONAL {{ ?place wdt:P856 ?website . }}
          OPTIONAL {{ ?place schema:description ?description FILTER(LANG(?description)="fr") }}

          SERVICE wikibase:label {{
            bd:serviceParam wikibase:language "fr,en".
          }}
        }}
        """

        data = run_sparql(query)

        results = data.get("results", {}).get("bindings", [])
        print("Results:", len(results))

        all_results.extend(results)

        time.sleep(15)

    print("Raw results:", len(all_results))

    places = []

    for r in all_results:
        lat = r.get("lat", {}).get("value")
        lon = r.get("lon", {}).get("value")

        # csak akkor vesszük be, ha van koordináta
        if not lat or not lon:
            continue

        place_url = r.get("place", {}).get("value", "")
        place_id = place_url.split("/")[-1] if place_url else ""

        place = {
            "id": place_id,
            "name": safe(r.get("placeLabel", {}).get("value")),
            "type": safe(r.get("typeLabel", {}).get("value")),
            "city": safe(r.get("cityLabel", {}).get("value")),
            "lat": float(lat),
            "lon": float(lon),
            "website": safe(r.get("website", {}).get("value")),
            "description": safe(r.get("description", {}).get("value")),
            "source": place_url
        }

        if place["name"]:
            places.append(place)

    final = {
        "source": "Wikidata (CC0)",
        "license": "CC0 1.0",
        "country": "France",
        "count": len(places),
        "places": places
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, ensure_ascii=False, indent=2)

    print(f"Generated {OUTPUT_FILE} with {len(places)} places.")


if __name__ == "__main__":
    main()
