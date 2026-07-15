#!usr/bin/python
#pfam

import requests

INTERPRO_PFAM_URL = "https://www.ebi.ac.uk/interpro/api/entry/pfam/protein/uniprot/{}"


def pfam_id(uniprotID):
    if not uniprotID or uniprotID[0] == "No data found":
        return []
    liste = []
    try:
        response = requests.get(
            INTERPRO_PFAM_URL.format(uniprotID[0]),
            timeout=60,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
    except (requests.RequestException, ValueError, KeyError):
        return []

    for entry in results:
        accession = entry.get("metadata", {}).get("accession")
        if accession and accession not in liste:
            liste.append(accession)
    return liste


def graphic_view(Pfam_access):
    liensProt = []
    liensView = []

    for acc in Pfam_access:
        lien = "https://www.ebi.ac.uk/interpro/entry/pfam/" + acc
        liensProt.append(lien)
        liensView.append(lien)
    return liensProt, liensView
