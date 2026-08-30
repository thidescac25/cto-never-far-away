"""
Page 2 — la version élargie du portefeuille, vingt lignes (« ADD++ »).

Reconstitué à l'identique de vues/portefeuille_12.py : ce fichier n'était pas
présent parmi les documents du projet au moment de l'intégration de la fiche
valeur — seul univers.py (qui définit déjà UNIVERS_20) et le README (qui en
décrit l'intitulé) étaient disponibles. Si votre version d'origine portait un
texte d'accroche différent, il suffit de l'ajuster ci-dessous : la mécanique
(afficher() prenant un univers) reste strictement la même.
"""

from datetime import date

from portfolio_page import afficher
from univers import UNIVERS_20

afficher(
    univers=UNIVERS_20,
    titre="CTO Never far away · ADD++",
    accroche="Le même socle de qualité, élargi à huit nouvelles franchises — "
             "construction et concessions, gaz industriels, infrastructures de "
             "marché — pour diluer davantage le risque idiosyncratique.",
    eyebrow="Compte-titres ordinaire",
    depart_defaut=date(2023, 1, 1),
)
