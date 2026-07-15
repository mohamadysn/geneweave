import requests

_NO_DATA = "No data found"


def Quick_GO(uniprot_ids):
    liste_go_function = []
    liste_go_cellular = []
    liste_go_biological = []
    liste_go_function_link = []
    liste_go_cellular_link = []
    liste_go_biological_link = []

    for uid in uniprot_ids:
        if not uid or uid == _NO_DATA:
            continue
        try:
            r = requests.post(
                f"https://www.ebi.ac.uk/QuickGO/services/annotation/search?geneProductId={uid}",
                headers={"Accept": "application/json"},
                timeout=30,
            )
            if not r.ok:
                continue
            for entry in r.json().get("results", []):
                go_id = entry.get("goId")
                aspect = entry.get("goAspect")
                link = f"https://amigo.geneontology.org/amigo/term/{go_id}"
                if aspect == "biological_process" and go_id not in liste_go_biological:
                    liste_go_biological.append(go_id)
                    liste_go_biological_link.append(link)
                elif aspect == "molecular_function" and go_id not in liste_go_function:
                    liste_go_function.append(go_id)
                    liste_go_function_link.append(link)
                elif aspect == "cellular_component" and go_id not in liste_go_cellular:
                    liste_go_cellular.append(go_id)
                    liste_go_cellular_link.append(link)
        except (requests.RequestException, ValueError, KeyError):
            continue

    if not any([liste_go_function, liste_go_cellular, liste_go_biological]):
        empty = [_NO_DATA]
        return empty, empty, empty, empty, empty, empty

    return (
        Name_and_ID(liste_go_function),
        Name_and_ID(liste_go_biological),
        Name_and_ID(liste_go_cellular),
        liste_go_biological_link,
        liste_go_function_link,
        liste_go_cellular_link,
    )


def Name_and_ID(liste_go):
    if not liste_go:
        return [_NO_DATA]

    go_ids = ",".join(liste_go)
    try:
        r = requests.get(
            f"https://www.ebi.ac.uk/QuickGO/services/ontology/go/terms/{go_ids}",
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if not r.ok:
            return [_NO_DATA]
        results = {entry["id"]: entry["name"] for entry in r.json().get("results", [])}
    except (requests.RequestException, ValueError, KeyError):
        return [_NO_DATA]

    return [f"{go_id}:{results.get(go_id, go_id)}" for go_id in liste_go]
