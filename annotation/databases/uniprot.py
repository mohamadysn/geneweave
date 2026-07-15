#!/usr/bin/python3
#-*- coding: utf-8 -*-

import re
import time
import requests

_NO_DATA = "No data found"
_UNIPROT_ACCESSION = re.compile(r"^[A-Z][0-9][A-Z0-9]{3,9}$")
_IDMAPPING_URL = "https://rest.uniprot.org/idmapping"
_UNIPROT_SEARCH_URL = "https://rest.uniprot.org/uniprotkb/search"


def _is_valid_id(value):
    return value and value not in (_NO_DATA, "None")


def _is_uniprot_accession(value):
    return bool(value and _UNIPROT_ACCESSION.match(value))


def _organism_name(organism):
    parts = organism.split("_")
    if len(parts) >= 2:
        return f"{parts[0].capitalize()} {parts[1].lower()}"
    return organism.replace("_", " ")


def _get_taxon_id(organism):
    """Resolve NCBI taxonomy id; prefer Ensembl, fall back to NCBI taxonomy."""
    if not organism:
        return None

    try:
        from annotation.http import request_get

        r = request_get(
            f"https://rest.ensembl.org/info/genomes/taxonomy/{organism}",
            headers={"Content-Type": "application/json"},
        )
        if r is not None and r.ok:
            return r.json()[0].get("taxonomy_id")
    except (requests.RequestException, IndexError, KeyError, ValueError, TypeError):
        pass

    # Fallback: NCBI taxonomy (does not depend on Ensembl being up)
    try:
        name = _organism_name(organism)
        r = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "taxonomy", "term": name, "retmode": "json"},
            timeout=30,
        )
        if r.ok:
            ids = r.json().get("esearchresult", {}).get("idlist") or []
            if ids:
                return int(ids[0])
    except (requests.RequestException, ValueError, TypeError, KeyError):
        pass
    return None


def _idmapping(from_db, ids, taxon_id=None):
    if not ids:
        return []

    data = {"from": from_db, "to": "UniProtKB", "ids": ids}
    if taxon_id:
        data["taxonId"] = str(taxon_id)

    try:
        r = requests.post(f"{_IDMAPPING_URL}/run", data=data, timeout=30)
        r.raise_for_status()
        job_id = r.json()["jobId"]
    except (requests.RequestException, KeyError, ValueError):
        return []

    for _ in range(20):
        try:
            # Don't follow the 303 to results — we only want the job status here.
            status = requests.get(
                f"{_IDMAPPING_URL}/status/{job_id}",
                timeout=30,
                allow_redirects=False,
            )
            if status.status_code in (303, 302):
                break
            status.raise_for_status()
            job_status = status.json().get("jobStatus")
            if job_status == "RUNNING":
                time.sleep(1)
                continue
            if job_status == "FINISHED":
                break
            return []
        except requests.RequestException:
            return []

    try:
        results = requests.get(
            f"{_IDMAPPING_URL}/results/{job_id}",
            params={"format": "tsv"},
            timeout=30,
        )
        results.raise_for_status()
    except requests.RequestException:
        return []

    accessions = []
    for line in results.text.strip().splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 2 and _is_uniprot_accession(parts[1]) and parts[1] not in accessions:
            accessions.append(parts[1])
    return accessions


def _search_uniprot(gene_symbol, taxon_id):
    if not gene_symbol or not taxon_id:
        return []

    try:
        r = requests.get(
            _UNIPROT_SEARCH_URL,
            params={
                "query": f"gene:{gene_symbol} AND organism_id:{taxon_id}",
                "format": "tsv",
                "fields": "accession,reviewed",
                "size": 20,
            },
            timeout=30,
        )
        r.raise_for_status()
    except requests.RequestException:
        return []

    reviewed = []
    other = []
    for line in r.text.strip().splitlines()[1:]:
        parts = line.split("\t")
        if len(parts) >= 1 and _is_uniprot_accession(parts[0]):
            if len(parts) >= 2 and parts[1] == "true":
                reviewed.append(parts[0])
            else:
                other.append(parts[0])
    return reviewed + other


def uniprot_ID_from_ncbi(gene_ids, taxon_id=None):
    valid_ids = [gid for gid in gene_ids if _is_valid_id(gid) and gid.isdigit()]
    if not valid_ids:
        return []
    return _idmapping("GeneID", ",".join(valid_ids), taxon_id)


def uniprot_ID_from_ensembl(gene_id, taxon_id=None):
    if not _is_valid_id(gene_id):
        return []
    return _idmapping("Ensembl", gene_id, taxon_id)


def uniprot_ID(ncbi_gene_ids, ensembl_gene_id, gene_symbol=None, organism=None):
    taxon_id = _get_taxon_id(organism) if organism else None

    accessions = uniprot_ID_from_ncbi(
        ncbi_gene_ids if isinstance(ncbi_gene_ids, list) else [],
        taxon_id,
    )
    for accession in uniprot_ID_from_ensembl(ensembl_gene_id, taxon_id):
        if accession not in accessions:
            accessions.append(accession)

    if not accessions and gene_symbol:
        for accession in _search_uniprot(gene_symbol, taxon_id):
            if accession not in accessions:
                accessions.append(accession)

    if not accessions:
        accessions.append(_NO_DATA)
    return accessions


def uniprot_link(uniprot_ids):
    return [f"https://www.uniprot.org/uniprotkb/{uid}" for uid in uniprot_ids if _is_uniprot_accession(uid)]


def uniprot_name(uniprot_ids):
    names = []
    for accession in uniprot_ids:
        if not _is_uniprot_accession(accession):
            continue
        try:
            r = requests.get(
                f"https://rest.uniprot.org/uniprotkb/{accession}.json",
                timeout=30,
            )
            if not r.ok:
                continue
            protein = r.json().get("proteinDescription", {})
            recommended = protein.get("recommendedName", {})
            if recommended:
                name = recommended.get("fullName", {}).get("value")
            else:
                submitted = protein.get("submissionNames", [])
                name = submitted[0].get("fullName", {}).get("value") if submitted else None
            if name and name not in names:
                names.append(name)
        except (requests.RequestException, KeyError, IndexError, ValueError):
            continue
    return names if names else [_NO_DATA]
