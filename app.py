"""
CTO Never far away — point d'entrée du projet.

Trois vues partagent le même moteur : le portefeuille d'origine à douze
lignes, sa version élargie à vingt lignes, et une fiche d'analyse détaillée
par valeur inspirée de Baggr.

Lancement :  streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="CTO Never far away",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

navigation = st.navigation(
    [
        st.Page("vues/portefeuille_12.py", title="12 valeurs", icon=":material/monitoring:", default=True),
        st.Page("vues/portefeuille_20.py", title="20 valeurs · ADD++", icon=":material/dashboard:"),
        st.Page("vues/fiche_valeur.py", title="Fiche valeur · Baggr", icon=":material/query_stats:"),
    ]
)
navigation.run()
