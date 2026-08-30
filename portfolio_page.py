"""
Rendu d'une page de suivi de portefeuille, commun aux deux vues du projet.

La fonction publique est afficher() : elle prend un univers d'investissement et
construit la page entière — bandeau de séance, trajectoire face aux indices,
simulation en euros, risque, attribution et détail des lignes.

Lancement du projet :  streamlit run app.py
"""

from __future__ import annotations

import io
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

from portfolio_core import (
    REBALANCE_FREQ,
    annual_returns,
    base_100,
    buy_and_hold,
    clean_prices,
    compute_metrics,
    contributions,
    convert_to_eur,
    drawdown,
    extend_with_reference,
    limiting_ticker,
    rebalanced,
    relative_metrics,
    splice_gap,
    splice_history,
    trim_to_full_coverage,
)

# --------------------------------------------------------------------------- #
# 1. Charte graphique (reprise de la présentation Mirion Technologies)
# --------------------------------------------------------------------------- #
ENCRE = "#0E1B2B"        # fond
PANNEAU = "#17293F"      # cartes
AMBRE = "#D8902A"        # accent principal
AMBRE_CLAIR = "#E9A94A"
BLANC = "#FFFFFF"
BRUME = "#ABBBCA"        # texte secondaire
ARDOISE = "#8598A9"      # texte tertiaire (contraste AA sur l'encre comme sur les cartes)
FILET = "rgba(171, 187, 202, 0.14)"
GRILLE = "rgba(171, 187, 202, 0.07)"

COULEURS_INDICES = {
    "CAC 40": "#5B8FB9",
    "S&P 500": "#98A6B5",
    "NASDAQ 100": "#4FB79A",
    "EURO STOXX 50": "#A98BC9",
    "DAX": "#C8636F",
    "Dow Jones": "#7285AD",
}

# --------------------------------------------------------------------------- #
# 2. Univers d'investissement
# --------------------------------------------------------------------------- #
INDICES = {
    "CAC 40": "#5B8FB9",
    "S&P 500": "#98A6B5",
    "NASDAQ 100": "#4FB79A",
    "EURO STOXX 50": "#A98BC9",
    "DAX": "#C8636F",
    "Dow Jones": "#7285AD",
}

# --------------------------------------------------------------------------- #
# 2. Univers d'investissement
# --------------------------------------------------------------------------- #
PORTEFEUILLE = {
    "ABT":    {"nom": "Abbott Laboratories",     "devise": "USD", "pays": "États-Unis",  "secteur": "Santé"},
    "GOOGL":  {"nom": "Alphabet A",              "devise": "USD", "pays": "États-Unis",  "secteur": "Technologie"},
    "BRK-B":  {"nom": "Berkshire Hathaway B",    "devise": "USD", "pays": "États-Unis",  "secteur": "Conglomérat"},
    "GTT.PA": {"nom": "Gaztransport & Technigaz","devise": "EUR", "pays": "France",      "secteur": "Énergie / GNL"},
    "MA":     {"nom": "Mastercard",              "devise": "USD", "pays": "États-Unis",  "secteur": "Paiements"},
    "MIR":    {"nom": "Mirion Technologies",     "devise": "USD", "pays": "États-Unis",  "secteur": "Instrumentation"},
    "NEE":    {"nom": "NextEra Energy",          "devise": "USD", "pays": "États-Unis",  "secteur": "Services aux collectivités"},
    "NOC":    {"nom": "Northrop Grumman",        "devise": "USD", "pays": "États-Unis",  "secteur": "Défense"},
    "RIO.L":  {"nom": "Rio Tinto",               "devise": "GBX", "pays": "Royaume-Uni", "secteur": "Matières premières"},
    "ROP.SW": {"nom": "Roche Holding",           "devise": "CHF", "pays": "Suisse",      "secteur": "Santé",
               # Genussschein « ROG » jusqu'au 16/03/2026, puis bon de participation
               # « ROP » depuis le 17/03/2026, échangé à parité. Nouvel ISIN CH1499059983.
               "anciens": ["ROG.SW"],
               "note": "Bon de participation ROP depuis le 17 mars 2026, en remplacement "
                       "du Genussschein ROG échangé à parité."},
    "RR.L":   {"nom": "Rolls-Royce Holdings",    "devise": "GBX", "pays": "Royaume-Uni", "secteur": "Aéronautique"},
    "VIE.PA": {"nom": "Veolia Environnement",    "devise": "EUR", "pays": "France",      "secteur": "Services aux collectivités"},
}

INDICES = {
    "CAC 40":        {"ticker": "^FCHI",     "devise": "EUR", "nature": "Prix"},
    "S&P 500":       {"ticker": "^GSPC",     "devise": "USD", "nature": "Prix"},
    "NASDAQ 100":    {"ticker": "^NDX",      "devise": "USD", "nature": "Prix"},
    "EURO STOXX 50": {"ticker": "^STOXX50E", "devise": "EUR", "nature": "Prix"},
    "DAX":           {"ticker": "^GDAXI",    "devise": "EUR", "nature": "Rendement global"},
    "Dow Jones":     {"ticker": "^DJI",      "devise": "USD", "nature": "Prix"},
}

PAIRES_FX = {"EURUSD": "EURUSD=X", "EURGBP": "EURGBP=X", "EURCHF": "EURCHF=X"}

def chaine_tickers(ligne: str) -> list[str]:
    """Symboles successifs d'une ligne, du plus récent au plus ancien."""
    return [ligne] + list(PORTEFEUILLE[ligne].get("anciens", []))


def ticker_reference(ligne: str) -> str | None:
    """Cotation de substitution éventuelle, utilisée pour prolonger l'historique."""
    reference = PORTEFEUILLE[ligne].get("reference")
    return reference["ticker"] if reference else None


def symboles_a_telecharger(lignes: list[str]) -> tuple[str, ...]:
    """Tous les symboles nécessaires : ligne, anciens symboles et substitution."""
    tous: list[str] = []
    for ligne in lignes:
        tous.extend(chaine_tickers(ligne))
        reference = ticker_reference(ligne)
        if reference:
            tous.append(reference)
    return tuple(dict.fromkeys(tous))


def carte_devises(univers: dict[str, dict]) -> dict[str, str]:
    """Devise de cotation de chaque symbole, substitutions comprises."""
    devises: dict[str, str] = {}
    for ticker, meta in univers.items():
        devises[ticker] = meta["devise"]
        for ancien in meta.get("anciens", []):
            devises[ancien] = meta["devise"]
        reference = meta.get("reference")
        if reference:
            devises[reference["ticker"]] = reference.get("devise", meta["devise"])
    return devises


def recomposer_lignes(
    close: pd.DataFrame, lignes: list[str]
) -> tuple[pd.DataFrame, dict[str, list[str]], dict[str, dict]]:
    """
    Assemble chaque ligne à partir de ses symboles successifs, puis prolonge
    l'historique par la cotation de substitution si elle est déclarée.

    Le tableau reçu doit déjà être exprimé en euro : le recalage d'une
    substitution cotée dans une autre devise n'a de sens qu'après conversion.
    """
    sortie = pd.DataFrame(index=close.index)
    origines: dict[str, list[str]] = {}
    calibrages: dict[str, dict] = {}

    for ligne in lignes:
        serie, utilises = splice_history(close, chaine_tickers(ligne))
        if serie is None:
            continue

        reference = ticker_reference(ligne)
        if reference and reference in close.columns:
            serie, facteur, recouvrement, dispersion = extend_with_reference(
                serie, close[reference]
            )
            if facteur is not None:
                calibrages[ligne] = {
                    "reference": reference,
                    "facteur": facteur,
                    "recouvrement": recouvrement,
                    "dispersion": dispersion,
                }

        sortie[ligne] = serie
        origines[ligne] = utilises
    return sortie, origines, calibrages


# Renseignés par afficher() selon l'univers de la page.
PORTEFEUILLE: dict[str, dict] = {}
DEVISES: dict[str, str] = {}


# --------------------------------------------------------------------------- #
# 3. Accès aux données de marché
# --------------------------------------------------------------------------- #
def _extraire_cloture(brut: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    """Normalise la sortie de yf.download, qu'elle soit à colonnes simples ou MultiIndex."""
    if brut is None or brut.empty:
        return pd.DataFrame()

    if isinstance(brut.columns, pd.MultiIndex):
        niveaux = brut.columns.get_level_values(0)
        champ = "Close" if "Close" in niveaux else brut.columns.levels[0][0]
        close = brut[champ].copy()
    else:
        close = brut[["Close"]].copy() if "Close" in brut.columns else brut.copy()
        if close.shape[1] == 1 and len(tickers) == 1:
            close.columns = tickers
    return close


@st.cache_data(ttl=900, show_spinner=False)
def telecharger_cloture(tickers: tuple[str, ...], debut: date, fin: date) -> pd.DataFrame:
    """
    Cours de clôture ajustés (dividendes et splits) pour une liste de tickers.

    yfinance abandonne par intermittence un symbole lors d'un téléchargement
    groupé, sans que le symbole soit pour autant radié. Toute colonne absente ou
    vide est donc redemandée une à une avant d'être considérée comme indisponible.
    """
    liste = list(tickers)
    try:
        brut = yf.download(
            liste,
            start=debut,
            end=fin + timedelta(days=1),
            auto_adjust=True,
            progress=False,
            threads=True,
            group_by="column",
        )
        close = clean_prices(_extraire_cloture(brut, liste))
    except Exception as exc:  # réseau, quota, ticker inconnu
        st.warning(f"Téléchargement groupé en échec ({exc}). Reprise ligne par ligne.")
        close = pd.DataFrame()

    absents = [t for t in liste if t not in close.columns or close[t].dropna().empty]
    for ticker in absents:
        try:
            hist = yf.Ticker(ticker).history(
                start=debut, end=fin + timedelta(days=1), auto_adjust=True
            )
            if not hist.empty and "Close" in hist:
                serie = hist["Close"]
                serie.index = pd.to_datetime(serie.index)
                if getattr(serie.index, "tz", None) is not None:
                    serie.index = serie.index.tz_localize(None)
                close = close.join(serie.rename(ticker), how="outer") if not close.empty \
                    else serie.rename(ticker).to_frame()
        except Exception:
            continue  # ligne réellement indisponible, signalée en aval

    return clean_prices(close)


@st.cache_data(ttl=300, show_spinner=False)
def telecharger_cotations_jour(tickers: tuple[str, ...]) -> dict[str, dict[str, float]]:
    """
    Dernier cours connu et variation depuis la clôture précédente, en devise de
    cotation. Sert au bandeau de séance, rafraîchi toutes les cinq minutes.
    """
    resultat: dict[str, dict[str, float]] = {}
    try:
        brut = yf.download(
            list(tickers), period="7d", interval="1d",
            auto_adjust=False, progress=False, threads=True, group_by="column",
        )
        close = clean_prices(_extraire_cloture(brut, list(tickers)))
    except Exception:
        return resultat

    for ticker in tickers:
        if ticker not in close.columns:
            continue
        serie = close[ticker].dropna()
        if len(serie) < 2:
            continue
        dernier, precedent = float(serie.iloc[-1]), float(serie.iloc[-2])
        resultat[ticker] = {
            "prix": dernier,
            "variation": (dernier / precedent - 1.0) * 100.0 if precedent else 0.0,
            "date": serie.index[-1],
        }
    return resultat


@st.cache_data(ttl=3600, show_spinner=False)
def telecharger_fx(debut: date, fin: date) -> pd.DataFrame:
    """Taux de change quotidiens, exprimés en devise étrangère pour 1 EUR."""
    close = telecharger_cloture(tuple(PAIRES_FX.values()), debut, fin)
    if close.empty:
        return pd.DataFrame()
    correspondance = {v: k for k, v in PAIRES_FX.items()}
    close = close.rename(columns=correspondance)
    return close[[c for c in PAIRES_FX if c in close.columns]]


def indices_en_euro(close: pd.DataFrame, fx: pd.DataFrame, actif: bool) -> pd.DataFrame:
    """Convertit les indices libellés en dollar pour raisonner du point de vue d'un investisseur euro."""
    if not actif or close.empty or fx.empty:
        return close
    devises = {INDICES[n]["ticker"]: INDICES[n]["devise"] for n in INDICES}
    return convert_to_eur(close, fx, {c: devises.get(c, "EUR") for c in close.columns})


# --------------------------------------------------------------------------- #
# 4. Mise en forme
# --------------------------------------------------------------------------- #
def fmt_eur(valeur: float, decimales: int = 0) -> str:
    if valeur is None or not np.isfinite(valeur):
        return "—"
    texte = f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")
    return f"{texte} €"


def fmt_pct(valeur: float, decimales: int = 1, signe: bool = True) -> str:
    if valeur is None or not np.isfinite(valeur):
        return "—"
    gabarit = f"{{:{'+' if signe else ''}.{decimales}f}}"
    return gabarit.format(valeur).replace(".", ",") + " %"


MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]


def fmt_date_longue(d) -> str:
    """« 2 janvier 2023 », sans dépendre de la locale installée sur la machine."""
    jour = "1er" if d.day == 1 else str(d.day)
    return f"{jour} {MOIS_FR[d.month - 1]} {d.year}"


def fmt_titres(valeur: float) -> str:
    """Nombre de titres, avec séparateur de milliers et une décimale utile."""
    if valeur is None or not np.isfinite(valeur):
        return "—"
    decimales = 0 if abs(valeur) >= 1000 else (1 if abs(valeur) >= 10 else 2)
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


SYMBOLES = {"USD": "$", "EUR": "€", "CHF": "CHF", "GBX": "p", "GBP": "£"}


def fmt_prix_local(valeur: float, devise: str) -> str:
    """Cours dans sa devise de cotation, pence compris (convention de Londres)."""
    if valeur is None or not np.isfinite(valeur):
        return "—"
    montant = f"{valeur:,.2f}".replace(",", " ").replace(".", ",")
    symbole = SYMBOLES.get(devise, devise)
    return f"{montant} {symbole}" if devise in ("CHF", "GBX") else f"{symbole}{montant}"


def fmt_nombre(valeur: float, decimales: int = 2) -> str:
    if valeur is None or not np.isfinite(valeur):
        return "—"
    return f"{valeur:.{decimales}f}".replace(".", ",")


def styliser(fig: go.Figure, hauteur: int = 460, marge_haut: int = 30) -> go.Figure:
    """Applique la charte sombre à une figure Plotly."""
    fig.update_layout(
        height=hauteur,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=BRUME, size=13),
        margin=dict(l=10, r=10, t=marge_haut, b=10),
        hoverlabel=dict(
            bgcolor=PANNEAU,
            bordercolor=FILET,
            font=dict(color=BLANC, family="Inter, sans-serif", size=12),
        ),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0,
            bgcolor="rgba(0,0,0,0)", font=dict(color=BRUME, size=12),
        ),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=FILET,
                     tickcolor=FILET, tickfont=dict(color=ARDOISE, size=11))
    fig.update_yaxes(showgrid=True, gridcolor=GRILLE, zeroline=False,
                     linecolor="rgba(0,0,0,0)", tickfont=dict(color=ARDOISE, size=11))
    return fig


def carte_kpi(valeur: str, libelle: str, note: str = "", couleur: str = BLANC) -> str:
    return f"""
    <div class="kpi">
      <div class="kpi-valeur" style="color:{couleur};">{valeur}</div>
      <div class="kpi-libelle">{libelle}</div>
      <div class="kpi-note">{note}</div>
    </div>"""


def tableau_html(df: pd.DataFrame, aligne_droite: list[str], surligne: str | None = None) -> str:
    entetes = "".join(
        f'<th class="{"num" if c in aligne_droite else ""}">{c}</th>' for c in df.columns
    )
    lignes = []
    for _, r in df.iterrows():
        classe = "ligne-phare" if surligne and str(r.iloc[0]) == surligne else ""
        cells = "".join(
            f'<td class="{"num" if c in aligne_droite else ""}">{r[c]}</td>' for c in df.columns
        )
        lignes.append(f'<tr class="{classe}">{cells}</tr>')
    return f'<table class="tbl"><thead><tr>{entetes}</tr></thead><tbody>{"".join(lignes)}</tbody></table>'




# --------------------------------------------------------------------------- #
# 5. Rendu de la page
# --------------------------------------------------------------------------- #
def afficher(
    univers: dict[str, dict],
    titre: str,
    accroche: str,
    eyebrow: str = "Compte-titres ordinaire",
    depart_defaut: date = date(2023, 1, 1),
) -> None:
    """
    Construit la page complète pour un univers donné.

    Args:
        univers: dictionnaire ticker -> métadonnées (voir univers.py).
        titre: titre affiché en haut de page.
        accroche: phrase d'intention sous le titre.
        eyebrow: petite ligne ambre au-dessus du titre.
        depart_defaut: date de début proposée par défaut.
    """
    global PORTEFEUILLE, DEVISES
    PORTEFEUILLE = univers
    DEVISES = carte_devises(univers)

    # --------------------------------------------------------------------------- #
    # 5. Configuration de la page et feuille de style
    # --------------------------------------------------------------------------- #

    st.markdown(
        f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,500;0,700;1,400;1,500&family=Inter:wght@400;500;600&display=swap');

    :root {{
      --encre: {ENCRE}; --panneau: {PANNEAU}; --ambre: {AMBRE};
      --brume: {BRUME}; --ardoise: {ARDOISE}; --filet: {FILET};
    }}

    .stApp {{ background: var(--encre); }}
    /* L'en-tete flottant de Streamlit recouvrait la ligne ambre du titre :
   on le rend transparent et on degage la hauteur correspondante. */
header[data-testid="stHeader"] {{ background: transparent; height: 3.2rem; }}
[data-testid="stAppDeployButton"] {{ display: none; }}
.block-container {{ padding: 3.6rem 3rem 4rem 3rem; max-width: 1560px; }}
@media (max-width: 900px) {{ .block-container {{ padding: 3.6rem 1.2rem 3rem 1.2rem; }} }}
    html, body, [class*="css"] {{ font-family: 'Inter', 'Segoe UI', sans-serif; color: var(--brume); }}

    /* ---------- Hero ---------- */
    .eyebrow {{
      font-size: 12px; letter-spacing: .22em; text-transform: uppercase;
      color: var(--ambre); font-weight: 600; margin-bottom: 18px;
    }}
    .eyebrow span {{ color: var(--ardoise); margin: 0 10px; }}
    .titre {{
      font-family: 'Playfair Display', Georgia, serif; font-weight: 700;
      font-size: clamp(38px, 5.2vw, 74px); line-height: 1.02; color: #fff;
      margin: 0 0 18px 0; letter-spacing: -.01em;
    }}
    .accroche {{
      font-family: 'Playfair Display', Georgia, serif; font-style: italic;
      font-size: clamp(17px, 1.5vw, 23px); line-height: 1.5; color: var(--brume);
      margin: 0 0 14px 0; max-width: 46ch;
    }}
    .legende {{ font-size: 13.5px; color: var(--ardoise); line-height: 1.7; }}

    /* ---------- Cartes de chiffres ---------- */
    .bande-kpi {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 1px; background: var(--filet); border: 1px solid var(--filet);
      border-radius: 6px; overflow: hidden; margin: 8px 0 4px 0;
    }}
    .kpi {{ background: var(--panneau); padding: 20px 22px 18px 22px; }}
    .kpi-valeur {{
      font-family: 'Playfair Display', Georgia, serif; font-weight: 700;
      font-size: 28px; line-height: 1.1; font-variant-numeric: tabular-nums;
    }}
    .kpi-libelle {{ font-size: 12px; color: var(--brume); margin-top: 8px; letter-spacing: .02em; }}
    .kpi-note {{ font-size: 11.5px; color: var(--ardoise); margin-top: 2px; }}

    /* ---------- Sections ---------- */
    .section {{ margin: 46px 0 6px 0; }}
    .section-num {{
      font-size: 11px; letter-spacing: .24em; color: var(--ambre);
      font-weight: 600; text-transform: uppercase;
    }}
    .section-titre {{
      font-family: 'Playfair Display', Georgia, serif; font-size: 27px;
      color: #fff; font-weight: 500; margin: 6px 0 4px 0;
    }}
    .section-sous {{ font-size: 13.5px; color: var(--ardoise); max-width: 92ch; line-height: 1.6; }}
    .filet {{ height: 1px; background: var(--filet); margin: 14px 0 22px 0; }}

    /* ---------- Bandeau de séance ---------- */
    .seance {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
      gap: 1px; background: var(--filet); border: 1px solid var(--filet);
      border-radius: 6px; overflow: hidden; margin: 6px 0 10px 0;
    }}
    .cote {{ background: var(--panneau); padding: 11px 13px; }}
    .cote-tk {{ font-size: 10.5px; letter-spacing: .13em; color: var(--ardoise); font-weight: 600; }}
    .cote-px {{
      font-size: 15px; color: #fff; font-variant-numeric: tabular-nums;
      margin-top: 4px; font-weight: 500;
    }}
    .cote-var {{ font-size: 12px; font-variant-numeric: tabular-nums; margin-top: 2px; }}

    /* ---------- État des données ---------- */
    .etat {{
      display: flex; flex-wrap: wrap; gap: 8px 26px; align-items: baseline;
      font-size: 12px; color: var(--ardoise); padding: 11px 16px;
      border: 1px solid var(--filet); border-left: 2px solid var(--ambre);
      border-radius: 4px; margin: 6px 0 4px 0;
    }}
    .etat b {{ color: var(--brume); font-weight: 500; }}

    /* ---------- Alerte de concentration ---------- */
    .alerte {{
      border: 1px solid var(--filet); border-left: 2px solid var(--ambre);
      border-radius: 4px; padding: 15px 18px; margin: 18px 0 4px 0;
      font-size: 13.5px; line-height: 1.65; color: var(--brume);
    }}
    .alerte b {{ color: #fff; font-weight: 600; }}

    /* ---------- Tableaux ---------- */
    .tbl {{ width: 100%; border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }}
    .tbl th {{
      text-align: left; font-size: 11px; letter-spacing: .1em; text-transform: uppercase;
      color: var(--ardoise); font-weight: 600; padding: 10px 14px;
      border-bottom: 1px solid var(--filet); white-space: nowrap;
    }}
    .tbl td {{ padding: 11px 14px; border-bottom: 1px solid rgba(171,187,202,.06); color: var(--brume); }}
    .tbl td.num, .tbl th.num {{ text-align: right; }}
    .tbl tbody tr:hover td {{ background: rgba(171,187,202,.04); }}
    .tbl tr.ligne-phare td {{
      background: rgba(216,144,42,.10); color: #fff; font-weight: 600;
      border-bottom: 1px solid rgba(216,144,42,.30);
    }}
    .hausse {{ color: #4FB79A; }} .baisse {{ color: #C8636F; }}

    /* ---------- Barre latérale ---------- */
    section[data-testid="stSidebar"] {{ background: {PANNEAU}; border-right: 1px solid var(--filet); }}
    section[data-testid="stSidebar"] .block-container {{ padding: 1.2rem 1.2rem; }}
/* Navigation entre les deux portefeuilles */
[data-testid="stSidebarNav"] {{ border-bottom: 1px solid var(--filet); padding-bottom: 10px; }}
[data-testid="stSidebarNav"] a span {{ font-size: 13.5px; }}
    .sb-titre {{
      font-size: 11px; letter-spacing: .2em; text-transform: uppercase;
      color: var(--ambre); font-weight: 600; margin: 22px 0 6px 0;
    }}
    .stSlider label, .stSelectbox label, .stMultiSelect label,
    .stDateInput label, .stNumberInput label, .stRadio label {{
      color: var(--brume) !important; font-size: 13px !important;
    }}

    /* ---------- Pied de page ---------- */
    .pied {{ font-size: 11.5px; color: var(--ardoise); line-height: 1.8; margin-top: 8px; }}
    .pied b {{ color: var(--brume); font-weight: 500; }}

    #MainMenu, footer {{ visibility: hidden; }}
    @media (prefers-reduced-motion: reduce) {{ * {{ animation: none !important; transition: none !important; }} }}
    </style>
    """,
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------------------------- #
    # 6. Paramètres (barre latérale)
    # --------------------------------------------------------------------------- #
    with st.sidebar:
        st.markdown('<div class="sb-titre">Période</div>', unsafe_allow_html=True)
        aujourdhui = date.today()
        debut = st.date_input(
            "Début d'investissement",
            value=depart_defaut,
            min_value=date(2000, 1, 3),
            max_value=aujourdhui - timedelta(days=30),
            format="DD/MM/YYYY",
        )
        fin = st.date_input(
            "Fin d'observation",
            value=aujourdhui,
            min_value=debut + timedelta(days=30),
            max_value=aujourdhui,
            format="DD/MM/YYYY",
        )

        st.markdown('<div class="sb-titre">Capital et gestion</div>', unsafe_allow_html=True)
        capital = st.number_input(
            "Capital initial (€)", min_value=1_000, max_value=100_000_000,
            value=1_000_000, step=10_000, format="%d",
        )
        mode = st.radio(
            "Mode de gestion",
            ["Achat et conservation", "Équipondéré rééquilibré"],
            help="« Achat et conservation » achète 1/12 du capital sur chaque ligne au premier jour "
                 "et ne touche plus à rien : les gagnantes prennent naturellement du poids.",
        )
        frequence = "Mensuel"
        if mode == "Équipondéré rééquilibré":
            frequence = st.select_slider(
                "Fréquence de rééquilibrage", options=list(REBALANCE_FREQ), value="Trimestriel"
            )

        st.markdown('<div class="sb-titre">Comparaison</div>', unsafe_allow_html=True)
        indices_choisis = st.multiselect(
            "Indices de référence", options=list(INDICES), default=list(INDICES),
        )
        convertir_indices = st.toggle(
            "Ramener les indices en euro", value=True,
            help="Vue d'un investisseur résidant en zone euro : les indices américains sont "
                 "convertis au taux de change du jour, l'effet devise est donc inclus des deux côtés.",
        )
        echelle = st.radio(
            "Échelle des courbes", ["Linéaire", "Logarithmique"], horizontal=True,
            help="L'échelle logarithmique donne la même hauteur à deux hausses de même "
                 "pourcentage : elle rend lisibles les lignes modestes à côté d'une valeur "
                 "qui a été multipliée par quinze.",
        )
        type_axe = "log" if echelle == "Logarithmique" else "linear"

        st.markdown('<div class="sb-titre">Composition</div>', unsafe_allow_html=True)
        lignes_choisies = st.multiselect(
            "Lignes retenues",
            options=list(PORTEFEUILLE),
            default=list(PORTEFEUILLE),
            format_func=lambda t: f"{PORTEFEUILLE[t]['nom']} ({t})",
        )

        st.markdown('<div class="sb-titre">Données</div>', unsafe_allow_html=True)
        if st.button("Actualiser les cours", width="stretch"):
            st.cache_data.clear()
            st.rerun()


    if not lignes_choisies:
        st.warning("Sélectionnez au moins une ligne dans la barre latérale pour construire le portefeuille.")
        st.stop()


    # --------------------------------------------------------------------------- #
    # 7. Chargement et construction
    # --------------------------------------------------------------------------- #
    with st.spinner("Récupération des cours et des taux de change…"):
        cours_bruts = telecharger_cloture(symboles_a_telecharger(lignes_choisies), debut, fin)
        fx = telecharger_fx(debut, fin)
        tickers_indices = [INDICES[n]["ticker"] for n in indices_choisis]
        cours_indices = telecharger_cloture(tuple(tickers_indices), debut, fin) if tickers_indices else pd.DataFrame()

    if cours_bruts.empty:
        st.error(
            "Aucune cotation reçue pour la période demandée. Vérifiez la connexion réseau, "
            "puis relancez avec le bouton « Actualiser les cours »."
        )
        st.stop()

    cours_bruts_eur = convert_to_eur(cours_bruts, fx, DEVISES)
    cours_eur, origines, calibrages = recomposer_lignes(cours_bruts_eur, lignes_choisies)
    manquants = [t for t in lignes_choisies if t not in cours_eur.columns]
    if manquants:
        st.error(
            "**Portefeuille incomplet.** Yahoo n'a rien renvoyé pour "
            + ", ".join(f"{PORTEFEUILLE[t]['nom']} ({t})" for t in manquants)
            + f", même après reprise ligne par ligne. Les chiffres ci-dessous portent donc sur "
              f"{len(lignes_choisies) - len(manquants)} lignes et non {len(lignes_choisies)}. "
              "C'est presque toujours passager : réessayez avec « Actualiser les cours »."
        )

    cours = trim_to_full_coverage(cours_eur)

    if cours.empty or len(cours) < 30:
        couverture = pd.DataFrame([
            {
                "Ligne": f"{PORTEFEUILLE[t]['nom']} ({t})",
                "Première cotation": cours_eur[t].dropna().index.min(),
                "Dernière cotation": cours_eur[t].dropna().index.max(),
                "Séances": int(cours_eur[t].notna().sum()),
            }
            for t in cours_eur.columns
        ]).sort_values("Première cotation", ascending=False)

        fautive = couverture.iloc[0]
        st.error(
            f"**Historique commun trop court.** La ligne la plus tardive est "
            f"**{fautive['Ligne']}**, dont la première cotation remonte au "
            f"{fautive['Première cotation']:%d/%m/%Y} — soit {len(cours)} séances communes "
            f"seulement, alors que toutes les lignes doivent démarrer ensemble.\n\n"
            f"Retirez-la dans « Lignes retenues », ou repoussez la date de début après cette "
            f"date. Si elle devrait avoir un historique plus long, son ticker est probablement "
            f"à revoir."
        )
        st.dataframe(
            couverture.assign(**{
                "Première cotation": couverture["Première cotation"].dt.strftime("%d/%m/%Y"),
                "Dernière cotation": couverture["Dernière cotation"].dt.strftime("%d/%m/%Y"),
            }),
            hide_index=True,
        )
        st.stop()

    contrainte_ticker, contrainte_date = limiting_ticker(cours_eur)
    depart_effectif, fin_effective = cours.index[0], cours.index[-1]

    valeur, positions = buy_and_hold(cours, capital)
    parts = pd.Series({p.ticker: p.parts for p in positions})
    valeurs_lignes = cours.mul(parts, axis=1)

    if mode == "Équipondéré rééquilibré":
        # Le détail par ligne est reconstruit à partir des poids réellement portés
        # chaque jour ; les positions « achat et conservation » restent la base de
        # l'attribution de performance, plus lisible car sans flux intermédiaires.
        valeur, valeurs_lignes = rebalanced(
            cours, capital, REBALANCE_FREQ[frequence], detail=True
        )

    portefeuille_100 = base_100(valeur)
    mesures = compute_metrics(valeur)

    # Indices, alignés sur le calendrier du portefeuille
    indices_100: dict[str, pd.Series] = {}
    if not cours_indices.empty:
        indices_eur = indices_en_euro(cours_indices, fx, convertir_indices)
        for nom in indices_choisis:
            tk = INDICES[nom]["ticker"]
            if tk not in indices_eur.columns:
                continue
            serie = indices_eur[tk].reindex(cours.index).ffill().dropna()
            if len(serie) > 20:
                indices_100[nom] = base_100(serie)


    # --------------------------------------------------------------------------- #
    # 8. En-tête
    # --------------------------------------------------------------------------- #
    gauche, droite = st.columns([1.35, 1], gap="large")

    with gauche:
        st.markdown(
            f'<div class="eyebrow">{eyebrow}<span>·</span>'
            f'{len(cours.columns)} lignes<span>·</span>Consolidé en euro</div>',
            unsafe_allow_html=True,
        )
        st.markdown(f'<h1 class="titre">{titre}</h1>', unsafe_allow_html=True)
        st.markdown(f'<p class="accroche">{accroche}</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="legende">Période retenue : <b style="color:{BRUME}">'
            f'{depart_effectif:%d/%m/%Y} → {fin_effective:%d/%m/%Y}</b>'
            f'&nbsp;·&nbsp;{mode.lower()}'
            f'{" (" + frequence.lower() + ")" if mode.startswith("Équipondéré") else ""}'
            f'&nbsp;·&nbsp;capital de départ {fmt_eur(capital)}</div>',
            unsafe_allow_html=True,
        )

    with droite:
        # Signature graphique : le motif d'orbites de la présentation Mirion,
        # dont le rayon du cercle plein traduit la performance totale.
        perf = mesures["perf_totale"]
        rayon = float(np.clip(46 + perf * 0.55, 26, 118))
        st.markdown(
            f"""
            <svg viewBox="0 0 340 300" width="100%" height="270" role="img"
                 aria-label="Motif d'orbites, le disque central mesure la performance totale">
              <g fill="none" stroke="{FILET}" stroke-width="1">
                <circle cx="196" cy="150" r="146"/><circle cx="196" cy="150" r="112"/>
                <circle cx="196" cy="150" r="78"/>
              </g>
              <circle cx="196" cy="150" r="{rayon:.1f}" fill="none"
                      stroke="{AMBRE}" stroke-width="1.6" opacity=".9"/>
              <circle cx="196" cy="150" r="13" fill="{AMBRE}"/>
            </svg>
            """,
            unsafe_allow_html=True,
        )

    meilleur_indice = max(indices_100, key=lambda n: indices_100[n].iloc[-1]) if indices_100 else None
    ecart_meilleur = (
        mesures["perf_totale"] - (indices_100[meilleur_indice].iloc[-1] - 100.0)
        if meilleur_indice else np.nan
    )

    st.markdown(
        '<div class="bande-kpi">'
        + carte_kpi(fmt_eur(mesures["valeur_finale"]), "Valeur du portefeuille",
                    f"soit {fmt_eur(mesures['valeur_finale'] - capital)} de plus-value latente")
        + carte_kpi(fmt_pct(mesures["perf_totale"]), "Performance cumulée",
                    f"{fmt_pct(mesures['tcac'])} par an", AMBRE)
        + carte_kpi(fmt_pct(mesures["max_drawdown"]), "Perte maximale",
                    "du plus haut au plus bas")
        + carte_kpi(fmt_nombre(mesures["sharpe"]), "Ratio de Sharpe",
                    f"volatilité {fmt_pct(mesures['volatilite'], signe=False)}")
        + carte_kpi(fmt_pct(ecart_meilleur) if np.isfinite(ecart_meilleur) else "—",
                    "Écart au meilleur indice",
                    meilleur_indice or "aucun indice sélectionné")
        + "</div>",
        unsafe_allow_html=True,
    )

    retard = (contrainte_date.date() - debut).days if contrainte_date is not None else 0
    # Un décalage de quelques jours n'est qu'un week-end ou un jour férié : inutile
    # de le signaler, seul un vrai retard de cotation mérite un message.
    if contrainte_ticker and retard > 7:
        message = (
            f"{PORTEFEUILLE[contrainte_ticker]['nom']} ({contrainte_ticker}) ne cote pas avant le "
            f"{depart_effectif:%d/%m/%Y}. Toutes les lignes démarrent ensemble pour que la "
            f"comparaison reste honnête, la période analysée débute donc à cette date."
        )
        if retard > 60:
            st.warning(
                f"**Période raccourcie de {retard} jours.** {message} Pour retrouver la période "
                f"complète, retirez cette ligne dans « Lignes retenues », en gardant en tête que "
                f"le portefeuille analysé n'aura alors plus que {len(cours.columns) - 1} valeurs."
            )
        else:
            st.caption(f"Départ décalé au {depart_effectif:%d/%m/%Y} : {message}")

    # Lignes prolongées par une cotation de substitution
    for ligne, info in calibrages.items():
        fiable = info["dispersion"] < 2.0
        st.caption(
            f"{PORTEFEUILLE[ligne]['nom']} : {PORTEFEUILLE[ligne].get('note', '')} "
            f"Facteur de recalage {fmt_nombre(info['facteur'], 4)}, estimé sur "
            f"{info['recouvrement']} séances communes"
            + (f" (dispersion {fmt_pct(info['dispersion'], 2, signe=False)}, cohérent)."
               if fiable else
               f" — **dispersion de {fmt_pct(info['dispersion'], 2, signe=False)}**, "
               f"les deux cotations divergent sensiblement : traitez cette ligne avec prudence.")
        )
    for ligne, utilises in origines.items():
        if len(utilises) < 2:
            continue
        ecart = splice_gap(cours_bruts_eur, utilises[0], utilises[1])
        controle = (
            f" Contrôle de parité à la jonction : {fmt_pct(ecart, 2)}."
            if ecart is not None and abs(ecart) < 5
            else f" **Attention, écart de {fmt_pct(ecart, 1)} à la jonction** : la série mérite "
                 f"une vérification manuelle." if ecart is not None else ""
        )
        st.caption(
            f"{PORTEFEUILLE[ligne]['nom']} : historique reconstitué à partir de "
            f"{' puis '.join(reversed(utilises))}. {PORTEFEUILLE[ligne].get('note', '')}{controle}"
        )


    # --------------------------------------------------------------------------- #
    # 9. Séance du jour et état des données
    # --------------------------------------------------------------------------- #
    cotations = telecharger_cotations_jour(tuple(cours.columns))

    if cotations:
        cellules = ""
        for ticker in cours.columns:
            cote = cotations.get(ticker)
            if not cote:
                continue
            hausse = cote["variation"] >= 0
            couleur = "#4FB79A" if hausse else "#C8636F"
            fleche = "▲" if hausse else "▼"
            cellules += (
                f'<div class="cote"><div class="cote-tk">{ticker}</div>'
                f'<div class="cote-px">{fmt_prix_local(cote["prix"], PORTEFEUILLE[ticker]["devise"])}</div>'
                f'<div class="cote-var" style="color:{couleur};">{fleche} '
                f'{fmt_pct(cote["variation"], 2)}</div></div>'
            )
        st.markdown(f'<div class="seance">{cellules}</div>', unsafe_allow_html=True)

    seance = max((c["date"] for c in cotations.values()), default=None)
    etat_seance = (
        f"<span>Dernière séance cotée <b>{seance:%d/%m/%Y}</b></span>" if seance
        else "<span>Cotations du jour <b>momentanément indisponibles</b></span>"
    )
    st.markdown(
        f'<div class="etat">{etat_seance}'
        f'<span>Courbes arrêtées au <b>{fin_effective:%d/%m/%Y}</b>, dernier jour où les '
        f'{len(cours.columns)} lignes ont toutes coté</span>'
        f'<span>Page actualisée à <b>{datetime.now():%H:%M}</b></span>'
        f'<span>Cotations rafraîchies toutes les 5 minutes, historiques toutes les 15</span>'
        f'</div>',
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------------------------- #
    # 10. Trajectoire
    # --------------------------------------------------------------------------- #
    st.markdown(
        '<div class="section"><div class="section-num">Trajectoire</div>'
        '<div class="section-titre">La courbe de croissance face aux indices</div>'
        '<div class="section-sous">Base 100 au premier jour commun. Dividendes réinvestis, '
        'effet de change inclus.</div><div class="filet"></div></div>',
        unsafe_allow_html=True,
    )

    fig = go.Figure()

    for nom, serie in indices_100.items():
        fig.add_trace(go.Scatter(
            x=serie.index, y=serie.values, name=nom, mode="lines",
            line=dict(width=1.5, color=COULEURS_INDICES.get(nom, ARDOISE)),
            opacity=0.85, hovertemplate="%{y:.1f}<extra>" + nom + "</extra>",
        ))

    fig.add_trace(go.Scatter(
        x=portefeuille_100.index, y=portefeuille_100.values, name="CTO Never far away",
        mode="lines", line=dict(width=3.4, color=AMBRE),
        hovertemplate="<b>%{y:.1f}</b><extra>Portefeuille</extra>",
    ))

    fig.add_hline(y=100, line=dict(color=FILET, width=1, dash="dot"))
    fig.add_trace(go.Scatter(
        x=[portefeuille_100.index[-1]], y=[portefeuille_100.iloc[-1]],
        mode="markers", marker=dict(size=11, color=AMBRE, line=dict(color=ENCRE, width=2)),
        showlegend=False, hoverinfo="skip",
    ))
    fig.add_annotation(
        x=portefeuille_100.index[-1], y=portefeuille_100.iloc[-1],
        text=f"<b>{portefeuille_100.iloc[-1]:.0f}</b>", showarrow=False,
        xshift=34, font=dict(color=AMBRE, size=15, family="Playfair Display, serif"),
    )

    styliser(fig, hauteur=520, marge_haut=44)
    fig.update_layout(hovermode="x unified")
    fig.update_yaxes(title=None, type=type_axe)
    fig.update_xaxes(
        rangeselector=dict(
            buttons=[
                dict(count=6, label="6 M", step="month", stepmode="backward"),
                dict(count=1, label="1 A", step="year", stepmode="backward"),
                dict(count=3, label="3 A", step="year", stepmode="backward"),
                dict(step="all", label="Tout"),
            ],
            bgcolor=PANNEAU, activecolor=AMBRE, bordercolor=FILET, borderwidth=1,
            font=dict(color=BRUME, size=11), x=0, y=1.14,
        ),
        rangeslider=dict(visible=False),
    )
    st.plotly_chart(fig,
                    config={"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]})

    # Tableau comparatif
    lignes_tableau = [{
        "Support": "CTO Never far away",
        "Performance": fmt_pct(mesures["perf_totale"]),
        "Par an": fmt_pct(mesures["tcac"]),
        "Volatilité": fmt_pct(mesures["volatilite"], signe=False),
        "Perte max.": fmt_pct(mesures["max_drawdown"]),
        "Sharpe": fmt_nombre(mesures["sharpe"]),
        "Bêta": "—",
        "Écart": "—",
    }]
    for nom, serie in sorted(indices_100.items(), key=lambda kv: kv[1].iloc[-1], reverse=True):
        m = compute_metrics(serie)
        r = relative_metrics(valeur, serie)
        lignes_tableau.append({
            "Support": nom,
            "Performance": fmt_pct(m["perf_totale"]),
            "Par an": fmt_pct(m["tcac"]),
            "Volatilité": fmt_pct(m["volatilite"], signe=False),
            "Perte max.": fmt_pct(m["max_drawdown"]),
            "Sharpe": fmt_nombre(m["sharpe"]),
            "Bêta": fmt_nombre(r["beta"]),
            "Écart": fmt_pct(r["surperformance"]),
        })

    st.markdown(
        tableau_html(
            pd.DataFrame(lignes_tableau),
            aligne_droite=["Performance", "Par an", "Volatilité", "Perte max.", "Sharpe", "Bêta", "Écart"],
            surligne="CTO Never far away",
        ),
        unsafe_allow_html=True,
    )
    st.caption(
        "Bêta et écart sont mesurés portefeuille contre indice sur la période affichée. "
        "Le DAX est un indice de rendement global (dividendes réinvestis) ; les cinq autres sont des "
        "indices de prix, donc mécaniquement désavantagés dans la comparaison."
    )


    # --------------------------------------------------------------------------- #
    # 11. Simulation en euros
    # --------------------------------------------------------------------------- #
    st.markdown(
        f'<div class="section"><div class="section-num">Simulation</div>'
        f'<div class="section-titre">{fmt_eur(capital)} placés le {fmt_date_longue(depart_effectif)}</div>'
        f'<div class="section-sous">Le capital est réparti à parts égales entre les '
        f'{len(cours.columns)} lignes au premier jour. En trait plein la valeur totale du '
        f'portefeuille, en pointillés fins chaque ligne prise isolément.</div>'
        f'<div class="filet"></div></div>',
        unsafe_allow_html=True,
    )

    fig_sim = go.Figure()

    for ticker in valeurs_lignes.columns:
        serie = valeurs_lignes[ticker]
        fig_sim.add_trace(go.Scatter(
            x=serie.index, y=serie.values, name=PORTEFEUILLE[ticker]["nom"],
            mode="lines", line=dict(width=1, color=ARDOISE, dash="dot"), opacity=0.42,
            showlegend=False,
            hovertemplate="%{y:,.0f} €<extra>" + PORTEFEUILLE[ticker]["nom"] + "</extra>",
        ))

    fig_sim.add_trace(go.Scatter(
        x=valeur.index, y=valeur.values, name="Portefeuille total", mode="lines",
        line=dict(width=3.4, color=AMBRE),
        hovertemplate="<b>%{y:,.0f} €</b><extra>Portefeuille total</extra>",
    ))

    fig_sim.add_hline(
        y=capital, line=dict(color=FILET, width=1.4, dash="dash"),
        annotation_text=f"Capital investi · {fmt_eur(capital)}",
        annotation_position="top left",
        annotation_font=dict(color=ARDOISE, size=11.5),
    )
    fig_sim.add_trace(go.Scatter(
        x=[valeur.index[-1]], y=[valeur.iloc[-1]], mode="markers",
        marker=dict(size=11, color=AMBRE, line=dict(color=ENCRE, width=2)),
        showlegend=False, hoverinfo="skip",
    ))
    fig_sim.add_annotation(
        x=valeur.index[-1], y=valeur.iloc[-1],
        text=f"<b>{fmt_eur(valeur.iloc[-1])}</b>", showarrow=False, xanchor="right", yshift=26,
        font=dict(color=AMBRE, size=15, family="Playfair Display, serif"),
    )

    styliser(fig_sim, hauteur=500, marge_haut=30)
    fig_sim.update_layout(hovermode="x unified", showlegend=False)
    fig_sim.update_yaxes(tickformat=",.0f", ticksuffix=" €", separatethousands=True, type=type_axe)
    st.plotly_chart(fig_sim, config={"displaylogo": False})

    st.markdown(
        '<div class="bande-kpi">'
        + carte_kpi(fmt_eur(capital), "Investi au départ",
                    f"{fmt_eur(capital / len(cours.columns))} par ligne")
        + carte_kpi(fmt_eur(mesures["valeur_finale"]), "Valeur au terme",
                    f"au {fin_effective:%d/%m/%Y}")
        + carte_kpi(fmt_eur(mesures["valeur_finale"] - capital), "Plus-value latente",
                    "hors frais et hors fiscalité",
                    "#4FB79A" if mesures["valeur_finale"] >= capital else "#C8636F")
        + carte_kpi(fmt_pct(mesures["perf_totale"]), "Performance",
                    f"{fmt_pct(mesures['tcac'])} par an", AMBRE)
        + "</div>",
        unsafe_allow_html=True,
    )


    # --------------------------------------------------------------------------- #
    # 12. Risque
    # --------------------------------------------------------------------------- #
    st.markdown(
        '<div class="section"><div class="section-num">Risque</div>'
        '<div class="section-titre">Ce qu\'il a fallu supporter en chemin</div>'
        '<div class="section-sous">La performance ne se juge pas sans son coût psychologique : '
        'profondeur des reculs et régularité année après année.</div><div class="filet"></div></div>',
        unsafe_allow_html=True,
    )

    col_dd, col_an = st.columns([1.15, 1], gap="large")

    with col_dd:
        dd_pf = drawdown(valeur)
        fig_dd = go.Figure()
        if meilleur_indice:
            dd_ref = drawdown(indices_100[meilleur_indice])
            fig_dd.add_trace(go.Scatter(
                x=dd_ref.index, y=dd_ref.values, name=meilleur_indice, mode="lines",
                line=dict(width=1.3, color=COULEURS_INDICES.get(meilleur_indice, ARDOISE)),
                hovertemplate="%{y:.1f} %<extra>" + meilleur_indice + "</extra>",
            ))
        fig_dd.add_trace(go.Scatter(
            x=dd_pf.index, y=dd_pf.values, name="Portefeuille", mode="lines",
            line=dict(width=2.2, color=AMBRE), fill="tozeroy",
            fillcolor="rgba(216,144,42,0.13)",
            hovertemplate="<b>%{y:.1f} %</b><extra>Portefeuille</extra>",
        ))
        creux = dd_pf.idxmin()
        fig_dd.add_annotation(
            x=creux, y=dd_pf.min(), text=f"{dd_pf.min():.1f} %".replace(".", ","),
            showarrow=True, arrowhead=0, arrowcolor=FILET, ay=28, ax=0,
            font=dict(color=BLANC, size=12),
        )
        styliser(fig_dd, hauteur=380, marge_haut=40)
        fig_dd.update_layout(hovermode="x unified")
        fig_dd.update_yaxes(ticksuffix=" %")
        st.plotly_chart(fig_dd, config={"displaylogo": False})
        st.caption(f"Reculs depuis le plus haut · creux atteint le {creux:%d/%m/%Y}")

    with col_an:
        perf_an = annual_returns(valeur)
        ref_an = annual_returns(indices_100[meilleur_indice]) if meilleur_indice else pd.Series(dtype=float)

        fig_an = go.Figure()
        fig_an.add_trace(go.Bar(
            x=perf_an.index.astype(str), y=perf_an.values, name="Portefeuille",
            marker_color=[AMBRE if v >= 0 else "#8E5A33" for v in perf_an.values],
            hovertemplate="%{y:.1f} %<extra>Portefeuille</extra>",
        ))
        if not ref_an.empty:
            commun = perf_an.index.intersection(ref_an.index)
            fig_an.add_trace(go.Bar(
                x=commun.astype(str), y=ref_an.loc[commun].values, name=meilleur_indice,
                marker_color=COULEURS_INDICES.get(meilleur_indice, ARDOISE), opacity=0.75,
                hovertemplate="%{y:.1f} %<extra>" + meilleur_indice + "</extra>",
            ))
        fig_an.add_hline(y=0, line=dict(color=FILET, width=1))
        styliser(fig_an, hauteur=380, marge_haut=40)
        fig_an.update_layout(barmode="group", bargap=0.32, bargroupgap=0.08)
        fig_an.update_yaxes(ticksuffix=" %")
        st.plotly_chart(fig_an, config={"displaylogo": False})
        st.caption(
            f"Performance par année civile · {fmt_pct(mesures['mois_positifs'], 0, signe=False)} "
            "de mois positifs sur la période"
        )


    # --------------------------------------------------------------------------- #
    # 13. Contributeurs
    # --------------------------------------------------------------------------- #
    st.markdown(
        '<div class="section"><div class="section-num">Attribution</div>'
        '<div class="section-titre">Qui a fait la performance</div>'
        '<div class="section-sous">Contribution en points de performance du portefeuille, mesurée '
        'sur une allocation initiale strictement équipondérée.</div><div class="filet"></div></div>',
        unsafe_allow_html=True,
    )

    contrib = contributions(positions, capital)
    col_barres, col_poids = st.columns([1.25, 1], gap="large")

    with col_barres:
        c = contrib.sort_values("Contribution (pts)")
        noms = [PORTEFEUILLE[t]["nom"] for t in c["Ticker"]]
        fig_c = go.Figure(go.Bar(
            x=c["Contribution (pts)"], y=noms, orientation="h",
            marker=dict(color=[AMBRE if v >= 0 else "#7C4A5C" for v in c["Contribution (pts)"]]),
            text=[f"{v:+.1f}".replace(".", ",") for v in c["Contribution (pts)"]],
            textposition="outside", textfont=dict(color=BRUME, size=12),
            hovertemplate="%{y}<br>%{x:.2f} point(s)<extra></extra>",
            cliponaxis=False,
        ))
        fig_c.add_vline(x=0, line=dict(color=FILET, width=1))
        styliser(fig_c, hauteur=max(360, 30 * len(c)), marge_haut=20)
        fig_c.update_layout(margin=dict(l=10, r=54, t=20, b=10))
        fig_c.update_xaxes(showticklabels=False)
        fig_c.update_yaxes(showgrid=False, tickfont=dict(color=BRUME, size=12.5))
        st.plotly_chart(fig_c, config={"displaylogo": False})

    with col_poids:
        c2 = contrib.copy()
        c2["Secteur"] = c2["Ticker"].map(lambda t: PORTEFEUILLE[t]["secteur"])
        c2["Nom"] = c2["Ticker"].map(lambda t: PORTEFEUILLE[t]["nom"])
        palette = [AMBRE, "#B9782A", "#5B8FB9", "#4FB79A", "#A98BC9", "#C8636F",
                   "#7285AD", "#98A6B5", "#C89B6A", "#6FA0C0"]
        secteurs = sorted(c2["Secteur"].unique())
        couleur_secteur = {s: palette[i % len(palette)] for i, s in enumerate(secteurs)}

        fig_t = go.Figure(go.Treemap(
            labels=c2["Nom"], parents=[""] * len(c2), values=c2["Valeur finale (€)"],
            marker=dict(colors=[couleur_secteur[s] for s in c2["Secteur"]],
                        line=dict(color=ENCRE, width=2)),
            text=[f"{p:.1f} %".replace(".", ",") for p in c2["Poids final (%)"]],
            texttemplate="<b>%{label}</b><br>%{text}",
            textfont=dict(color=ENCRE, size=12, family="Inter, sans-serif"),
            hovertemplate="%{label}<br>%{value:,.0f} €<extra></extra>",
            tiling=dict(pad=2),
        ))
        styliser(fig_t, hauteur=max(360, 30 * len(c)), marge_haut=20)
        st.plotly_chart(fig_t, config={"displaylogo": False})
        st.caption("Poids de fin de période, couleur par secteur — la dérive des poids révèle les gagnantes.")

    # Concentration : ce que la performance doit à sa première ligne
    if not contrib.empty and mesures["perf_totale"] > 0:
        tete = contrib.iloc[0]
        nom_tete = PORTEFEUILLE[tete["Ticker"]]["nom"]
        part_perf = tete["Contribution (pts)"] / mesures["perf_totale"] * 100.0
        poids_depart = 100.0 / len(positions)
        trois_premieres = contrib.head(3)["Poids final (%)"].sum()

        if part_perf >= 40 or tete["Poids final (%)"] >= 25:
            st.markdown(
                f'<div class="alerte">'
                f'<b>La performance tient à une ligne.</b> {nom_tete} apporte '
                f'{fmt_nombre(tete["Contribution (pts)"], 1)} points sur les '
                f'{fmt_nombre(mesures["perf_totale"], 1)} du portefeuille, soit '
                f'<b>{fmt_pct(part_perf, 0, signe=False)} du résultat</b>. Partie à '
                f'{fmt_pct(poids_depart, 1, signe=False)} du capital, elle en représente aujourd\'hui '
                f'<b>{fmt_pct(tete["Poids final (%)"], 1, signe=False)}</b>, et les trois premières '
                f'lignes pèsent {fmt_pct(trois_premieres, 0, signe=False)} de l\'ensemble.<br>'
                f'Le portefeuille n\'est donc plus équipondéré : son sort dépend désormais '
                f'largement de cette seule valeur. Écrêter ramènerait le risque à sa cible '
                f'initiale, laisser courir suppose que la thèse reste intacte au cours actuel. '
                f'Le mode « équipondéré rééquilibré » de la barre latérale chiffre la première option.'
                f'</div>',
                unsafe_allow_html=True,
            )


    # --------------------------------------------------------------------------- #
    # 14. Détail des lignes
    # --------------------------------------------------------------------------- #
    st.markdown(
        f'<div class="section"><div class="section-num">Détail</div>'
        f'<div class="section-titre">Les {len(positions)} lignes, une par une</div>'
        f'<div class="filet"></div></div>',
        unsafe_allow_html=True,
    )

    detail = pd.DataFrame([{
        "Société": PORTEFEUILLE[p.ticker]["nom"],
        "Ticker": p.ticker,
        "Pays": PORTEFEUILLE[p.ticker]["pays"],
        "Secteur": PORTEFEUILLE[p.ticker]["secteur"],
        "Cotée en": "GBp" if PORTEFEUILLE[p.ticker]["devise"] == "GBX" else PORTEFEUILLE[p.ticker]["devise"],
        "Titres": fmt_titres(p.parts),
        "Investi": fmt_eur(p.montant_initial),
        "Valeur": fmt_eur(p.montant_final),
        "Plus-value": f'<span class="{"hausse" if p.plus_value >= 0 else "baisse"}">{fmt_eur(p.plus_value)}</span>',
        "Perf.": f'<span class="{"hausse" if p.performance >= 0 else "baisse"}">'
                 f'{fmt_pct(p.performance * 100)}</span>',
    } for p in sorted(positions, key=lambda x: x.performance, reverse=True)])

    st.markdown(
        tableau_html(detail, aligne_droite=["Titres", "Investi", "Valeur", "Plus-value", "Perf."]),
        unsafe_allow_html=True,
    )

    export = pd.DataFrame({"Portefeuille (€)": valeur})
    for nom, serie in indices_100.items():
        export[f"{nom} (base 100)"] = serie
    tampon = io.StringIO()
    export.round(4).to_csv(tampon, sep=";", decimal=",", encoding="utf-8")
    st.download_button(
        "Télécharger la série quotidienne (CSV)",
        data=tampon.getvalue().encode("utf-8-sig"),
        file_name=f"cto_never_far_away_{fin_effective:%Y%m%d}.csv",
        mime="text/csv",
    )


    # --------------------------------------------------------------------------- #
    # 15. Pied de page
    # --------------------------------------------------------------------------- #
    st.markdown('<div class="filet" style="margin-top:44px;"></div>', unsafe_allow_html=True)
    st.markdown(
        f"""
    <div class="pied">
      <b>{titre}</b> · courbes arrêtées au {fin_effective:%d/%m/%Y} ·
      page actualisée le {datetime.now():%d/%m/%Y à %H:%M}<br>
      Les courbes s'arrêtent à la dernière séance où les {len(cours.columns)} lignes ont toutes coté :
      un jour férié à Paris ou à Zurich décale donc le dernier point, même si Wall Street a ouvert.
      Le bandeau du haut, lui, donne le dernier cours connu de chaque valeur.<br>
      Source des cours : Yahoo Finance via yfinance, clôtures ajustées des dividendes et des divisions
      d'actions. Les cours de Londres sont fournis en pence et divisés par cent avant conversion.
      Taux de change quotidiens EURUSD, EURGBP et EURCHF.<br>
      Simulation hors frais de courtage, hors droits de garde et hors fiscalité : sur un compte-titres
      ordinaire, dividendes et plus-values sont imposables, l'écart avec le résultat net réel est donc
      significatif.<br>
      Document d'analyse personnelle. Ne constitue ni un conseil en investissement, ni une
      recommandation, ni une sollicitation d'achat ou de vente.
    </div>
    """,
        unsafe_allow_html=True,
    )
