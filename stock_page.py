"""
Fiche d'analyse détaillée d'une valeur, façon Baggr — thème sombre du CTO.

Point d'entrée unique : afficher_fiche(ticker, univers). La page reprend la
disposition observée sur Baggr (en-tête compact, onglets thématiques, cartes
de graphiques avec bannière Perf/CAGR, jauges de synthèse en bas de page)
tout en conservant la charte graphique sombre du projet CTO Never far away.

Toutes les données proviennent de yfinance via market_data.py, qui isole les
échecs réseau et les champs manquants : cette page ne fait donc jamais
planter Streamlit, elle affiche des replis ("donnée non disponible pour
cette valeur") quand une information n'est pas fournie par Yahoo Finance.
"""

from __future__ import annotations

from datetime import datetime

import numpy as np
import pandas as pd
import streamlit as st

import market_data as md
import stock_charts as sc

CONFIG_PLOTLY = {"displaylogo": False, "modeBarButtonsToRemove": ["lasso2d", "select2d"]}


# --------------------------------------------------------------------------- #
# 1. Mise en forme
# --------------------------------------------------------------------------- #
def fmt_pct(valeur: float | None, decimales: int = 1, signe: bool = True) -> str:
    if valeur is None or not np.isfinite(valeur):
        return "—"
    gabarit = f"{{:{'+' if signe else ''}.{decimales}f}}"
    return gabarit.format(valeur).replace(".", ",") + " %"


def fmt_nombre(valeur: float | None, decimales: int = 2) -> str:
    if valeur is None or not np.isfinite(valeur):
        return "—"
    return f"{valeur:.{decimales}f}".replace(".", ",")


def fmt_prix(valeur: float | None, devise: str = "") -> str:
    if valeur is None or not np.isfinite(valeur):
        return "—"
    texte = f"{valeur:,.2f}".replace(",", " ").replace(".", ",")
    return f"{texte} {devise}".strip()


def fmt_grand_nombre(valeur: float | None, devise: str = "") -> str:
    """Montant compact : 16,2 Md / 462 M / 3 204 — pour axes et cartes."""
    if valeur is None or not np.isfinite(valeur):
        return "—"
    signe = "-" if valeur < 0 else ""
    v = abs(valeur)
    if v >= 1e9:
        texte = f"{v / 1e9:,.1f} Md".replace(",", " ").replace(".", ",")
    elif v >= 1e6:
        texte = f"{v / 1e6:,.0f} M".replace(",", " ")
    else:
        texte = f"{v:,.0f}".replace(",", " ")
    return f"{signe}{texte} {devise}".strip()


def carte_kpi(valeur: str, libelle: str, note: str = "", couleur: str = sc.BLANC) -> str:
    return (
        f'<div class="kpi-baggr"><div class="kpi-baggr-valeur" style="color:{couleur};">{valeur}</div>'
        f'<div class="kpi-baggr-libelle">{libelle}</div>'
        f'<div class="kpi-baggr-note">{note}</div></div>'
    )


def tableau_html(df: pd.DataFrame) -> str:
    entetes = "".join(f"<th class='num'>{c}</th>" if i > 0 else f"<th>{c}</th>" for i, c in enumerate(df.columns))
    lignes = []
    for _, r in df.iterrows():
        cellules = "".join(f"<td class='num'>{r[c]}</td>" if i > 0 else f"<td>{r[c]}</td>" for i, c in enumerate(df.columns))
        lignes.append(f"<tr>{cellules}</tr>")
    return f"<table class='tbl-baggr'><thead><tr>{entetes}</tr></thead><tbody>{''.join(lignes)}</tbody></table>"


def injecter_css() -> None:
    st.markdown(
        f"""
    <style>
    .carte-baggr {{
        background: {sc.PANNEAU}; border: 1px solid {sc.FILET}; border-radius: 12px;
        padding: 16px 18px 14px 18px; margin-bottom: 16px; height: 100%;
    }}
    .carte-titre {{
        font-size: 13.5px; font-weight: 600; color: {sc.BLANC}; margin-bottom: 4px;
        letter-spacing: .01em;
    }}
    .bandeau-carte {{ display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap; }}
    .pastille {{
        font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 999px;
        background: rgba(171,187,202,.08);
    }}
    .pastille-hausse {{ color: {sc.HAUSSE}; background: rgba(34,197,94,.12); }}
    .pastille-baisse {{ color: {sc.BAISSE}; background: rgba(239,68,68,.12); }}
    .pastille-neutre {{ color: {sc.ARDOISE}; }}

    .jauge-ligne {{ display: flex; align-items: center; gap: 10px; padding: 6px 0; }}
    .jauge-libelle {{ flex: 0 0 46%; font-size: 12.5px; color: {sc.BRUME}; }}
    .jauge-valeur {{ flex: 0 0 18%; font-size: 12.5px; font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }}
    .jauge-piste {{ flex: 1; height: 6px; background: rgba(171,187,202,.12); border-radius: 999px; overflow: hidden; }}
    .jauge-remplissage {{ height: 100%; border-radius: 999px; }}

    .kpi-baggr-valeur {{ font-size: 22px; font-weight: 700; font-variant-numeric: tabular-nums; }}
    .kpi-baggr-libelle {{ font-size: 11.5px; color: {sc.BRUME}; margin-top: 4px; }}
    .kpi-baggr-note {{ font-size: 10.5px; color: {sc.ARDOISE}; margin-top: 1px; }}

    .tbl-baggr {{ width: 100%; border-collapse: collapse; font-size: 13px; font-variant-numeric: tabular-nums; }}
    .tbl-baggr th {{
        text-align: right; font-size: 10.5px; letter-spacing: .07em; text-transform: uppercase;
        color: {sc.ARDOISE}; font-weight: 600; padding: 8px 10px; border-bottom: 1px solid {sc.FILET};
    }}
    .tbl-baggr th:first-child {{ text-align: left; }}
    .tbl-baggr td {{ text-align: right; padding: 8px 10px; border-bottom: 1px solid rgba(171,187,202,.06); color: {sc.BRUME}; }}
    .tbl-baggr td:first-child {{ text-align: left; color: {sc.BLANC}; }}
    .tbl-baggr tbody tr:hover td {{ background: rgba(171,187,202,.04); }}

    .fiche-logo {{
        width: 46px; height: 46px; border-radius: 12px; background: {sc.AMBRE};
        display: flex; align-items: center; justify-content: center;
        font-size: 20px; font-weight: 700; color: {sc.ENCRE};
    }}
    .fiche-nom {{ font-size: 21px; font-weight: 700; color: {sc.BLANC}; margin: 0; }}
    .fiche-sous {{ font-size: 12.5px; color: {sc.ARDOISE}; margin-top: 2px; }}
    .fiche-prix {{ font-size: 24px; font-weight: 700; color: {sc.BLANC}; font-variant-numeric: tabular-nums; }}
    .fiche-var {{ font-size: 13.5px; font-weight: 600; margin-top: 2px; }}
    .badge-score {{
        display: inline-flex; align-items: center; justify-content: center;
        padding: 8px 16px; border-radius: 10px; font-size: 17px; font-weight: 700;
        font-variant-numeric: tabular-nums;
    }}
    .badge-score-note {{ font-size: 10.5px; font-weight: 500; color: {sc.ARDOISE}; text-align: center; margin-top: 4px; }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 12px; }}
    .stTabs [data-baseweb="tab-list"] {{ gap: 4px; border-bottom: 1px solid {sc.FILET}; }}
    .stTabs [data-baseweb="tab"] {{ color: {sc.ARDOISE}; font-size: 13.5px; padding: 8px 4px; }}
    .stTabs [aria-selected="true"] {{ color: {sc.BLANC} !important; border-bottom-color: {sc.AMBRE} !important; }}
    </style>
    """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# 2. En-tête
# --------------------------------------------------------------------------- #
def _couleur_score(score: float) -> str:
    if score >= 14:
        return sc.HAUSSE
    if score >= 8:
        return sc.AMBRE
    return sc.BAISSE


def afficher_entete(ticker: str, meta: dict, info: dict, score: float) -> None:
    nom = info.get("longName") or info.get("shortName") or meta.get("nom", ticker)
    devise = info.get("currency", meta.get("devise", ""))
    prix = info.get("currentPrice") or info.get("regularMarketPrice")
    cloture_prec = info.get("previousClose") or info.get("regularMarketPreviousClose")
    variation_pct = info.get("regularMarketChangePercent")
    if variation_pct is None and prix and cloture_prec:
        variation_pct = (prix / cloture_prec - 1.0) * 100.0
    bourse = info.get("fullExchangeName") or info.get("exchange") or meta.get("pays", "")

    col_logo, col_nom, col_prix, col_score = st.columns([0.55, 3.2, 1.6, 1.1], gap="small")
    with col_logo:
        st.markdown(f'<div class="fiche-logo">{ticker[0]}</div>', unsafe_allow_html=True)
    with col_nom:
        st.markdown(f'<p class="fiche-nom">{nom}</p>', unsafe_allow_html=True)
        st.markdown(f'<div class="fiche-sous">{ticker} · {bourse}</div>', unsafe_allow_html=True)
    with col_prix:
        couleur_var = sc.couleur_signe(variation_pct)
        fleche = "▲" if (variation_pct or 0) >= 0 else "▼"
        st.markdown(f'<div class="fiche-prix">{fmt_prix(prix, devise)}</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="fiche-var" style="color:{couleur_var};">{fleche} {fmt_pct(variation_pct, 2)}</div>',
            unsafe_allow_html=True,
        )
    with col_score:
        couleur = _couleur_score(score)
        st.markdown(
            f'<div class="badge-score" style="color:{couleur}; border:1px solid {couleur}44; '
            f'background:{couleur}1A;">{fmt_nombre(score, 1)}/20</div>'
            f'<div class="badge-score-note">Score qualité (interne)</div>',
            unsafe_allow_html=True,
        )
    st.markdown(f'<div style="height:1px;background:{sc.FILET};margin:14px 0 18px 0;"></div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# 3. Onglet Résumé
# --------------------------------------------------------------------------- #
def onglet_resume(ticker: str, meta: dict, info: dict, historique: pd.DataFrame,
                  indicateurs: pd.DataFrame, score: float, detail_score: dict[str, float]) -> None:
    devise = info.get("currency", meta.get("devise", ""))

    bande = "".join([
        carte_kpi(fmt_grand_nombre(info.get("marketCap"), devise), "Capitalisation"),
        carte_kpi(fmt_nombre(info.get("trailingPE")), "PER (trailing)"),
        carte_kpi(fmt_pct((info.get("dividendYield") or 0)), "Rendement dividende"),
        carte_kpi(
            f"{fmt_prix(info.get('fiftyTwoWeekLow'), '')} – {fmt_prix(info.get('fiftyTwoWeekHigh'), devise)}",
            "Range 52 semaines",
        ),
        carte_kpi(fmt_nombre(info.get("beta")), "Bêta"),
        carte_kpi(
            f"{(info.get('fullTimeEmployees') or 0):,}".replace(",", " ") if info.get("fullTimeEmployees") else "—",
            "Effectifs",
        ),
    ])
    st.markdown(f'<div class="carte-baggr" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:4px;">{bande}</div>', unsafe_allow_html=True)

    col_graph, col_score = st.columns([1.6, 1], gap="large")
    with col_graph:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Cours sur un an</div>', unsafe_allow_html=True)
            if not historique.empty:
                h = historique["Close"].dropna().tail(252)
                fig = sc.fig_lignes_multi(list(h.index.strftime("%d/%m/%y")), {"Cours": h}, [sc.AMBRE], hauteur=280, suffixe="")
                fig.update_traces(mode="lines")
                fig.update_xaxes(tickvals=list(h.index.strftime("%d/%m/%y"))[::max(1, len(h)//6)])
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"resume_cours_{ticker}", width="stretch")
            else:
                st.caption("Historique de cours non disponible pour le moment.")

    with col_score:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Détail du score qualité</div>', unsafe_allow_html=True)
            for libelle, note in detail_score.items():
                st.markdown(sc.jauge_html(libelle, note, echelle=4.0, suffixe=" /4"), unsafe_allow_html=True)

    if detail_score:
        tri = sorted(detail_score.items(), key=lambda kv: kv[1], reverse=True)
        forces = [n for n, v in tri if v >= 3.0][:3]
        vigilances = [n for n, v in tri if v <= 1.8][:3]
        texte = ""
        if forces:
            texte += f"<b style='color:{sc.HAUSSE}'>Points forts :</b> {', '.join(forces)}. "
        if vigilances:
            texte += f"<b style='color:{sc.BAISSE}'>Points de vigilance :</b> {', '.join(vigilances)}."
        if texte:
            st.markdown(f'<div class="carte-baggr">{texte}</div>', unsafe_allow_html=True)

    resume = info.get("longBusinessSummary")
    if resume:
        with st.expander("Présentation de l'activité"):
            st.write(resume)


# --------------------------------------------------------------------------- #
# 4. Onglet Quantitatif
# --------------------------------------------------------------------------- #
def _carte_bar(colonne, titre: str, serie: pd.Series, labels: list[str], couleur: str, ticker: str, cle: str, suffixe: str = "") -> None:
    with colonne:
        with st.container(border=True):
            st.markdown(f'<div class="carte-titre">{titre}</div>', unsafe_allow_html=True)
            if serie.dropna().empty:
                st.caption("Donnée non disponible pour cette valeur.")
                return
            fig = sc.fig_barres(labels, serie, couleur=couleur, suffixe=suffixe, hauteur=250)
            st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"{cle}_{ticker}", width="stretch")
            st.markdown(sc.banniere_perf_cagr(md.performance_totale(serie), md.cagr(serie)), unsafe_allow_html=True)


def onglet_quantitatif(ticker: str, indicateurs: pd.DataFrame, info: dict) -> None:
    if indicateurs.empty:
        st.warning("Aucun état financier annuel n'a été retourné par Yahoo Finance pour cette valeur.")
        return

    labels = [f"FY{d.year % 100:02d}" for d in indicateurs.index]
    devise = info.get("financialCurrency", info.get("currency", ""))

    c1, c2, c3 = st.columns(3, gap="medium")
    _carte_bar(c1, "Chiffre d'affaires", indicateurs["revenu"], labels, sc.BLEU, ticker, "revenu")
    _carte_bar(c2, "Bénéfices nets", indicateurs["resultat_net"], labels, sc.AMBRE, ticker, "net")
    _carte_bar(c3, "Free Cash Flow", indicateurs["fcf"], labels, sc.HAUSSE_DOUX, ticker, "fcf")

    c4, c5, c6 = st.columns(3, gap="medium")
    with c4:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Marges historiques</div>', unsafe_allow_html=True)
            series = {
                "Brute": indicateurs["marge_brute"], "Opérationnelle": indicateurs["marge_operationnelle"],
                "Nette": indicateurs["marge_nette"],
            }
            series = {k: v for k, v in series.items() if v.notna().any()}
            if series:
                fig = sc.fig_lignes_multi(labels, series, [sc.BLEU, sc.AMBRE, sc.HAUSSE_DOUX], hauteur=250)
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"marges_{ticker}", width="stretch")
            else:
                st.caption("Donnée non disponible pour cette valeur.")
    with c5:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Retours sur capitaux</div>', unsafe_allow_html=True)
            series = {"ROE": indicateurs["roe"], "ROIC": indicateurs["roic"], "ROCE": indicateurs["roce"]}
            series = {k: v for k, v in series.items() if v.notna().any()}
            if series:
                fig = sc.fig_lignes_multi(labels, series, [sc.AMBRE, sc.BLEU, sc.VIOLET], hauteur=250)
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"retours_{ticker}", width="stretch")
            else:
                st.caption("Donnée non disponible pour cette valeur.")
    with c6:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Trésorerie vs Dette</div>', unsafe_allow_html=True)
            if indicateurs["tresorerie"].notna().any() or indicateurs["dette_totale"].notna().any():
                fig = sc.fig_barres_lignes(
                    labels,
                    {"Trésorerie": indicateurs["tresorerie"], "Dette totale": indicateurs["dette_totale"]},
                    [sc.HAUSSE_DOUX, sc.BAISSE_DOUX],
                    ligne=indicateurs["dette_nette_ebitda"], nom_ligne="Dette nette / EBITDA", hauteur=250,
                )
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"dette_{ticker}", width="stretch")
            else:
                st.caption("Donnée non disponible pour cette valeur.")

    c7, c8, c9 = st.columns(3, gap="medium")
    _carte_bar(c7, "Actions en circulation", indicateurs["actions_en_circulation"], labels, sc.VIOLET, ticker, "actions")
    with c8:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Dépenses (% du CA)</div>', unsafe_allow_html=True)
            series = {
                "R&D / CA": indicateurs["rd"] / indicateurs["revenu"] * 100.0,
                "CAPEX / CA": -indicateurs["capex"] / indicateurs["revenu"] * 100.0,
                "Rém. en actions / CA": indicateurs["remuneration_actions"] / indicateurs["revenu"] * 100.0,
            }
            series = {k: v for k, v in series.items() if v.notna().any()}
            if series:
                fig = sc.fig_lignes_multi(labels, series, [sc.VIOLET, sc.AMBRE, sc.BAISSE_DOUX], hauteur=250)
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"depenses_{ticker}", width="stretch")
            else:
                st.caption("Donnée non disponible pour cette valeur.")
    with c9:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Résultat d\'exploitation</div>', unsafe_allow_html=True)
            serie = indicateurs["resultat_exploitation"]
            if serie.notna().any():
                fig = sc.fig_barres(labels, serie, couleur=sc.GRIS_BLEU, hauteur=250)
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"exploitation_{ticker}", width="stretch")
                st.markdown(sc.banniere_perf_cagr(md.performance_totale(serie), md.cagr(serie)), unsafe_allow_html=True)
            else:
                st.caption("Donnée non disponible pour cette valeur.")

    st.caption(
        "Historique limité aux exercices annuels renvoyés par Yahoo Finance (généralement 4 à 5 ans). "
        "ROIC, ROCE et WACC sont des estimations calculées à partir des lignes disponibles, pas des "
        "valeurs publiées par l'entreprise."
    )

    # ---- Jauges de synthèse ---------------------------------------------- #
    st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
    g1, g2, g3 = st.columns(3, gap="medium")
    with g1:
        st.markdown(
            sc.bloc_jauges("Rentabilité (dernier exercice)", [
                ("Marge brute", _dernier(indicateurs["marge_brute"]), 80, " %"),
                ("Marge opérationnelle", _dernier(indicateurs["marge_operationnelle"]), 40, " %"),
                ("Marge nette", _dernier(indicateurs["marge_nette"]), 30, " %"),
                ("Marge FCF", _dernier(indicateurs["marge_fcf"]), 30, " %"),
                ("WACC estimé", _dernier(indicateurs["wacc"]), 15, " %"),
            ]), unsafe_allow_html=True,
        )
    with g2:
        st.markdown(
            sc.bloc_jauges("Retours sur capitaux", [
                ("ROE — dernier exercice", _dernier(indicateurs["roe"]), 35, " %"),
                ("ROE — moyenne 3 ans", _moyenne(indicateurs["roe"], 3), 35, " %"),
                ("ROIC — dernier exercice", _dernier(indicateurs["roic"]), 25, " %"),
                ("ROIC — moyenne 3 ans", _moyenne(indicateurs["roic"], 3), 25, " %"),
                ("ROCE — dernier exercice", _dernier(indicateurs["roce"]), 25, " %"),
            ]), unsafe_allow_html=True,
        )
    with g3:
        croissance_3a = md.cagr_sur(indicateurs["revenu"], 3)
        croissance_5a = md.cagr_sur(indicateurs["revenu"], 5)
        predict = md.predictibilite_ca(indicateurs["revenu"])
        dette_ebitda = _dernier(indicateurs["dette_nette_ebitda"])
        st.markdown(
            sc.bloc_jauges("Croissance & solidité", [
                ("CA — CAGR 3 ans", croissance_3a, 20, " %"),
                ("CA — CAGR 5 ans", croissance_5a, 20, " %"),
                ("Prédictibilité du CA", predict, 100, " %"),
                ("Dette nette / EBITDA", -dette_ebitda if dette_ebitda is not None else None, 4, "x"),
            ]), unsafe_allow_html=True,
        )


def _dernier(serie: pd.Series) -> float | None:
    s = serie.dropna()
    return float(s.iloc[-1]) if not s.empty else None


def _moyenne(serie: pd.Series, n: int) -> float | None:
    s = serie.dropna().tail(n)
    return float(s.mean()) if not s.empty else None


# --------------------------------------------------------------------------- #
# 5. Onglet Résultats
# --------------------------------------------------------------------------- #
def onglet_resultats(ticker: str, info: dict, historique: pd.DataFrame, analystes: dict) -> None:
    c1, c2, c3 = st.columns(3, gap="medium")

    with c1:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Objectifs de cours</div>', unsafe_allow_html=True)
            cibles = analystes.get("cibles", {})
            bas = cibles.get("low", info.get("targetLowPrice"))
            moyen = cibles.get("mean", info.get("targetMeanPrice"))
            haut = cibles.get("high", info.get("targetHighPrice"))
            if not historique.empty and any(v for v in [bas, moyen, haut]):
                fig = sc.fig_projection_cours(historique["Close"], bas, moyen, haut, hauteur=260)
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"cibles_{ticker}", width="stretch")
                dernier = float(historique["Close"].dropna().iloc[-1])
                perf_haut = (haut / dernier - 1) * 100 if haut else None
                perf_moy = (moyen / dernier - 1) * 100 if moyen else None
                perf_bas = (bas / dernier - 1) * 100 if bas else None
                st.markdown(
                    f'<div class="bandeau-carte">'
                    f'<span class="pastille pastille-hausse">High : {fmt_pct(perf_haut)}</span>'
                    f'<span class="pastille pastille-neutre">Avg : {fmt_pct(perf_moy)}</span>'
                    f'<span class="pastille pastille-baisse">Low : {fmt_pct(perf_bas)}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("Objectifs de cours non disponibles pour cette valeur.")

    with c2:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Prévisions du chiffre d\'affaires</div>', unsafe_allow_html=True)
            _figure_prevision(analystes.get("prevision_ca"), ticker, "prevision_ca")

    with c3:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Prévisions des EPS</div>', unsafe_allow_html=True)
            _figure_prevision(analystes.get("prevision_eps"), ticker, "prevision_eps")

    c4, c5, c6 = st.columns(3, gap="medium")

    with c4:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Surprises sur les résultats (EPS)</div>', unsafe_allow_html=True)
            surprises = analystes.get("surprises_eps", pd.DataFrame())
            colonne_surp = next((c for c in surprises.columns if "surprise" in c.lower()), None) if not surprises.empty else None
            if colonne_surp is not None:
                # yfinance renvoie déjà « Surprise(%) » sous forme de pourcentage (5.71 = +5,71 %).
                s = pd.to_numeric(surprises[colonne_surp], errors="coerce").dropna()
                if not s.empty:
                    labels = [f"{i.strftime('%m/%y')}" if hasattr(i, "strftime") else str(i) for i in s.index][-10:]
                    fig = sc.fig_surprises_eps(labels, s.tail(10), hauteur=260)
                    st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"surprises_{ticker}", width="stretch")
                    reussies = int((s > 0).sum())
                    total = int(s.notna().sum())
                    st.markdown(
                        f'<div class="bandeau-carte">'
                        f'<span class="pastille pastille-hausse">Beat : {reussies}/{total}</span>'
                        f'<span class="pastille pastille-baisse">Miss : {total - reussies}/{total}</span></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Historique de surprises non disponible pour cette valeur.")
            else:
                st.caption("Historique de surprises non disponible pour cette valeur.")

    with c5:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Répartition des avis d\'analystes</div>', unsafe_allow_html=True)
            reco = analystes.get("recommandations", pd.DataFrame())
            categories = ["strongBuy", "buy", "hold", "sell", "strongSell"]
            libelles = {"strongBuy": "Achat fort", "buy": "Achat", "hold": "Conserver", "sell": "Vente", "strongSell": "Vente forte"}
            couleurs = {"strongBuy": sc.HAUSSE, "buy": sc.HAUSSE_DOUX, "hold": sc.AMBRE, "sell": sc.BAISSE_DOUX, "strongSell": sc.BAISSE}
            if not reco.empty and all(c in reco.columns for c in categories):
                derniere = reco.iloc[0]
                valeurs = [derniere.get(c, 0) for c in categories]
                if sum(valeurs) > 0:
                    fig = sc.fig_donut([libelles[c] for c in categories], valeurs, [couleurs[c] for c in categories], hauteur=260)
                    st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"avis_{ticker}", width="stretch")
                else:
                    st.caption("Aucun avis d'analyste recensé.")
            else:
                cle = info_cle = info.get("recommendationKey")
                if cle:
                    st.metric("Recommandation consensus", cle.replace("_", " ").title())
                    st.caption(f"{info.get('numberOfAnalystOpinions', '—')} analyste(s) suivent cette valeur.")
                else:
                    st.caption("Notes d'analystes non disponibles pour cette valeur.")

    with c6:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Score global (interne)</div>', unsafe_allow_html=True)
            recommandation_moy = info.get("recommendationMean")
            note_reco = (5 - recommandation_moy) / 4 * 100 if recommandation_moy else None
            st.markdown(sc.jauge_html("Consensus analystes", note_reco, 100, " /100"), unsafe_allow_html=True)
            pe = info.get("trailingPE")
            note_pe = 100 - min(max((pe or 25) / 40 * 100, 0), 100) if pe else None
            st.markdown(sc.jauge_html("Valorisation (P/E, plus bas = mieux noté)", note_pe, 100, " /100"), unsafe_allow_html=True)
            st.markdown(sc.jauge_html("Objectif moyen vs cours", (info.get('targetMeanPrice', 0) / info.get('currentPrice', 1) - 1) * 100
                                      if info.get('currentPrice') and info.get('targetMeanPrice') else None, 30, " %"), unsafe_allow_html=True)


def _figure_prevision(df: pd.DataFrame | None, ticker: str, cle: str) -> None:
    if df is None or df.empty:
        st.caption("Prévisions non disponibles pour cette valeur.")
        return
    colonne = next((c for c in ["avg", "average", "0y"] if c in df.columns), df.columns[0] if len(df.columns) else None)
    if colonne is None:
        st.caption("Prévisions non disponibles pour cette valeur.")
        return
    serie = pd.to_numeric(df[colonne], errors="coerce").dropna()
    if serie.empty:
        st.caption("Prévisions non disponibles pour cette valeur.")
        return
    fig = sc.fig_lignes_multi(list(serie.index.astype(str)), {"Consensus": serie}, [sc.AMBRE], hauteur=260, suffixe="")
    st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"{cle}_{ticker}", width="stretch")
    growth_col = next((c for c in ["growth"] if c in df.columns), None)
    if growth_col:
        st.caption(f"Croissance attendue (consensus) : {fmt_pct(pd.to_numeric(df[growth_col], errors='coerce').iloc[-1] * 100)}")


# --------------------------------------------------------------------------- #
# 6. Onglet Finances (+ répartition d'activité)
# --------------------------------------------------------------------------- #
def onglet_finances(ticker: str, etats: dict[str, pd.DataFrame], indicateurs: pd.DataFrame,
                    repartition: dict[str, pd.Series], devise: str) -> None:
    c1, c2 = st.columns(2, gap="medium")
    with c1:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Répartition du CA par segment</div>', unsafe_allow_html=True)
            seg = repartition.get("segments", pd.Series(dtype="float64"))
            if not seg.empty:
                fig = sc.fig_donut(list(seg.index), list(seg.values), hauteur=300)
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"seg_{ticker}", width="stretch")
            else:
                st.caption("Yahoo Finance ne publie pas la répartition sectorielle du chiffre d'affaires pour cette valeur.")
    with c2:
        with st.container(border=True):
            st.markdown('<div class="carte-titre">Répartition du CA par géographie</div>', unsafe_allow_html=True)
            geo = repartition.get("geographie", pd.Series(dtype="float64"))
            if not geo.empty:
                fig = sc.fig_donut(list(geo.index), list(geo.values), hauteur=300)
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"geo_{ticker}", width="stretch")
            else:
                st.caption("Yahoo Finance ne publie pas la répartition géographique du chiffre d'affaires pour cette valeur.")

    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)

    onglets_etats = st.tabs(["Compte de résultat", "Bilan", "Flux de trésorerie"])
    lignes_cr = [("Chiffre d'affaires", "revenu"), ("Marge brute", "marge_brute_val"),
                ("Résultat d'exploitation", "resultat_exploitation"), ("Résultat net", "resultat_net")]
    lignes_bilan = [("Trésorerie", "tresorerie"), ("Dette totale", "dette_totale"), ("Actifs totaux", "actifs_totaux"),
                    ("Capitaux propres", "capitaux_propres"), ("Goodwill", "goodwill")]
    lignes_flux = [("Flux d'exploitation", "flux_exploitation"), ("CAPEX", "capex"), ("Free Cash Flow", "fcf"),
                  ("R&D", "rd"), ("Rémunération en actions", "remuneration_actions")]

    if indicateurs.empty:
        for onglet in onglets_etats:
            with onglet:
                st.caption("États financiers non disponibles pour cette valeur.")
        return

    labels = [f"FY{d.year % 100:02d}" for d in indicateurs.index]
    for onglet, lignes in zip(onglets_etats, [lignes_cr, lignes_bilan, lignes_flux]):
        with onglet:
            data = {"Poste": [nom for nom, _ in lignes]}
            for i, label in enumerate(labels):
                data[label] = [fmt_grand_nombre(indicateurs[cle].iloc[i] if cle in indicateurs else None, devise) for _, cle in lignes]
            st.markdown(tableau_html(pd.DataFrame(data)), unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# 7. Onglet Société
# --------------------------------------------------------------------------- #
def onglet_societe(ticker: str, meta: dict, info: dict) -> None:
    c1, c2, c3, c4 = st.columns(4, gap="medium")
    for col, (valeur, libelle) in zip(
        [c1, c2, c3, c4],
        [
            (info.get("sector", meta.get("secteur", "—")), "Secteur"),
            (info.get("industry", "—"), "Industrie"),
            (info.get("country", meta.get("pays", "—")), "Pays"),
            (f"{(info.get('fullTimeEmployees') or 0):,}".replace(",", " ") if info.get("fullTimeEmployees") else "—", "Effectifs"),
        ],
    ):
        with col:
            st.markdown(f'<div class="carte-baggr">{carte_kpi(str(valeur), libelle)}</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown('<div class="carte-titre">Présentation</div>', unsafe_allow_html=True)
        resume = info.get("longBusinessSummary")
        st.write(resume if resume else "Description non disponible pour cette valeur.")
        infos_pratiques = []
        if info.get("website"):
            infos_pratiques.append(f"[Site officiel]({info['website']})")
        if info.get("city"):
            infos_pratiques.append(f"Siège : {info.get('city')}, {info.get('country', '')}")
        if infos_pratiques:
            st.caption(" · ".join(infos_pratiques))


# --------------------------------------------------------------------------- #
# 8. Onglet Thèses
# --------------------------------------------------------------------------- #
def onglet_theses(ticker: str, detail_score: dict[str, float]) -> None:
    if detail_score:
        tri = sorted(detail_score.items(), key=lambda kv: kv[1], reverse=True)
        col_forces, col_vigilance = st.columns(2, gap="medium")
        with col_forces:
            with st.container(border=True):
                st.markdown(f'<div class="carte-titre" style="color:{sc.HAUSSE}">Points forts (thèse qualité)</div>', unsafe_allow_html=True)
                for nom, note in tri[:3]:
                    st.markdown(sc.jauge_html(nom, note, echelle=4.0, suffixe=" /4"), unsafe_allow_html=True)
        with col_vigilance:
            with st.container(border=True):
                st.markdown(f'<div class="carte-titre" style="color:{sc.BAISSE}">Points de vigilance</div>', unsafe_allow_html=True)
                for nom, note in tri[-3:]:
                    st.markdown(sc.jauge_html(nom, note, echelle=4.0, suffixe=" /4"), unsafe_allow_html=True)
        st.caption(
            "Grille générée automatiquement à partir des ratios disponibles via yfinance (rentabilité des "
            "capitaux, marges, croissance, conversion en cash, endettement, prédictibilité) — inspirée des "
            "critères de qualité mis en avant par Warren Buffett et Charlie Munger, sans en reproduire la "
            "méthodologie exacte. Ce n'est pas une analyse exhaustive ni un conseil en investissement."
        )
    else:
        st.info("Données insuffisantes pour générer une grille de thèse automatique sur cette valeur.")

    cle_note = f"these_perso_{ticker}"
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown('<div class="carte-titre">Votre thèse d\'investissement</div>', unsafe_allow_html=True)
        st.text_area(
            "Notes personnelles (conservées le temps de la session uniquement)",
            key=cle_note, height=160,
            placeholder="Pourquoi cette valeur dans le portefeuille ? Catalyseurs attendus, risques identifiés, "
                       "seuil de remise en cause de la thèse...",
            label_visibility="collapsed",
        )
        st.caption("Ces notes ne sont pas sauvegardées entre deux sessions de l'application.")


# --------------------------------------------------------------------------- #
# 9. Onglet Valorisation
# --------------------------------------------------------------------------- #
def onglet_valorisation(ticker: str, info: dict, indicateurs: pd.DataFrame, historique: pd.DataFrame) -> None:
    devise = info.get("currency", "")
    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    for col, (val, lib) in zip(
        [c1, c2, c3, c4, c5],
        [
            (fmt_nombre(info.get("trailingPE")), "P/E (trailing)"),
            (fmt_nombre(info.get("forwardPE")), "P/E (forward)"),
            (fmt_nombre(info.get("priceToBook")), "P/B"),
            (fmt_nombre(info.get("enterpriseToEbitda")), "EV/EBITDA"),
            (fmt_nombre(info.get("pegRatio")), "PEG"),
        ],
    ):
        with col:
            st.markdown(f'<div class="carte-baggr">{carte_kpi(val, lib)}</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:10px;'></div>", unsafe_allow_html=True)
    st.markdown('<div class="carte-titre" style="font-size:15px;">Calculateur de prix juste (indicatif)</div>', unsafe_allow_html=True)
    st.caption(
        "Actualisation simple des bénéfices futurs à un multiple de sortie choisi par vous. Hypothèses "
        "modifiables ci-dessous : ceci reste un ordre de grandeur, pas une valorisation professionnelle."
    )

    eps = info.get("trailingEps")
    prix_actuel = info.get("currentPrice") or info.get("regularMarketPrice")
    wacc_estime = _dernier(indicateurs["wacc"]) if not indicateurs.empty and "wacc" in indicateurs else None

    col_param, col_resultat = st.columns([1, 1.3], gap="large")
    with col_param:
        croissance = st.slider("Croissance annuelle des bénéfices attendue (%)", -10.0, 30.0, 8.0, 0.5, key=f"croiss_{ticker}")
        horizon = st.slider("Horizon (années)", 1, 10, 5, key=f"horizon_{ticker}")
        multiple_sortie = st.slider("Multiple de sortie (P/E)", 5.0, 40.0, float(info.get("trailingPE") or 18.0), 0.5, key=f"multiple_{ticker}")
        taux_actualisation = st.slider(
            "Taux d'actualisation (%)", 4.0, 15.0, float(wacc_estime) if wacc_estime else 9.0, 0.5, key=f"taux_{ticker}",
            help="Pré-rempli avec le WACC estimé de la valeur quand disponible.",
        )

    with col_resultat:
        if eps and eps > 0 and prix_actuel:
            eps_futur = eps * (1 + croissance / 100) ** horizon
            prix_cible_futur = eps_futur * multiple_sortie
            valeur_actualisee = prix_cible_futur / (1 + taux_actualisation / 100) ** horizon
            marge_securite = (valeur_actualisee / prix_actuel - 1) * 100

            st.markdown(
                '<div class="carte-baggr">'
                + carte_kpi(fmt_prix(valeur_actualisee, devise), "Valeur actualisée estimée")
                + carte_kpi(fmt_prix(prix_actuel, devise), "Cours actuel")
                + carte_kpi(fmt_pct(marge_securite), "Marge de sécurité implicite",
                           couleur=sc.couleur_signe(marge_securite))
                + "</div>",
                unsafe_allow_html=True,
            )
            if not historique.empty:
                h = historique["Close"].dropna().tail(504)
                fig = sc.fig_lignes_multi(list(h.index.strftime("%m/%y")), {"Cours": h}, [sc.BLANC], hauteur=240, suffixe="")
                fig.add_hline(y=valeur_actualisee, line=dict(color=sc.AMBRE, width=1.6, dash="dash"))
                st.plotly_chart(fig, config=CONFIG_PLOTLY, key=f"valo_chart_{ticker}", width="stretch")
        else:
            st.info("Bénéfice par action (trailing EPS) non disponible : le calculateur ne peut pas s'appliquer à cette valeur.")


# --------------------------------------------------------------------------- #
# 10. Assemblage de la page
# --------------------------------------------------------------------------- #
def afficher_fiche(ticker: str, univers: dict[str, dict]) -> None:
    injecter_css()
    meta = univers.get(ticker, {"nom": ticker, "devise": "", "pays": "", "secteur": ""})

    with st.spinner(f"Récupération des données fondamentales de {meta.get('nom', ticker)}…"):
        info = md.get_info(ticker)
        historique = md.get_historique(ticker)
        etats = md.get_etats_financiers(ticker)
        analystes = md.get_donnees_analystes(ticker)
        repartition = md.get_repartition_activite(ticker)
        indicateurs = md.construire_indicateurs(etats, info)
        score, detail_score = md.score_qualite(indicateurs, info)

    if not info and historique.empty:
        st.error(
            f"Aucune donnée n'a pu être récupérée pour **{ticker}** ({meta.get('nom', '')}). "
            "Yahoo Finance est peut-être temporairement indisponible : réessayez dans quelques instants."
        )
        return

    afficher_entete(ticker, meta, info, score)

    devise_etats = info.get("financialCurrency", info.get("currency", meta.get("devise", "")))

    onglets = st.tabs(["Résumé", "Quantitatif", "Résultats", "Finances", "Thèses", "Société", "Valorisation"])
    with onglets[0]:
        onglet_resume(ticker, meta, info, historique, indicateurs, score, detail_score)
    with onglets[1]:
        onglet_quantitatif(ticker, indicateurs, info)
    with onglets[2]:
        onglet_resultats(ticker, info, historique, analystes)
    with onglets[3]:
        onglet_finances(ticker, etats, indicateurs, repartition, devise_etats)
    with onglets[4]:
        onglet_theses(ticker, detail_score)
    with onglets[5]:
        onglet_societe(ticker, meta, info)
    with onglets[6]:
        onglet_valorisation(ticker, info, indicateurs, historique)

    st.markdown(
        f'<div style="font-size:11px;color:{sc.ARDOISE};margin-top:24px;line-height:1.7;">'
        f"Données Yahoo Finance via yfinance, à titre indicatif — délai possible et champs parfois absents "
        f"selon les valeurs. Score qualité et calculateur de prix juste sont des estimations internes, non "
        f"affiliées à Baggr ni à aucun fournisseur de données professionnel. Page actualisée à "
        f"{datetime.now():%H:%M}. Document d'analyse personnelle, ne constitue ni un conseil en "
        f"investissement, ni une recommandation, ni une sollicitation d'achat ou de vente.</div>",
        unsafe_allow_html=True,
    )
