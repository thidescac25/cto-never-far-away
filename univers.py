"""
Univers d'investissement du projet.

Chaque ligne porte son ticker Yahoo, sa devise de cotation et son identité.
Clés facultatives :
    anciens     : symboles précédents, du plus récent au plus ancien. La série
                  est recollée automatiquement (changement de symbole).
    note        : phrase affichée sous les indicateurs pour expliquer ce recollement.
    reference   : cotation de substitution servant à prolonger un historique tronqué.

Clés documentaires des douze lignes du CTO (affichées dans la fiche valeur) :
    industrie    : métier précis, plus fin que le secteur.
    effectifs    : dernier effectif publié par la société, avec effectifs_au.
    arrete_au    : date d'arrêté des chiffres cités dans description et moat.
    description  : d'où vient l'argent — segments, modèle, récurrence.
    moat         : pourquoi ces revenus devraient résister à la concurrence.

Pourquoi ces textes sont écrits en dur plutôt que récupérés de Yahoo : la notice
`longBusinessSummary` de Yahoo transite par un point d'entrée que le fournisseur
refuse aux adresses IP de centre de données (voir market_data.get_info), donc
indisponible dès que l'application tourne sur un hébergeur. Elle est de surcroît
en anglais et purement descriptive. Les textes ci-dessous la remplacent avec un
angle modèle économique et récurrence des revenus.

ATTENTION — les chiffres cités sont datés par `arrete_au`. Ils proviennent des
dernières publications officielles disponibles au 4 octobre 2026 (résultats du
deuxième trimestre ou du premier semestre 2026, publiés en juillet et août 2026).
Ils ne se mettent pas à jour tout seuls : à relire une à deux fois par an, après
les publications annuelles.

Rappel sur les devises : Londres cote en pence (GBX), d'où la division par cent
avant conversion en euro. Le reste est coté dans la devise du marché.
"""

from __future__ import annotations

# Roche : le Genussschein « ROG » a cessé de coter le 16 mars 2026, échangé à
# parité contre le bon de participation « ROP » (nouvel ISIN CH1499059983),
# première cotation le 17 mars 2026 — opération confirmée auprès de Roche
# Investor Relations. Yahoo a reporté l'intégralité de l'historique sur ROP.SW,
# donc aucun recollement n'est nécessaire. Si Yahoo venait à repartir de zéro,
# il suffirait de rétablir la clé : "anciens": ["ROG.SW"].
ROCHE = {
    "nom": "Roche Holding", "devise": "CHF", "pays": "Suisse", "secteur": "Santé",
    "industrie": "Pharmacie et diagnostic in vitro",
    "arrete_au": "30/06/2026",
    "description":
        "Roche associe un laboratoire pharmaceutique et le premier diagnosticien mondial. "
        "Au premier semestre 2026, 30 364 M CHF de ventes, en hausse de 6 % à taux de change "
        "constants mais en recul de 2 % en francs du fait de l'appréciation de la devise. La "
        "division Pharmaceuticals (23 629 M CHF) dégage environ 53 % de marge opérationnelle de "
        "base et repose sur cinq moteurs — Ocrevus, Hemlibra, Vabysmo, Phesgo, Xolair — qui "
        "totalisent 11,0 Md CHF en croissance de 12 %. La division Diagnostics (6 735 M CHF) vend "
        "des analyseurs puis les réactifs consommés dessus. La recherche absorbe 5 765 M CHF, soit "
        "19 % des ventes ; deux programmes majeurs sont en phase III, l'enicepatide dans l'obésité "
        "(22,5 % de perte de poids ajustée du placebo à 48 semaines en phase II) et le trontinemab "
        "dans la maladie d'Alzheimer. Le titre coté depuis le 17 mars 2026 est un bon de "
        "participation, échangé à parité contre l'ancien bon de jouissance : mêmes droits au "
        "dividende, pas de droit de vote.",
    "moat":
        "Le fossé pharmaceutique est à durée déterminée : un brevet protège une molécule puis "
        "expire, et le portefeuille historique en fait l'expérience — Avastin, Herceptin, MabThera "
        "et Actemra reculent de 8 %, Xolair affronte ses premiers biosimilaires américains au "
        "second semestre 2026. Ce qui dure, c'est la machine à renouveler : 19 % des ventes "
        "réinvesties en recherche, cinq examens prioritaires obtenus de la FDA au seul premier "
        "semestre 2026. Le second fossé, bien plus stable, est celui des diagnostics : un "
        "analyseur installé dans un laboratoire hospitalier consomme pendant une décennie des "
        "réactifs propriétaires, et en changer impose de revalider tous les protocoles. La "
        "combinaison des deux divisions donne enfin un avantage rare — concevoir simultanément le "
        "test qui identifie les patients et le médicament qui les traite. Le dividende a été "
        "relevé trente-neuf années de suite.",
}

UNIVERS_12: dict[str, dict] = {
    "ABT": {
        "nom": "Abbott Laboratories", "devise": "USD", "pays": "États-Unis", "secteur": "Santé",
        "industrie": "Dispositifs médicaux, diagnostics et nutrition",
        "effectifs": 115_000, "effectifs_au": "31/12/2025",
        "arrete_au": "30/06/2026",
        "description":
            "Abbott combine quatre métiers aux cycles différents : les dispositifs médicaux "
            "(5 853 M$ au deuxième trimestre 2026, +9 %), les diagnostics (3 092 M$), les produits "
            "pharmaceutiques établis vendus hors États-Unis (1 499 M$) et la nutrition (2 144 M$). "
            "Le moteur est le diabète : la division Diabetes Care a facturé 2 188 M$ sur le "
            "trimestre (+8,6 %), portée par les capteurs de glycémie en continu Libre, en hausse de "
            "11 %. L'acquisition d'Exact Sciences, bouclée le 23 mars 2026 pour 21 Md$, ajoute le "
            "dépistage du cancer colorectal (Cologuard) et explique l'essentiel du bond affiché par "
            "les diagnostics. Le modèle repose sur des consommables renouvelés — capteurs remplacés "
            "tous les quinze jours, tests, réactifs utilisés sur une base installée d'analyseurs — "
            "une récurrence qu'Abbott ne chiffre pas mais qui structure le chiffre d'affaires. "
            "Revers de l'exposition grand public : 385 M$ de provisions pour litiges sur le seul "
            "deuxième trimestre, et une transaction de 670 M$ conclue le 20 août 2026 sur les "
            "préparations pour nourrissons prématurés.",
        "moat":
            "La base installée est la première barrière : un laboratoire équipé d'analyseurs Abbott "
            "achète ses réactifs chez Abbott pendant toute la durée de vie des machines, et changer "
            "de fournisseur impose de revalider l'ensemble des protocoles. S'y ajoute la marque, "
            "rare dans le matériel médical mais réelle sur la nutrition infantile et sur Libre, "
            "désormais prescrit et porté en continu par des millions de patients qui n'en changent "
            "pas sans raison. L'homologation réglementaire protège chaque référence et interdit "
            "une entrée rapide, y compris à un concurrent techniquement prêt. La distribution "
            "mondiale, enfin, atteint des réseaux hospitaliers et des pharmacies que peu de "
            "fabricants peuvent servir simultanément.",
    },
    "GOOGL": {
        "nom": "Alphabet A", "devise": "USD", "pays": "États-Unis", "secteur": "Technologie",
        "industrie": "Publicité en ligne, cloud et abonnements numériques",
        "effectifs": 198_933, "effectifs_au": "30/06/2026",
        "arrete_au": "30/06/2026",
        "description":
            "Alphabet est la maison mère de Google. La publicité reste le socle du modèle — "
            "recherche, YouTube et réseau partenaire ont pesé 81,7 Md$ sur les 119,8 Md$ de revenus "
            "du deuxième trimestre 2026, soit un peu plus des deux tiers — mais la croissance vient "
            "désormais d'ailleurs. Google Cloud a facturé 24,8 Md$ sur le trimestre, en hausse de "
            "82 %, pour 8,8 Md$ de résultat d'exploitation : l'activité qui a perdu de l'argent "
            "pendant une décennie dégage aujourd'hui près de 36 % de marge et porte un carnet de "
            "commandes de 514 Md$. Le troisième pilier, le plus régulier, réunit abonnements, "
            "plateformes et appareils — YouTube Premium, Google One, Workspace — pour 12,9 Md$ "
            "trimestriels en croissance de 15 %, facturés par prélèvement mensuel ou annuel. Le "
            "pôle Other Bets (Waymo, Verily) reste anecdotique en revenus, 382 M$, et déficitaire "
            "de 1,8 Md$ par trimestre. L'intensité capitalistique est le fait marquant de "
            "l'exercice : 80,6 Md$ d'investissements sur le seul premier semestre 2026.",
        "moat":
            "Trois barrières se cumulent. La distribution d'abord : Chrome, Android et les accords "
            "de moteur par défaut placent Google au point d'entrée de la majorité des recherches "
            "mondiales — c'est précisément ce que la justice américaine attaque, le juge Mehta "
            "ayant imposé en septembre 2025 une remise en concurrence annuelle de ces contrats, "
            "décision frappée d'appel par le ministère de la Justice le 3 février 2026. L'effet de "
            "réseau publicitaire ensuite : annonceurs et éditeurs s'attirent mutuellement, et "
            "l'audience accumulée améliore le ciblage, donc le rendement, donc l'attractivité. "
            "L'intégration verticale enfin : les processeurs TPU conçus en interne abaissent le "
            "coût unitaire de l'inférence face à des concurrents qui achètent leurs accélérateurs "
            "à un fournisseur tiers — un avantage de coût qui pèse de plus en plus lourd à mesure "
            "que l'IA se généralise dans la recherche et le cloud.",
    },
    "BRK-B": {
        "nom": "Berkshire Hathaway B", "devise": "USD", "pays": "États-Unis", "secteur": "Conglomérat",
        "industrie": "Assurance, infrastructures et participations industrielles",
        "effectifs": 387_800, "effectifs_au": "31/12/2025",
        "arrete_au": "30/06/2026",
        "description":
            "Berkshire est un conglomérat assurantiel qui réinvestit les flux de ses filiales. "
            "Trois moteurs : l'assurance (GEICO, Berkshire Hathaway Reinsurance), qui dégage un "
            "flottant de 177,5 Md$ — des primes encaissées avant d'être éventuellement décaissées, "
            "utilisables entre-temps ; les infrastructures régulées, avec le chemin de fer BNSF et "
            "les services publics de Berkshire Hathaway Energy ; et un ensemble industriel et de "
            "distribution. Au deuxième trimestre 2026, le résultat d'exploitation atteint "
            "12 983 M$ (+16 %) pour 101,8 Md$ de revenus. Le résultat net publié de 25 667 M$ est "
            "en revanche sans portée économique : il intègre 12,7 Md$ de plus-values, dont 10,9 Md$ "
            "de simples réévaluations comptables de titres non cédés — c'est bien le résultat "
            "d'exploitation qu'il faut suivre, comme le groupe le rappelle lui-même. La trésorerie "
            "et les bons du Trésor atteignent 365 Md$, le portefeuille coté 324 Md$, lequel inclut "
            "depuis le deuxième trimestre 2026 une ligne Alphabet de 10 Md$. Greg Abel dirige le "
            "groupe depuis le 1er janvier 2026, Warren Buffett restant président du conseil.",
        "moat":
            "Le fossé n'est pas industriel mais financier. Le flottant d'assurance fournit un "
            "levier dont le coût est nul ou négatif tant que la souscription reste bénéficiaire, "
            "ce qu'aucune société non assurantielle ne peut répliquer. La permanence du capital "
            "permet d'acheter quand les autres sont contraints de vendre : le bilan est construit "
            "pour être liquide au pire moment du cycle, là où le rendement se fait. La réputation "
            "du groupe en fait l'acquéreur de dernier recours pour des entreprises familiales qui "
            "refusent un fonds de capital-investissement, ce qui donne accès à des transactions "
            "sans enchères. BNSF et les services publics détiennent enfin des actifs physiques "
            "irremplaçables, protégés par des autorisations qu'on ne délivre plus aujourd'hui.",
    },
    "GTT.PA": {
        "nom": "Gaztransport & Technigaz", "devise": "EUR", "pays": "France", "secteur": "Énergie / GNL",
        "industrie": "Licences de technologies de confinement cryogénique",
        "arrete_au": "30/06/2026",
        "description":
            "GTT ne construit pas de navires : elle licencie aux chantiers navals, essentiellement "
            "coréens et chinois, ses technologies brevetées de cuves à membrane destinées au "
            "transport du gaz naturel liquéfié, et perçoit une redevance par navire. Le chiffre "
            "d'affaires est reconnu à l'avancement de la construction, sur deux à trois ans, ce qui "
            "décale les commandes des revenus. Au premier semestre 2026, 387,3 M€ de chiffre "
            "d'affaires pour 263,6 M€ d'EBITDA — 68 % de marge — et 1,7 M€ d'investissements "
            "seulement : le modèle ne consomme quasiment pas de capital. Le carnet s'établit à "
            "306 unités pour 1,9 Md€, avec une visibilité au-delà de 2029. L'activité hydrogène "
            "Elogen, déficitaire, a été ramenée à de la recherche depuis début 2025 ; le pôle GTT "
            "Marine, issu de l'acquisition de Danelec, apporte 31,8 M€. Environ 80 % du résultat "
            "est distribué, avec un acompte de 4,30 € par action versé en décembre 2026.",
        "moat":
            "Le fossé est technologique et quasi monopolistique. Les membranes cryogéniques Mark III "
            "et NO96 sont protégées par brevets et, surtout, homologuées par les sociétés de "
            "classification : un armateur ne change pas de technologie de cuve sans remettre en "
            "cause l'assurabilité et la valeur de revente de son navire. Les chantiers ont formé "
            "leurs équipes et adapté leurs cales à ces systèmes, ce qui crée un coût de "
            "commutation considérable pour un poste qui ne représente qu'une fraction du prix du "
            "navire — l'économie potentielle ne justifie jamais le risque. Le modèle de licence, "
            "sans usine ni stock, transforme cette position en rente : le capital employé est "
            "minime, la marge d'exploitation dépasse 64 %, et l'expansion de la flotte GNL "
            "mondiale se convertit mécaniquement en redevances.",
    },
    "MA": {
        "nom": "Mastercard", "devise": "USD", "pays": "États-Unis", "secteur": "Paiements",
        "industrie": "Réseau de paiement et services à valeur ajoutée",
        "effectifs": 39_800, "effectifs_au": "31/12/2025",
        "arrete_au": "30/06/2026",
        "description":
            "Mastercard n'émet pas de cartes et ne prête pas : elle exploite le réseau qui achemine "
            "l'autorisation et la compensation entre la banque du commerçant et celle du porteur, "
            "et prélève une commission sur chaque transaction. Au deuxième trimestre 2026, "
            "2 900 Md$ de volume brut (+8 %) et 57,1 milliards de transactions commutées (+9 %) ont "
            "produit 9 277 M$ de revenus nets (+14 %) pour 5 587 M$ de résultat d'exploitation, "
            "soit 60 % de marge. La croissance vient désormais des services à valeur ajoutée — "
            "lutte contre la fraude, données, conseil, identité numérique — qui pèsent 3 826 M$, "
            "41 % du chiffre d'affaires, et progressent de 20 %. Le volume transfrontalier, le plus "
            "rémunérateur, croît de 12 %. Le règlement antitrust approuvé le 9 juin 2026 abaisse "
            "les taux d'interchange de 10 points de base pendant cinq ans : il porte sur la "
            "rémunération des banques émettrices plus que sur celle du réseau, mais il encadre "
            "désormais l'économie du système.",
        "moat":
            "Un réseau bilatéral : les commerçants acceptent Mastercard parce que les porteurs en "
            "détiennent, et les banques en émettent parce que les commerçants l'acceptent — "
            "3,7 milliards de cartes en circulation rendent cette boucle presque impossible à "
            "amorcer pour un nouvel entrant, qui devrait conquérir les deux côtés simultanément. "
            "Les coûts de commutation sont élevés de part et d'autre : un émetteur renégocie des "
            "accords pluriannuels, un acquéreur recâble ses systèmes. L'échelle est l'autre "
            "barrière : le coût marginal d'une transaction supplémentaire est quasi nul, ce qui "
            "explique 60 % de marge d'exploitation et interdit à un concurrent sous-dimensionné de "
            "s'aligner durablement sur les prix. La conformité réglementaire, enfin, souvent perçue "
            "comme une contrainte, agit comme un fossé de plus : elle est coûteuse à atteindre et "
            "décourage les acteurs locaux.",
    },
    "MIR": {
        "nom": "Mirion Technologies", "devise": "USD", "pays": "États-Unis", "secteur": "Instrumentation",
        "industrie": "Mesure et gestion du rayonnement ionisant",
        "effectifs": 3_281, "effectifs_au": "31/12/2025",
        "arrete_au": "30/06/2026",
        "description":
            "Mirion mesure et gère le rayonnement ionisant. Deux pôles : Nuclear & Safety "
            "(186,2 M$ au deuxième trimestre 2026, +31,4 %), qui équipe centrales, laboratoires et "
            "armées en instruments de détection et systèmes de protection de réacteur ; et Medical "
            "(80,6 M$, 38,6 % de marge d'EBITDA ajusté), qui couvre la dosimétrie des personnels, "
            "le contrôle qualité en radiothérapie et la médecine nucléaire. Les produits Mirion "
            "sont présents dans plus de 98 % des centrales nucléaires mondiales, et environ 80 % du "
            "chiffre d'affaires nucléaire provient de la base installée — pièces, consommables et "
            "maintenance sur des réacteurs exploités quarante à soixante ans. Le carnet atteint "
            "1 139 M$ (+39 %), dont 63 % lié au nucléaire de puissance. La croissance organique "
            "n'est toutefois que de 1,2 % sur le trimestre : l'essentiel de la progression affichée "
            "vient des acquisitions de Paragon Energy Solutions (décembre 2025) et Certrec "
            "(juillet 2025).",
        "moat":
            "La barrière est réglementaire avant d'être technologique. Un instrument de mesure "
            "installé dans une centrale est qualifié avec le réacteur : le remplacer par un "
            "équipement concurrent suppose une requalification longue et coûteuse qu'aucun "
            "exploitant n'engage sans raison impérieuse — et sûrement pas pour économiser sur un "
            "poste marginal au regard du coût d'un arrêt de tranche. Cette qualification, combinée "
            "à une base installée couvrant la quasi-totalité du parc mondial, transforme chaque "
            "réacteur en annuité de plusieurs décennies. La dosimétrie fonctionne par abonnement, "
            "avec plus d'un million de porteurs de badges facturés en continu. Le marché est enfin "
            "trop étroit et trop normé pour attirer un entrant généraliste, ce qui protège les prix.",
    },
    "NEE": {
        "nom": "NextEra Energy", "devise": "USD", "pays": "États-Unis", "secteur": "Services aux collectivités",
        "industrie": "Électricité régulée et production renouvelable",
        "effectifs": 17_300, "effectifs_au": "31/12/2025",
        "arrete_au": "30/06/2026",
        "description":
            "NextEra réunit deux métiers que peu d'acteurs combinent. Florida Power & Light est un "
            "monopole électrique régulé : son accord tarifaire couvrant 2026 à 2029, approuvé en "
            "novembre 2025, garantit un rendement autorisé de 10,95 % sur les capitaux propres et "
            "des hausses de recettes programmées, pour un investissement annuel de 12 à 13 Md$. "
            "NextEra Energy Resources est le premier producteur mondial d'électricité éolienne et "
            "solaire, avec un carnet contractualisé d'environ 35,1 GW vendus sous contrats d'achat "
            "d'électricité de long terme. Au deuxième trimestre 2026, le bénéfice ajusté par action "
            "atteint 1,15 $ (+9,5 %) ; le groupe vise plus de 8 % de croissance annuelle jusqu'en "
            "2032 et une hausse du dividende de 6 % par an. La demande des centres de données est "
            "devenue un moteur explicite : 21 GW d'intérêt exprimé auprès de Florida Power & Light, "
            "dont 12 GW en discussions avancées. L'acquisition de Dominion Energy, annoncée le "
            "18 mai 2026, a été approuvée par les actionnaires de Dominion le 3 septembre 2026 ; "
            "elle reste suspendue aux autorisations réglementaires, pour une clôture attendue au "
            "second semestre 2027.",
        "moat":
            "Deux fossés de nature opposée. Côté Floride, un monopole territorial concédé : nul ne "
            "construira un second réseau de distribution, les tarifs sont fixés par le régulateur "
            "sur une base de rendement, et la croissance démographique de l'État alimente "
            "mécaniquement la base d'actifs rémunérée. Côté renouvelables, l'avantage tient à "
            "l'échelle et au coût du capital : premier développeur mondial, NextEra négocie "
            "turbines et panneaux à des conditions inaccessibles aux indépendants, et se finance à "
            "un coût que sa taille et sa notation rendent structurellement plus bas — dans un "
            "métier où le projet se décide sur le coût actualisé de l'électricité, cet écart "
            "emporte les appels d'offres. S'y ajoute une ressource devenue la plus rare de toutes : "
            "le foncier déjà sécurisé et les droits de raccordement déjà obtenus, alors que la file "
            "d'attente des réseaux américains s'allonge d'année en année.",
    },
    "NOC": {
        "nom": "Northrop Grumman", "devise": "USD", "pays": "États-Unis", "secteur": "Défense",
        "industrie": "Systèmes aéronautiques, spatiaux et électronique de défense",
        "effectifs": 95_000, "effectifs_au": "31/12/2025",
        "arrete_au": "30/06/2026",
        "description":
            "Northrop Grumman tire 84 % de son chiffre d'affaires du gouvernement américain, "
            "réparti sur quatre secteurs : Aeronautics (3 519 M$ au deuxième trimestre 2026, "
            "+13 %), qui porte le bombardier B-21 ; Mission Systems (3 250 M$, 15,4 % de marge), "
            "l'électronique de défense ; Space Systems (2 753 M$), qui développe le missile "
            "stratégique Sentinel ; et Defense Systems (2 093 M$). Le carnet atteint 104,7 Md$ fin "
            "juin 2026, un record, dont 7,6 Md$ ajoutés sur le seul trimestre par la "
            "contractualisation définitive de Sentinel ; 35 % se convertira en chiffre d'affaires "
            "sous douze mois, 55 % sous vingt-quatre. La moitié des contrats est à prix fixe, ce "
            "qui expose le groupe aux dérapages de coûts : la phase initiale de production du B-21 "
            "a déjà coûté environ 2,0 Md$ de pertes cumulées, avec 1,0 Md$ de provision résiduelle "
            "au bilan.",
        "moat":
            "Les barrières à l'entrée comptent parmi les plus hautes de l'économie : habilitations "
            "de sécurité, installations classifiées, maîtrise de l'intégration de systèmes acquise "
            "sur plusieurs décennies et capacité financière à porter des programmes de dix à trente "
            "ans. Le client est unique mais captif — une fois le maître d'œuvre choisi sur un "
            "programme structurant comme le B-21 ou Sentinel, en changer reviendrait à repartir de "
            "zéro, ce que ni le calendrier stratégique ni le budget n'autorisent. Le carnet, "
            "équivalent à plus de deux années de chiffre d'affaires, confère une visibilité "
            "qu'aucun industriel civil n'obtient. La contrepartie de ce fossé est l'absence de "
            "pouvoir de fixation des prix : le client impose ses règles comptables, audite les "
            "coûts et capte une part de la productivité.",
    },
    "RIO.L": {
        "nom": "Rio Tinto", "devise": "GBX", "pays": "Royaume-Uni", "secteur": "Matières premières",
        "industrie": "Minerai de fer, cuivre, aluminium et lithium",
        "effectifs": 56_890, "effectifs_au": "31/12/2025",
        "arrete_au": "30/06/2026",
        "description":
            "Rio Tinto extrait et vend des matières premières, sans aucune maîtrise du prix auquel "
            "elle les vend. Trois métiers depuis la réorganisation de 2025 : le minerai de fer, qui "
            "reste le cœur du résultat (14 027 M$ de ventes et 6 769 M$ d'EBITDA sous-jacent au "
            "premier semestre 2026) ; le cuivre, devenu le moteur de croissance (8 622 M$ de "
            "ventes, EBITDA en hausse de 84 %) ; et l'aluminium-lithium (9 969 M$). Sur le "
            "semestre, 31 028 M$ de ventes pour 14 826 M$ d'EBITDA sous-jacent (+28 %) et un retour "
            "sur capitaux employés de 17 %. Deux projets changent le profil : Simandou, en Guinée, "
            "a livré son premier minerai à haute teneur en avril 2026 et montera en cadence "
            "jusqu'en 2028 ; Oyu Tolgoi, en Mongolie, vise 500 000 tonnes de cuivre par an entre "
            "2028 et 2036. La politique de distribution prévoit 40 à 60 % du résultat sous-jacent "
            "sur un cycle, l'acompte semestriel ayant été fixé à 50 %, soit 211 cents par action.",
        "moat":
            "Rio Tinto ne possède pas de fossé au sens où une marque ou un réseau en détiennent "
            "un : le minerai est un produit indifférencié et le prix est subi. L'avantage est "
            "celui du coût et de l'emplacement. Les gisements du Pilbara, exploités avec un chemin "
            "de fer et des ports détenus en propre, placent le groupe dans le premier quartile "
            "mondial des coûts — 23,5 à 25 dollars la tonne — ce qui le laisse rentable à des prix "
            "où les producteurs marginaux perdent de l'argent et finissent par fermer, soutenant le "
            "prix. Ces actifs sont irréplicables : ni le gisement, ni les permis, ni quarante ans "
            "d'infrastructure ne se reconstituent. C'est une protection contre la disparition, pas "
            "contre la volatilité : le résultat suivra toujours le cycle, largement dicté par la "
            "demande chinoise d'acier.",
    },
    "ROP.SW": ROCHE,
    "RR.L": {
        "nom": "Rolls-Royce Holdings", "devise": "GBX", "pays": "Royaume-Uni", "secteur": "Aéronautique",
        "industrie": "Motorisation aéronautique, défense et systèmes de puissance",
        "arrete_au": "30/06/2026",
        "description":
            "Rolls-Royce vend ses moteurs d'avion à marge faible, puis gagne sa vie sur leur "
            "maintenance pendant trente ans. Les contrats TotalCare facturent l'après-vente à "
            "l'heure de vol : le revenu suit l'utilisation réelle des flottes, non les livraisons. "
            "Au premier semestre 2026, 11 279 M£ de chiffre d'affaires sous-jacent (+24,5 %) et "
            "2 534 M£ de résultat opérationnel sous-jacent, soit 22,5 % de marge contre 19,1 % un "
            "an plus tôt. Civil Aerospace (6 186 M£) porte 2 266 gros moteurs en carnet ; Defence "
            "(2 484 M£) dispose de 17,5 Md£ de commandes, plus de trois années d'activité ; Power "
            "Systems (2 604 M£) a enregistré 4,6 Md£ de prises de commandes. Les heures de vol "
            "long-courrier atteignent 113 % de leur niveau de 2019. La trésorerie nette s'établit à "
            "2 136 M£, le flux de trésorerie disponible à 1 964 M£, et le groupe a relevé ses "
            "objectifs annuels en juillet 2026. Les petits réacteurs modulaires ont décroché trois "
            "unités en Suède et l'approbation du site de Wylfa, au pays de Galles.",
        "moat":
            "Le fossé tient à la base installée et à la durée. Un long-courrier vole trente ans, et "
            "son moteur ne peut être remplacé par celui d'un concurrent : le choix fait à la "
            "commande engage l'exploitant pour toute la vie de l'appareil, maintenance comprise. "
            "Cette rente est verrouillée par la certification — concevoir et faire homologuer un "
            "moteur civil demande une décennie et plusieurs milliards, ce qui a réduit le marché du "
            "long-courrier à deux ou trois acteurs dans le monde. Le modèle TotalCare convertit la "
            "base installée en annuité indexée sur le trafic aérien, avec un réseau de pièces et "
            "d'ateliers que nul autre ne peut servir. La contrepartie est la cyclicité : le revenu "
            "dépend des heures de vol, et 2020 a montré ce que produit un arrêt du trafic.",
    },
    "VIE.PA": {
        "nom": "Veolia Environnement", "devise": "EUR", "pays": "France", "secteur": "Services aux collectivités",
        "industrie": "Eau, déchets et services énergétiques",
        "effectifs": 215_000, "effectifs_au": "30/06/2026",
        "arrete_au": "30/06/2026",
        "description":
            "Veolia exploite pour le compte de collectivités et d'industriels ce qu'ils ne veulent "
            "pas exploiter eux-mêmes : usines de production et d'assainissement d'eau, collecte et "
            "traitement de déchets, réseaux de chaleur et services énergétiques. Au premier "
            "semestre 2026, 22 193 M€ de chiffre d'affaires, un EBITDA de 3 552 M€ en croissance "
            "organique de 5,0 % et une marge en progression de 70 points de base. L'Eau pèse "
            "8 489 M€, les Déchets 7 771 M€, l'Énergie 5 933 M€. Le groupe indique que 85 % de son "
            "activité est insensible au cycle, portée par des contrats d'une durée moyenne de onze "
            "ans dont 70 % sont indexés sur l'inflation. L'acquisition de Clean Earth, finalisée en "
            "juin 2026, fait de Veolia le deuxième acteur américain du traitement des déchets "
            "dangereux et porte la dette nette à 24,5 Md€, pour un levier annoncé autour de trois "
            "fois l'EBITDA. Le plan GreenUp a atteint son objectif de rentabilité des capitaux avec "
            "deux ans d'avance et vise plus d'un milliard d'euros de chiffre d'affaires dans les "
            "centres de données et la microélectronique d'ici 2030.",
        "moat":
            "Trois protections se superposent. Les contrats d'abord : onze ans de durée moyenne, "
            "indexés sur l'inflation, renouvelés par des collectivités qui changent rarement "
            "d'opérateur parce que la transition est opérationnellement risquée et politiquement "
            "visible. Les actifs ensuite : une usine d'incinération, un centre d'enfouissement ou "
            "un réseau de chaleur sont des infrastructures locales, longues à autoriser et "
            "impossibles à déplacer — un concurrent ne peut pas servir Prague depuis Lyon. La "
            "réglementation enfin, particulièrement sur les déchets dangereux, où le permis "
            "d'exploitation constitue en lui-même la barrière : c'est ce que Veolia a acheté avec "
            "Clean Earth, davantage qu'un chiffre d'affaires. L'échelle complète l'ensemble, en "
            "permettant d'amortir sur des centaines de contrats une ingénierie que personne ne "
            "rentabiliserait sur un seul.",
    },
}

# Les huit ajouts de la version ADD++ (sans fiche documentaire : la page
# « Fiche valeur » ne porte que sur les douze lignes du CTO).
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
