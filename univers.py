"""
Univers d'investissement du projet.

Chaque ligne porte son ticker Yahoo, sa devise de cotation et son identité.
Deux clés facultatives :
    anciens : symboles précédents, du plus récent au plus ancien. La série est
              recollée automatiquement (utile après un changement de symbole).
    note    : phrase affichée sous les indicateurs pour expliquer ce recollement.

Rappel sur les devises : Londres cote en pence (GBX), d'où la division par cent
avant conversion en euro. Le reste est coté dans la devise du marché.
"""

from __future__ import annotations

# Roche : le Genussschein « ROG » a cessé de coter le 16 mars 2026, échangé à
# parité contre le bon de participation « ROP » (nouvel ISIN CH1499059983).
# Yahoo a reporté l'intégralité de l'historique sur ROP.SW — vérifié le
# 15/08/2026, 905 séances depuis janvier 2023 — donc aucun recollement n'est
# nécessaire. Si Yahoo venait à repartir de zéro, il suffirait de rétablir
# la clé : "anciens": ["ROG.SW"].
ROCHE = {
    "nom": "Roche Holding", "devise": "CHF", "pays": "Suisse", "secteur": "Santé",
}

UNIVERS_12: dict[str, dict] = {
    "ABT":    {"nom": "Abbott Laboratories",      "devise": "USD", "pays": "États-Unis",  "secteur": "Santé"},
    "GOOGL":  {"nom": "Alphabet A",               "devise": "USD", "pays": "États-Unis",  "secteur": "Technologie"},
    "BRK-B":  {"nom": "Berkshire Hathaway B",     "devise": "USD", "pays": "États-Unis",  "secteur": "Conglomérat"},
    "GTT.PA": {"nom": "Gaztransport & Technigaz", "devise": "EUR", "pays": "France",      "secteur": "Énergie / GNL"},
    "MA":     {"nom": "Mastercard",               "devise": "USD", "pays": "États-Unis",  "secteur": "Paiements"},
    "MIR":    {"nom": "Mirion Technologies",      "devise": "USD", "pays": "États-Unis",  "secteur": "Instrumentation"},
    "NEE":    {"nom": "NextEra Energy",           "devise": "USD", "pays": "États-Unis",  "secteur": "Services aux collectivités"},
    "NOC":    {"nom": "Northrop Grumman",         "devise": "USD", "pays": "États-Unis",  "secteur": "Défense"},
    "RIO.L":  {"nom": "Rio Tinto",                "devise": "GBX", "pays": "Royaume-Uni", "secteur": "Matières premières"},
    "ROP.SW": ROCHE,
    "RR.L":   {"nom": "Rolls-Royce Holdings",     "devise": "GBX", "pays": "Royaume-Uni", "secteur": "Aéronautique"},
    "VIE.PA": {"nom": "Veolia Environnement",     "devise": "EUR", "pays": "France",      "secteur": "Services aux collectivités"},
}

# Les huit ajouts de la version ADD++
AJOUTS_8: dict[str, dict] = {
    "ACS.MC":  {"nom": "ACS",                "devise": "EUR", "pays": "Espagne",     "secteur": "Construction / Concessions",
                # Yahoo a réinitialisé la série de Madrid le 3 août 2026, ne laissant
                # qu'une dizaine de séances. ACSAF est la cotation hors cote américaine
                # de la même action ordinaire : elle sert à reconstituer l'historique
                # antérieur, convertie en euro puis recalée sur les séances communes.
                "reference": {"ticker": "ACSAF", "devise": "USD"},
                "note": "Historique antérieur au 3 août 2026 reconstitué depuis la cotation "
                        "hors cote ACSAF, convertie en euro et recalée sur le recouvrement."},
    "AI.PA":   {"nom": "Air Liquide",        "devise": "EUR", "pays": "France",      "secteur": "Gaz industriels"},
    "BA.L":    {"nom": "BAE Systems",        "devise": "GBX", "pays": "Royaume-Uni", "secteur": "Défense"},
    "ICE":     {"nom": "Intercontinental Exchange", "devise": "USD", "pays": "États-Unis", "secteur": "Infrastructures de marché"},
    "SU.PA":   {"nom": "Schneider Electric", "devise": "EUR", "pays": "France",      "secteur": "Électrification"},
    "STF.PA":  {"nom": "STEF",               "devise": "EUR", "pays": "France",      "secteur": "Logistique du froid"},
    "UBSG.SW": {"nom": "UBS Group",          "devise": "CHF", "pays": "Suisse",      "secteur": "Banque / Gestion de fortune"},
    "WMT":     {"nom": "Walmart",            "devise": "USD", "pays": "États-Unis",  "secteur": "Distribution"},
}

# Ordre d'affichage : les douze d'origine, puis les huit ajouts.
UNIVERS_20: dict[str, dict] = {**UNIVERS_12, **AJOUTS_8}
