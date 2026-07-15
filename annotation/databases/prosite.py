#!/usr/bin/python3
#-*- coding: utf-8 -*-

import requests

SCANPROSITE_URL = "https://prosite.expasy.org/cgi-bin/prosite/scanprosite/PSScan.cgi"

## récuperer les ID prosite à partir des ID uniprot
# uniprotID : prend le premier ID car meilleur (validé)
def scan_prosite(uniprotID):
    if not uniprotID or uniprotID[0] == "No data found":
        return ("No data found", "No data found")
    try:
        response = requests.get(
            SCANPROSITE_URL,
            params={"seq": uniprotID[0], "output": "json"},
            timeout=60,
        )
        response.raise_for_status()
        results = response.json().get("matchset", [])
    except (requests.RequestException, ValueError, KeyError):
        return ("No data found", "No data found")

    liste = []
    for element in results:
        domainAccession = element.get("signature_ac")
        if domainAccession and domainAccession not in liste:
            liste.append(domainAccession)

    if liste:
        graphicalView = graph_prosite(uniprotID)
        return (liste, graphicalView)
    return ("No data found", "No data found")

## création du lien vers la vue graphique
def graph_prosite(uniprotID):
    link = "https://prosite.expasy.org/cgi-bin/prosite/PSScan.cgi?seq=" + uniprotID[0] + "&output=nice"
    return(link)

def prosite_id_link(prositeID):
    linkList = []
    for element in prositeID :
        link = "https://prosite.expasy.org/cgi-bin/prosite/prosite_search_full.pl?SEARCH=" + element
        linkList.append(link)
    return(linkList)
