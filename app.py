# -*- coding: utf-8 -*-
"""
app.py — Veille Hympyr Énergies (rapport à la demande)
-------------------------------------------------------
App Streamlit indépendante. Tu ouvres, tu cliques « Générer le rapport »,
elle va chercher les données en direct et les affiche.

⚠️ Ce n'est PAS de la veille automatisée : rien ne tourne tant que tu n'ouvres pas
l'app. C'est un rapport À LA DEMANDE. Sa valeur dépend de ta régularité à l'ouvrir.

Lancement :
    pip install -r requirements.txt
    streamlit run app.py
"""

import datetime as dt
import streamlit as st

import collecte  # module de collecte réutilisé (prix, Brent, Trends, RSS)

VERT, VERT_FONCE, ORANGE = "#1A6B45", "#0D3D27", "#FF5C29"

st.set_page_config(page_title="Veille Hympyr", page_icon="🛢️", layout="centered")

st.markdown(f"""
<style>
  h1, h2, h3 {{ color: {VERT_FONCE}; }}
  .stButton>button {{ border-radius: 8px; font-weight: 600; background: {VERT}; color: #fff; }}
  .src-note {{ font-size: 12px; color: #9aa8a2; }}
</style>
""", unsafe_allow_html=True)

st.title("🛢️ Veille Hympyr Énergies")
st.caption("Rapport à la demande — prix carburants (ta zone), Brent, Google Trends, actus énergie.")

# Mise en cache 30 min : évite de retaper les API à chaque clic dans la même session
@st.cache_data(ttl=1800, show_spinner=False)
def collecter():
    prix, prix_err = collecte.prix_carburants_locaux()
    brent, brent_err = collecte.cours_brent()
    trends, trends_err = collecte.google_trends()
    actus, actus_err = collecte.actus_rss()
    return {
        "prix": (prix, prix_err), "brent": (brent, brent_err),
        "trends": (trends, trends_err), "actus": (actus, actus_err),
        "genere_le": dt.datetime.now(),
    }

col1, col2 = st.columns([1, 2])
with col1:
    lancer = st.button("🔄 Générer le rapport", use_container_width=True)
with col2:
    if st.button("Vider le cache et régénérer", use_container_width=True):
        st.cache_data.clear()
        lancer = True

if not lancer and "deja_genere" not in st.session_state:
    st.info("Clique sur « Générer le rapport » pour lancer la collecte en direct.")
    st.stop()

st.session_state.deja_genere = True

with st.spinner("Collecte des données en direct…"):
    data = collecter()

st.caption(f"Généré le {data['genere_le']:%d/%m/%Y à %H:%M} · "
           f"départements {', '.join(collecte.DEPARTEMENTS)}")

# ── BLOC 1 : PRIX ──────────────────────────────────────────────────────────
st.subheader("💶 Prix carburants (ta zone)")
prix, prix_err = data["prix"]
if prix_err:
    st.warning(prix_err)
else:
    cols = st.columns(len(prix))
    for c, p in zip(cols, prix):
        c.metric(p["carburant"], f'{p["prix"]:.3f} €/L', help=f'{p["stations"]} stations')

# ── BLOC 2 : BRENT ─────────────────────────────────────────────────────────
st.subheader("🛢️ Cours du Brent")
brent, brent_err = data["brent"]
if brent_err:
    st.warning(brent_err)
else:
    st.metric("Brent", f'{brent["close"]:.2f} $', help=f'Cotation du {brent["date"]}')

# ── BLOC 3 : GOOGLE TRENDS ─────────────────────────────────────────────────
st.subheader("🔍 Google Trends (France, 7 jours)")
trends, trends_err = data["trends"]
if trends_err:
    st.warning(trends_err)
else:
    cols = st.columns(len(trends))
    for c, t in zip(cols, trends):
        c.metric(f'{t["tendance"]} {t["kw"]}', t["actuel"], help=f'Moyenne 7j : {t["moyenne"]}')

# ── BLOC 4 : ACTUS RSS ─────────────────────────────────────────────────────
st.subheader("📰 Actus énergie")
actus, actus_err = data["actus"]
if actus_err and not actus:
    st.warning(actus_err)
elif not actus:
    st.info("Rien de neuf dans les dernières 48 h.")
else:
    for a in actus:
        st.markdown(f'- [{a["titre"]}]({a["lien"]}) — *{a["source"]}*')

st.divider()
st.markdown(
    '<p class="src-note">GNR &amp; fioul domestique ne sont pas dans le flux station '
    '(à suivre manuellement sur la base DGEC hebdo). Ce rapport donne la matière — '
    'l\'analyse « qu\'est-ce que ça change pour Hympyr » reste ton travail.</p>',
    unsafe_allow_html=True)
