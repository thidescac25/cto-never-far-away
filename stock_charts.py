"""
Bibliothèque de graphiques Plotly et de composants HTML pour les fiches
valeur (style Baggr), au thème sombre du CTO.

Toutes les figures utilisent `template="plotly_dark"` comme base puis sont
retouchées avec la charte du projet (fond transparent, grille discrète,
palette ambre/vert/rouge) via `appliquer_theme`.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go

# --------------------------------------------------------------------------- #
# Charte — reprise de portfolio_page.py pour une continuité visuelle parfaite,
# avec un vert/rouge plus saturé pour les indicateurs de performance, comme
# demandé pour les fiches valeur.
# --------------------------------------------------------------------------- #
ENCRE = "#0E1B2B"
PANNEAU = "#17293F"
PANNEAU_CLAIR = "#1E2F47"
AMBRE = "#D8902A"
AMBRE_CLAIR = "#E9A94A"
BLANC = "#FFFFFF"
BRUME = "#ABBBCA"
ARDOISE = "#8598A9"
FILET = "rgba(171, 187, 202, 0.14)"
GRILLE = "rgba(171, 187, 202, 0.07)"

HAUSSE = "#22C55E"
HAUSSE_DOUX = "#10B981"
BAISSE = "#EF4444"
BAISSE_DOUX = "#F87171"

BLEU = "#5B8FB9"
VIOLET = "#A98BC9"
GRIS_BLEU = "#7285AD"

PALETTE_CATEGORIES = [AMBRE, BLEU, HAUSSE_DOUX, VIOLET, BAISSE_DOUX, GRIS_BLEU, AMBRE_CLAIR, ARDOISE]


def couleur_signe(valeur: float | None) -> str:
    if valeur is None or not np.isfinite(valeur):
        return ARDOISE
    return HAUSSE if valeur >= 0 else BAISSE


def appliquer_theme(fig: go.Figure, hauteur: int = 280, marge_haut: int = 24) -> go.Figure:
    fig.update_layout(
        template="plotly_dark",
        height=hauteur,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, Segoe UI, sans-serif", color=BRUME, size=12),
        margin=dict(l=8, r=8, t=marge_haut, b=8),
        hoverlabel=dict(bgcolor=PANNEAU_CLAIR, bordercolor=FILET,
                        font=dict(color=BLANC, family="Inter, sans-serif", size=12)),
        legend=dict(orientation="h", yanchor="bottom", y=1.0, xanchor="left", x=0,
                   bgcolor="rgba(0,0,0,0)", font=dict(color=BRUME, size=11)),
        showlegend=False,
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=FILET,
                     tickcolor=FILET, tickfont=dict(color=ARDOISE, size=10.5))
    fig.update_yaxes(showgrid=True, gridcolor=GRILLE, zeroline=False,
                     linecolor="rgba(0,0,0,0)", tickfont=dict(color=ARDOISE, size=10.5))
    return fig


# --------------------------------------------------------------------------- #
# Graphiques en barres (revenu, bénéfices, FCF, actions en circulation, ...)
# --------------------------------------------------------------------------- #
def format_compact(valeur: float) -> str:
    """
    Étiquette courte pour un montant : 402,8 Md / 1,25 Md / 850 M / 12,4.

    Les états financiers se chiffrent en milliards : sans cette compression,
    les étiquettes de barres deviennent illisibles (« 402 800 000 000,0 ») et
    se chevauchent.
    """
    if valeur is None or not np.isfinite(valeur):
        return ""
    signe = "-" if valeur < 0 else ""
    v = abs(float(valeur))
    if v >= 1e12:
        return f"{signe}{v / 1e12:.2f} T".replace(".", ",")
    if v >= 1e9:
        return f"{signe}{v / 1e9:.1f} Md".replace(".", ",")
    if v >= 1e6:
        return f"{signe}{v / 1e6:.0f} M"
    if v >= 1e4:
        return f"{signe}{v:,.0f}".replace(",", " ")
    return f"{signe}{v:,.2f}".replace(",", " ").replace(".", ",")


def fig_barres(
    labels: list[str],
    valeurs: pd.Series,
    couleur: str = AMBRE,
    previsions: int = 0,
    hauteur: int = 260,
    suffixe: str = "",
    prefixe: str = "",
) -> go.Figure:
    """
    Barres verticales, avec un motif hachuré et une opacité réduite sur les
    `previsions` dernières colonnes — pour distinguer historique et
    consensus, comme sur les fiches Baggr.

    Les étiquettes sont mises en forme compacte (Md, M) : les montants
    comptables se comptent en milliards.
    """
    n = len(valeurs)
    opacites = [0.45 if i >= n - previsions else 0.92 for i in range(n)]
    motifs = ["/" if i >= n - previsions else "" for i in range(n)]
    textes = [
        f"{prefixe}{format_compact(v)}{suffixe}" if np.isfinite(v) else ""
        for v in valeurs
    ]

    fig = go.Figure(go.Bar(
        x=labels, y=valeurs.values, marker=dict(color=couleur, opacity=opacites,
                                                pattern=dict(shape=motifs, fgcolor=ENCRE, size=5)),
        text=textes, textposition="outside", textfont=dict(color=BRUME, size=10.5),
        hovertemplate="%{x}<br>%{y:,.4s}<extra></extra>",
        cliponaxis=False,
    ))
    appliquer_theme(fig, hauteur=hauteur)
    fig.update_yaxes(showticklabels=False)
    return fig


def fig_lignes_multi(
    labels: list[str],
    series: dict[str, pd.Series],
    couleurs: list[str] | None = None,
    hauteur: int = 260,
    suffixe: str = " %",
) -> go.Figure:
    """Plusieurs lignes superposées (marges, retours sur capitaux, ...)."""
    couleurs = couleurs or PALETTE_CATEGORIES
    fig = go.Figure()
    for i, (nom, valeurs) in enumerate(series.items()):
        fig.add_trace(go.Scatter(
            x=labels, y=valeurs.values, name=nom, mode="lines+markers",
            line=dict(width=2.2, color=couleurs[i % len(couleurs)]),
            marker=dict(size=5),
            hovertemplate="%{x} · " + nom + " : %{y:.1f}" + suffixe + "<extra></extra>",
        ))
    appliquer_theme(fig, hauteur=hauteur)
    fig.update_layout(showlegend=True, margin=dict(l=8, r=8, t=34, b=8))
    fig.add_hline(y=0, line=dict(color=FILET, width=1))
    fig.update_yaxes(ticksuffix=suffixe.strip() and suffixe or None)
    return fig


def fig_barres_lignes(
    labels: list[str],
    barres: dict[str, pd.Series],
    couleurs_barres: list[str],
    ligne: pd.Series | None = None,
    nom_ligne: str = "",
    hauteur: int = 260,
) -> go.Figure:
    """Barres groupées (ex. trésorerie vs dette) + une ligne secondaire (ex. dette nette/EBITDA)."""
    fig = go.Figure()
    for i, (nom, valeurs) in enumerate(barres.items()):
        fig.add_trace(go.Bar(
            x=labels, y=valeurs.values, name=nom,
            marker=dict(color=couleurs_barres[i % len(couleurs_barres)]),
            hovertemplate="%{x} · " + nom + " : %{y:,.2f}<extra></extra>",
        ))
    if ligne is not None and ligne.notna().any():
        fig.add_trace(go.Scatter(
            x=labels, y=ligne.values, name=nom_ligne, mode="lines+markers",
            line=dict(width=2, color=BLANC, dash="dot"), marker=dict(size=5),
            yaxis="y2",
            hovertemplate="%{x} · " + nom_ligne + " : %{y:.2f}x<extra></extra>",
        ))
        fig.update_layout(yaxis2=dict(overlaying="y", side="right", showgrid=False,
                                      tickfont=dict(color=ARDOISE, size=10.5)))
    appliquer_theme(fig, hauteur=hauteur)
    fig.update_layout(
        barmode="relative", showlegend=True, margin=dict(l=8, r=8, t=34, b=8),
        yaxis=dict(showticklabels=False, showgrid=True, gridcolor=GRILLE, zeroline=False),
    )
    return fig


def fig_donut(labels: list[str], valeurs: list[float], couleurs: list[str] | None = None, hauteur: int = 300) -> go.Figure:
    couleurs = couleurs or PALETTE_CATEGORIES
    fig = go.Figure(go.Pie(
        labels=labels, values=valeurs, hole=0.62,
        marker=dict(colors=couleurs[: len(labels)], line=dict(color=ENCRE, width=2)),
        textinfo="percent", textfont=dict(color=BLANC, size=11),
        hovertemplate="%{label}<br>%{percent}<extra></extra>",
    ))
    appliquer_theme(fig, hauteur=hauteur, marge_haut=8)
    fig.update_layout(showlegend=True, legend=dict(orientation="v", yanchor="middle", y=0.5, xanchor="left", x=1.02))
    return fig


def fig_projection_cours(historique: pd.Series, bas: float, moyen: float, haut: float, hauteur: int = 300) -> go.Figure:
    """Cours récent en trait plein, puis trois trajectoires pointillées vers les objectifs analystes."""
    fig = go.Figure()
    h = historique.dropna().tail(180)
    if not h.empty:
        fig.add_trace(go.Scatter(x=h.index, y=h.values, mode="lines", name="Cours",
                                 line=dict(width=2, color=BLANC),
                                 hovertemplate="%{y:.2f}<extra>Cours</extra>"))
        depart = h.index[-1]
        horizon = depart + pd.Timedelta(days=365)
        dernier = float(h.iloc[-1])
        for cible, nom, couleur in [(haut, "Cible haute", HAUSSE), (moyen, "Cible moyenne", AMBRE), (bas, "Cible basse", BAISSE)]:
            if cible and np.isfinite(cible):
                fig.add_trace(go.Scatter(
                    x=[depart, horizon], y=[dernier, cible], mode="lines+markers", name=nom,
                    line=dict(width=1.6, color=couleur, dash="dot"), marker=dict(size=6),
                    hovertemplate=nom + " : %{y:.2f}<extra></extra>",
                ))
    appliquer_theme(fig, hauteur=hauteur, marge_haut=8)
    fig.update_layout(showlegend=True)
    return fig


def fig_surprises_eps(labels: list[str], surprises_pct: pd.Series, hauteur: int = 300) -> go.Figure:
    couleurs = [HAUSSE if v >= 0 else BAISSE for v in surprises_pct.values]
    fig = go.Figure(go.Bar(
        x=labels, y=surprises_pct.values, marker=dict(color=couleurs),
        text=[f"{v:+.1f} %" for v in surprises_pct.values], textposition="outside",
        textfont=dict(color=BRUME, size=10.5),
        hovertemplate="%{x} : %{y:+.1f} %<extra></extra>", cliponaxis=False,
    ))
    fig.add_hline(y=0, line=dict(color=FILET, width=1))
    appliquer_theme(fig, hauteur=hauteur)
    fig.update_yaxes(showticklabels=False)
    return fig


# --------------------------------------------------------------------------- #
# Composants HTML — bannières perf/CAGR et jauges, dans l'esprit Baggr
# --------------------------------------------------------------------------- #
def banniere_perf_cagr(perf: float | None, croissance: float | None) -> str:
    def _pastille(valeur: float | None, libelle: str) -> str:
        if valeur is None or not np.isfinite(valeur):
            return f'<span class="pastille pastille-neutre">{libelle} : —</span>'
        couleur = "pastille-hausse" if valeur >= 0 else "pastille-baisse"
        signe = "+" if valeur >= 0 else ""
        return f'<span class="pastille {couleur}">{libelle} : {signe}{valeur:.1f} %</span>'

    return f'<div class="bandeau-carte">{_pastille(perf, "Perf")}{_pastille(croissance, "CAGR")}</div>'


def carte_graphique(titre: str, corps_html: str, bandeau_html: str = "") -> str:
    """Enveloppe une figure Plotly (déjà rendue en amont) dans une carte au style Baggr/CTO."""
    return (
        f'<div class="carte-baggr"><div class="carte-titre">{titre}</div>'
        f'{corps_html}{bandeau_html}</div>'
    )


def jauge_html(libelle: str, valeur: float | None, echelle: float = 30.0, suffixe: str = " %") -> str:
    """
    Barre de jauge horizontale : piste grise, remplissage coloré (vert si
    positif, rouge si négatif) proportionnel à |valeur| / échelle.
    """
    if valeur is None or not np.isfinite(valeur):
        return (
            f'<div class="jauge-ligne"><span class="jauge-libelle">{libelle}</span>'
            f'<span class="jauge-valeur" style="color:{ARDOISE}">—</span>'
            f'<div class="jauge-piste"></div></div>'
        )
    couleur = HAUSSE if valeur >= 0 else BAISSE
    largeur = float(np.clip(abs(valeur) / echelle * 100.0, 2.0, 100.0))
    signe = "+" if valeur >= 0 else ""
    return (
        f'<div class="jauge-ligne"><span class="jauge-libelle">{libelle}</span>'
        f'<span class="jauge-valeur" style="color:{couleur}">{signe}{valeur:.1f}{suffixe}</span>'
        f'<div class="jauge-piste"><div class="jauge-remplissage" '
        f'style="width:{largeur:.0f}%; background:{couleur};"></div></div></div>'
    )


def bloc_jauges(titre: str, lignes: list[tuple[str, float | None, float, str]]) -> str:
    """Une carte contenant plusieurs jauges (ex. bloc « Rentabilité » ou « Croissance »)."""
    corps = "".join(jauge_html(libelle, valeur, echelle, suffixe) for libelle, valeur, echelle, suffixe in lignes)
    return f'<div class="carte-baggr"><div class="carte-titre">{titre}</div>{corps}</div>'
