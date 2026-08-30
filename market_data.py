"""
Couche d'accès aux données de marché pour les fiches valeur (style Baggr).

Principe : toutes les fonctions de récupération sont mises en cache via
`@st.cache_data` et ne laissent jamais remonter d'exception à l'appelant.
En cas de donnée manquante, de ticker inconnu ou d'échec réseau, elles
renvoient une structure vide (dict/DataFrame/Series vides) que les fonctions
d'affichage de `stock_page.py` savent traduire en repli élégant plutôt qu'en
page cassée — conformément à la consigne de gérer les trous de données
yfinance sans faire planter l'application.

Aucune fonction ici ne dépend de Streamlit pour le calcul : seule la mise en
cache utilise `st.cache_data`, ce qui garde la couche de calcul testable.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

# --------------------------------------------------------------------------- #
# Durées de cache — les données fondamentales changent rarement, les cours
# beaucoup plus souvent.
# --------------------------------------------------------------------------- #
TTL_INFO = 3600            # 1 h  : identité, secteur, description, ratios courants
TTL_PRIX = 300             # 5 min : cours et historique de prix
TTL_ETATS = 6 * 3600       # 6 h  : comptes annuels / trimestriels
TTL_ANALYSTES = 3600       # 1 h  : notes, objectifs de cours, surprises d'EPS

RISK_FREE_DEFAUT = 4.0     # taux sans risque (%) utilisé à défaut pour le WACC
PRIME_MARCHE_DEFAUT = 5.0  # prime de risque actions (%) par défaut


# --------------------------------------------------------------------------- #
# 1. Récupération brute (mise en cache, jamais d'exception)
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=TTL_INFO, show_spinner=False)
def get_info(ticker: str) -> dict:
    """Fiche d'identité et ratios instantanés (yf.Ticker.info)."""
    try:
        t = yf.Ticker(ticker)
        info = t.get_info()
        return dict(info) if info else {}
    except Exception:
        return {}


@st.cache_data(ttl=TTL_PRIX, show_spinner=False)
def get_historique(ticker: str, periode: str = "10y") -> pd.DataFrame:
    """Historique de cours (colonnes Open/High/Low/Close/Volume), ajusté."""
    try:
        hist = yf.Ticker(ticker).history(period=periode, auto_adjust=True)
        if hist is None or hist.empty:
            return pd.DataFrame()
        hist = hist.copy()
        hist.index = pd.to_datetime(hist.index)
        if getattr(hist.index, "tz", None) is not None:
            hist.index = hist.index.tz_localize(None)
        return hist
    except Exception:
        return pd.DataFrame()


def _ordonner_colonnes(df: pd.DataFrame) -> pd.DataFrame:
    """Trie les colonnes (des exercices) de la plus ancienne à la plus récente."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    try:
        return df[sorted(df.columns, key=lambda c: pd.Timestamp(c))]
    except Exception:
        return df


@st.cache_data(ttl=TTL_ETATS, show_spinner=False)
def get_etats_financiers(ticker: str) -> dict[str, pd.DataFrame]:
    """
    Comptes de résultat, bilans et flux de trésorerie, annuels et trimestriels.

    yfinance change régulièrement le nom de ses attributs (`financials` puis
    `income_stmt`, etc.) : chaque bloc est isolé dans son propre `try/except`
    pour qu'un attribut manquant sur une version donnée n'empêche pas de
    récupérer les autres.
    """
    t = yf.Ticker(ticker)
    cles = {
        "compte_resultat": "income_stmt",
        "compte_resultat_t": "quarterly_income_stmt",
        "bilan": "balance_sheet",
        "bilan_t": "quarterly_balance_sheet",
        "flux": "cashflow",
        "flux_t": "quarterly_cashflow",
    }
    resultat: dict[str, pd.DataFrame] = {}
    for cle, attribut in cles.items():
        try:
            df = getattr(t, attribut, None)
            resultat[cle] = _ordonner_colonnes(df)
        except Exception:
            resultat[cle] = pd.DataFrame()
    return resultat


@st.cache_data(ttl=TTL_ANALYSTES, show_spinner=False)
def get_donnees_analystes(ticker: str) -> dict:
    """Objectifs de cours, recommandations, surprises d'EPS, prévisions."""
    t = yf.Ticker(ticker)
    donnees: dict = {}

    try:
        cibles = t.analyst_price_targets
        donnees["cibles"] = dict(cibles) if cibles else {}
    except Exception:
        donnees["cibles"] = {}

    try:
        reco = t.recommendations
        donnees["recommandations"] = reco.copy() if isinstance(reco, pd.DataFrame) else pd.DataFrame()
    except Exception:
        donnees["recommandations"] = pd.DataFrame()

    try:
        dates = t.get_earnings_dates(limit=12)
        donnees["surprises_eps"] = dates.copy() if isinstance(dates, pd.DataFrame) else pd.DataFrame()
    except Exception:
        donnees["surprises_eps"] = pd.DataFrame()

    for cle, attribut in [
        ("prevision_ca", "revenue_estimate"),
        ("prevision_eps", "earnings_estimate"),
        ("croissance_est", "growth_estimates"),
    ]:
        try:
            df = getattr(t, attribut, None)
            donnees[cle] = df.copy() if isinstance(df, pd.DataFrame) else pd.DataFrame()
        except Exception:
            donnees[cle] = pd.DataFrame()

    return donnees


@st.cache_data(ttl=TTL_ANALYSTES, show_spinner=False)
def get_repartition_activite(ticker: str) -> dict[str, pd.Series]:
    """
    Répartition du chiffre d'affaires par segment et par zone géographique.

    Cette information n'est disponible sur Yahoo Finance que pour une minorité
    de valeurs (essentiellement les grandes capitalisations américaines) :
    l'appelant doit prévoir un repli quand les deux séries reviennent vides.
    """
    t = yf.Ticker(ticker)
    sortie: dict[str, pd.Series] = {"segments": pd.Series(dtype="float64"), "geographie": pd.Series(dtype="float64")}
    try:
        segments = getattr(t, "revenue_segments", None) or getattr(t, "segments", None)
        if isinstance(segments, pd.DataFrame) and not segments.empty:
            derniere = segments.iloc[:, -1]
            sortie["segments"] = derniere[derniere > 0]
    except Exception:
        pass
    try:
        geo = getattr(t, "geographic_segments", None) or getattr(t, "revenue_by_geography", None)
        if isinstance(geo, pd.DataFrame) and not geo.empty:
            derniere = geo.iloc[:, -1]
            sortie["geographie"] = derniere[derniere > 0]
    except Exception:
        pass
    return sortie


# --------------------------------------------------------------------------- #
# 2. Lecture tolérante des lignes d'un état financier
# --------------------------------------------------------------------------- #
# Chaque ligne comptable peut porter un nom différent selon le référentiel
# d'origine de la société (US GAAP, IFRS) : on tente plusieurs alias connus.
ALIAS_LIGNES = {
    "revenu": ["Total Revenue", "TotalRevenue", "Operating Revenue"],
    "cout_des_ventes": ["Cost Of Revenue", "CostOfRevenue"],
    "marge_brute": ["Gross Profit", "GrossProfit"],
    "resultat_exploitation": ["Operating Income", "OperatingIncome", "EBIT"],
    "ebitda": ["EBITDA", "Normalized EBITDA"],
    "resultat_net": ["Net Income", "NetIncome", "Net Income Common Stockholders"],
    "impots": ["Tax Provision", "IncomeTaxExpense"],
    "resultat_avant_impots": ["Pretax Income", "PretaxIncome"],
    "interets_charges": ["Interest Expense", "InterestExpense"],
    "eps_dilue": ["Diluted EPS", "DilutedEPS"],

    "tresorerie": ["Cash And Cash Equivalents", "CashAndCashEquivalents", "Cash Cash Equivalents And Short Term Investments"],
    "dette_totale": ["Total Debt", "TotalDebt"],
    "dette_court_terme": ["Current Debt", "CurrentDebt"],
    "dette_long_terme": ["Long Term Debt", "LongTermDebt"],
    "actifs_totaux": ["Total Assets", "TotalAssets"],
    "passifs_courants": ["Current Liabilities", "CurrentLiabilities", "Total Current Liabilities"],
    "capitaux_propres": ["Stockholders Equity", "Total Equity Gross Minority Interest", "StockholdersEquity"],
    "actions_en_circulation": ["Ordinary Shares Number", "Share Issued", "OrdinarySharesNumber"],
    "goodwill": ["Goodwill"],

    "flux_exploitation": ["Operating Cash Flow", "OperatingCashFlow", "Cash Flow From Continuing Operating Activities"],
    "capex": ["Capital Expenditure", "CapitalExpenditure", "Purchase Of PPE"],
    "fcf": ["Free Cash Flow", "FreeCashFlow"],
    "rd": ["Research And Development", "ResearchAndDevelopment"],
    "remuneration_actions": ["Stock Based Compensation", "StockBasedCompensation"],
    "dividendes_verses": ["Cash Dividends Paid", "CommonStockDividendPaid"],
    "rachats_actions": ["Repurchase Of Capital Stock", "RepurchaseOfCapitalStock"],
}


def ligne(df: pd.DataFrame, cle: str) -> pd.Series:
    """Renvoie la ligne comptable `cle` (voir ALIAS_LIGNES), triée par date, en float."""
    if df is None or not isinstance(df, pd.DataFrame) or df.empty:
        return pd.Series(dtype="float64")
    index_normalise = {str(i).strip().lower(): i for i in df.index}
    for alias in ALIAS_LIGNES.get(cle, [cle]):
        trouve = index_normalise.get(alias.strip().lower())
        if trouve is not None:
            serie = df.loc[trouve]
            if isinstance(serie, pd.DataFrame):  # doublon d'étiquette : on garde la 1re occurrence
                serie = serie.iloc[0]
            return pd.to_numeric(serie, errors="coerce").sort_index()
    return pd.Series(dtype="float64")


def libelles_exercices(df: pd.DataFrame) -> list[str]:
    """Étiquettes d'exercice courtes ('FY21', ..., 'FY25') à partir des colonnes datées."""
    if df is None or df.empty:
        return []
    return [f"FY{pd.Timestamp(c).year % 100:02d}" for c in df.columns]


# --------------------------------------------------------------------------- #
# 3. Mesures dérivées : performance, CAGR, marges, retours sur capitaux
# --------------------------------------------------------------------------- #
def performance_totale(serie: pd.Series) -> float | None:
    s = serie.dropna()
    if len(s) < 2 or s.iloc[0] == 0 or not np.isfinite(s.iloc[0]):
        return None
    return float((s.iloc[-1] / s.iloc[0] - 1.0) * 100.0)


def cagr(serie: pd.Series) -> float | None:
    """Taux de croissance annuel composé sur la période couverte par la série."""
    s = serie.dropna()
    if len(s) < 2:
        return None
    n = len(s) - 1
    debut, fin = s.iloc[0], s.iloc[-1]
    if debut <= 0 or fin <= 0 or n <= 0:
        return None
    return float((fin / debut) ** (1.0 / n) - 1.0) * 100.0


def cagr_sur(serie: pd.Series, n_dernieres: int) -> float | None:
    """CAGR calculé sur les `n_dernieres` valeurs seulement (ex. 5 dernières années)."""
    s = serie.dropna()
    if len(s) < 2:
        return None
    return cagr(s.iloc[-min(n_dernieres + 1, len(s)):])


def predictibilite_ca(revenu: pd.Series) -> float | None:
    """
    Régularité de la croissance du chiffre d'affaires, en %.

    100 % = croissance parfaitement linéaire d'une année sur l'autre, 0 % =
    croissance erratique. Calculée comme l'inverse du coefficient de variation
    des taux de croissance annuels, borné à [0, 100].
    """
    s = revenu.dropna()
    if len(s) < 4:
        return None
    croissances = s.pct_change().dropna()
    if len(croissances) < 3 or croissances.mean() == 0:
        return None
    dispersion = float(croissances.std(ddof=0) / abs(croissances.mean()))
    return float(np.clip(100.0 - dispersion * 100.0, 0.0, 100.0))


def construire_indicateurs(etats: dict[str, pd.DataFrame], info: dict) -> pd.DataFrame:
    """
    Assemble un tableau annuel unique (une colonne par exercice) avec les
    lignes brutes utiles et les ratios qui s'en déduisent : marges, ROE,
    ROIC, ROCE, WACC estimé. Toute ligne indisponible reste à NaN plutôt que
    de faire échouer le calcul des autres.
    """
    cr, bilan, flux = etats.get("compte_resultat"), etats.get("bilan"), etats.get("flux")
    colonnes = cr.columns if isinstance(cr, pd.DataFrame) and not cr.empty else pd.Index([])
    idx = pd.Index(sorted(colonnes, key=lambda c: pd.Timestamp(c))) if len(colonnes) else pd.Index([])

    out = pd.DataFrame(index=idx)
    out["revenu"] = ligne(cr, "revenu").reindex(idx)
    out["marge_brute_val"] = ligne(cr, "marge_brute").reindex(idx)
    out["resultat_exploitation"] = ligne(cr, "resultat_exploitation").reindex(idx)
    out["resultat_net"] = ligne(cr, "resultat_net").reindex(idx)
    out["impots"] = ligne(cr, "impots").reindex(idx)
    out["resultat_avant_impots"] = ligne(cr, "resultat_avant_impots").reindex(idx)
    out["interets_charges"] = ligne(cr, "interets_charges").reindex(idx)

    out["tresorerie"] = ligne(bilan, "tresorerie").reindex(idx)
    out["dette_totale"] = ligne(bilan, "dette_totale").reindex(idx)
    out["actifs_totaux"] = ligne(bilan, "actifs_totaux").reindex(idx)
    out["passifs_courants"] = ligne(bilan, "passifs_courants").reindex(idx)
    out["capitaux_propres"] = ligne(bilan, "capitaux_propres").reindex(idx)
    out["actions_en_circulation"] = ligne(bilan, "actions_en_circulation").reindex(idx)
    out["goodwill"] = ligne(bilan, "goodwill").reindex(idx)

    out["flux_exploitation"] = ligne(flux, "flux_exploitation").reindex(idx)
    out["capex"] = ligne(flux, "capex").reindex(idx)
    out["fcf"] = ligne(flux, "fcf").reindex(idx)
    if out["fcf"].isna().all() and not out["flux_exploitation"].isna().all():
        out["fcf"] = out["flux_exploitation"] + out["capex"].fillna(0.0)  # capex déjà négatif chez yfinance
    out["rd"] = ligne(flux, "rd").reindex(idx)
    out["remuneration_actions"] = ligne(flux, "remuneration_actions").reindex(idx)

    # ---- Marges (%) ----
    out["marge_brute"] = out["marge_brute_val"] / out["revenu"] * 100.0
    out["marge_operationnelle"] = out["resultat_exploitation"] / out["revenu"] * 100.0
    out["marge_nette"] = out["resultat_net"] / out["revenu"] * 100.0
    out["marge_fcf"] = out["fcf"] / out["revenu"] * 100.0

    # ---- Retours sur capitaux (%) ----
    capital_investi = out["capitaux_propres"].fillna(0.0) + out["dette_totale"].fillna(0.0) - out["tresorerie"].fillna(0.0)
    taux_impot = (out["impots"] / out["resultat_avant_impots"]).clip(0.0, 0.6)
    taux_impot = taux_impot.fillna(taux_impot.mean() if taux_impot.notna().any() else 0.22)
    nopat = out["resultat_exploitation"] * (1.0 - taux_impot)

    out["roe"] = out["resultat_net"] / out["capitaux_propres"] * 100.0
    out["roic"] = nopat / capital_investi.replace(0.0, np.nan) * 100.0
    out["roce"] = out["resultat_exploitation"] / (out["actifs_totaux"] - out["passifs_courants"]).replace(0.0, np.nan) * 100.0

    # ---- Dette nette / EBITDA ----
    ebitda = out["resultat_exploitation"]  # approximation en l'absence de ligne EBITDA dédiée
    out["dette_nette"] = out["dette_totale"] - out["tresorerie"]
    out["dette_nette_ebitda"] = out["dette_nette"] / ebitda.replace(0.0, np.nan)

    # ---- WACC estimé (%) : pondération capitaux propres / dette au marché ----
    capitalisation = info.get("marketCap")
    beta = info.get("beta") or 1.0
    cout_fonds_propres = RISK_FREE_DEFAUT + beta * PRIME_MARCHE_DEFAUT
    cout_dette_brut = (out["interets_charges"].abs() / out["dette_totale"].replace(0.0, np.nan)) * 100.0
    cout_dette_brut = cout_dette_brut.clip(1.0, 12.0)
    if capitalisation and capitalisation > 0:
        poids_cp = capitalisation / (capitalisation + out["dette_totale"].fillna(0.0))
    else:
        poids_cp = pd.Series(0.7, index=idx)
    poids_dette = 1.0 - poids_cp
    out["wacc"] = poids_cp * cout_fonds_propres + poids_dette * cout_dette_brut.fillna(cout_dette_brut.mean() or 6.0) * (1.0 - taux_impot)

    out.index = [pd.Timestamp(c) for c in out.index]
    return out.sort_index()


# --------------------------------------------------------------------------- #
# 4. Score de qualité (méthodologie interne, inspirée Buffett / Munger)
# --------------------------------------------------------------------------- #
def score_qualite(indicateurs: pd.DataFrame, info: dict) -> tuple[float, dict[str, float]]:
    """
    Score interne sur 20, pondérant rentabilité des capitaux, marges,
    récurrence des revenus, génération de cash et solidité du bilan — les
    critères que Buffett et Munger mettent en avant pour juger une franchise
    de qualité. Ce n'est pas le score propriétaire de Baggr : c'est une
    estimation maison, calculée uniquement sur ce que yfinance expose.

    Renvoie (score_sur_20, détail_par_critère_sur_4).
    """
    detail: dict[str, float] = {}

    def _note(valeur: float | None, seuils: list[tuple[float, float]]) -> float:
        """Interpole une note sur [0, 4] à partir de paliers (valeur_seuil, note)."""
        if valeur is None or not np.isfinite(valeur):
            return 2.0  # neutre si donnée manquante, pour ne pas pénaliser injustement
        for seuil, note in seuils:
            if valeur >= seuil:
                return note
        return 0.0

    roe_moy = indicateurs["roe"].tail(5).mean() if "roe" in indicateurs else None
    detail["Retours sur capitaux (ROE)"] = _note(roe_moy, [(25, 4), (18, 3.4), (12, 2.6), (8, 1.6), (0, 0.8)])

    marge_nette_moy = indicateurs["marge_nette"].tail(5).mean() if "marge_nette" in indicateurs else None
    detail["Marges nettes"] = _note(marge_nette_moy, [(20, 4), (14, 3.4), (9, 2.6), (5, 1.6), (0, 0.8)])

    croissance_ca = cagr(indicateurs["revenu"]) if "revenu" in indicateurs else None
    detail["Croissance du chiffre d'affaires"] = _note(croissance_ca, [(12, 4), (8, 3.4), (5, 2.6), (2, 1.6), (0, 0.8)])

    if "fcf" in indicateurs and "resultat_net" in indicateurs:
        conversion = (indicateurs["fcf"] / indicateurs["resultat_net"].replace(0, np.nan)).tail(5).mean() * 100
    else:
        conversion = None
    detail["Conversion en cash (FCF/résultat net)"] = _note(conversion, [(100, 4), (85, 3.4), (65, 2.6), (40, 1.6), (0, 0.8)])

    dette_ebitda = indicateurs["dette_nette_ebitda"].iloc[-1] if "dette_nette_ebitda" in indicateurs and len(indicateurs) else None
    if dette_ebitda is not None and np.isfinite(dette_ebitda):
        note_dette = _note(-dette_ebitda, [(0, 4), (-1, 3.4), (-2, 2.6), (-3.5, 1.6), (-999, 0.8)])
    else:
        note_dette = 2.0
    detail["Solidité du bilan (dette nette/EBITDA)"] = note_dette

    predict = predictibilite_ca(indicateurs["revenu"]) if "revenu" in indicateurs else None
    detail["Prédictibilité des revenus"] = _note(predict, [(80, 4), (65, 3.4), (50, 2.6), (35, 1.6), (0, 0.8)])

    score = float(sum(detail.values()) / len(detail) * 5.0) if detail else 10.0
    return round(min(max(score, 0.0), 20.0), 1), detail
