#!/usr/bin/python3
#-*- coding: utf-8 -*-

import logging

from annotation.http import request_get

server = "https://rest.ensembl.org"

ENSEMBL_DIVISIONS = {
    "EnsemblPlants": "plants",
    "EnsemblProtists": "protists",
    "EnsembleFungi": "fungi",
    "EnsemblMetazoa": "metazoa",
    "EnsemblBacteria": "bacteria",
}

_NO_DATA = "No data found"
_HEADERS = {"Content-Type": "application/json"}
_division_cache = {}
logger = logging.getLogger("annotation")


def _ensembl_base_url(division):
    if division and division != "core":
        return f"https://{division}.ensembl.org"
    return "https://www.ensembl.org"


def check_division(organism):
    if organism in _division_cache:
        return _division_cache[organism]

    try:
        r = request_get(
            f"{server}/info/genomes/taxonomy/{organism}",
            headers=_HEADERS,
        )
    except Exception as error:
        logger.warning("Ensembl taxonomy failed for %s: %s", organism, error)
        _division_cache[organism] = "None"
        return "None"

    if not r.ok:
        _division_cache[organism] = "None"
        return "None"

    taxon_info = r.json()[0]["division"]
    division = ENSEMBL_DIVISIONS.get(taxon_info, "core")
    _division_cache[organism] = division
    return division


def ensembl_gene_id(geneSymbol, organism):
    extension = f"/lookup/symbol/{organism}/{geneSymbol}?expand=1;db_type=core"
    try:
        r = request_get(server + extension, headers=_HEADERS)
    except Exception as error:
        logger.warning("Ensembl lookup failed for %s,%s: %s", geneSymbol, organism, error)
        return "None"

    if r.ok:
        return r.json()["id"]

    division = check_division(organism)
    if division == "None":
        return "None"

    new_extension = f"/lookup/symbol/{organism}/{geneSymbol}?expand=1;db_type={division}"
    try:
        r = request_get(server + new_extension, headers=_HEADERS)
    except Exception as error:
        logger.warning("Ensembl division lookup failed for %s,%s: %s", geneSymbol, organism, error)
        return "None"

    if r.ok:
        return r.json()["id"]
    return "None"


def RNA_and_protein_id(geneId):
    transcript_list = []
    protein_list = []

    try:
        r = request_get(f"{server}/lookup/id/{geneId}?expand=1", headers=_HEADERS)
    except Exception as error:
        logger.warning("Ensembl transcripts failed for %s: %s", geneId, error)
        return transcript_list, protein_list

    if not r.ok:
        return transcript_list, protein_list

    decoded = r.json()
    transcript_list.append(decoded["canonical_transcript"])
    for transcript in decoded.get("Transcript", []):
        transcript_list.append(transcript["id"])
        if "Translation" in transcript:
            protein_list.append(transcript["Translation"]["id"])
    return transcript_list, protein_list


def RNA_and_protein_links(geneId, organism, transcript_list):
    transcript_links = []
    protein_links = []
    base = _ensembl_base_url(check_division(organism))

    for transcript_id in transcript_list:
        transcript_links.append(
            f"{base}/{organism}/Transcript/Summary?g={geneId};t={transcript_id}"
        )
        protein_links.append(
            f"{base}/{organism}/Transcript/ProteinSummary?g={geneId};t={transcript_id}"
        )
    return transcript_links, protein_links


def genome_browser_and_orthologues_links(geneId, organism):
    division = check_division(organism)
    base = _ensembl_base_url(division)
    genome_browser = f"{base}/{organism}/Location/View?db=core;g={geneId}"
    orthologues = f"{base}/{organism}/Gene/Compara_Ortholog?g={geneId}"
    return genome_browser, orthologues


def ensembl_gene_link(geneId, organism):
    division = check_division(organism)
    base = _ensembl_base_url(division)
    return f"{base}/{organism}/Gene/Summary?db=core;g={geneId}"


def Ensembl_function_calling(geneSymbol, organism):
    try:
        gene_id = ensembl_gene_id(geneSymbol, organism)
        if gene_id == "None":
            return [_NO_DATA, _NO_DATA, _NO_DATA, _NO_DATA, _NO_DATA]

        transcripts, proteins = RNA_and_protein_id(gene_id)
        genome_browser, orthologues = genome_browser_and_orthologues_links(gene_id, organism)
        return [gene_id, transcripts, proteins, genome_browser, orthologues]
    except Exception as error:
        logger.warning("Ensembl annotation failed for %s,%s: %s", geneSymbol, organism, error)
        return [_NO_DATA, _NO_DATA, _NO_DATA, _NO_DATA, _NO_DATA]
