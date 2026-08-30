# CTO Never far away

Page unique de suivi d'un compte-titres ordinaire de douze valeurs, consolidé en euro
et confronté à six indices : CAC 40, S&P 500, NASDAQ 100, EURO STOXX 50, DAX et Dow Jones.

Une troisième vue offre, pour chacune des douze lignes, une fiche d'analyse détaillée
inspirée de l'expérience Baggr (onglets Résumé / Quantitatif / Résultats / Finances /
Thèses / Société / Valorisation), alimentée en direct par `yfinance`.

## Installation

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
streamlit run app.py
```

L'application s'ouvre sur `http://localhost:8501`.

## Structure

```
cto-never-far-away/
├── app.py                   # point d'entrée : navigation entre les trois pages
├── vues/
│   ├── portefeuille_12.py       # page 1 — les douze d'origine
│   ├── portefeuille_20.py       # page 2 — la version ADD++, vingt lignes
│   └── fiche_valeur.py          # page 3 — fiche d'analyse détaillée, style Baggr
├── univers.py                # composition des portefeuilles (tickers, devises, secteurs)
├── portfolio_page.py         # rendu de la page portefeuille : mise en forme, graphiques
├── portfolio_core.py         # calculs purs de portefeuille (aucune dépendance Streamlit), testables
├── market_data.py            # accès yfinance pour la fiche valeur (cache, ratios, score qualité)
├── stock_charts.py           # graphiques Plotly + composants HTML (jauges, bannières) de la fiche valeur
├── stock_page.py             # assemblage de la fiche valeur : en-tête + 7 onglets
├── diagnostic.py
├── requirements.txt
└── .streamlit/
    └── config.toml           # thème sombre ambre
```

Les deux premières pages partagent le même moteur : `portfolio_page.afficher()` prend un
univers et construit la page entière. La troisième page repose sur un moteur séparé,
`stock_page.afficher_fiche()`, pensé pour l'analyse d'une seule valeur plutôt que d'un
panier — les deux moteurs ne s'interpénètrent pas, ce qui permet de faire évoluer la fiche
valeur sans risquer de casser le suivi de portefeuille, et réciproquement.

## Univers — page 1, douze lignes

| Ticker Yahoo | Société | Place | Devise de cotation |
|---|---|---|---|
| ABT | Abbott Laboratories | NYSE | USD |
| GOOGL | Alphabet A | NASDAQ | USD |
| BRK-B | Berkshire Hathaway B | NYSE | USD |
| GTT.PA | Gaztransport & Technigaz | Euronext Paris | EUR |
| MA | Mastercard | NYSE | USD |
| MIR | Mirion Technologies | NYSE | USD |
| NEE | NextEra Energy | NYSE | USD |
| NOC | Northrop Grumman | NYSE | USD |
| RIO.L | Rio Tinto | LSE | **GBX (pence)** |
| ROP.SW | Roche Holding, bon de participation | SIX | CHF |
| RR.L | Rolls-Royce Holdings | LSE | **GBX (pence)** |
| VIE.PA | Veolia Environnement | Euronext Paris | EUR |

## Univers — page 2, ADD++, vingt lignes

Les douze ci-dessus, plus :

| Ticker Yahoo | Société | Place | Devise de cotation |
|---|---|---|---|
| ACS.MC | ACS | BME Madrid | EUR |
| AI.PA | Air Liquide | Euronext Paris | EUR |
| BA.L | BAE Systems | LSE | **GBX (pence)** |
| ICE | Intercontinental Exchange | NYSE | USD |
| SU.PA | Schneider Electric | Euronext Paris | EUR |
| STF.PA | STEF | Euronext Paris | EUR |
| UBSG.SW | UBS Group | SIX | CHF |
| WMT | Walmart | NYSE | USD |

## Page 3 — Fiche valeur, style Baggr

Le sélecteur en haut de page ne porte que sur les douze lignes du portefeuille d'origine.
Pour chaque valeur, sept onglets :

- **Résumé** : capitalisation, PER, rendement, range 52 semaines, bêta, effectifs, cours
  sur un an, détail du score qualité interne.
- **Quantitatif** : chiffre d'affaires, bénéfices, Free Cash Flow, marges (brute/opérationnelle/
  nette), retours sur capitaux (ROE/ROIC/ROCE), trésorerie vs dette (avec dette nette/EBITDA en
  ligne secondaire), actions en circulation, dépenses (R&D/CAPEX/rémunération en actions en %
  du CA), résultat d'exploitation — chaque graphique avec sa bannière Performance/CAGR — puis
  trois blocs de jauges de synthèse (rentabilité, retours sur capitaux, croissance & solidité).
- **Résultats** : objectifs de cours des analystes (haut/moyen/bas), prévisions de chiffre
  d'affaires et d'EPS, historique des surprises d'EPS (beat/miss), répartition des avis
  d'analystes, score global interne.
- **Finances** : répartition du chiffre d'affaires par segment et par géographie (quand Yahoo
  la publie), comptes de résultat / bilan / flux de trésorerie sur les exercices disponibles.
- **Thèses** : grille automatique de points forts / points de vigilance dérivée du score
  qualité, plus une zone de notes personnelles (conservée le temps de la session).
- **Société** : secteur, industrie, pays, effectifs, présentation de l'activité.
- **Valorisation** : PER, P/B, EV/EBITDA, PEG, et un calculateur de prix juste indicatif
  (croissance des bénéfices, horizon, multiple de sortie, taux d'actualisation pré-rempli
  avec le WACC estimé de la valeur).

### Déploiement en ligne : ce que Yahoo refuse aux hébergeurs

Yahoo Finance sert ses données par plusieurs points d'entrée, qui n'ont pas la même
politique d'accès :

| Point d'entrée | Contenu | Depuis un poste personnel | Depuis un hébergeur |
|---|---|---|---|
| `chart` | cours, dividendes, `fast_info` | ✅ | ✅ |
| `fundamentals-timeseries` | comptes de résultat, bilans, flux | ✅ | ✅ |
| `quoteSummary` | identité, ratios instantanés, avis d'analystes | ✅ | ❌ |

`quoteSummary` exige un cookie et un jeton (« crumb ») délivrés par `fc.yahoo.com`.
Yahoo refuse de les accorder aux adresses IP de centre de données : l'appel réussit
en local et échoue sur Streamlit Community Cloud (ainsi que sur Heroku, Render ou
toute VM cloud). Ce n'est pas un défaut de configuration et attendre n'y change rien.

L'application le gère explicitement plutôt que d'afficher des cases vides :

- **Récupéré par une autre voie** (`fast_info`, endpoint `chart`) : cours, clôture
  précédente, capitalisation, extrêmes 52 semaines, nombre d'actions, devise.
- **Recalculé** à partir des comptes publiés et des cours : bénéfice par action, PER,
  P/B, valeur d'entreprise, EV/EBITDA, rendement du dividende (douze derniers mois
  effectivement versés) et bêta (régression hebdomadaire face au S&P 500). Ces valeurs
  portent à l'écran la mention **« estimé — calcul interne »** : un ratio reconstruit
  et un chiffre publié n'ont pas la même valeur probante, les confondre serait la pire
  des facilités sur un outil d'aide à la décision.
- **Définitivement absent** : le consensus des analystes (objectifs de cours, prévisions
  de chiffre d'affaires et de bénéfices, répartition des avis), la description d'activité
  et les effectifs. Rien dans le flux disponible ne permet de les reconstituer
  honnêtement. Les cartes concernées basculent alors sur un repli factuel — amplitude
  52 semaines à la place des objectifs de cours, trajectoire historique à la place des
  prévisions — clairement étiqueté comme tel.

Un bandeau dépliable en tête de fiche explique la situation lorsqu'elle se produit.
Pour disposer de l'ensemble des données, exécutez l'application en local.

**Sur la fiabilité des données.** Yahoo Finance ne fournit pas tout, pour toutes les valeurs :
la répartition géographique/sectorielle du chiffre d'affaires, en particulier, n'est publiée
que pour une minorité de grandes capitalisations. Quand une donnée manque, la fiche affiche un
message de repli plutôt que de planter. ROIC, ROCE, WACC et le score qualité sont des
**estimations internes**, calculées à partir des lignes comptables disponibles (généralement
4 à 5 exercices annuels) — ce ne sont pas les chiffres propriétaires de Baggr, dont la
méthodologie exacte n'est pas publique, ni des données auditées par un fournisseur professionnel.
Le calculateur de prix juste est un ordre de grandeur pédagogique, pas une valorisation
d'analyste financier.

## Choix méthodologiques (pages 1 et 2)

- **Cours ajustés** (`auto_adjust=True`) : dividendes réinvestis et divisions d'actions neutralisées.
- **Pence de Londres** : Yahoo cote `RIO.L` et `RR.L` en pence. Les cours sont divisés par cent
  avant conversion, sans quoi ces deux lignes pèseraient cent fois trop peu en nombre de titres.
- **Consolidation en euro** : conversion quotidienne via `EURUSD=X`, `EURGBP=X` et `EURCHF=X`.
  L'effet de change fait donc partie de la performance, comme pour un porteur réel.
- **Roche, changement de symbole** : le Genussschein « ROG » a cessé de coter le 16 mars 2026,
  échangé à parité contre un bon de participation « ROP » (nouvel ISIN CH1499059983). L'application
  télécharge les deux symboles et recolle les séries : `ROG.SW` avant la bascule, `ROP.SW` après.
  Sans ce recollement, l'historique de Roche démarrerait en mars 2026 et tronquerait toute la
  période analysée. Un contrôle de parité affiche l'écart de cours à la jonction, qui doit rester
  proche de zéro. Le mécanisme est générique : il suffit d'ajouter une clé `anciens` à une ligne
  du dictionnaire `PORTEFEUILLE` pour traiter un futur changement de symbole.
- **Reprise après échec** : yfinance abandonne parfois un symbole lors d'un téléchargement groupé.
  Toute colonne absente est redemandée individuellement avant d'être déclarée indisponible.
- **Départ commun** : l'historique démarre au premier jour où les douze lignes cotent toutes.
  Mirion Technologies n'est cotée que depuis octobre 2021 et contraint donc les périodes longues ;
  la page l'annonce explicitement plutôt que de décaler silencieusement la date.
- **Indices ramenés en euro** (activé par défaut) : sans cela, la comparaison mélange une
  performance en euro et des indices en dollar.
- **DAX** : indice de rendement global, dividendes réinvestis. Les cinq autres sont des indices
  de prix, donc structurellement en retrait d'environ deux points par an.
- **Deux modes de gestion** : achat et conservation (les gagnantes prennent du poids) ou
  équipondéré rééquilibré (mensuel, trimestriel ou annuel).
- **Hors frais et hors fiscalité** : la simulation ignore courtage, droits de garde et
  imposition des dividendes et des plus-values sur un CTO.

## Avertissement

Outil d'analyse personnelle. Ne constitue ni un conseil en investissement, ni une
recommandation, ni une sollicitation d'achat ou de vente.

## Publication sur GitHub et déploiement

Le dépôt ne contient que le code : l'environnement virtuel et les fichiers compilés
sont exclus par `.gitignore` et se reconstruisent avec `pip install -r requirements.txt`.

```bash
git init
git add .
git commit -m "CTO Never far away — suivi de portefeuille et fiches valeur"
git branch -M main
git remote add origin https://github.com/<compte>/cto-never-far-away.git
git push -u origin main
```

Vérifiez avant de pousser que `.venv` n'apparaît pas dans `git status`.

Pour un déploiement sur Streamlit Community Cloud : dépôt `cto-never-far-away`,
branche `main`, fichier principal `app.py`. Le thème de `.streamlit/config.toml`
est repris automatiquement. Aucune clé d'API n'est nécessaire, yfinance interroge
Yahoo sans authentification.

**Avant de rendre le dépôt public**, gardez à l'esprit que `univers.py` décrit
la composition exacte de votre portefeuille. Le code n'a rien de confidentiel,
mais vos positions le sont peut-être : un dépôt privé reste possible, et Streamlit
Community Cloud sait déployer depuis un dépôt privé.
