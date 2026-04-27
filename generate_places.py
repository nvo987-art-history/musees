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


def fetch_json(url, headers=None, retries=5):
    req = urllib.request.Request(url, headers=headers or {})

    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=60) as response:
                raw = response.read().decode("utf-8", errors="replace")

                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    print("ERROR: Wikidata response is not valid JSON (attempt", attempt + 1, ")")
                    print(raw[:300])

        except Exception as e:
            print("ERROR: request failed (attempt", attempt + 1, "):", str(e))

        time.sleep(3 * (attempt + 1))

    raise RuntimeError("Failed to fetch valid JSON from Wikidata after retries.")


def run_sparql(query):
    params = {
        "query": query,
        "format": "json"
    }

    url = SPARQL_URL + "?" + urllib.parse.urlencode(params)

    headers = {
        "User-Agent": "Mozilla/5.0 (NVO987 Cultural Map Bot)",
        "Accept": "application/sparql-results+json"
    }

    return fetch_json(url, headers=headers)


def main():
    type_values = " ".join(CULTURAL_TYPES)

    query = f"""
    SELECT ?place ?placeLabel ?typeLabel ?lat ?lon ?cityLabel ?website ?description WHERE {{
      VALUES ?type {{ {type_values} }}

      ?place wdt:P31 ?type .
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

    print("Downloading Wikidata cultural places for France...")
    data = run_sparql(query)

    results = data.get("results", {}).get("bindings", [])
    print("Raw results:", len(results))

    places = []

    for r in results:
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
