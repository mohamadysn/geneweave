import requests

_NO_DATA = "No data found"
STRING_API_URL = "https://string-db.org/api"


def string_id(gene_symbol, espece):
    params = {
        "identifiers": gene_symbol,
        "species": espece,
        "limit": 1,
        "echo_query": 1,
        "caller_identity": "ngs_annotation_tool",
    }
    try:
        r = requests.post(
            f"{STRING_API_URL}/tsv-no-header/get_string_ids",
            data=params,
            timeout=30,
        )
        if not r.ok:
            return [_NO_DATA]
        for line in r.text.strip().split("\n"):
            fields = line.split("\t")
            if len(fields) >= 3:
                return [fields[2]]
    except requests.RequestException:
        pass
    return [_NO_DATA]


def Network_view(string_access):
    links = []
    for acc in string_access:
        if acc != _NO_DATA:
            links.append(f"https://string-db.org/network/{acc}")
    return [links] if links else [[_NO_DATA]]


def image_network(string_access):
    links = []
    for acc in string_access:
        if acc != _NO_DATA:
            links.append(f"https://string-db.org/api/image/network?identifiers={acc}")
    return [links] if links else [[_NO_DATA]]
