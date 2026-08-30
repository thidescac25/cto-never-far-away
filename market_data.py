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

import time

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
    """
    Fiche d'identité et ratios instantanés (yf.Ticker.info).

    ATTENTION — cet appel passe par l'endpoint `quoteSummary` de Yahoo, qui
    exige un cookie et un jeton (« crumb ») obtenus auprès de fc.yahoo.com.
    Yahoo refuse cette authentification depuis les adresses IP de centre de
    données : l'appel réussit depuis une connexion résidentielle mais échoue
    presque systématiquement depuis un hébergeur (Streamlit Community Cloud,
    Heroku, Render, une VM cloud…). Le dictionnaire revient alors vide.

    C'est une limite de Yahoo, pas un défaut de configuration : d'où la
    couche de repli `get_fast_info` puis `construire_profil`, qui reconstruit
    les mêmes grandeurs à partir des endpoints non protégés.

    Deux tentatives sont faites, l'échec pouvant être un simple throttling.
    """
    for tentative in range(2):
        try:
            info = yf.Ticker(ticker).get_info()
            if info and len(info) > 5:
                return dict(info)
        except Exception:
            pass
        if tentative == 0:
            time.sleep(0.8)
    return {}


@st.cache_data(ttl=TTL_PRIX, show_spinner=False)
def get_fast_info(ticker: str) -> dict:
    """
    Grandeurs de marché servies par l'endpoint `chart`, non protégé par crumb.

    Contrairement à `get_info`, cet appel fonctionne aussi bien depuis un
    hébergeur que depuis un poste personnel. Il ne fournit pas les données
    fondamentales ni les avis d'analystes, mais couvre l'essentiel du bandeau
    de tête : cours, clôture précédente, capitalisation, extrêmes 52 semaines,
    nombre d'actions et devise.

    Les clés renvoyées reprennent la nomenclature de `.info` (camelCase) pour
    que les deux sources soient interchangeables en aval.
    """
    correspondances = {
        "currency": "currency", "exchange": "exchange", "quote_type": "quoteType",
        "shares": "sharesOutstanding", "market_cap": "marketCap",
        "last_price": "currentPrice", "previous_close": "previousClose",
        "open": "open", "day_high": "dayHigh", "day_low": "dayLow",
        "year_high": "fiftyTwoWeekHigh", "year_low": "fiftyTwoWeekLow",
        "year_change": "yearChange", "fifty_day_average": "fiftyDayAverage",
        "two_hundred_day_average": "twoHundredDayAverage",
    }
    sortie: dict = {}
    try:
        rapide = yf.Ticker(ticker).fast_info
    except Exception:
        return sortie

    for attribut, cle in correspondances.items():
        try:
            valeur = getattr(rapide, attribut, None)
            if valeur is None:
                continue
            if isinstance(valeur, (int, float)) and not np.isfinite(float(valeur)):
                continue
            sortie[cle] = valeur
        except Exception:
            continue
    return sortie


@st.cache_data(ttl=TTL_PRIX, show_spinner=False)
def get_dividendes(ticker: str) -> pd.Series:
    """
    Historique des dividendes versés par action (endpoint `chart`, non protégé).

    Permet de recalculer un rendement courant même quand `.info` est
    inaccessible.
    """
    try:
        serie = yf.Ticker(ticker).dividends
        if serie is None or len(serie) == 0:
            return pd.Series(dtype="float64")
        serie = serie.copy()
        serie.index = pd.to_datetime(serie.index)
        if getattr(serie.index, "tz", None) is not None:
            serie.index = serie.index.tz_localize(None)
        return serie.sort_index()
    except Exception:
        return pd.Series(dtype="float64")


@st.cache_data(ttl=TTL_PRIX, show_spinner=False)
def get_historique_indice(ticker_indice: str = "^GSPC", periode: str = "3y") -> pd.Series:
    """Clôtures d'un indice de référence, pour estimer un bêta quand `.info` est muet."""
    try:
        hist = yf.Ticker(ticker_indice).history(period=periode, auto_adjust=True)
        if hist is None or hist.empty or "Close" not in hist:
            return pd.Series(dtype="float64")
        serie = hist["Close"].dropna()
        serie.index = pd.to_datetime(serie.index)
        if getattr(serie.index, "tz", None) is not None:
            serie.index = serie.index.tz_localize(None)
        return serie
    except Exception:
        return pd.Series(dtype="float64")


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
# 3 bis. Profil consolidé — trois sources, de la plus fiable à la plus dérivée
# --------------------------------------------------------------------------- #
def _valide(valeur) -> bool:
    """Vrai si la valeur est exploitable (ni None, ni NaN, ni infini)."""
    if valeur is None:
        return False
    if isinstance(valeur, (int, float, np.floating, np.integer)):
        return bool(np.isfinite(float(valeur)))
    return True


def _premier_valide(*valeurs):
    for valeur in valeurs:
        if _valide(valeur):
            return valeur
    return None


def beta_estime(cours: pd.Series, indice: pd.Series, minimum_points: int = 60) -> float | None:
    """
    Bêta hebdomadaire d'une valeur face à un indice, sur la période commune.

    Utilisé uniquement quand Yahoo ne fournit pas le bêta publié. Le pas
    hebdomadaire limite le bruit des décalages d'horaires de clôture entre
    places (Londres, Zurich, Paris contre New York), qui biaiserait un bêta
    quotidien vers le bas.
    """
    if cours is None or indice is None or cours.empty or indice.empty:
        return None
    try:
        rv = cours.resample("W-FRI").last().pct_change().dropna()
        ri = indice.resample("W-FRI").last().pct_change().dropna()
        commun = rv.index.intersection(ri.index)
        if len(commun) < minimum_points:
            return None
        rv, ri = rv.loc[commun], ri.loc[commun]
        variance = float(ri.var(ddof=1))
        if variance <= 0:
            return None
        return float(np.cov(rv, ri, ddof=1)[0, 1] / variance)
    except Exception:
        return None


def construire_profil(
    info: dict,
    rapide: dict,
    indicateurs: pd.DataFrame,
    historique: pd.DataFrame,
    dividendes: pd.Series,
    meta: dict,
    indice: pd.Series | None = None,
) -> dict:
    """
    Fusionne les sources disponibles en un profil unique, exploitable par la
    fiche valeur, et note précisément d'où vient chaque grandeur.

    Ordre de préférence, du plus fiable au plus reconstruit :
        1. `.info` — chiffres publiés par Yahoo (indisponibles depuis un
           hébergeur, voir la note de get_info) ;
        2. `.fast_info` — grandeurs de marché de l'endpoint chart ;
        3. dérivation — recalcul à partir des comptes annuels et des cours.

    Les clés dérivées sont listées dans `profil["_derives"]`, ce qui permet à
    l'affichage de les signaler comme des estimations : sur un outil d'aide à
    la décision, faire passer un ratio recalculé pour un chiffre publié serait
    la pire des commodités.

    Le profil conserve la nomenclature de `.info` : les fonctions d'affichage
    l'utilisent exactement comme elles utilisaient `.info` auparavant.
    """
    profil: dict = dict(info) if info else {}
    derives: set[str] = set()

    def poser(cle: str, valeur, derive: bool) -> None:
        """Renseigne une clé absente et mémorise si la valeur est reconstruite."""
        if _valide(profil.get(cle)) or not _valide(valeur):
            return
        profil[cle] = valeur
        if derive:
            derives.add(cle)

    # ---- Cours et devise -------------------------------------------------- #
    clotures = (
        historique["Close"].dropna()
        if isinstance(historique, pd.DataFrame) and not historique.empty and "Close" in historique
        else pd.Series(dtype="float64")
    )
    dernier = float(clotures.iloc[-1]) if len(clotures) else None
    avant_dernier = float(clotures.iloc[-2]) if len(clotures) > 1 else None

    for cle in ("currency", "exchange", "quoteType", "marketCap", "sharesOutstanding",
                "currentPrice", "previousClose", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
                "fiftyDayAverage", "twoHundredDayAverage"):
        poser(cle, rapide.get(cle), derive=False)  # fast_info : valeurs de marché, non dérivées

    poser("currency", meta.get("devise"), derive=False)
    poser("currentPrice", dernier, derive=True)
    poser("previousClose", avant_dernier, derive=True)

    if not _valide(profil.get("regularMarketChangePercent")):
        prix, veille = profil.get("currentPrice"), profil.get("previousClose")
        if _valide(prix) and _valide(veille) and veille:
            poser("regularMarketChangePercent", (prix / veille - 1.0) * 100.0, derive=True)

    # Extrêmes 52 semaines depuis l'historique, à défaut de fast_info
    if len(clotures) > 20:
        fenetre = clotures.tail(252)
        hauts = historique["High"].dropna().tail(252) if "High" in historique else fenetre
        bas = historique["Low"].dropna().tail(252) if "Low" in historique else fenetre
        poser("fiftyTwoWeekHigh", float(hauts.max()), derive=True)
        poser("fiftyTwoWeekLow", float(bas.min()), derive=True)

    # ---- Grandeurs de bilan et de résultat -------------------------------- #
    def dernier_valide(colonne: str) -> float | None:
        if indicateurs is None or indicateurs.empty or colonne not in indicateurs:
            return None
        serie = indicateurs[colonne].dropna()
        return float(serie.iloc[-1]) if not serie.empty else None

    actions = _premier_valide(profil.get("sharesOutstanding"), dernier_valide("actions_en_circulation"))
    if not _valide(profil.get("sharesOutstanding")) and _valide(actions):
        poser("sharesOutstanding", actions, derive=True)

    resultat_net = dernier_valide("resultat_net")
    capitaux_propres = dernier_valide("capitaux_propres")
    dette = dernier_valide("dette_totale")
    tresorerie = dernier_valide("tresorerie")
    exploitation = dernier_valide("resultat_exploitation")
    prix = profil.get("currentPrice")

    # Capitalisation = nombre d'actions x cours
    if _valide(actions) and _valide(prix):
        poser("marketCap", float(actions) * float(prix), derive=True)
    capitalisation = profil.get("marketCap")

    # Bénéfice par action, puis PER
    if _valide(resultat_net) and _valide(actions) and actions:
        poser("trailingEps", float(resultat_net) / float(actions), derive=True)
    eps = profil.get("trailingEps")
    if _valide(eps) and _valide(prix) and float(eps) > 0:
        poser("trailingPE", float(prix) / float(eps), derive=True)

    # Actif net par action, puis P/B
    if _valide(capitalisation) and _valide(capitaux_propres) and capitaux_propres:
        poser("priceToBook", float(capitalisation) / float(capitaux_propres), derive=True)

    # Valeur d'entreprise et EV/EBITDA — l'EBITDA est approché par le résultat
    # d'exploitation, faute de ligne d'amortissements fiable chez yfinance.
    if _valide(capitalisation):
        valeur_entreprise = float(capitalisation) + float(dette or 0.0) - float(tresorerie or 0.0)
        poser("enterpriseValue", valeur_entreprise, derive=True)
        if _valide(exploitation) and float(exploitation) > 0:
            poser("enterpriseToEbitda", valeur_entreprise / float(exploitation), derive=True)

    # Rendement du dividende, sur les douze derniers mois effectivement versés
    if _valide(prix) and dividendes is not None and len(dividendes):
        recents = dividendes[dividendes.index >= (dividendes.index[-1] - pd.Timedelta(days=365))]
        verses = float(recents.sum())
        if verses > 0:
            poser("dividendYieldPct", verses / float(prix) * 100.0, derive=True)
    if not _valide(profil.get("dividendYieldPct")) and _valide(info.get("dividendYield")):
        # yfinance a livré ce champ tantôt en fraction, tantôt en pourcentage
        # selon les versions : on normalise sur une base pourcentage.
        brut = float(info["dividendYield"])
        poser("dividendYieldPct", brut * 100.0 if brut < 1.0 else brut, derive=False)

    # Bêta estimé face au S&P 500 quand Yahoo ne le publie pas
    if not _valide(profil.get("beta")) and indice is not None and len(clotures) > 60:
        estime = beta_estime(clotures, indice)
        if _valide(estime):
            poser("beta", estime, derive=True)

    # ---- Identité, non reconstructible : repli sur l'univers du projet ----- #
    poser("sector", meta.get("secteur"), derive=False)
    poser("country", meta.get("pays"), derive=False)
    poser("longName", meta.get("nom"), derive=False)

    profil["_derives"] = derives
    profil["_mode_degrade"] = not bool(info)
    return profil


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
