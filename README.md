# Veille Hympyr — app Streamlit (rapport à la demande)

App indépendante. Tu ouvres, tu cliques « Générer le rapport », elle collecte
en direct : prix carburants de ta zone, Brent, Google Trends, actus énergie.

## ⚠️ À la demande, PAS automatique
Streamlit ne tourne que quand la page est ouverte. Ce rapport ne se génère donc
que quand TU l'ouvres et cliques. Sa valeur dépend entièrement de ta régularité
à venir le consulter. Si tu ne l'ouvres pas, il n'y a pas de veille.

## Lancement
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Fichiers
- `app.py` : l'interface Streamlit.
- `collecte.py` : les 4 collecteurs de données (prix, Brent, Trends, RSS).
- `requirements.txt` : dépendances.

## Ce qui est fiable / ce qui ne l'est pas
- ✅ Prix carburants routiers (open data DGEC), Brent, RSS énergie.
- ⚠️ Google Trends (pytrends) : librairie non officielle, indisponible certains jours.
- ⚠️ GNR & fioul domestique : PAS dans le flux station, à suivre à la main (base DGEC hebdo).
- ❌ L'app ne fait pas l'analyse : elle donne la matière, l'interprétation reste ton travail.

## Déploiement
En local (`streamlit run`) ou sur Streamlit Cloud. Aucun secret requis
(toutes les sources sont publiques). Attention : sur Streamlit Cloud l'app
s'endort après inactivité — au réveil, un premier chargement plus lent.
