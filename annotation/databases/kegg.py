#!/usr/bin/python3
# -*- coding: utf8 -*-

import re
import requests

KEGG_REST_URL = "https://rest.kegg.jp"


def _kegg_get(path):
    try:
        response = requests.get(f"{KEGG_REST_URL}/{path}", timeout=60)
        response.raise_for_status()
        return response.text
    except requests.RequestException:
        return None


def _organism_code(organism):
    parts = organism.split("_")
    if len(parts) >= 2:
        return (parts[0][0] + parts[1][:2]).lower()
    return None


def _parse_pathways(info):
    pathways = []
    pathway_links = []
    in_pathway = False

    for line in info.splitlines():
        if line.startswith("PATHWAY"):
            in_pathway = True
            parts = line.split(None, 1)
            if len(parts) == 2:
                pathway_id, pathway_name = parts[1].split(None, 1)
                pathways.append(f"{pathway_id} : {pathway_name}")
                pathway_links.append(f"https://www.genome.jp/dbget-bin/www_bget?{pathway_id}")
            continue
        if in_pathway:
            if not line.startswith(" "):
                break
            pathway_id, pathway_name = line.strip().split(None, 1)
            pathways.append(f"{pathway_id} : {pathway_name}")
            pathway_links.append(f"https://www.genome.jp/dbget-bin/www_bget?{pathway_id}")

    return pathways, pathway_links


def _entry_result(kegg_id):
    info = _kegg_get(f"get/{kegg_id}")
    if not info or info.startswith("ERROR"):
        return None

    kegg_link = f"https://www.genome.jp/dbget-bin/www_bget?{kegg_id}"
    pathways, pathway_links = _parse_pathways(info)
    if pathways:
        return ([kegg_id], [kegg_link], pathways, pathway_links)
    return ([kegg_id], [kegg_link], ["No data found"], ["No data found"])


def KEGG_infos(NCBI_Id, geneSymbol, organism):
    if not NCBI_Id or NCBI_Id == "No data found":
        return (["No data found"], ["No data found"], ["No data found"], ["No data found"])

    organism_code = _organism_code(organism)
    if not organism_code:
        return (["No data found"], ["No data found"], ["No data found"], ["No data found"])

    if re.fullmatch(r"[0-9]+", str(NCBI_Id)):
        result = _entry_result(f"{organism_code}:{NCBI_Id}")
        if result:
            return result

    find_result = _kegg_get(f"find/genes/{organism_code}/{geneSymbol}")
    if find_result and not find_result.startswith("ERROR"):
        kegg_id = find_result.splitlines()[0].split("\t")[0]
        result = _entry_result(kegg_id)
        if result:
            return result

    return (["No data found"], ["No data found"], ["No data found"], ["No data found"])


def KEGG_id_pathway(organism, NCBI_Id, geneSymbol):
    organism_key = organism.replace(" ", "_").lower()
    return KEGG_infos(NCBI_Id, geneSymbol, organism_key)
