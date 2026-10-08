# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Ce que c'est

Coach de fitness temps réel **dans le navigateur** (`web/static/app/`, joué sur iPad) : la caméra de l'appareil détecte la pose (MediaPipe Tasks Vision, sur l'appareil), l'application compte les répétitions, guide à la voix (annonces françaises pré-enregistrées), enregistre l'historique dans IndexedDB et fait progresser les objectifs. Site **purement statique**, déployé sur GitHub Pages ; aucun serveur. Des gestes (bras en croix, bras levés) pilotent la séance à trois mètres de l'écran.

Une version desktop Python (OpenCV, Flask, SQLite) a existé et a été **retirée** : son code reste au tag `derniere-version-desktop`. Un portage natif Swift est envisagé à long terme.

## Commandes

```bash
python -m scripts.servir_statique 8001   # serveur local sans cache (entrée `statique-dev` de .claude/launch.json)
node scripts/tester.mjs                  # toutes les vérifications, ~5 s ; s'arrête au premier rouge
node scripts/tester.mjs ligues ressenti  # seulement ces tests-là
node scripts/tester.mjs --mettre-a-jour  # réécrire les réponses figées (changement VOULU et compris)
node scripts/lister_annonces.mjs         # réécrit audio/A_ENREGISTRER.md, la feuille de prise de son
python audio/nettoyer_sons.py            # audio/a_traiter/ -> web/static/sons/ (pydub + ffmpeg)
```

Aucun linter. La CI (`.github/workflows/demo.yml`) lance `tester.mjs` puis publie `web/static` à chaque push sur une des branches **qu'elle liste** — lire la liste dans le fichier : une branche absente ne déploie rien, en silence.

## Le principe : chaque règle n'existe qu'une fois

C'est la raison du retrait du desktop : chaque règle vivait en Python et en JS, et l'essentiel de l'énergie passait à les tenir d'accord. **Ne jamais réintroduire un jumeau d'une règle JS, dans aucun langage.** Un outil peut être écrit en Python tant qu'il n'applique aucune règle (`nettoyer_sons.py`, `empreinte_deploiement.py`, `servir_statique.py`) ; un outil qui *applique* une règle importe le module JS (d'où `lister_annonces.mjs` et `verifier_annonces.mjs`, qui ont besoin de `normaliser_nom`).

Les noms JS restent en **snake_case** (héritage du portage) : ne rien renommer, c'est aussi la carte du futur portage Swift.

## Tests

`scripts/tester.mjs` enchaîne :
- **`verifier_methodes.mjs`** : chaque `this.methode()` appelée existe, et les `<script type="module">` inline n'ont pas de faute de syntaxe (`node --check` ne lit que les `.js`, or le module de l'application fait trois mille lignes dans `app/index.html` — une faute y donne un écran blanc).
- **`sommaire.mjs`** (sans argument) : chaque page a un titre et une description pour le sommaire du site.
- **`verifier_donnees.mjs`** : les JSON de `donnees/` se tiennent (voir *Données*). C'est l'ancien rôle des validations au chargement, qui n'existent plus nulle part ailleurs.
- **`verifier_annonces.mjs`** : les tables du coach se tiennent (voir *Coach vocal*).
- **`verifier_instruments.mjs`** : chaque instrument du banc d'essai redit exactement le jeton de sa détection, et toute détection a son instrument.
- **onze `comparer_*.mjs`** : rejouent des milliers de questions figées (poses, scénarios de séance, historiques, barèmes, ligues, objectifs, programmes, ressenti, annonces, variantes, écritures d'historique) et comparent aux réponses de `tests/fixtures/*.jsonl.gz`.

**Les réponses figées ont été produites une dernière fois par l'ancienne implémentation Python**, qui faisait autorité, puis figées. Un rouge veut donc dire « le comportement a changé », pas « c'est faux ». Si le changement est voulu, `--mettre-a-jour` réécrit les réponses avec ce que rend le code — **jamais pour faire taire un rouge non compris**. `scripts/fixtures.mjs` porte la mécanique (`Releve.verifier(ou, cible, cle, obtenu)` désigne la réponse par son *emplacement*, pour pouvoir la réécrire sur place).

Trois décisions tiennent ces tests :
- **Les entrées sont figées aussi** (`tests/fixtures/donnees/`) : un test qui lirait les `donnees/*.json` vivants virerait au rouge au premier réglage de barème sans qu'une ligne de code ait bougé. La validité des données vivantes, c'est `verifier_donnees`.
- **Poses et réponses sont séparées** pour les détections (`poses_detections` figées pour toujours, 9 Mo ; `detections` les jetons, 115 Ko) : un changement de seuil ne réécrit que les jetons. En mise à jour, **toutes** les fonctions de `DETECTIONS` sont rejouées, si bien qu'une détection ajoutée entre d'elle-même dans le jeu.
- **Les familles construites restent** : les poses contiennent, après les tirages au hasard, des familles construites autour des seuils (bras levés buste orienté, un bras levé, élévation, planches, contacts coude-genou, pompes au mur…), et les scénarios des scénarios écrits (`superset_refaire`, `decompte_final`, `pompes_peu_profondes`, `changement_en_cours`, `variante_en_cours`) — les états profonds d'une machine à états sont hors de portée du hasard. Ces entrées ne peuvent plus être régénérées : une nouvelle règle qui demande un cas que le jeu ne visite pas se teste par un script dédié ou une famille ajoutée à la main.

**Un test qui n'a jamais échoué ne prouve rien** : après un changement, saboter la règle et vérifier que le test rougit fait partie du travail. Limite connue : des poses tirées au hasard ne tombent jamais *exactement* sur un seuil, donc un `<` devenu `<=` passe inaperçu aux détections ; `verifier_instruments` imprime les jetons peu visités, dont les seuils sont mal vérifiés. `camera.js` n'a aucun test (il importe MediaPipe depuis un CDN) ; `seance.js` est couvert en partie seulement (par `comparer_seances` et `comparer_variantes`).

## Données (`web/static/donnees/`)

Des **sources éditées à la main** — plus rien ne les fabrique. Chaque fait n'a qu'une source :
- **`reglages.json`** — tous les nombres réglables : barèmes (`specs`), ligues, XP, note d'athlète, retour des variantes. Édité depuis `dev/baremes.html`. **Le pourquoi de chaque réglage est dans `docs/reglages.md` : le lire avant de changer une valeur.**
- **`baremes.json`** — le *socle* qui ne se règle pas : échelles d'haltères, matériel par exercice (`halteres`, `brut`), accessoires, matériel par défaut, repères écrits de la note.
- **`composer_baremes(socle, reglages)`** (`paliers.js`) assemble les deux au chargement : specs complétées de leurs défauts, `xp.*` renommés dans `ligues`. **Toute page qui construit un `Baremes` passe par là** — l'application, `dev/baremes.html`. Avant, l'application relisait une *copie* des réglages : éditer `reglages.json` n'aurait rien changé.
- **`fiches.json`** — le texte des fiches (cinq champs). Édité depuis `dev/fiches.html`.
- **`mouvements.json`** — ce qui est couplé au code : `detection`, `erreurs`, `amplitude` (par **nom** de fonction de `detections.js`), `orientation`, `changements`, variantes, `materiel`, `est_echauffement`. **`avec_fiches(mouvements, fiches)`** (`seance.js`) y remet le texte au chargement, dans l'application comme dans la démo.
- **`seances.json`**, **`programmes.json`** — les séances et les programmes partagés.
- **`sons.json`** — les tables du coach : `fichiers` (clé → variantes `.wav`), `priorites`, `delais`, `silences`, `textes` (le texte de chaque brique), `briques` (clé → fichier), `fragments`, `orientations`, `longueur_maximale_nom`.

Les pages `dev/` rechargent les données déployées, les rendent éditables, recalculent tout avec les mêmes modules que l'application, et rendent le fichier prêt à coller : on colle dans `web/static/donnees/`, on pousse. Leur brouillon (`localStorage`) est jeté si le fichier déployé a changé depuis.

**Le nom d'une séance est à la fois sa clé et son titre**, et il est référencé ailleurs : valeurs du dict `seances` de chaque programme (sans quoi le programme ne pilote plus rien), `nom_seance` des séances enregistrées (« dernière fois », semaine du programme), `seances_locales` des appareils. Renommer une séance casse ces liens en silence ; `verifier_donnees` attrape seulement ceux des programmes.

**Aucun mouvement de tirage ne se fait sans haltère** (les quatre mouvements de dos en exigent) : une séance sans matériel couvre poussée, jambes et gainage, et le dit dans sa description. Ajouter un exercice demande sa détection, son instrument, sa fiche, sa spec, son entrée de matériel, ses bornes de ligue — `verifier_donnees` signale ce qui manque.

## Architecture (`web/static/`)

`app/` l'application ; `demo/` le banc d'essai d'un exercice isolé ; `dev/` les pages de réglage ; `js/` les modules ; `sons/` les annonces (nom de fichier = texte prononcé). Feuilles de style partagées à la racine (`palette.css`, `hud.css`, `programmes.css`, `exercices.css`, `ressentis.css`, `ancrages.css`, `graphique.css`, `programme_resume.css`, `editeur.css`).

**Une page qui garde sa logique pour elle est invérifiable.** Les règles vivent dans des modules purs (`circuit.js`, `moteur.js`, `seance.js`, `tutoriel.js`, `progression`…), testables dans Node ; la page ne fait que câbler.

**Un cycle d'imports ne se rattrape pas en module ES** : il laisse une liaison non initialisée et la page meurt au chargement sur un `ReferenceError` qui ne nomme aucun des deux fichiers. Sortir la feuille dans un module sans dépendance (c'est l'origine de `cible_manuelle.js`, ré-exporté par `objectifs.js`).

### Messages

**Tout texte destiné à l'utilisateur porte une clé** (`messages.js`) : une fonction d'erreur de forme retourne une clé, `texte()`/`libelle_etape()` ne lèvent jamais (elles tournent dans la boucle d'images, où une exception gèle l'écran) et une clé inconnue rend `null` — rien à l'écran. Ajouter un message se fait dans ce module.

L'état de séance porte quatre champs qui ne se confondent pas : `erreur` (faute de forme, bandeau rouge), `consigne` (quoi faire, bandeau bleu), `stage` (jeton brut du détecteur), `etape_libelle` (sa traduction). **Une faute de forme n'existe que pendant l'effort** : `peindre_hud` ne montre le bandeau rouge qu'en phase `exercice`. **Une consigne d'absence s'efface dès que le corps revient** : remise à `null` en tête de la branche « corps vu » de la boucle.

### Séance (`circuit.js`, `moteur.js`, `seance.js`, `etat.js`)

- **`Circuit`** : une séance en cours, faite de `BlocExercice` (mode, séries, répétitions/durée, repos). Phases `preparation` → `exercice` → `recuperation_serie` → … → `termine`/`abandonne`. L'entrelacement (`entrelace_avec`, superset gauche/droite) est la logique la plus délicate (`_est_entrelace`, `terminer_serie`). **Invariant : la phase `exercice` implique un bloc courant** — la règle vit dans la classe, pas chez les appelants.
- **`executer_mode`** dispatche vers répétitions / maintien / chrono / AMRAP / échauffement, et retourne toujours un triplet `(derniere_rep, repetitions, serie_terminee)`. Une fin de série passe par `_finaliser_serie`, et l'état temporel du bloc se nettoie dans `reinitialiser_etat_serie`, seul endroit qui en connaît la liste.
- **Deux mesures du temps, incompatibles** : chrono et AMRAP en temps *mural* (ils ne se mettent pas en pause hors champ) ; maintien et échauffement en *deltas* image par image, **plafonnés à `INTERVALLE_MAX`** (0,5 s), pour qu'un retour dans le champ ou un onglet suspendu ne crédite pas d'un coup tout le temps écoulé.
- **L'horloge est celle de la séance, `seance.maintenant()`**, jamais `performance.now()` en dur — y compris pour les repos et `duree_totale`. C'est ce qui permet de rejouer 45 minutes de séance en quelques millisecondes dans les tests.
- **Un bloc porte `repetitions` et `duree` à la fois ; seul le mode dit lequel est joué.** Point d'entrée unique : `cible_du_bloc(bloc)` (adossé à `MODES_CIBLE_TEMPORELLE`, AMRAP compris). Jamais de `repetitions || duree`. Une **cible nulle dans l'unité jouée** est refusée (`problemes_des_blocs`) : elle finirait la séance entière à la première image, en silence.
- **Échauffement** : détection *facultative* (affichage seulement, jamais une condition d'avancement) et **invisible dans les statistiques**, exclu à la source par `resultats_par_exercice` (point d'entrée : `est_echauffement(bloc)`). Ne pas ajouter de filtre en aval.
- **Deux barres de progression, jamais en même temps** : échauffement ou exercices, décidé par `dans_echauffement`.
- **Variante en pleine séance** (`passer_a_la_variante`) : le bloc repart à la série 1 sur la variante ; chaque série enregistrée porte le nom de son mouvement ; le mouvement quitté garde sa ligne (`bloc.abandons`) ; le `Circuit` ne connaît pas le catalogue (`variante_possible()` rend un nom, l'appelant résout l'`Exercice`). Refusée sur un bloc entrelacé.
- **Refaire la dernière série** ne se déduit pas de l'état courant (`terminer_serie` a cinq sorties) : `terminer_serie` écrit un repère `_derniere_serie_terminee` **avant toute mutation**, `refaire_derniere_serie` le restaure (y compris `_exercice_precedent_entrelace`, et `index_exercice` d'abord) et oublie tout de suite le résultat désavoué.
- **Terminer une série à la main** est le seul chemin vers un `completee` faux : `terminer_serie_manuellement` interroge `objectif_serie_atteint`. La durée réalisée se lit avec `duree_realisee(bloc, etat)`, jamais en chaînant les compteurs de modes (un gainage lâché avant une seconde est *falsy*).
- **`payload_etat`** (`seance.js`) est le contrat de l'écran : il relit les champs dérivés du circuit au lieu de les recopier au fil de la boucle.

### Progression (`paliers.js`, `niveaux.js`, `objectifs.js`, `ressenti.js`, `calibration.js`, `variantes.js`, `programmes.js`, `ligues.js`, `cible_manuelle.js`)

Rien n'est stocké hormis l'historique et les ancrages : tout se recalcule à la lecture.

**Niveau ≠ objectif, et rien ne doit brouiller la distinction.** Le *niveau* est le plus haut palier **jamais** validé (preuve stricte, ne recule jamais). L'*objectif* est ce que la prochaine séance demande : il monte ou descend, et peut passer **sous** le niveau (délestage, pas régression).

- **Barème** (`paliers.js`) : voir `docs/reglages.md`. Invariant du volume ; tranches de longueurs inégales, donc **parcourues** (`_iterer_tranches`), jamais calculées par modulo ; ordre cible → poids → séries ; **tranche ouverte** sans fin, si bien qu'un objectif n'est jamais hors d'atteinte. Le générateur de tranches est infini : tout appelant pose sa condition d'arrêt. `est_suivi_par_le_moteur(nom)` dit si un exercice a des paliers. Quiconque calcule un volume sans palier en main passe par `volume_exercice(nom, …)`, qui connaît la charge du corps. **`charge_facultative`** (poids_min à 0) est le point d'entrée unique de « ce mouvement se fait à vide ». Bizarrerie voulue : le palier suivant peut demander **moins** de répétitions quand il monte en charge (l'écran l'explique).
- **Matériel** (`materiel.js`) : un inventaire `{poids: quantité}`, dont dérivent l'échelle à un haltère et celle à la paire. `normaliser(null)` rend le matériel supposé (profil muet), un inventaire déclaré vide reste vide. Trois listes : la gamme proposée au questionnaire, ce qui est déclarable (1-60 kg au demi-kilo), et le matériel **supposé** — figé sur l'ancienne gamme : l'allonger changerait le barème de tout profil muet. Le repli « barème toujours calculable » vit dans `echelle_exercice`, pas sur l'inventaire (un squat sans haltère a pour vraie échelle le poids du corps).
- **Niveaux** (`niveaux.js`) : une performance valide un palier si elle est au moins aussi lourde **et** au moins aussi volumineuse, au **maillon faible** (séries `completee` seulement). `etat_niveau` distingue trois cas qu'un écran ne doit pas confondre : hors barème (`niveau` null, ce n'est pas « niveau 0 »), barème épuisé, cas ordinaire. `montees_de_niveau` rejoue l'historique en ordre chronologique.
- **Ancrages** : recalent un niveau que l'historique ne prouve pas. Un ancrage fait **table rase et plancher** à la fois. Repère chronologique : `apres_seance_id`, **jamais la date** (`JJ/MM/AAAA` ne se compare pas). C'est un journal : seul le dernier ancrage compte. L'écran ne demande jamais un numéro de niveau, mais une **performance**, et refuse celle qui n'atteint pas le palier 1.
- **Objectifs** (`objectifs.js`) : trois règles dans l'ordre — repère de la dernière séance ± ressenti ; exercice jamais fait → départ de la note d'athlète ; sinon `niveau + 1`. Une note relevée à la main pose un plancher. Un exercice jamais fait dont une **variante plus facile** a un niveau part du palier 1. Un bloc échappe au moteur pour trois raisons seulement : pas de barème, mode qui ne mesure pas la même chose, cible manuelle. `appliquer_a_blocs` (dictionnaires) et `appliquer_a_circuit` (`BlocExercice`) partagent `objectif_pour`. Le drapeau « 1re fois » est posé par l'affichage, jamais par une fonction partagée avec l'écriture.
- **Ressenti** (`ressenti.js`) : toute la progression tient dans la table `AJUSTEMENT` : réussi +1, « facile » +2, « trop facile » +3 ; échoué 0, « trop dur » −1. Pas de réponse = comportement de base. Le repère est le **palier visé** à la dernière séance, re-dérivé des cibles stockées (`_cible_visee`), jamais le niveau. Un échec ne fait **pas** reculer (`base_apres_echec`). Une ancienne série de test (`CIBLE_TEST`) n'est ni réussie ni échouée (`est_serie_de_test`). Les écrans ne proposent que les réponses qui *changent* quelque chose ; pas de bouton neutre.
- **Note d'athlète** (`calibration.js`) : une note générale 1-10, traduite par les **bornes de ligue** (rang par note), jamais par un numéro de niveau ; rien n'est ancré. Elle monte toute seule (`note_mesuree`, lue sur la **dernière** séance de chaque exercice, pas le record) ; relevée à la main, elle pose un plancher jusqu'à la séance suivante (repère `note_relevee_apres` = id de séance). `arrondi_python` reproduit l'arrondi au pair (`Math.round` diffère sur les demis exacts).
- **Variantes** (`variantes.js`) : une substitution est une **préférence du profil** (`utilisateurs.variantes`, `{original: joué}`), jamais une donnée de séance — elle ne doit **jamais atteindre une séance écrite** : `appliquer_au_circuit` sur le seul chemin de jeu, `substitution` pour l'affichage. `definir` vérifie la chaîne, la jouabilité et l'unité. **On remonte tout seul** (`montees`) : une séance menée à son terme qui prouve la performance de retour fait passer au cran du dessus — lue sur la séance jouée, jamais sur le record ; un cran par séance et par clé ; rien sur une séance abandonnée. La montée est une annonce de fin de séance avec un bouton « Rester sur… ». Un programme garde l'exigence du mouvement complet (`via_variante`) sans toucher à l'avancement.
- **Programmes** (`programmes.js`, lecture seule) : une performance à atteindre par exercice ; rien n'est stocké. La ligne affiche la **prescription** et sa traduction sur le barème (par le **volume**, ce qui aplatit la structure des séries). Une seule convention de charge partout : **le poids d'un haltère**. Le `pourcentage` est la moyenne des avancements (bornés à 100 %). Le lien libellé → séance est une **donnée** (`seances` du programme). **Un programme se vit à la semaine** (`semaine_du_programme`) : cycle de sept jours démarrant à la première séance, cases cochées par identifiant, une séance dans le désordre coche la première case vide de son libellé, série de cycles réussis, rythme multiple du nombre de séances (`programme_tours`, borné à la lecture). Dates en heure murale naïve (`Date.UTC`). Il n'y a **pas d'éditeur de programme** : `programmes.json` s'édite à la main.
- **Ligues** (`ligues.js`) : le rang vient du **volume** du palier atteint, comparé à des **bornes par exercice en volume absolu** (`seuils_par_exercice`), avec repli sur une table relative pour un exercice sans bornes — repli qui masque aussi un branchement oublié. Hors barème = pas de ligue. `rang_pour_volume` sature au dernier rang. La ligue générale avance d'un cran par niveau général, et c'est le **coût** du niveau général qui porte l'exigence. Inégalité de cadence assumée entre mouvements chargés (deux axes de croissance) et au poids du corps (un seul). `ligue_pour_rang` rend `cle` et `division_index` pour les écrans.
- **Cible manuelle** (`cible_manuelle.js`) : un bloc dont la cible s'écarte du palier proposé est marqué et le moteur ne le touche plus. La marque appartient à un **profil** (`cible_manuelle` = liste d'identifiants ; un format inconnu vaut « personne »). **Une séance menée à son terme entérine ses cibles figées** (`enteriner_cibles_manuelles`), seulement sur une séance locale. L'éditeur part des valeurs **du moteur** (`blocs_a_editer`) : sinon enregistrer sans rien toucher figerait tout.

**Fiche d'exercice** : niveau, ligue, graphique, recalage et consignes au même endroit. La cible d'un exercice jamais fait se lit dans `objectifs_par_exercice` (« Première séance »), jamais dans le palier 1. Pas de jauge ni de total de paliers sur une fiche : ce qui exprime un objectif appartient aux programmes.

### Détection (`detections.js`, `positions.js`, `compteur.js`, `landmarks.js`, `outils.js`, `instruments.js`)

Chaque mouvement a une fonction `*_detection(corps)` qui rend un jeton (`debut`/`fin`/`milieu`/`maintien`/`repos`). **`debut` et `fin` désignent un moment du comptage, pas une posture** : le compteur s'arme sur `debut` et compte sur `fin`, la fin de la phase concentrique (le haut d'un curl, le verrouillage d'une pompe, le retour debout d'un squat). Un mouvement compté a **deux seuils** (hystérésis : les déplacer ensemble), un maintien un seul.

Règles apprises, à appliquer à toute nouvelle détection :
- **Un angle se lit en 2D** : une flexion dans le plan sagittal (genou, hanche) est illisible de face. Préférer un repère **vertical** rapporté à un segment du corps (`_descente_hanche`) dès que la fiche demande une vue de face.
- **Bilatéral vu de face** : les deux côtés doivent franchir le seuil (vieux bug `a and b < seuil`). **Vu de profil**, le membre éloigné est estimé : moyenner (gainage), ou lire **le bras le mieux vu par `visibility`** quand l'estimation décroche (`_bras_proche`, pompes) — jamais par `z`.
- **Une détection dit quelle forme a le corps *et* où il est** : sans condition de position, un développé épaule comptait des bras baissés, un développé couché comptait debout. Une condition de position partagée par `debut` et `fin` fait tomber tout le reste en `milieu`.
- **Un maintien se reconnaît à ce qui le rend difficile** (hanche décollée, épaules soulevées), pas à sa seule forme. Vérifier au banc qu'une condition d'effort filtre vraiment.
- **Une faute de forme ne retire jamais une répétition.** **Ce qui compte et ce qui est bien fait sont deux seuils** : les pompes arment à 120° (`SEUIL_COMPTAGE_POMPE`) et `Exercice.amplitude` + `suivre_amplitude` avertissent au moment où la répétition compte si le point le plus bas n'est pas passé sous 100°.
- **Devant une détection qui compte mal, lire d'abord ce que la fiche omet de demander** avant de déplacer un seuil (le squat : le contact coude-genou n'était demandé qu'en troisième ligne).
- `CompteurMouvement` refuse deux répétitions à moins de `DELAI_MIN_ENTRE_REPS` (un écho de détection), avec l'horloge de la séance.

**Gestes de contrôle** (`positions.js`) : ils ne doivent pas se confondre avec un mouvement d'exercice. `deux_bras_leves` exige un **buste debout** (sinon le haut d'un développé couché remettait la série à zéro). Un bras seul corrige le compte (droit +1, gauche −1) à condition que **l'autre poignet soit sous son épaule**. La règle du compte vit dans `ajuster_repetitions` (phase `exercice`, modes à compte) ; un +1 ne touche que le compteur et c'est `executer_mode` qui l'annonce et clôt la série ; un −1 fait reculer `derniere_rep`. `bras_en_x` ne contraint que les abscisses : la hauteur est libre.

**Instruments** (`instruments.js`) : chaque détection redécrite en mesures et zones ordonnées, pour le banc d'essai. Jamais sur le chemin du comptage ; c'est une copie des seuils, tenue par `verifier_instruments`.

**Repère gauche/droite** : le navigateur passe la vidéo brute au modèle, l'étiquetage est correct ; `Camera.miroir` ne touche que le dessin. Les séances importées de l'ancien desktop (capture en miroir) portent l'étiquetage inversé sur les exercices asymétriques.

### Fiches et texte

Une fiche (`Exercice.fiche()`) a des champs qui ne se recouvrent pas : `description`, `mise_en_place` (avant de commencer, cadrage caméra compris), `instructions`, `sensations` (ce qu'on doit sentir et ce qui ne doit pas arriver), `erreurs_frequentes` (pédagogie écrite — à ne pas confondre avec `erreurs`, des **fonctions**). `orientation` est le seul champ que le coach **prononce** (cinq valeurs ; `null` = « rien de sûr à dire », jamais « face » par défaut). `changements` (`[fraction, "sens"|"jambe"]`) fait dire au coach de changer de sens ou de jambe pendant un échauffement (`annoncer_changements`, sans état sur le bloc). **Un champ d'`Exercice` oublié dans `exercice_pour` ne lève rien** : il vaut `undefined` partout (c'est arrivé à `orientation`, et le coach n'a jamais dit où se placer).

`dev/fiches.html` montre chaque fiche telle qu'elle s'affiche, à côté de ce que le coach dira et de ce que la détection vérifie : c'est ce qui rend une contradiction visible. Ses avertissements (jargon, phrase de plus de dix-huit mots, accord genré) aident et ne bloquent rien — **un relevé qui crie partout apprend à ne plus être lu**.

### Coach vocal (`annonces.js`, `lecteur.js`, `sons.json`)

Il n'y a **aucun TTS** : toutes les voix sont enregistrées à la main. D'où la règle : **une annonce se compose, elle ne s'enregistre pas en entier.** Une phrase est une suite de briques, chacune enregistrée une fois. **L'écrit est gratuit, la voix est chère** : l'écran peut tout dire, la voix factorise.

- **Deux critères décident d'un découpage** : la **recombinaison** (le nom d'un mouvement se dit derrière trois amorces — « prochain exercice », « le premier exercice sera », « pour finir ») et la **couture**, qui doit tomber sur une pause que la phrase a déjà. D'où une charge enregistrée **entière** (« prépare un haltère de 8 kilos ») : couper avant le nombre tombe dans un groupe nominal et s'entend.
- **Le nom du fichier est le texte prononcé**, normalisé (`normaliser_nom`) : la feuille de prise de son se **dérive** (`lister_annonces.mjs`) au lieu d'être tenue à la main. `sons.json` porte `textes` *et* `briques` ; `verifier_annonces` contrôle que chaque brique porte le fichier que son texte produit, l'absence de collision, la longueur des noms, les orientations, les amorces de `Circuit` et les changements, et que la charge cousue par fichiers (`fichier_assemble`, ce que fait l'application) mène au même nom que son texte.
- **L'amorce se tranche dans `Circuit.amorce_annonce(bloc)`** (comparaison d'identité, pas d'index ; une séance d'un bloc est « premier »).
- **Une séquence est indivisible** (`Lecteur.sequence` empile une seule entrée). **Un fichier absent est un silence, jamais une panne** : on enregistre par lots.
- **Une clé inconnue de `fichiers` se tait** (`coach()` ne lève pas) : une table de clés qui ne lève pas se vérifie de l'extérieur. Rétablir un palier sonore demande sa clé, son fichier, sa priorité et le seuil qui l'appelle — tous, ou aucun. **Un fichier que rien ne déclare est aussi muet qu'un fichier absent** : relancer le diff entre `sons/` et ce que réclament les tables.
- **Lecteur** : un son à la fois ; file à priorités ; un événement ≥ 5 vide les petits sons en attente ; un **blanc entre deux phrases** (`silences.entre_annonces`), mais **un chiffre n'est pas une phrase** — un son de rythme (priorité ≤ `silences.priorite_rythme_max`) part tout de suite et remplace celui de son espèce. Délai minimal par type (`delais`), sans quoi une correction se répète à chaque image. `silence_avant` (`silences.presentation`) sur la seule annonce longue (présentation du prochain exercice) ; **sous `silences.repos_minimal` secondes de repos, on n'annonce que ce qui vient** ; sans repos, le changement de bloc se détecte via `_derniere_serie_terminee`.
- **Écouteurs** : un contexte qui sort de `running` est relancé ; un `devicechange` **recrée** le contexte (WebKit garde parfois un contexte « running » muet) ; une entrée jouée sur un contexte arrêté est jetée ; une relance refusée s'arme sur le prochain `pointerdown`. `son_actif()` alimente le voyant du HUD.
- **iOS** : le son se prépare **au clic** (`lecteur.preparer()` dans le gestionnaire du geste) — sans lui, tout reste muet plus tard sans erreur.
- **Pendant les pauses** : `annoncer_temps_repos` (repère sur la séance, remis à `null` à chaque entrée en pause et au retour à l'effort ; `Math.trunc`). « À la moitié » a été retiré : **devant un coach trop bavard, chercher d'abord l'annonce qui redit ce qu'une autre dit déjà.**
- Les briques de cadrage dormantes restent déclarées : les retirer rendrait orphelins des `.wav` enregistrés.

### L'application (`app/index.html`)

**Ordre d'une séance : installation → guide d'exercice → préparation → effort.**
- **Installation** : la caméra vérifie que le corps entier tient dans l'image (`POINTS_DU_CORPS_ENTIER`, dérivé de `PARTIES`) pendant deux secondes ; une seule consigne, « recule ». Elle se referme sur ce seul contrôle, sans geste. C'est **sa sortie** qui présente le premier exercice (`fermer_installation`) ; la branche `preparation` d'`annoncer_changement` est délibérément muette (la phase est posée dès le constructeur). Le voile de repos est retiré pendant qu'on se place, le HUD masqué.
- **Guide d'un exercice** (premier passage sur un mouvement) : suspend le comptage sans suspendre la séance — un drapeau de page, **pas une phase** ni `statut = "paused"`. Calque en `z-index: 11`, hors de `#restOverlay`. Il ne parle pas (l'annonce vient de passer). Fermé **par geste**, il vaut pour l'entrée en série ; par le bouton « J'ai compris », non. Son `HoldPosition` est à lui.
- **Préparation** : un seul geste (bras en croix 1,5 s) lance la séance. Valider une série, remettre à zéro, ±1 : **3 s**. L'anneau de geste montre la tenue la plus avancée ; `progression_maintien` lit l'avancement **sans appeler `update`** (qui ne rend la transition qu'une fois).
- **Tutoriel d'installation** (`tutoriel.js`, pur) : une seule étape, la place autour de soi — **avant d'ajouter une étape, chercher qui la dit déjà**. Il rend des clés : `sons.textes` pour le bandeau, `sons.briques` pour la voix.
- **Cadrage** (`cadrage.js`) : **ne parler que lorsque la détection ne peut pas travailler** — un contrôle de distance « approche-toi » se déclenchait sur une planche parfaitement cadrée, et a été supprimé. Les points requis sont **observés** (corps espion `Proxy`), pas déclarés. La `visibility` n'entre pas dans le calcul (elle s'effondre sur le membre éloigné d'une vue de profil). Il se tait au décompte. `message_de_cadrage` garde son contrat `{partie, action}` pour pouvoir rebrancher une consigne fine sans prise de son.

**Accueil d'un profil neuf** (`#ecranBienvenue`) : identité d'abord (pas de profil inventé), puis matériel, note, programme, gestes, appareil. **Tout ce qui se touche vient d'abord** ; la caméra s'ouvre à la fin et à partir de là plus rien ne se clique. Une phrase par écran, deux écrans par étape au plus, **aucune voix** tant qu'on lit — *le canal suit la distance*. Le questionnaire de matériel **part vide** (cocher à sa place, c'est répondre à sa place). Chaque étape écrit ce qu'elle récolte en la quittant (`recolter_etape`) ; `onboarding_termine` ne se pose qu'à la dernière. La garde est dans `ouvrir_pour_le_profil`, appelée au démarrage **et** au changement de personne. La pratique (`#ecranPratique`, balisage de `.installation`) est une machine à états (`PHASES_PRATIQUE`) : chaque consigne de geste dit à quoi il sert ; aucune phase ne se franchit au doigt ; « Passer cette étape » avance d'une phase. La caméra se demande depuis un bouton, avant tout `await` ; un refus n'est jamais bloquant ; en sortant, elle est suspendue et non fermée. L'accueil a sa propre boucle d'images.

**La mémoire des tutoriels vit sur le profil** (`tutos_vus`), pas en `localStorage` : deux personnes partagent la tablette. Toute lecture passe par `tutos_vus(profil)` (pas de champ = rien vu ; il n'existe aucune migration côté JS). `marquer_tuto_vu` rend un booléen pour éviter une écriture inutile.

**Profils** : « Qui s'entraîne ? » s'impose à chaque lancement (`profil_a_choisir`) ; le dernier profil est pré-désigné via `localStorage` (commodité de l'appareil, pas donnée d'entraînement). **Changer de profil ou de matériel reconstruit le moteur** (`construire_moteur`) : `Baremes` normalise l'inventaire une fois pour toutes. Profil en lecture seule par défaut ; quatre mesures facultatives (`poids_corps_kg` : jamais raccourci en `poids`, qui désigne la charge). Supprimer un profil descend les clés étrangères ; le dernier profil ne se supprime pas ; l'export est proposé avant.

**Historique** (`historique.js` + `stockage.js`) : la base est un **objet JS ordinaire** de collections reprenant d'anciennes tables (`utilisateur_id` seulement sur les racines `seances` et ancrages ; filtrer les racines puis descendre). Les identifiants sont croissants (`prochains_id`). `stockage.js` : **IndexedDB, la base entière dans un seul enregistrement** (écriture atomique) ; `charger()` ne lève jamais ; `sauver()` rend un booléen que l'écran de fin affiche. **L'export n'est pas un raffinement** : Safari purge les sites peu visités. `seances_locales` (sixième collection) est **optionnelle à l'import** — l'exiger rendrait illisibles les sauvegardes existantes.
- **Les statistiques disent ce qui a été fait, les niveaux ce qui est prouvé** : `statistiques_exercices` garde les séries manquées (seules une série vide et une séance abandonnée sont écartées).
- **La charge est portée par la série** : `resume_series(series, mode)` est le point d'entrée unique des pastilles (`11×5 kg`, `15` au poids du corps, une durée sans charge).
- Un seul marqueur de progrès dans l'historique : la montée de niveau.
- Le `<summary>` d'une séance porte date, durée et nombre d'exercices ; le nom d'un exercice mène à sa fiche (avec retour à la séance lue).

**Écran de fin** : la même fiche que l'historique (`dessiner_seance`, `brancher_fiches_de_seance`), relue en base. L'écriture est automatique ; le bouton « Enregistrer la séance » confirme, ou réessaie si le stockage a refusé. Le ressenti s'y saisit, et après coup depuis l'historique (`ressentis_ui.js` ne décide rien, il propose les réponses qui changent quelque chose).

**Éditeur de séances** : une séance modifiée vit dans `seances_locales` et **masque** la version déployée (badge, bouton « revenir à la version du fichier ») — une édition faite loin de l'ordinateur ne doit pas disparaître au déploiement ; corollaire : une correction de `seances.json` n'atteint plus cette séance sur cet appareil. Règles : partir des valeurs du moteur ; la cible va dans le champ de son mode (`MODES_DUREE`) ; refuser à l'enregistrement (`problemes_des_blocs`, liste complète) ; un nom orphelin reste sélectionné (`optgroup` « Inconnu ») ; l'entrelacement est un **drapeau « avec le bloc suivant »**, recalculé.

**Liste des séances** : la carte est un `<article>` dont seule la zone de titre est un bouton (**devant un élément qui ne peut rien contenir, changer l'élément porteur**). **Choisir n'est pas commencer** : le clic sélectionne, « Démarrer la séance » lance — `verrou_ecran.tenir()` et la préparation audio au plus près de ce clic. Le contenu ne s'affiche qu'une fois (déplié). Les cibles figées et « 1re fois » restent visibles sans clic. La carte de programme (`programme_resume.css`) montre la semaine ; toucher une case est une bascule ponctuelle ; `null` dans `programme_choisi` invite à choisir.

**HUD** (`hud.js`, `hud.css`) : tout `hud.js` est une fonction de `donnees` (`payload_etat`) — ni requête, ni horloge, ni caméra. Les commandes s'exécutent via `brancher_commandes(executer)`, par **nom**. Les commandes secondaires vivent dans un menu qui s'ouvre vers le haut et se referme **au changement de phase**, jamais à chaque image. La fiche à l'écran est un `<details>` replié pendant l'effort, déplié en pause, au-dessus du voile de repos (`z-index: 7`) ; `fiche` (courant) et `fiche_suivante` (pendant `repos_exercice`) sont deux champs ; **deux choses qui ne changent pas aux mêmes instants demandent deux repères** (`fiche_affichee`, `fiche_en_effort`). L'image est en `object-fit: contain`, **jamais `cover`** (recadrer cacherait ce que le modèle analyse). Socle CSS : **`[hidden] { display: none !important; }`** — sans lui, une règle `display` neutralise `hidden` en silence.

**Graphique** (`graphique.js`) : rend une chaîne SVG, l'axe part de zéro. Au doigt : un appui montre le détail, un second dans les 500 ms ouvre la séance (reconnu par le temps et la cible, pas `dblclick`) ; cible de toucher transparente (`fill="transparent"`) plafonnée à la moitié de l'écart entre points ; `touch-action: manipulation` ; état `.actif` (`:hover` ne dit rien au doigt).

**Veille** (`veille.js`) : deux mécanismes. Le **verrou** (libéré quand la page se cache, repris sur `visibilitychange` ; demandé **depuis le gestionnaire de clic, avant tout `await`**) et, en repli, la **vidéo de la caméra lue** dans un élément attaché et rendu (un pixel quasi transparent, jamais `display:none`). L'état s'affiche dans le voyant du HUD, sans prétendre distinguer les causes d'un `NotAllowedError`.

**Caméra** (`camera.js`) : ouverte **une fois par session** — entre deux exercices les pistes sont désactivées, pas arrêtées (chaque `getUserMedia` peut redemander l'autorisation). **Une seule pose par défaut** (36 images/s contre 24 à quatre poses) ; `choisirPose` suit la même personne d'une image à l'autre. `preparerDetecteur` sérialise ses appels. **Ne pas oublier `camera.preparer()`** : sans détecteur, `detecter` rend `[]`, exactement comme une image vide. **Le corps a deux formes** : `peindre` veut la pose brute, les règles veulent le corps nommé (`construire_corps`). Une exception dans un `requestAnimationFrame` gèle le flux définitivement : la boucle attrape, trace et replanifie.

**Barres d'onglets** : rendues par `remplir_barres_onglets()` dans chaque `[data-onglets]`, **avant** le câblage générique ; le bouton de profil est délégué au document. L'écran de séance n'a pas de barre.

### Démo et banc d'essai (`demo/index.html`)

Un exercice isolé, comptage et voix, sans séance ni historique : le livrable pour un testeur et l'outil de diagnostic. Elle lit les mêmes `mouvements.json` + `fiches.json` (mouvements non-échauffement avec détection, triés) et les sons de `../sons/`. Les résultats s'accumulent (`localStorage`, attaché à l'origine : ne pas changer d'adresse) ; un QCM par exercice et un seul bouton de copie. Fluidité par minute **de caméra**, cumulée d'un exercice à l'autre, en histogrammes (arrondis, pas tronqués) ; un écart de plus de deux secondes est une suspension. `?poses=N` force le nombre de poses.

**Le banc d'essai** (visible par défaut, `?banc=0` le masque) : jeton brut, armement, part de **temps** par jeton dès la préparation (`perdu` quand il n'y a pas de corps), jauges des instruments, angles sur l'image, faute de forme en direct, et un **journal des tentatives** (`SuiviTentatives`) : aller complet, aller interrompu, retour incomplet ; une tentative n'est un échec qu'au-delà de 30 % du chemin (`PROGRESSION_SIGNIFICATIVE`), sinon c'est une hésitation. Le résumé copié enregistre des nombres.

### Déploiement et cache

`scripts/empreinte_deploiement.py` (CI, copie `_site` seulement) marque chaque ressource locale de l'empreinte du commit (`camera.js?v=<sha>`, imports internes et `fetch("../donnees/*.json")` compris, adresses absolues jamais) : chaque fichier expire pour son compte, et un document neuf combiné à un module en cache échoue en accusant un code déjà corrigé. **Le document ne peut pas être marqué** : `version.js` relit `version.json` (seul fichier jamais marqué) en `no-store`, compare à sa propre empreinte (`import.meta.url`), et recharge sous `?maj=<empreinte>` en cas d'écart — sans toucher IndexedDB ni `localStorage`, et sans rien faire hors ligne. **La racine du site est le sommaire** (`scripts/sommaire.mjs`, joué par la CI sur `_site`) : une carte par page `.html`, tirée de son `<title>` et de sa `<meta name="description">`, rangée par dossier. Une page ajoutée y apparaît d'elle-même ; `tester.mjs` refuse une page sans titre ni description, sans quoi sa carte ne dirait rien.

**En développement, utiliser `statique-dev`** (`Cache-Control: no-store`) : `python -m http.server` laisse le navigateur ressortir un module depuis son cache avec un statut 200, et *un import figé fait passer un code correct pour cassé*. L'entrée `statique` reproduit le déploiement.

**Vérifier une page dans le volet de prévisualisation** : un volet masqué ne déclenche aucun `requestAnimationFrame` — remplacer la fonction par un pas à pas avant le démarrage de la page. Une caméra se simule en remplaçant `getUserMedia` par le `captureStream()` d'un `<canvas>`. `HoldPosition` lit `performance.now()` : un test de geste doit laisser passer le temps réel. Le verrou d'écran ne se vérifie que sur l'appareil.

## Leçons générales

- **Un repli placé trop tôt répond à la place de celui qui savait**, et masque un branchement oublié. Il se reconnaît à ce que **deux causes opposées y produisent la même valeur** (détecteur absent = image vide ; bornes oubliées = table relative ; cible de test = échec). Devant deux vues de la même donnée, vérifier qu'elles passent par le même objet.
- **Une duplication reste invisible tant que les deux copies coïncident** ; c'est son premier écart qui se signale, souvent en production. Un jeu d'entrées dupliqué a le même défaut que le code qu'il surveille.
- **Une garde ne protège que ce qu'on lui a donné** : une recherche qui ne voit qu'une forme d'appel, un contrôle qui ne couvre que certains modules, un `grep -v` par numéro de ligne (il a masqué les deux appels orphelins qui empêchaient l'application de démarrer) — préférer un filtre par contenu, ou lire la sortie entière.
- **En JavaScript, un argument surnuméraire est muet** : une signature de raccourci est un site d'appel comme un autre (`coach_sequence` perdait sa clé de délai). Un renommage se vérifie aux **sites d'appel**, pas en appelant soi-même la fonction.
- **Un défaut en masque un autre** : après un correctif, rejouer le parcours entier, pas seulement l'étape visée.
- **Une consigne qui se déclenche à tort est pire qu'absente** : elle apprend à ne plus être lue. N'ajouter un critère de contrôle qu'après avoir nommé ce qu'il empêche.
- **Une correction en amont réveille les filtres en aval** (`completee` devenu honnête a faussé un graphe qui filtrait dessus).
- **Devant un diff massif et inattendu, se demander d'abord si les deux côtés lisent la même version des données.**

## Notes

- `docs/reglages.md` — le pourquoi de chaque réglage de `reglages.json`.
- `IDEES_DETECTION.md` — carnet d'idées d'amélioration de la détection (rien n'y est décidé ; certains chemins de fichiers cités datent de la version Python).
- `audio/A_ENREGISTRER.md` — généré par `lister_annonces.mjs`, ne pas éditer.
- `personaltrainer.db` (non versionné, ignoré) — archive de l'ancienne base SQLite. Ne jamais versionner une base : c'est un historique d'entraînement réel.
