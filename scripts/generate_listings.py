"""Generate realistic sample listings across Vancouver into db/seed.sql.

    python scripts/generate_listings.py            # 200 listings
    python scripts/generate_listings.py -n 500     # more

The listings go in a marked section at the end of seed.sql. Rerunning replaces
that section; the hand-written listings above it are never touched.
Uses a fixed random seed, so everyone gets the same listings.
"""
import argparse
import random
from pathlib import Path

SEED = 2026
SEED_FILE = Path(__file__).resolve().parent.parent / "db" / "seed.sql"
BEGIN = "-- BEGIN GENERATED LISTINGS"
END = "-- END GENERATED LISTINGS"

# name: (lat, lon, spread in degrees, price tier, streets, type weights, local perks)
# Tier scales price per sqft: 1.0 is a typical Vancouver price.
NEIGHBOURHOODS = {
    "Downtown": (49.2810, -123.1180, 0.004, 1.10,
        ["Granville St", "Seymour St", "Richards St", "Homer St", "Hornby St", "Howe St", "W Georgia St", "Robson St"],
        {"condo": 9, "loft": 1}, ["steps to shops and restaurants", "near SkyTrain", "walk to the seawall"]),
    "West End": (49.2860, -123.1360, 0.004, 1.05,
        ["Davie St", "Denman St", "Nelson St", "Comox St", "Barclay St", "Haro St", "Pendrell St", "Bidwell St"],
        {"condo": 9, "townhouse": 1}, ["steps from English Bay", "close to Stanley Park", "quiet tree-lined street"]),
    "Yaletown": (49.2755, -123.1210, 0.003, 1.15,
        ["Mainland St", "Hamilton St", "Homer St", "Pacific Blvd", "Drake St", "Davie St"],
        {"condo": 7, "loft": 3}, ["near the Yaletown seawall", "close to Canada Line", "restaurants at your door"]),
    "Coal Harbour": (49.2895, -123.1260, 0.002, 1.40,
        ["W Hastings St", "W Cordova St", "Bayshore Dr", "Cardero St"],
        {"condo": 10}, ["harbour and mountain views", "steps to the seawall", "concierge building"]),
    "Gastown": (49.2835, -123.1070, 0.002, 1.00,
        ["Water St", "Alexander St", "Powell St", "Abbott St", "W Cordova St"],
        {"loft": 6, "condo": 4}, ["heritage character", "near Waterfront Station", "cobblestone streets and cafes"]),
    "Strathcona": (49.2770, -123.0890, 0.004, 0.90,
        ["Union St", "Prior St", "Keefer St", "Hawks Ave", "Princess Ave"],
        {"house": 3, "duplex": 3, "condo": 3, "townhouse": 1}, ["close to Strathcona Park", "historic neighbourhood", "near Chinatown"]),
    "Mount Pleasant": (49.2630, -123.1010, 0.005, 1.00,
        ["Main St", "E 7th Ave", "E 10th Ave", "Quebec St", "Ontario St", "Prince Edward St"],
        {"condo": 5, "townhouse": 2, "duplex": 2, "house": 1}, ["near Main St cafes and breweries", "close to transit", "bike-friendly"]),
    "Fairview": (49.2635, -123.1300, 0.004, 1.05,
        ["W 10th Ave", "W 8th Ave", "Oak St", "Laurel St", "W Broadway", "Granville St"],
        {"condo": 8, "townhouse": 2}, ["close to VGH and shops", "near the future Broadway subway", "views of downtown"]),
    "Kitsilano": (49.2685, -123.1620, 0.006, 1.15,
        ["W 4th Ave", "W 2nd Ave", "Yew St", "Vine St", "Arbutus St", "W Broadway", "Macdonald St"],
        {"condo": 4, "townhouse": 2, "duplex": 2, "house": 2}, ["steps to Kits Beach", "walk to W 4th shops", "close to parks and schools"]),
    "Point Grey": (49.2660, -123.1950, 0.006, 1.35,
        ["W 8th Ave", "W 10th Ave", "Sasamat St", "Tolmie St", "Blanca St"],
        {"house": 6, "condo": 2, "duplex": 2}, ["near UBC", "close to Jericho Beach", "quiet family street"]),
    "Dunbar": (49.2480, -123.1850, 0.007, 1.20,
        ["Dunbar St", "W 27th Ave", "W 33rd Ave", "Collingwood St", "Highbury St"],
        {"house": 8, "duplex": 2}, ["near Pacific Spirit Park", "top-rated schools nearby", "large private yard"]),
    "Kerrisdale": (49.2340, -123.1560, 0.006, 1.20,
        ["W 41st Ave", "East Blvd", "W Boulevard", "Yew St", "Larch St"],
        {"condo": 4, "house": 4, "townhouse": 2}, ["walk to Kerrisdale Village", "close to schools", "on a quiet street"]),
    "Shaughnessy": (49.2480, -123.1400, 0.006, 1.60,
        ["Matthews Ave", "Osler St", "Hudson St", "W 16th Ave", "The Crescent"],
        {"house": 10}, ["mature gardens", "prestigious tree-lined street", "close to private schools"]),
    "South Cambie": (49.2450, -123.1200, 0.004, 1.10,
        ["Cambie St", "W King Edward Ave", "Heather St", "W 29th Ave"],
        {"condo": 6, "townhouse": 3, "house": 1}, ["near Queen Elizabeth Park", "steps to Canada Line", "close to Hillcrest Centre"]),
    "Oakridge": (49.2280, -123.1170, 0.005, 1.10,
        ["Cambie St", "W 41st Ave", "Oak St", "Willow St", "W 45th Ave"],
        {"condo": 6, "townhouse": 2, "house": 2}, ["near Oakridge Park", "steps to Canada Line", "new community amenities"]),
    "Marpole": (49.2100, -123.1300, 0.005, 0.90,
        ["Granville St", "SW Marine Dr", "W 70th Ave", "Hudson St", "Fremlin St"],
        {"condo": 5, "townhouse": 3, "house": 2}, ["close to the Fraser River", "easy airport access", "near Marpole Community Centre"]),
    "Riley Park": (49.2450, -123.1010, 0.005, 1.00,
        ["Main St", "Prince Edward St", "E 22nd Ave", "Sophia St", "E 26th Ave"],
        {"house": 4, "duplex": 3, "townhouse": 2, "condo": 1}, ["near Nat Bailey Stadium", "walk to Main St shops", "close to Hillcrest pool"]),
    "Kensington": (49.2450, -123.0850, 0.006, 0.90,
        ["Fraser St", "Knight St", "E 29th Ave", "Inverness St"],
        {"house": 5, "duplex": 3, "townhouse": 2}, ["close to Trout Lake", "family-friendly block", "near Fraser St restaurants"]),
    "Grandview": (49.2700, -123.0700, 0.005, 0.95,
        ["Commercial Dr", "Victoria Dr", "E 1st Ave", "Garden Dr", "Woodland Dr", "Venables St"],
        {"condo": 3, "house": 3, "duplex": 2, "loft": 1, "townhouse": 1}, ["walk to Commercial Drive", "near Commercial-Broadway SkyTrain", "close to Trout Lake"]),
    "Hastings-Sunrise": (49.2805, -123.0450, 0.005, 0.85,
        ["E Hastings St", "Nanaimo St", "Renfrew St", "Pandora St", "Eton St"],
        {"house": 4, "condo": 3, "duplex": 2, "townhouse": 1}, ["near New Brighton Park", "close to the PNE", "mountain views"]),
    "Renfrew": (49.2550, -123.0400, 0.006, 0.85,
        ["Renfrew St", "E 22nd Ave", "Rupert St", "Nootka St"],
        {"house": 5, "duplex": 3, "townhouse": 2}, ["near Renfrew SkyTrain", "close to Renfrew Ravine Park", "large lot"]),
    "Sunset": (49.2200, -123.0900, 0.005, 0.85,
        ["Fraser St", "E 49th Ave", "Knight St", "St. George St"],
        {"house": 6, "duplex": 3, "townhouse": 1}, ["close to Sunset Park", "basement suite potential", "near Punjabi Market"]),
    "Killarney": (49.2200, -123.0400, 0.005, 0.85,
        ["Kerr St", "E 49th Ave", "Killarney St", "E 54th Ave"],
        {"townhouse": 4, "house": 4, "condo": 2}, ["near Killarney Community Centre", "close to Everett Crowley Park", "quiet cul-de-sac"]),
    "Victoria-Fraserview": (49.2200, -123.0650, 0.005, 0.90,
        ["Victoria Dr", "E 54th Ave", "Elliott St", "E 49th Ave"],
        {"house": 6, "townhouse": 2, "duplex": 2}, ["near Fraserview Golf Course", "mountain views", "close to Champlain Mall"]),
}

# Same shape as NEIGHBOURHOODS. Prices are lower the farther from Vancouver.
SUBURBS = {
    # Richmond
    "Brighouse": (49.1680, -123.1370, 0.005, 0.85,
        ["No. 3 Rd", "Westminster Hwy", "Granville Ave", "Cooney Rd", "Saba Rd", "Minoru Blvd"],
        {"condo": 8, "townhouse": 2}, ["steps to Richmond-Brighouse Station", "near Richmond Centre", "close to Minoru Park"]),
    "Steveston": (49.1290, -123.1780, 0.005, 0.95,
        ["Moncton St", "Chatham St", "No. 1 Rd", "Bayview St", "Railway Ave"],
        {"townhouse": 4, "house": 4, "condo": 2}, ["walk to Steveston Village", "near the waterfront boardwalk", "close to Garry Point Park"]),
    "Terra Nova": (49.1790, -123.1760, 0.004, 0.90,
        ["River Rd", "Westminster Hwy", "Barnard Dr", "No. 1 Rd"],
        {"house": 6, "townhouse": 4}, ["near Terra Nova Rural Park", "quiet family street", "close to the West Dyke Trail"]),
    "Broadmoor": (49.1500, -123.1200, 0.005, 0.85,
        ["Williams Rd", "No. 3 Rd", "Garden City Rd", "Francis Rd"],
        {"house": 5, "townhouse": 4, "duplex": 1}, ["close to Broadmoor Shopping Centre", "top-rated schools nearby", "large private yard"]),
    # Burnaby
    "Metrotown": (49.2270, -123.0030, 0.004, 0.90,
        ["Kingsway", "Willingdon Ave", "Beresford St", "Central Blvd", "Imperial St"],
        {"condo": 9, "townhouse": 1}, ["steps to Metrotown Station", "next to Metropolis at Metrotown", "close to Central Park"]),
    "Brentwood": (49.2665, -123.0010, 0.004, 0.90,
        ["Lougheed Hwy", "Willingdon Ave", "Halifax St", "Beta Ave"],
        {"condo": 9, "townhouse": 1}, ["near Brentwood Town Centre Station", "next to The Amazing Brentwood", "mountain views"]),
    "Burnaby Heights": (49.2830, -123.0050, 0.004, 0.95,
        ["Hastings St", "Albert St", "Pender St", "Gamma Ave"],
        {"house": 5, "townhouse": 3, "duplex": 2}, ["walk to Hastings St shops", "close to Confederation Park", "North Shore mountain views"]),
    "Edmonds": (49.2120, -122.9570, 0.004, 0.80,
        ["Edmonds St", "Kingsway", "18th Ave", "Griffiths Dr"],
        {"condo": 5, "townhouse": 3, "house": 2}, ["near Edmonds Station", "close to Highland Park", "near Highgate Village"]),
    "Lougheed": (49.2490, -122.8970, 0.004, 0.80,
        ["Lougheed Hwy", "Austin Rd", "Cameron St", "North Rd"],
        {"condo": 7, "townhouse": 3}, ["steps to Lougheed Town Centre Station", "near Burnaby Mountain", "close to Cameron Park"]),
    # Surrey
    "Surrey City Centre": (49.1880, -122.8490, 0.005, 0.70,
        ["King George Blvd", "104 Ave", "University Dr", "100 Ave"],
        {"condo": 8, "townhouse": 2}, ["steps to Surrey Central Station", "near SFU Surrey", "close to Holland Park"]),
    "Guildford": (49.1910, -122.8030, 0.005, 0.65,
        ["152 St", "104 Ave", "Guildford Way", "148 St"],
        {"townhouse": 4, "condo": 3, "house": 3}, ["near Guildford Town Centre", "close to the Green Timbers forest", "easy highway access"]),
    "Fleetwood": (49.1500, -122.7950, 0.006, 0.65,
        ["Fraser Hwy", "160 St", "84 Ave", "156 St"],
        {"house": 5, "townhouse": 4, "duplex": 1}, ["near Fleetwood Park", "close to the future SkyTrain extension", "family-friendly block"]),
    "Newton": (49.1300, -122.8450, 0.006, 0.60,
        ["72 Ave", "King George Blvd", "128 St", "136 St"],
        {"house": 5, "townhouse": 4, "condo": 1}, ["near Newton Athletic Park", "basement suite potential", "close to transit"]),
    "Cloverdale": (49.1050, -122.7250, 0.006, 0.65,
        ["176 St", "60 Ave", "64 Ave", "168 St"],
        {"house": 5, "townhouse": 4, "duplex": 1}, ["walk to historic Cloverdale", "near the fairgrounds", "large lot"]),
    "South Surrey": (49.0400, -122.8000, 0.007, 0.85,
        ["24 Ave", "152 St", "32 Ave", "160 St"],
        {"house": 6, "townhouse": 3, "condo": 1}, ["near Crescent Beach", "close to Morgan Crossing", "quiet cul-de-sac"]),
}

CITY = {**{h: "Vancouver" for h in NEIGHBOURHOODS},
        **{h: "Richmond" for h in ("Brighouse", "Steveston", "Terra Nova", "Broadmoor")},
        **{h: "Burnaby" for h in ("Metrotown", "Brentwood", "Burnaby Heights", "Edmonds", "Lougheed")},
        **{h: "Surrey" for h in ("Surrey City Centre", "Guildford", "Fleetwood", "Newton", "Cloverdale", "South Surrey")}}

# Street-number ranges per city: (condo/loft buildings, houses and townhouses).
NUMBERS = {
    "Vancouver": ((100, 1999), (100, 4999)),
    "Richmond": ((3000, 9999), (3000, 11999)),
    "Burnaby": ((3000, 7999), (3000, 8999)),
    "Surrey": ((10000, 19999), (5000, 19999)),
}

# property type: (base price per sqft, {bedrooms: (min sqft, max sqft), ...}, adjectives, features)
TYPES = {
    "condo": (1150, {0: (380, 480), 1: (520, 720), 2: (780, 1100), 3: (1150, 1500)},
              ["Bright", "Modern", "Updated", "Sunny", "Spacious", "Corner"],
              ["floor-to-ceiling windows", "in-suite laundry", "large balcony", "rooftop amenity deck", "renovated kitchen", "secure parking"]),
    "loft": (1050, {1: (600, 900), 2: (900, 1250)},
             ["Industrial", "Heritage", "Open-concept", "Character", "Converted"],
             ["exposed brick", "16-foot ceilings", "polished concrete floors", "original timber beams", "oversized windows"]),
    "townhouse": (1000, {2: (1000, 1300), 3: (1250, 1700), 4: (1600, 1950)},
                  ["Family", "Modern", "Well-kept", "Quiet", "End-unit"],
                  ["private patio", "attached garage", "rooftop deck", "two-level layout", "low strata fees"]),
    "duplex": (1050, {3: (1300, 1700), 4: (1600, 2150)},
               ["Updated", "Character", "Brand-new", "Spacious", "Bright"],
               ["private yard", "radiant floor heating", "laneway parking", "high-end finishes", "spacious basement"]),
    "house": (950, {3: (1800, 2400), 4: (2200, 3000), 5: (2800, 3800), 6: (3400, 4600)},
              ["Family", "Renovated", "Character", "Craftsman", "Classic", "Modern"],
              ["large backyard", "basement suite", "detached garage", "updated kitchen", "mountain views", "south-facing garden"]),
}

BEDROOM_WEIGHTS = {
    "condo": {0: 1, 1: 4, 2: 4, 3: 1},
    "loft": {1: 3, 2: 2},
    "townhouse": {2: 3, 3: 5, 4: 2},
    "duplex": {3: 5, 4: 3},
    "house": {3: 3, 4: 4, 5: 2, 6: 1},
}


def pick(rng, weights: dict):
    return rng.choices(list(weights), weights=list(weights.values()))[0]


def washrooms_for(rng, ptype, beds):
    if ptype in ("condo", "loft"):
        if beds <= 1:
            return 1.0
        return rng.choice([1.0, 2.0, 2.0]) if beds == 2 else 2.0
    if ptype == "house":
        return max(2.0, beds - 1 + rng.choice([0.0, 0.5, 1.0]))
    return beds - 1 + 0.5  # townhouses and duplexes: e.g. 3 bed -> 2.5 bath


def price_for(rng, ptype, sqft, tier):
    base_ppsf = TYPES[ptype][0]
    # Houses carry land value, so neighbourhood matters even more for them.
    tier_effect = tier ** 1.6 if ptype == "house" else tier
    price = sqft * base_ppsf * tier_effect * rng.uniform(0.88, 1.12)
    return int(round(price, -4)) - 1000  # list prices like 849,000


def address_for(rng, ptype, streets, city):
    street = rng.choice(streets)
    building_numbers, house_numbers = NUMBERS[city]
    if ptype in ("condo", "loft"):
        number = rng.randrange(*building_numbers)
        unit = rng.randrange(2, 35) * 100 + rng.randrange(1, 12)
        return f"{unit}-{number} {street}"
    return f"{rng.randrange(*house_numbers)} {street}"


def describe(rng, ptype, beds, hood, perks):
    adjective = rng.choice(TYPES[ptype][2])
    size = "studio" if beds == 0 else f"{beds}-bed {ptype}"
    features = rng.sample(TYPES[ptype][3], 2)
    city = CITY[hood]
    # Outside Vancouver, name the city too, so "Richmond" or "Burnaby" shows up in the text.
    where = hood if city == "Vancouver" or city in hood else f"{hood}, {city},"
    return f"{adjective} {where} {size} with {features[0]} and {features[1]}, {rng.choice(perks)}"


def generate(n: int, areas: dict = NEIGHBOURHOODS, seed: int = SEED, used: set | None = None) -> list[dict]:
    rng = random.Random(seed)
    hoods = list(areas)
    listings, used = [], used if used is not None else set()
    while len(listings) < n:
        hood = rng.choice(hoods)
        lat0, lon0, spread, tier, streets, type_weights, perks = areas[hood]
        ptype = pick(rng, type_weights)
        beds = pick(rng, BEDROOM_WEIGHTS[ptype])
        address = address_for(rng, ptype, streets, CITY[hood])
        if address in used:
            continue
        used.add(address)
        sqft = rng.randint(*TYPES[ptype][1][beds]) // 10 * 10
        listings.append({
            "address": address,
            "description": describe(rng, ptype, beds, hood, perks),
            # Longitude spread is wider: a degree of longitude is shorter than one of latitude here.
            "lat": round(lat0 + rng.uniform(-spread, spread), 5),
            "lon": round(lon0 + rng.uniform(-spread, spread) * 1.5, 5),
            "bedrooms": beds,
            "washrooms": washrooms_for(rng, ptype, beds),
            "sqft": sqft,
            "price": price_for(rng, ptype, sqft, tier),
            "property_type": ptype,
        })
    return listings


def sql_text(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def to_sql(listings: list[dict]) -> str:
    rows = [
        f"({sql_text(l['address'])}, {sql_text(l['description'])}, "
        f"ST_MakePoint({l['lon']}, {l['lat']}), {l['bedrooms']}, {l['washrooms']:.1f}, "
        f"{l['sqft']}, {l['price']}, {sql_text(l['property_type'])})"
        for l in listings
    ]
    return (
        f"{BEGIN} ({len(listings)}): made by scripts/generate_listings.py, do not edit by hand\n"
        "INSERT INTO listings (address, description, location, bedrooms, washrooms, sqft, price, property_type) VALUES\n"
        + ",\n".join(rows)
        + f";\n{END}\n"
    )


def write_into_seed(block: str, path: Path) -> None:
    """Replace the generated section of seed.sql, or append it if missing."""
    text = path.read_text()
    if BEGIN in text:
        before = text[:text.index(BEGIN)]
        after = text[text.index(END) + len(END):].lstrip("\n")
        text = before + block + after
    else:
        text = text.rstrip("\n") + "\n\n" + block
    path.write_text(text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("-n", type=int, default=200, help="listings in Vancouver (default 200)")
    parser.add_argument("--suburbs", type=int, default=100, help="listings in Richmond, Burnaby and Surrey (default 100)")
    args = parser.parse_args()
    used = set()
    # Separate random sequences, so changing --suburbs never changes the Vancouver listings.
    listings = generate(args.n, NEIGHBOURHOODS, SEED, used) + generate(args.suburbs, SUBURBS, SEED + 1, used)
    write_into_seed(to_sql(listings), SEED_FILE)
    print(f"Wrote {len(listings)} generated listings into {SEED_FILE}")
