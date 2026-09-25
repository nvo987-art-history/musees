import json
import urllib.request
import urllib.parse
import time

OUTPUT_FILE = "places.json"
SPARQL_URL = "https://query.wikidata.org/sparql"

# ------------------------------------------------------------
# Wikidata kulturális hely típusok
#
# A lekérdezés P31/P279* használ:
#
#   place
#      P31 -> art museum
#      P279 -> museum
#
# Így a specializált altípusok is bekerülnek.
# ------------------------------------------------------------

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


def safe(value):
    """
    Biztonságos string-konverzió.
    """
    if value is None:
        return ""

    return str(value).strip()


def fetch_json(req, retries=5):
    """
    HTTP JSON lekérés újrapróbálkozással.
    """

    for attempt in range(retries):

        try:
            with urllib.request.urlopen(req, timeout=180) as response:

                raw = response.read().decode(
                    "utf-8",
                    errors="replace"
                )

                try:
                    return json.loads(raw)

                except json.JSONDecodeError:

                    print(
                        "ERROR: Wikidata response is not valid JSON "
                        f"(attempt {attempt + 1})"
                    )

                    print(raw[:1000])

        except Exception as e:

            print(
                f"ERROR: request failed "
                f"(attempt {attempt + 1}): {e}"
            )

        wait = 5 * (attempt + 1)

        print(f"Retrying in {wait} seconds...")

        time.sleep(wait)

    raise RuntimeError(
        "Failed to fetch valid JSON from Wikidata after retries."
    )


def run_sparql(query):
    """
    SPARQL lekérdezés küldése a Wikidata Query Service-nek.
    """

    post_data = urllib.parse.urlencode({
        "query": query,
        "format": "json"
    }).encode("utf-8")

    headers = {
        "User-Agent": (
            "NVO987 Cultural Map Bot/1.0 "
            "(https://musees.nvo987.eu/)"
        ),
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


def get_value(binding, key):
    """
    Wikidata SPARQL bindingből érték kivétele.
    """

    return safe(
        binding.get(key, {}).get("value", "")
    )


def add_unique(lst, value):
    """
    Hozzáad egy értéket, ha még nincs a listában.
    """

    value = safe(value)

    if value and value not in lst:
        lst.append(value)


def main():

    print("Starting Wikidata cultural places import...")

    # --------------------------------------------------------
    # Kulturális gyökértípusok VALUES blokkja
    # --------------------------------------------------------

    cultural_values = "\n".join(
        f"    {item}"
        for item in CULTURAL_TYPES
    )

    # --------------------------------------------------------
    # FONTOS:
    #
    # ?place wdt:P31/wdt:P279* ?cultural_type
    #
    # Ez oldja meg a Louvre problémát.
    #
    # A Louvre:
    #
    # Q19675
    #   P31 -> art museum
    #   art museum P279 -> museum
    #
    # Ezért most megtalálja a museum ágon keresztül.
    # --------------------------------------------------------

    query = f"""
    SELECT DISTINCT
        ?place
        ?placeLabel
        ?cultural_type
        ?cultural_typeLabel
        ?lat
        ?lon
        ?city
        ?cityLabel
        ?website
        ?description
        ?alias
    WHERE {{

        VALUES ?cultural_type {{
{cultural_values}
        }}

        ?place wdt:P31/wdt:P279* ?cultural_type .

        # Franciaország
        ?place wdt:P17 wd:Q142 .

        # --------------------------------------------
        # Koordináták
        # --------------------------------------------

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

        # --------------------------------------------
        # Közigazgatási hely
        # --------------------------------------------

        OPTIONAL {{
            ?place wdt:P131 ?city .
        }}

        # --------------------------------------------
        # Hivatalos weboldal
        # --------------------------------------------

        OPTIONAL {{
            ?place wdt:P856 ?website .
        }}

        # --------------------------------------------
        # Francia leírás
        # --------------------------------------------

        OPTIONAL {{
            ?place schema:description ?description .

            FILTER(
                LANG(?description) = "fr"
            )
        }}

        # --------------------------------------------
        # Wikidata aliasok
        #
        # Ez különösen fontos a kereséshez.
        #
        # Például:
        # Musée du Louvre
        # Louvre Museum
        # The Louvre
        # Louvre
        # --------------------------------------------

        OPTIONAL {{
            ?place skos:altLabel ?alias .

            FILTER(
                LANG(?alias) = "fr"
                ||
                LANG(?alias) = "en"
            )
        }}

        # --------------------------------------------
        # Label service
        # --------------------------------------------

        SERVICE wikibase:label {{
            bd:serviceParam
                wikibase:language "fr,en" .
        }}
    }}
    """

    print("Downloading data from Wikidata...")
    print("This may take some time...")

    data = run_sparql(query)

    results = (
        data
        .get("results", {})
        .get("bindings", [])
    )

    print("Raw SPARQL rows:", len(results))

    # --------------------------------------------------------
    # HELPER:
    #
    # A Wikidata SPARQL eredményben ugyanaz a hely többször
    # szerepelhet:
    #
    # - több alias
    # - több P31
    # - több website
    # - több P131
    #
    # Ezért ID alapján összefűzzük őket.
    # --------------------------------------------------------

    places_by_id = {}

    for r in results:

        place_url = get_value(r, "place")

        if not place_url:
            continue

        place_id = place_url.rstrip("/").split("/")[-1]

        if not place_id:
            continue

        # ----------------------------------------------------
        # Alapobjektum létrehozása
        # ----------------------------------------------------

        if place_id not in places_by_id:

            places_by_id[place_id] = {
                "id": place_id,
                "name": "",
                "aliases": [],
                "type": "",
                "types": [],
                "city": "",
                "lat": None,
                "lon": None,
                "website": "",
                "description": "",
                "source": place_url
            }

        place = places_by_id[place_id]

        # ----------------------------------------------------
        # NAME
        # ----------------------------------------------------

        name = get_value(r, "placeLabel")

        if name and not place["name"]:
            place["name"] = name

        # ----------------------------------------------------
        # ALIAS
        # ----------------------------------------------------

        alias = get_value(r, "alias")

        add_unique(
            place["aliases"],
            alias
        )

        # A fő nevet is tegyük bele az alias-listába.
        # Ez megkönnyíti a kliensoldali keresést.
        if place["name"]:
            add_unique(
                place["aliases"],
                place["name"]
            )

        # ----------------------------------------------------
        # TYPE
        # ----------------------------------------------------

        type_label = get_value(
            r,
            "cultural_typeLabel"
        )

        add_unique(
            place["types"],
            type_label
        )

        # ----------------------------------------------------
        # CITY
        # ----------------------------------------------------

        city = get_value(
            r,
            "cityLabel"
        )

        if city and not place["city"]:
            place["city"] = city

        # ----------------------------------------------------
        # COORDINATES
        # ----------------------------------------------------

        lat = get_value(r, "lat")
        lon = get_value(r, "lon")

        if lat and place["lat"] is None:

            try:
                place["lat"] = float(lat)

            except ValueError:
                pass

        if lon and place["lon"] is None:

            try:
                place["lon"] = float(lon)

            except ValueError:
                pass

        # ----------------------------------------------------
        # WEBSITE
        # ----------------------------------------------------

        website = get_value(
            r,
            "website"
        )

        if website and not place["website"]:
            place["website"] = website

        # ----------------------------------------------------
        # DESCRIPTION
        # ----------------------------------------------------

        description = get_value(
            r,
            "description"
        )

        if description and not place["description"]:
            place["description"] = description

    # --------------------------------------------------------
    # PLACE lista
    # --------------------------------------------------------

    places = []

    for place_id, place in places_by_id.items():

        # ----------------------------------------------------
        # Csak koordinátával rendelkező helyek
        # ----------------------------------------------------

        if place["lat"] is None:
            continue

        if place["lon"] is None:
            continue

        # ----------------------------------------------------
        # Név nélküli objektum kihagyása
        # ----------------------------------------------------

        if not place["name"]:
            continue

        # ----------------------------------------------------
        # Aliasok rendezése
        # ----------------------------------------------------

        place["aliases"] = sorted(
            set(place["aliases"]),
            key=str.casefold
        )

        # ----------------------------------------------------
        # Típusok rendezése
        # ----------------------------------------------------

        place["types"] = sorted(
            set(place["types"]),
            key=str.casefold
        )

        # ----------------------------------------------------
        # Kompatibilitás a régi struktúrával
        #
        # A meglévő frontend valószínűleg a "type" mezőt
        # használja, ezért megtartjuk.
        # ----------------------------------------------------

        if place["types"]:
            place["type"] = ", ".join(
                place["types"]
            )

        else:
            place["type"] = ""

        places.append(place)

    # --------------------------------------------------------
    # ID szerinti végső biztonsági deduplikáció
    # --------------------------------------------------------

    unique_places = {}

    for place in places:

        unique_places[place["id"]] = place

    places = list(
        unique_places.values()
    )

    # --------------------------------------------------------
    # Rendezés név szerint
    # --------------------------------------------------------

    places.sort(
        key=lambda x: x["name"].casefold()
    )

    # --------------------------------------------------------
    # Louvre ellenőrzése
    # --------------------------------------------------------

    louvre = next(
        (
            place
            for place in places
            if place["id"] == "Q19675"
        ),
        None
    )

    if louvre:

        print()
        print("======================================")
        print("LOUVRE FOUND")
        print("======================================")
        print("ID:", louvre["id"])
        print("Name:", louvre["name"])
        print("Type:", louvre["type"])
        print("City:", louvre["city"])
        print("Lat:", louvre["lat"])
        print("Lon:", louvre["lon"])
        print("Website:", louvre["website"])
        print("Aliases:", louvre["aliases"])
        print("======================================")
        print()

    else:

        print()
        print("WARNING:")
        print("Q19675 (Musée du Louvre) was NOT found!")
        print()

    # --------------------------------------------------------
    # Végső JSON
    # --------------------------------------------------------

    final = {
        "source": "Wikidata (CC0)",
        "license": "CC0 1.0",
        "country": "France",
        "count": len(places),
        "places": places
    }

    # --------------------------------------------------------
    # JSON mentése
    # --------------------------------------------------------

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
