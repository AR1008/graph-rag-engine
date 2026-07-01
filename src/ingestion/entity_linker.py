import requests
import json
import os

HEADERS = {
    "User-Agent": "GraphRAGEngine/1.0 (student project; contact: ashutosh20003@gmail.com)"
}
CACHE_FILE = os.path.join(os.path.dirname(__file__), "entity_cache.json")
LOCATION_QIDS = {"Q515", "Q1549591", "Q6256", "Q15284", "Q5119", "Q3957", "Q486972"}
# city, big city, country, municipality, capital, town, human settlement

ORG_QIDS = {"Q43229", "Q4830453", "Q891723", "Q783794", "Q6881511","Q43229", "Q4830453", "Q891723", "Q783794", "Q6881511",
    # organization, business, public company, company, enterprise
    "Q7397", "Q166142", "Q2462003", "Q3220391", "Q1668024"
    # software, application, instant messaging client, social networking service, online service
    }
# organization, business, public company, company, enterprise

PERSON_QIDS = {"Q5"}  # human

def local_cache_load():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            return json.load(f)
    return {}
def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)
_cache=local_cache_load()

def lookup_entity_type(name):
    key = name.lower().strip()
    if key in _cache:
        return _cache[key]

    try:
        search = requests.get("https://www.wikidata.org/w/api.php", params={
            "action": "wbsearchentities", "search": name,
            "language": "en", "format": "json", "limit": 1
        }, headers=HEADERS, timeout=5).json()

        if not search.get("search"):
            _cache[key] = "UNKNOWN"
            save_cache(_cache)
            return "UNKNOWN"

        qid = search["search"][0]["id"]

        claims = requests.get("https://www.wikidata.org/w/api.php", params={
            "action": "wbgetclaims", "entity": qid, "property": "P31", "format": "json"
        }, headers=HEADERS, timeout=5).json()

        instance_qids = set()
        for claim in claims.get("claims", {}).get("P31", []):
            instance_qids.add(claim["mainsnak"]["datavalue"]["value"]["id"])

        if instance_qids & LOCATION_QIDS:
            result = "LOCATION"
        elif instance_qids & ORG_QIDS:
            result = "ORGANIZATION"
        elif instance_qids & PERSON_QIDS:
            result = "PERSON"
        else:
            result = "UNKNOWN"

        _cache[key] = result
        save_cache(_cache)
        return result

    except Exception as e:
        print(f"Wikidata lookup failed for {name}: {e}")
        return "UNKNOWN"
