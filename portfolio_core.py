"""
Coeur de calcul du portefeuille « CTO Never far away ».

Ce module ne dépend que de numpy / pandas : aucune dépendance à Streamlit ni à
yfinance, ce qui le rend testable unitairement et réutilisable.

Conventions :
    - toutes les séries de prix sont indexées par un DatetimeIndex naïf (sans tz),
      trié, sans doublon ;
    - les taux de change sont exprimés « unités de devise étrangère pour 1 EUR »
      (convention Yahoo : EURUSD=X, EURGBP=X, EURCHF=X) ;
    - les cours des valeurs britanniques cotées à Londres sont fournis par Yahoo
      en pence (GBX) : ils sont divisés par 100 avant conversion.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

TRADING_DAYS = 252
PENCE_PER_POUND = 100.0

# Fréquences de rééquilibrage proposées dans l'interface -> alias pandas Period
REBALANCE_FREQ = {
    "Mensuel": "M",
    "Trimestriel": "Q",
    "Annuel": "Y",
}


# --------------------------------------------------------------------------- #
# Nettoyage et conversion de devise
# --------------------------------------------------------------------------- #
def clean_prices(close: pd.DataFrame) -> pd.DataFrame:
    """Trie l'index, retire les doublons, supprime les colonnes entièrement vides."""
    if close is None or close.empty:
        return pd.DataFrame()

    out = close.copy()
    out.index = pd.to_datetime(out.index)
    if getattr(out.index, "tz", None) is not None:
        out.index = out.index.tz_localize(None)
    out = out[~out.index.duplicated(keep="last")].sort_index()
    out = out.dropna(axis=1, how="all")
    return out


def convert_to_eur(
    close: pd.DataFrame,
    fx: pd.DataFrame,
    currencies: dict[str, str],
) -> pd.DataFrame:
    """
    Convertit un tableau de cours en euros.

    Args:
        close: cours de clôture ajustés, une colonne par ticker.
        fx: colonnes 'EURUSD', 'EURGBP', 'EURCHF' (devise étrangère pour 1 EUR).
        currencies: ticker -> devise de cotation ('EUR', 'USD', 'GBP', 'GBX', 'CHF').

    Returns:
        DataFrame de mêmes dimensions, exprimé en EUR.
    """
    if close.empty:
        return close

    rates = fx.reindex(close.index).ffill().bfill() if not fx.empty else pd.DataFrame(index=close.index)
    out = pd.DataFrame(index=close.index)

    for ticker in close.columns:
        devise = currencies.get(ticker, "EUR").upper()
        serie = close[ticker].astype("float64")

        if devise == "GBX":
            serie = serie / PENCE_PER_POUND
            devise = "GBP"

        if devise == "EUR":
            out[ticker] = serie
            continue

        paire = f"EUR{devise}"
        if paire in rates.columns:
            taux = rates[paire].replace(0.0, np.nan)
            out[ticker] = serie / taux
        else:  # pas de taux disponible : on conserve la série brute
            out[ticker] = serie

    return out


def splice_history(
    close: pd.DataFrame, chaine: list[str]
) -> tuple[pd.Series | None, list[str]]:
    """
    Reconstitue une ligne dont le symbole a changé au fil du temps.

    La chaîne est donnée du plus récent au plus ancien. Chaque symbole comble
    les dates que le précédent ne couvre pas, ce qui suppose un échange à parité
    (aucun ajustement de niveau n'est appliqué). Renvoie la série et la liste
    des symboles réellement utilisés.
    """
    utilises = [t for t in chaine if t in close.columns and not close[t].dropna().empty]
    if not utilises:
        return None, []

    serie = close[utilises[0]].copy()
    for suivant in utilises[1:]:
        serie = serie.combine_first(close[suivant])
    return serie.dropna(), utilises


def splice_gap(close: pd.DataFrame, recent: str, ancien: str) -> float | None:
    """
    Écart de cours à la jonction entre deux symboles successifs, en %.

    Sert de garde-fou : un échange à parité doit produire un écart proche de
    zéro entre la dernière cotation de l'ancien titre et la première du nouveau.
    """
    if recent not in close.columns or ancien not in close.columns:
        return None
    a, b = close[ancien].dropna(), close[recent].dropna()
    if a.empty or b.empty:
        return None
    derniere = a[a.index < b.index[0]]
    if derniere.empty or derniere.iloc[-1] == 0:
        return None
    return float(b.iloc[0] / derniere.iloc[-1] - 1.0) * 100.0
def extend_with_reference(
    principale: pd.Series,
    reference: pd.Series,
    recouvrement_minimum: int = 5,
) -> tuple[pd.Series, float | None, int, float]:
    """
    Prolonge vers le passé une série écourtée, à l'aide d'une autre cotation
    du même titre (place étrangère, ADR, hors cote).

    Contrairement à splice_history, les deux séries ne sont pas supposées être
    au même niveau : le facteur d'échelle est estimé sur la période où elles
    coexistent, en prenant la médiane des rapports quotidiens — insensible aux
    décalages ponctuels d'horaires de clôture. Les deux séries doivent être
    exprimées dans la même devise.

    Returns:
        (série prolongée, facteur appliqué, nombre de séances de recouvrement,
         dispersion relative des rapports en %). Le facteur vaut None et la
        série est renvoyée inchangée si le recouvrement est insuffisant.
    """
    p = principale.dropna()
    r = reference.dropna()
    if p.empty or r.empty:
        return principale, None, 0, 0.0

    commun = p.index.intersection(r.index)
    if len(commun) < recouvrement_minimum:
        return principale, None, len(commun), 0.0

    rapports = (p.loc[commun] / r.loc[commun]).replace([np.inf, -np.inf], np.nan).dropna()
    if rapports.empty or rapports.median() <= 0:
        return principale, None, len(commun), 0.0

    facteur = float(rapports.median())
    dispersion = float(rapports.std(ddof=0) / facteur * 100.0) if len(rapports) > 1 else 0.0
    prolongee = p.combine_first(r * facteur).dropna()
    return prolongee, facteur, len(commun), dispersion


def trim_to_full_coverage(prices: pd.DataFrame) -> pd.DataFrame:
    """
    Restreint l'historique à la période où *toutes* les colonnes cotent.

    Les trous ponctuels (jours fériés locaux d'une place) sont comblés par report
    de la dernière cotation connue ; en revanche l'historique ne démarre qu'à la
    date à laquelle la valeur la plus jeune du panier dispose d'une cotation.
    """
    if prices.empty:
        return prices

    filled = prices.ffill()
    debuts = [filled[c].first_valid_index() for c in filled.columns]
    debuts = [d for d in debuts if d is not None]
    if not debuts:
        return pd.DataFrame()

    return filled.loc[max(debuts):].dropna(axis=0, how="any")


def limiting_ticker(prices: pd.DataFrame) -> tuple[str | None, pd.Timestamp | None]:
    """Renvoie le ticker qui contraint la date de départ, et cette date."""
    if prices.empty:
        return None, None
    debuts = {c: prices[c].first_valid_index() for c in prices.columns}
    debuts = {c: d for c, d in debuts.items() if d is not None}
    if not debuts:
        return None, None
    ticker = max(debuts, key=lambda c: debuts[c])
    return ticker, debuts[ticker]


# --------------------------------------------------------------------------- #
# Construction du portefeuille
# --------------------------------------------------------------------------- #
@dataclass
class Position:
    ticker: str
    parts: float
    prix_initial: float
    prix_final: float
    montant_initial: float
    montant_final: float

    @property
    def performance(self) -> float:
        return self.prix_final / self.prix_initial - 1.0 if self.prix_initial else 0.0

    @property
    def plus_value(self) -> float:
        return self.montant_final - self.montant_initial


def buy_and_hold(prices: pd.DataFrame, capital: float) -> tuple[pd.Series, list[Position]]:
    """
    Achat initial équipondéré, puis aucune intervention (fractions d'actions
    autorisées pour éviter le biais d'arrondi sur les cours élevés).
    """
    if prices.empty:
        return pd.Series(dtype="float64"), []

    n = prices.shape[1]
    montant_ligne = capital / n
    p0 = prices.iloc[0]
    parts = montant_ligne / p0

    valeurs = prices.mul(parts, axis=1)
    positions = [
        Position(
            ticker=t,
            parts=float(parts[t]),
            prix_initial=float(p0[t]),
            prix_final=float(prices[t].iloc[-1]),
            montant_initial=float(montant_ligne),
            montant_final=float(valeurs[t].iloc[-1]),
        )
        for t in prices.columns
    ]
    return valeurs.sum(axis=1), positions


def rebalanced(
    prices: pd.DataFrame, capital: float, freq: str = "M", detail: bool = False
) -> pd.Series | tuple[pd.Series, pd.DataFrame]:
    """
    Portefeuille équipondéré rééquilibré à chaque changement de période.

    Le rééquilibrage est appliqué à la clôture du dernier jour de la période :
    les poids reviennent à 1/n avant la première performance de la période
    suivante, ce qui évite de « perdre » le rendement du jour de bascule.

    Args:
        detail: si vrai, renvoie aussi la valeur quotidienne de chaque ligne.
    """
    if prices.empty:
        vide = pd.Series(dtype="float64")
        return (vide, pd.DataFrame()) if detail else vide

    rendements = prices.pct_change().fillna(0.0).to_numpy()
    periodes = prices.index.to_period(freq)
    n = prices.shape[1]

    valeurs = np.empty(len(prices), dtype="float64")
    poids_hist = np.empty((len(prices), n), dtype="float64")
    poids = np.full(n, 1.0 / n)
    valeur = float(capital)
    valeurs[0] = valeur
    poids_hist[0] = poids
    periode_courante = periodes[0]

    for i in range(1, len(prices)):
        if periodes[i] != periode_courante:
            poids = np.full(n, 1.0 / n)
            periode_courante = periodes[i]
        brut = 1.0 + rendements[i]
        croissance = float(poids @ brut)
        if croissance <= 0 or not np.isfinite(croissance):
            croissance = 1.0
        valeur *= croissance
        poids = poids * brut / croissance
        valeurs[i] = valeur
        poids_hist[i] = poids

    total = pd.Series(valeurs, index=prices.index, name="Portefeuille")
    if not detail:
        return total

    lignes = pd.DataFrame(
        poids_hist * valeurs[:, None], index=prices.index, columns=prices.columns
    )
    return total, lignes


def base_100(serie: pd.Series) -> pd.Series:
    """Rebase une série sur 100 à sa première valeur valide."""
    serie = serie.dropna()
    if serie.empty or serie.iloc[0] == 0:
        return serie
    return serie / serie.iloc[0] * 100.0


def drawdown(serie: pd.Series) -> pd.Series:
    """Perte relative par rapport au plus haut historique, en %."""
    if serie.empty:
        return serie
    return (serie / serie.cummax() - 1.0) * 100.0


# --------------------------------------------------------------------------- #
# Mesures de performance et de risque
# --------------------------------------------------------------------------- #
def annees(serie: pd.Series) -> float:
    if len(serie) < 2:
        return 0.0
    return (serie.index[-1] - serie.index[0]).days / 365.25


def compute_metrics(serie: pd.Series, taux_sans_risque: float = 0.0) -> dict[str, float]:
    """Indicateurs standards calculés sur une série de valeur liquidative."""
    vide = {
        "perf_totale": 0.0, "tcac": 0.0, "volatilite": 0.0, "sharpe": 0.0,
        "max_drawdown": 0.0, "calmar": 0.0, "meilleur_jour": 0.0,
        "pire_jour": 0.0, "mois_positifs": 0.0, "valeur_finale": 0.0,
    }
    serie = serie.dropna()
    if len(serie) < 2 or serie.iloc[0] <= 0:
        return vide

    duree = annees(serie)
    perf_totale = serie.iloc[-1] / serie.iloc[0] - 1.0
    tcac = (serie.iloc[-1] / serie.iloc[0]) ** (1.0 / duree) - 1.0 if duree > 0.08 else perf_totale

    rendements = serie.pct_change().dropna()
    volatilite = float(rendements.std(ddof=1) * np.sqrt(TRADING_DAYS)) if len(rendements) > 2 else 0.0
    sharpe = (tcac - taux_sans_risque) / volatilite if volatilite > 0 else 0.0

    dd = drawdown(serie)
    max_dd = float(dd.min()) if not dd.empty else 0.0
    calmar = tcac / abs(max_dd / 100.0) if max_dd < 0 else 0.0

    mensuel = serie.resample("ME").last().pct_change().dropna()
    mois_positifs = float((mensuel > 0).mean() * 100.0) if len(mensuel) else 0.0

    return {
        "perf_totale": float(perf_totale * 100.0),
        "tcac": float(tcac * 100.0),
        "volatilite": float(volatilite * 100.0),
        "sharpe": float(sharpe),
        "max_drawdown": max_dd,
        "calmar": float(calmar),
        "meilleur_jour": float(rendements.max() * 100.0) if len(rendements) else 0.0,
        "pire_jour": float(rendements.min() * 100.0) if len(rendements) else 0.0,
        "mois_positifs": mois_positifs,
        "valeur_finale": float(serie.iloc[-1]),
    }


def relative_metrics(portefeuille: pd.Series, indice: pd.Series) -> dict[str, float]:
    """Bêta, corrélation, tracking error et ratio d'information face à un indice."""
    vide = {"beta": np.nan, "correlation": np.nan, "tracking_error": np.nan,
            "information_ratio": np.nan, "surperformance": np.nan}

    rp = portefeuille.pct_change().dropna()
    ri = indice.pct_change().dropna()
    commun = rp.index.intersection(ri.index)
    if len(commun) < 20:
        return vide

    rp, ri = rp.loc[commun], ri.loc[commun]
    variance = float(ri.var(ddof=1))
    beta = float(np.cov(rp, ri, ddof=1)[0, 1] / variance) if variance > 0 else np.nan
    correlation = float(rp.corr(ri))

    ecart = rp - ri
    tracking_error = float(ecart.std(ddof=1) * np.sqrt(TRADING_DAYS))
    information_ratio = float(ecart.mean() * TRADING_DAYS / tracking_error) if tracking_error > 0 else np.nan

    p = portefeuille.dropna()
    i = indice.dropna()
    surperformance = float(
        (p.iloc[-1] / p.iloc[0] - 1.0) - (i.iloc[-1] / i.iloc[0] - 1.0)
    ) * 100.0

    return {
        "beta": beta,
        "correlation": correlation,
        "tracking_error": tracking_error * 100.0,
        "information_ratio": information_ratio,
        "surperformance": surperformance,
    }


def annual_returns(serie: pd.Series) -> pd.Series:
    """Performance par année civile, en %."""
    serie = serie.dropna()
    if len(serie) < 2:
        return pd.Series(dtype="float64")

    fin_annee = serie.resample("YE").last()
    debut = pd.Series([serie.iloc[0]], index=[serie.index[0]])
    complet = pd.concat([debut, fin_annee]).sort_index()
    complet = complet[~complet.index.duplicated(keep="first")]
    perfs = complet.pct_change().dropna() * 100.0
    perfs.index = perfs.index.year
    return perfs


def contributions(positions: list[Position], capital: float) -> pd.DataFrame:
    """Contribution de chaque ligne à la performance globale (buy & hold)."""
    if not positions or capital <= 0:
        return pd.DataFrame()

    lignes = [
        {
            "Ticker": p.ticker,
            "Performance (%)": p.performance * 100.0,
            "Plus-value (€)": p.plus_value,
            "Contribution (pts)": p.plus_value / capital * 100.0,
            "Valeur finale (€)": p.montant_final,
            "Poids final (%)": 0.0,
        }
        for p in positions
    ]
    df = pd.DataFrame(lignes)
    total = df["Valeur finale (€)"].sum()
    if total > 0:
        df["Poids final (%)"] = df["Valeur finale (€)"] / total * 100.0
    return df.sort_values("Contribution (pts)", ascending=False).reset_index(drop=True)
