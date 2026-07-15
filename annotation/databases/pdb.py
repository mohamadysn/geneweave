import requests

_NO_DATA = "No data found"
_PDB_SEARCH_URL = "https://search.rcsb.org/rcsbsearch/v2/query"
_PDB_ENTRY_URL = "https://data.rcsb.org/rest/v1/core/entry/"


def _organism_name(organism):
    parts = organism.split("_")
    if len(parts) >= 2:
        return f"{parts[0].capitalize()} {parts[1].lower()}"
    return organism.replace("_", " ")


def PDB_Names(liste_id):
    if liste_id == [_NO_DATA]:
        return [_NO_DATA]

    pdb_names = []
    for pdb_id in liste_id:
        try:
            r = requests.get(f"{_PDB_ENTRY_URL}{pdb_id}", timeout=30)
            if r.ok:
                title = r.json()["struct"]["title"]
                pdb_names.append(f"{pdb_id} : {title}")
        except (requests.RequestException, KeyError, ValueError):
            continue
    return pdb_names if pdb_names else [_NO_DATA]


def PDB_URL(liste_id):
    if liste_id == [_NO_DATA]:
        return [_NO_DATA]
    return [f"https://www.rcsb.org/structure/{pdb_id}" for pdb_id in liste_id]


def PDB_infos(gene_symbol, espece):
    organism_name = _organism_name(espece)
    query = {
        "query": {
            "type": "group",
            "logical_operator": "and",
            "nodes": [
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entity_source_organism.rcsb_gene_name.value",
                        "operator": "exact_match",
                        "value": gene_symbol,
                    },
                },
                {
                    "type": "terminal",
                    "service": "text",
                    "parameters": {
                        "attribute": "rcsb_entity_source_organism.ncbi_scientific_name",
                        "operator": "exact_match",
                        "value": organism_name,
                    },
                },
            ],
        },
        "return_type": "entry",
    }

    try:
        r = requests.post(_PDB_SEARCH_URL, json=query, timeout=30)
        if not r.ok:
            liste_id = [_NO_DATA]
        else:
            result_set = r.json().get("result_set", [])
            liste_id = [entry["identifier"] for entry in result_set] if result_set else [_NO_DATA]
    except (requests.RequestException, ValueError, KeyError):
        liste_id = [_NO_DATA]

    return PDB_Names(liste_id), PDB_URL(liste_id)
