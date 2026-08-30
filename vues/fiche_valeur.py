"""
Page 3 — fiche d'analyse détaillée par valeur, façon Baggr.

Le sélecteur ne porte que sur les douze lignes du portefeuille d'origine
(UNIVERS_12), conformément à la demande : c'est la fiche de chaque
composante du portefeuille de 12 valeurs qui est détaillée ici, pas celle
des huit ajouts de la version ADD++. Le choix de la vue (portefeuille
global vs fiche valeur) se fait via la navigation de la barre latérale ;
le choix de la ligne se fait via ce sélecteur, comme demandé.
"""

import streamlit as st

from stock_page import afficher_fiche
from univers import UNIVERS_12

st.markdown(
    """
    <style>
    .stApp { background: #0E1B2B; }
    .block-container { padding: 2.4rem 3rem 4rem 3rem; max-width: 1560px; }
    @media (max-width: 900px) { .block-container { padding: 2.4rem 1.2rem 3rem 1.2rem; } }
    html, body, [class*="css"] { font-family: 'Inter', 'Segoe UI', sans-serif; }
    #MainMenu, footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

tickers = list(UNIVERS_12)
cle_selection = "ticker_fiche_valeur"
valeur_defaut = st.session_state.get(cle_selection, tickers[0])
index_defaut = tickers.index(valeur_defaut) if valeur_defaut in tickers else 0

col_titre, col_choix = st.columns([2, 1.4], gap="large")
with col_titre:
    st.markdown(
        "<div style='font-size:11px;letter-spacing:.22em;text-transform:uppercase;"
        "color:#D8902A;font-weight:600;margin-bottom:6px;'>Fiche valeur · style Baggr</div>"
        "<h2 style='color:#fff;margin:0 0 4px 0;font-weight:600;'>Analyse détaillée d'une ligne du portefeuille</h2>"
        "<div style='color:#8598A9;font-size:13px;'>Sept angles d'analyse par valeur — quantitatif, "
        "résultats, finances, thèses, société et valorisation — construits sur les données yfinance.</div>",
        unsafe_allow_html=True,
    )
with col_choix:
    ticker = st.selectbox(
        "Choisissez une valeur du portefeuille (12 lignes)",
        options=tickers,
        index=index_defaut,
        format_func=lambda t: f"{UNIVERS_12[t]['nom']} ({t})",
        key=cle_selection,
    )

st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
afficher_fiche(ticker, UNIVERS_12)
