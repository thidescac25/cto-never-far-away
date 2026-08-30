"""
Diagnostic des tickers — à lancer quand une page refuse de se construire.

    python diagnostic.py           # les vingt lignes de la version ADD++
    python diagnostic.py 12        # les douze lignes d'origine
    python diagnostic.py STF.PA ICE UBSG.SW    # des tickers précis

Affiche, pour chaque symbole, la première et la dernière cotation obtenues
depuis Yahoo ainsi que le nombre de séances. Une ligne dont la première
cotation est bien plus tardive que les autres est celle qui tronque la période.
"""

from __future__ import annotations

import sys
from datetime import date, timedelta

import pandas as pd
import yfinance as yf

from univers import UNIVERS_12, UNIVERS_20

DEBUT = date(2023, 1, 1)


def couverture(symboles: list[str], debut: date = DEBUT) -> pd.DataFrame:
    """Interroge Yahoo symbole par symbole et résume ce qui revient."""
    lignes = []
    for symbole in symboles:
        try:
            hist = yf.Ticker(symbole).history(
                start=debut, end=date.today() + timedelta(days=1), auto_adjust=True
            )
            serie = hist["Close"].dropna() if "Close" in hist else pd.Series(dtype="float64")
        except Exception as exc:
            lignes.append({"Ticker": symbole, "Séances": 0, "Première": "—",
                           "Dernière": "—", "Dernier cours": "—", "État": f"échec : {exc}"})
            continue

        if serie.empty:
            lignes.append({"Ticker": symbole, "Séances": 0, "Première": "—",
                           "Dernière": "—", "Dernier cours": "—",
                           "État": "aucune donnée — ticker à revoir"})
            continue

        lignes.append({
            "Ticker": symbole,
            "Séances": len(serie),
            "Première": serie.index[0].strftime("%d/%m/%Y"),
            "Dernière": serie.index[-1].strftime("%d/%m/%Y"),
            "Dernier cours": f"{serie.iloc[-1]:.2f}",
            "État": "ok",
        })
    return pd.DataFrame(lignes)


def main() -> None:
    args = sys.argv[1:]
    if args == ["12"]:
        univers, titre = UNIVERS_12, "les douze lignes d'origine"
    elif args:
        univers, titre = {t: {"nom": t} for t in args}, "les tickers demandés"
    else:
        univers, titre = UNIVERS_20, "les vingt lignes de la version ADD++"

    symboles: list[str] = []
    for ticker, meta in univers.items():
        symboles.append(ticker)
        symboles.extend(meta.get("anciens", []))
        reference = meta.get("reference")
        if reference:
            symboles.append(reference["ticker"])

    print(f"\nCouverture Yahoo depuis le {DEBUT:%d/%m/%Y} — {titre}\n")
    resultat = couverture(list(dict.fromkeys(symboles)))
    print(resultat.to_string(index=False))

    muets = resultat[resultat["Séances"] == 0]["Ticker"].tolist()
    if muets:
        print("\nAucune donnée pour :", ", ".join(muets))
        print("Ces tickers sont à corriger dans univers.py.")

    vivants = resultat[resultat["Séances"] > 0]
    if not vivants.empty:
        tardive = vivants.sort_values("Première", key=lambda s: pd.to_datetime(s, format="%d/%m/%Y")).iloc[-1]
        print(f"\nLigne la plus tardive : {tardive['Ticker']}, première cotation le "
              f"{tardive['Première']}. C'est elle qui fixe le départ commun.")


if __name__ == "__main__":
    main()
