#!/usr/bin/python3
#-*- coding: utf-8 -*-

#Module NCBI

#GENE SYMBOL (gene)
#GENRE SPECIES (orgn)

from Bio import Entrez
import re
import time

from annotation.config import NCBI_EMAIL, NCBI_DELAY

Entrez.email = NCBI_EMAIL

_NO_DATA = "No data found"
_MAX_RETRIES = 3
_RETRY_DELAY = 1.0


def _organism_name(organism):
    parts = organism.split("_")
    if len(parts) >= 2:
        return f"{parts[0].capitalize()} {parts[1].lower()}"
    return organism.replace("_", " ")


def _entrez_call(func, *args, **kwargs):
    for attempt in range(_MAX_RETRIES):
        try:
            handle = func(*args, **kwargs)
            result = Entrez.read(handle)
            time.sleep(NCBI_DELAY)
            return result
        except (RuntimeError, Exception):
            if attempt == _MAX_RETRIES - 1:
                return None
            time.sleep(_RETRY_DELAY * (attempt + 1))
    return None


def _entrez_fetch_text(db, ids, **kwargs):
    if not ids:
        return ""
    for attempt in range(_MAX_RETRIES):
        try:
            handle = Entrez.efetch(db=db, id=ids, **kwargs)
            text = handle.read()
            time.sleep(NCBI_DELAY)
            return text
        except (RuntimeError, Exception):
            if attempt == _MAX_RETRIES - 1:
                return ""
            time.sleep(_RETRY_DELAY * (attempt + 1))
    return ""


## appel des fonctions NCBI
def NCBI_function_call(geneSymbol, organism):
    gene_ids = NCBI_Id(geneSymbol, organism)

    if not gene_ids:
        empty = [_NO_DATA]
        return [_NO_DATA, [], (empty, empty), (empty, empty)]

    official_name = NCBI_official_name(gene_ids)
    transcripts, transcript_links = RefSeq_transcript_id(geneSymbol, organism)
    proteins, protein_links = RefSeq_protein_id(geneSymbol, organism)

    return [official_name, gene_ids, (transcripts, transcript_links), (proteins, protein_links)]


## récupérer les gene id NCBI
def NCBI_Id(geneSymbol, organism):
    orgn = _organism_name(organism)
    records = _entrez_call(
        Entrez.esearch,
        db="gene",
        term=f"{geneSymbol}[GENE] AND {orgn}[ORGN]",
    )
    if not records:
        return []
    return records.get("IdList", [])


def NCBI_gene_link(geneID):
    linkList = []
    for element in geneID:
        link = "https://www.ncbi.nlm.nih.gov/gene/?term=" + element
        linkList.append(link)
    return linkList


## récupérer official full name
def NCBI_official_name(identifiers):
    text = _entrez_fetch_text(
        "gene",
        identifiers,
        retmax=100,
        rettype="gb",
        retmode="text",
    )
    if not text:
        return _NO_DATA

    lines = text.splitlines()
    if len(lines) < 3:
        return _NO_DATA

    lineOfInterest = lines[2].strip()
    if re.search("Name", lineOfInterest):
        isolatedName = lineOfInterest.split("Name: ")
        officialName = isolatedName[1].split(" [")
        officialName = officialName[0]
    else:
        officialName = lineOfInterest.split(" [")
        officialName = officialName[0]
    return officialName


## récupérer les id (accession number = acc) ARN sur RefSeq
def RefSeq_transcript_id(geneSymbol, organism):
    transcript = []
    transcriptLink = []

    orgn = _organism_name(organism)
    rec = _entrez_call(
        Entrez.esearch,
        db="nucleotide",
        term=f"{geneSymbol}[GENE] AND {orgn}[ORGN]",
    )
    if not rec:
        transcript.append(_NO_DATA)
        transcriptLink.append(_NO_DATA)
        return transcript, transcriptLink

    rnaIdList = rec.get("IdList", [])
    text = _entrez_fetch_text(
        "nucleotide",
        rnaIdList,
        retmax=100,
        rettype="acc",
        retmode="text",
    )
    textLines = text.split("\n")
    for line in textLines:
        if re.search(".M_", line):
            transcript.append(line)
            transcriptLink.append("https://www.ncbi.nlm.nih.gov/nuccore/" + line)

    if transcript == []:
        transcript.append(_NO_DATA)
        transcriptLink.append(_NO_DATA)

    return transcript, transcriptLink


## récupérer les id protéines sur RefSeq
def RefSeq_protein_id(geneSymbol, organism):
    protein = []
    proteinLink = []

    orgn = _organism_name(organism)
    rec = _entrez_call(
        Entrez.esearch,
        db="protein",
        term=f"{geneSymbol}[GENE] AND {orgn}[ORGN]",
    )
    if not rec:
        protein.append(_NO_DATA)
        proteinLink.append(_NO_DATA)
        return protein, proteinLink

    idProt = rec.get("IdList", [])
    text = _entrez_fetch_text(
        "protein",
        idProt,
        retmax=100,
        rettype="acc",
        retmode="text",
    )
    textLines = text.split("\n")
    for line in textLines:
        if re.search(".P_", line):
            protein.append(line)
            proteinLink.append("https://www.ncbi.nlm.nih.gov/nuccore/" + line)

    if protein == []:
        protein.append(_NO_DATA)
        proteinLink.append(_NO_DATA)

    return protein, proteinLink
