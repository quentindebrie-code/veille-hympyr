# -*- coding: utf-8 -*-
"""
veille_hympyr.py — Digest de veille matinal pour Hympyr Énergies
-----------------------------------------------------------------
Collecte 4 blocs (prix carburants locaux, Brent, Google Trends, actus RSS),
expose 4 collecteurs (prix carburants locaux, Brent, Google Trends, actus RSS)
réutilisés par l'app Streamlit de veille (affichage à la demande).

Le script est TOLÉRANT À LA PANNE : si une source échoue, les autres blocs
partent quand même, et le bloc en échec affiche un message au lieu de tout planter.
Une veille qui saute un matin parce qu'un site a bronché, c'est une veille morte.
"""

import os
import datetime as dt

import requests

# ─────────────────────────────────────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────────────────────────────────────
DEPARTEMENTS = ["81", "82", "31", "11", "65"]  # zone Hympyr
CARBURANTS_STATION = ["Gazole", "SP95", "SP98", "E85"]  # dispo dans l'open data station
SEUIL_VARIATION_CENT = 1.0  # variation (c€/L) au-delà de laquelle on signale "a bougé"

# Mots-clés Google Trends (France)
TRENDS_KW = ["prix fioul", "granulés de bois", "GNR"]

# Flux RSS énergie (sources publiques et stables)
RSS_FEEDS = [
    ("Connaissance des Énergies", "https://www.connaissancedesenergies.org/rss.xml"),
    ("Actu-Environnement Énergie", "https://www.actu-environnement.com/ae/rss/news_energie.php4"),
]

HTTP_TIMEOUT = 20
UA = {"User-Agent": "VeilleHympyr/1.0 (interne)"}


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 1 — PRIX CARBURANTS LOCAUX (open data data.economie.gouv.fr, API Explore v2)
# ─────────────────────────────────────────────────────────────────────────────
def prix_carburants_locaux():
    """Prix moyens par carburant sur les départements Hympyr, via l'API Opendatasoft.
    Retourne (lignes:list[dict], erreur:str|None)."""
    base = ("https://data.economie.gouv.fr/api/explore/v2.1/catalog/datasets/"
            "prix-des-carburants-en-france-flux-instantane-v2/records")
    lignes = []
    try:
        for carb in CARBURANTS_STATION:
            # filtre départements : code_departement IN (...)
            deps = ",".join(f'"{d}"' for d in DEPARTEMENTS)
            params = {
                "select": f'avg({carb.lower()}_prix) as moyenne, count(*) as n',
                "where": f'code_departement in ({deps}) and {carb.lower()}_prix is not null',
                "limit": 1,
            }
            r = requests.get(base, params=params, headers=UA, timeout=HTTP_TIMEOUT)
            r.raise_for_status()
            data = r.json()
            res = (data.get("results") or [{}])[0]
            moy = res.get("moyenne")
            n = res.get("n")
            if moy is not None:
                lignes.append({"carburant": carb, "prix": round(float(moy), 3), "stations": n})
        if not lignes:
            return [], "Aucune donnée prix retournée (structure du dataset à revérifier)."
        return lignes, None
    except Exception as e:
        return [], f"Prix carburants indisponibles : {e}"


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 2 — COURS DU BRENT
# ─────────────────────────────────────────────────────────────────────────────
def cours_brent():
    """Dernier cours du Brent via l'API Stooq (CSV public, sans clé).
    Retourne (dict|None, erreur:str|None)."""
    try:
        url = "https://stooq.com/q/l/?s=cb.f&f=sd2t2ohlcv&h&e=csv"
        r = requests.get(url, headers=UA, timeout=HTTP_TIMEOUT)
        r.raise_for_status()
        lignes = r.text.strip().splitlines()
        if len(lignes) < 2:
            return None, "Réponse Brent vide."
        entetes = lignes[0].split(",")
        valeurs = lignes[1].split(",")
        row = dict(zip(entetes, valeurs))
        close = row.get("Close")
        if not close or close.upper() == "N/D":
            return None, "Cours Brent non disponible aujourd'hui (marché fermé ?)."
        return {"close": float(close), "date": row.get("Date", "")}, None
    except Exception as e:
        return None, f"Brent indisponible : {e}"


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 3 — GOOGLE TRENDS
# ─────────────────────────────────────────────────────────────────────────────
def google_trends():
    """Intérêt de recherche (France, 7 derniers jours) pour les mots-clés.
    Utilise pytrends. Retourne (lignes:list[dict], erreur:str|None)."""
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="fr-FR", tz=60)
        pytrends.build_payload(TRENDS_KW, timeframe="now 7-d", geo="FR")
        df = pytrends.interest_over_time()
        if df is None or df.empty:
            return [], "Google Trends n'a rien renvoyé (quota ou indisponibilité)."
        lignes = []
        for kw in TRENDS_KW:
            if kw in df.columns:
                serie = df[kw]
                actuel = int(serie.iloc[-1])
                moyenne = round(float(serie.mean()), 1)
                tendance = "▲" if actuel > moyenne else ("▼" if actuel < moyenne else "→")
                lignes.append({"kw": kw, "actuel": actuel, "moyenne": moyenne, "tendance": tendance})
        return lignes, None
    except Exception as e:
        return [], f"Google Trends indisponible : {e}"


# ─────────────────────────────────────────────────────────────────────────────
# BLOC 4 — ACTUS ÉNERGIE (RSS)
# ─────────────────────────────────────────────────────────────────────────────
def actus_rss(max_par_source=4):
    """Derniers titres des flux RSS énergie. Retourne (lignes:list[dict], erreur:str|None)."""
    try:
        import feedparser
    except Exception as e:
        return [], f"Module feedparser absent : {e}"
    lignes = []
    erreurs = []
    hier = dt.datetime.now() - dt.timedelta(days=2)
    for nom, url in RSS_FEEDS:
        try:
            flux = feedparser.parse(url)
            for entry in flux.entries[:max_par_source]:
                # ne garder que le récent si une date est dispo
                pub = entry.get("published_parsed") or entry.get("updated_parsed")
                if pub:
                    d = dt.datetime(*pub[:6])
                    if d < hier:
                        continue
                lignes.append({"source": nom,
                               "titre": entry.get("title", "(sans titre)"),
                               "lien": entry.get("link", "")})
        except Exception as e:
            erreurs.append(f"{nom}: {e}")
    err = " | ".join(erreurs) if erreurs else None
    return lignes, err


