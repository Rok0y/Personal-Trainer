# Personal Trainer

Coach de fitness en temps réel : la webcam détecte votre pose grâce à MediaPipe, l'application compte vos répétitions, vous guide à la voix (français), enregistre l'historique de vos séances et affiche tout ça sur une interface web locale.

## Fonctionnalités principales

- **Prise en main d'un nouveau profil** : une seule question à sa création — son
  **matériel**. Quels haltères il possède (aucun, un, une paire, poids par
  poids) et quels accessoires. Le matériel appartient au profil : il fixe
  l'échelle de charge de ses barèmes et dit quels exercices lui sont
  accessibles. Modifiable à tout moment depuis la page *Mon matériel*.
- **Calibration en séance, pas en tunnel** : il n'y a pas d'examen d'entrée. On
  lance une séance normale, et le premier exercice sur lequel l'application ne
  sait rien devient une **série unique au maximum** à charge moyenne (« fais
  autant de répétitions propres que tu peux, puis croise les bras »). Le niveau
  de départ s'en déduit sur-le-champ, et la séance suivante propose un vrai
  objectif. Rien n'est à reprendre si on s'arrête en cours de route : un
  exercice est calibré dès qu'il a été testé une fois.
- **Fiches d'exercice** : chaque mouvement explique comment se placer (cadrage
  caméra compris), comment l'exécuter et ce qu'il faut éviter. Consultables à
  tout moment depuis l'onglet **Exercices**, et rappelées pendant la séance.
- **Variantes assistées** : pompes inclinées, pompes et gainage sur les genoux,
  squat sur chaise. Ce sont des exercices à part entière — ils ont leur barème,
  leurs records et leur progression — et servent de repli quand le mouvement
  complet est encore hors de portée. Les premiers paliers des
  mouvements au poids du corps sont par ailleurs délibérément bas, pour que
  quelqu'un qui débute ait toujours un objectif à sa mesure.
- **Messages écrits pendant la séance** : en plus des corrections de forme, une
  bande d'aide indique quoi faire — sortir du champ de la caméra le signale
  désormais explicitement au lieu de figer l'écran en silence — et les consignes
  du mouvement en cours s'affichent à droite, au-dessus du compteur. Elles
  restent lisibles **pendant les temps de repos**, et entre deux exercices elles
  basculent sur le mouvement suivant, mise en place comprise : de quoi préparer
  le matériel et le cadrage caméra avant de reprendre. Ces messages sont
  identifiés par une clé, de la même façon que les annonces vocales, en vue de
  les faire dire par le coach.
- **Refaire une série ratée** : pendant un temps de repos, le bouton « Refaire
  cette série » relance celle qui vient de s'achever — y compris la dernière
  d'un exercice, où il revenait auparavant une série trop tôt — et sa
  performance précédente est écartée de l'historique.
- **Détection de pose en temps réel** via la webcam et MediaPipe (squelette dessiné à l'écran).
- **Comptage automatique des répétitions** et gestion des séries/circuits (répétitions, maintien, chrono, AMRAP).
- **Échauffement guidé** : une séance peut commencer par des mouvements d'échauffement minutés (rotations articulaires, jumping jacks, pompes lentes...), annoncés à la voix et décomptés à l'écran. Le chrono se met en pause si vous sortez du champ de la caméra, et l'échauffement n'est comptabilisé ni dans les records ni dans l'historique.
- **Coach vocal** : annonces pré-enregistrées en français (début/fin de série, temps de repos, changement d'exercice, encouragements, etc.).
- **Gestes de contrôle** sans clavier ni souris (ex. bras en X pour valider une série, deux bras levés pour réinitialiser) afin de piloter la séance depuis devant la caméra.
- **Historique des séances et records** stockés en base SQLite, avec suivi de la progression (meilleur volume, dernières performances). Sur la page Historique, un seul marqueur signale un progrès : la montée de niveau. Le badge de record qui la doublait a été retiré — il ne savait mesurer que les exercices avec charge, et restait donc muet sur les pompes, les gainages et les squats.
- **Niveaux par exercice** : chaque exercice possède un barème de paliers (poids, séries, répétitions) dont le volume ne redescend jamais, et votre niveau est déduit de votre historique — le plus haut palier jamais validé. La progression monte d'abord les répétitions, puis la charge, puis le nombre de séries (jusqu'à six) ; au-delà, ce sont les répétitions qui montent sans limite, si bien qu'aucun objectif n'est jamais inaccessible faute de matériel. La fiche de chaque exercice affiche le niveau atteint, le palier correspondant et le palier suivant, avec la courbe de progression — les records ont fusionné avec les fiches, il n'y a plus qu'un endroit où lire un mouvement.
- **Progression automatique des séances** : chaque séance repart de l'objectif de la précédente. Réussi, il monte d'un palier ; manqué, il revient à l'identique. Vous pouvez toujours saisir une cible à la main : elle est alors figée (badge « cible manuelle » sur l'accueil) jusqu'à ce que vous la remettiez sur la valeur proposée.
- **Ressenti en fin de séance** : chaque exercice vous demande comment c'était, et l'objectif suivant s'ajuste en conséquence. Réussi, « c'était facile » fait sauter deux paliers au lieu d'un et « c'était trop facile » en fait sauter trois ; manqué, « c'était trop dur » redescend d'un palier. Ne rien répondre garde la progression d'un palier par séance réussie. Les réponses proposées dépendent de ce qui s'est passé, et peuvent être saisies ou corrigées plus tard depuis la page Historique.
  Votre **niveau ne recule jamais** pour autant : il reste le plus haut palier que vous ayez validé. Seul l'objectif descend, le temps de repasser la marche.
- **Programmes sportifs** : un programme (« Road to TKT ») liste une performance à atteindre par exercice, et la page Programmes montre où vous en êtes sur chacune. Les prescriptions sont traduites **par le volume** — une répétition à 20 kg en vaut deux à 10 kg — pour rester réalisables avec le matériel dont vous disposez ; chaque ligne montre les deux, ce que le programme demande et l'équivalent sur votre barème (« 6x15 » peut s'y lire « 4x23 »). Un programme ne stocke aucune progression : tout est recalculé depuis votre historique. Les programmes se créent et se modifient depuis l'interface (bouton « Modifier » sur la page Programmes), y compris ceux livrés avec l'application. Chaque exigence est **calée sur un palier de votre barème** à l'enregistrement : une prescription qui n'y correspond pas (plus lourde que vos haltères, ou dans une forme que le barème ne propose pas) est remplacée par le premier palier de même volume. Les charges s'y saisissent **pour un seul haltère**, comme partout ailleurs dans l'application : un tableau qui annonce la charge totale des deux haltères se divise par deux avant d'être recopié. Enregistrer un programme **relie chacune de ses séances à une séance jouable** : si une séance existante correspond au libellé (même nom, ou majorité d'exercices en commun) elle est adoptée telle quelle — vos échauffements et vos repos sont conservés, rien n'est réécrit — et sinon elle est créée. Le lien est ensuite mémorisé dans le programme.
- **Recalage du niveau** : si votre historique ne reflète pas votre niveau réel (séance faite sans l'application, reprise après une interruption, premier usage), la fiche de l'exercice permet de le recaler. Vous n'entrez pas un numéro de niveau mais une performance que vous savez tenir — séries, répétitions ou secondes, charge — et le barème en déduit le niveau. L'historique antérieur cesse alors de compter pour cet exercice, ce qui permet aussi bien de monter que de descendre.
- **Barre de progression de l'échauffement** : pendant l'échauffement, la barre du bas suit les mouvements d'échauffement (en bleu) et non les exercices, qu'elle laisse place dès le premier exercice comptabilisé. Deux barres, jamais deux en même temps.
- **Interface web locale** (Flask) pour démarrer/mettre en pause une séance, suivre l'état en direct via le flux caméra, consulter l'historique, les programmes et les fiches d'exercice — accessibles par des onglets en haut de chaque page, avec le profil à droite. La page Profil regroupe vos informations, votre matériel et le changement de personne.
- **Résumé de programme sur l'accueil** : un seul programme y figure — celui que vous suivez en ce moment — avec son avancement global (la moyenne de votre progression sur chaque exigence, pas seulement celles déjà bouclées) et, surtout, la prochaine séance à enchaîner, sélectionnable d'un clic. Les séances d'un programme se suivent en boucle ; une séance abandonnée est reproposée. « Commencer plutôt par » accompagne la carte : elle démarre une autre séance du programme pour aujourd'hui, sans rien changer à la suite.
- **Un seul programme actif** : tant que vous n'en avez choisi aucun, la page Programmes les montre tous, repliés, et l'accueil vous invite à choisir plutôt que d'en proposer un à votre place. Dès qu'un programme est choisi, il est le seul affiché — un bouton « Changer de programme » rouvre la liste. Le choix se retient par profil.
- **Profils** : sur le poste fixe, l'application demande à chaque lancement qui s'entraîne ; la version navigateur rouvre sur le dernier profil utilisé et ne pose la question que si on la lui demande. Chaque profil garde son propre historique, ses records, ses niveaux et ses recalages ; les séances et les programmes, eux, sont communs à tout le monde. Un nouveau profil déclare son matériel, puis ses niveaux se posent au fil de ses séances par le test décrit plus haut ; ils restent recalables à tout moment depuis la fiche de l'exercice. Le profil connecté s'affiche à droite des onglets et mène à votre page de profil : informations personnelles (sexe, date de naissance, taille, poids du corps — aucune n'entre dans le calcul des objectifs), matériel, et changement de personne. On ne change pas de profil pendant une séance en cours.
- **Création de séances personnalisées** : composez vos propres circuits d'exercices depuis l'interface web, avec réorganisation des exercices par glisser-déposer. La version navigateur a son propre éditeur, plus simple, dont les modifications restent sur l'appareil — faute de serveur à qui les renvoyer.

## Deux applications, un seul comportement

L'application existe sous deux formes, et l'objectif est qu'elles soient
**indiscernables** : mêmes fonctions, même écran de séance, mêmes règles de
progression.

- La **version poste fixe** (`python main.py`) : caméra, coach vocal, serveur
  Flask local, historique en SQLite. C'est celle qui tourne depuis le début, et
  elle fait autorité en cas de désaccord.
- La **version navigateur** (`web/static/app/`), installable sur un iPad :
  tout y tourne **sur l'appareil**, y compris la détection de pose. L'image ne
  quitte jamais le téléphone ou la tablette, l'historique vit dans IndexedDB, et
  le site est purement statique — il n'y a aucun serveur à qui parler.

Cette seconde version n'est pas une démo réduite : elle joue une séance entière,
avec les mêmes gestes, la même voix, la même progression, les mêmes écrans
d'historique, de programmes et de fiches d'exercice. Trois
différences subsistent, toutes délibérées, et elles découlent toutes de
l'absence de serveur :

- une séance **modifiée dans l'application** est gardée sur l'appareil et masque
  la version déployée, qu'un badge signale ; le bouton « revenir à la version du
  fichier » la rend au dépôt ;
- les **programmes** s'y lisent mais ne s'y écrivent pas — ils s'éditent sur
  l'ordinateur ;
- le badge « cible manuelle » y est en lecture seule, pour la même raison.

`web/static/demo/` est un troisième livrable, plus petit : un banc d'essai d'un
exercice isolé, qui sert à faire tester la détection par quelqu'un d'autre et à
diagnostiquer un comptage qui ne démarre pas (`?banc=1`).

**Comment les deux restent alignées.** Le code qui *calcule* existe en double,
Python d'un côté et JavaScript de l'autre, et neuf harnais de comparaison
vérifient que les deux rendent exactement les mêmes réponses (voir *Tests*). Le
code qui *affiche* l'écran de séance, lui, n'existe qu'une fois : `hud.css` et
`hud.js` sont chargés par les deux pages, tout comme la palette, les feuilles
des programmes, des fiches d'exercice, du ressenti et du recalage de niveau.
Les données que le navigateur relit (catalogue, séances, sons, barèmes,
programmes) sont **dérivées du Python** par `python -m scripts.preparer_demo`,
jamais recopiées à la main.

**Faire passer son historique du poste fixe à l'application** :
`python -m scripts.exporter_profil <profil>` écrit une sauvegarde que l'écran
des séances relit (« Importer un fichier »). Le fichier contient un historique
réel : il est écrit hors du dépôt, et le script refuse d'écrire dedans.

## Architecture / organisation du code

- `vision/` — Détection de pose avec MediaPipe (`detector.py`), extraction des points clés du corps (`body.py`, `landmarks.py`) et dessin du squelette sur l'image (`dessin.py`).
- `mouvements/` — Règles métier des exercices : comptage des répétitions (`compteur.py`), définitions des exercices (`exercices.py`), mouvements d'échauffement (`echauffements.py`), positions de contrôle comme le bras en X ou les bras levés (`positions.py`), utilitaires de maintien de position (`outils.py`).
- `session/` — Machine à états de la séance : le circuit d'exercices (`circuit.py`), le moteur qui fait avancer une répétition/série/exercice (`moteur.py`), le `SessionManager` qui coordonne les commandes web et la séance en cours (`controleur.py`), et le catalogue des séances prédéfinies/personnalisées (`seances.py`, `seances_personnalisees.json`).
- `audio/` — Coach vocal : sélection et déclenchement des annonces (`coach.py`), lecture des fichiers son (`lecteur.py`), banque de fichiers audio (`Fichiers/`) et outils de génération/nettoyage des sons (`nettoyer_sons.py`, `generer_annonces_manquantes.py`).
- `historique/` — Persistance SQLite des séances, statistiques et records (`database.py`, base `personaltrainer.db`).
- `web/` — Deux choses distinctes. Le **serveur Flask** (`app.py`) exposant l'API et les pages (démarrage/pause de séance, historique, programmes, fiches d'exercice, profil, création/édition de séances), avec ses templates (`templates/`). Et le **portage navigateur** dans `static/` : `static/js/` porte les jumeaux JavaScript des modules de calcul plus le code d'affichage partagé avec les templates, `static/app/` l'application complète, `static/demo/` le banc d'essai, `static/donnees/` les fichiers dérivés du Python. Les feuilles de style de la racine (`palette.css`, `hud.css`, `programmes.css`, `exercices.css`, `ressentis.css`, `ancrages.css`) sont chargées par les deux applications : c'est ce qui les empêche de diverger à chaque correction.
- `progression/` — Moteur de progression : le barème de paliers de chaque exercice (`paliers.py`), la déduction du niveau atteint à partir de l'historique (`niveaux.py`), l'application des objectifs aux séances (`objectifs.py`), l'ajustement par le ressenti déclaré en fin de séance (`ressenti.py`), les programmes sportifs (`programmes.py`), la traduction d'un maximum en niveau de départ (`calibration.py`) et les ligues, divisions et XP qui rendent tout cela lisible (`ligues.py`).
- `core/` — État partagé entre la boucle caméra et le site web (`state.py`), identité du profil connecté (`utilisateur.py`), matériel déclaré par le profil (`materiel.py`) et catalogue des messages affichés à l'utilisateur (`messages.py`).
- `scripts/` — Trois genres d'outils, tous hors du chemin critique. Les **vérifications manuelles** (`script_verification_positions.py`, `script_niveaux.py`, `verifier_hud.py`), les **harnais de portage** par paires `generer_*.py` / `comparer_*.mjs`, et les **exports** : `preparer_demo.py` (tout ce que le navigateur relit) et `exporter_profil.py` (un historique SQLite vers l'application).

Le point d'entrée de l'application est `main.py`, qui orchestre la boucle caméra, la machine à séances, le coach vocal et le serveur web. L'état partagé entre la boucle caméra et le site web transite par `core/state.py`.

`audio/generer_annonces_manquantes.py`, `scripts/script_verification_positions.py` et `scripts/script_niveaux.py` important des modules du projet par chemin absolu (`audio.coach`, `session.seances`, `mouvements.positions`...), il faut les lancer avec `python -m`, depuis la racine du dépôt, pour que ces imports se résolvent correctement — par exemple `python -m scripts.script_verification_positions` (un simple `python scripts/script_verification_positions.py` échouerait, Python n'ajoutant que le dossier du script à son chemin d'import).

## Prérequis

- Python 3.11
- Une webcam
- **Node.js**, uniquement pour lancer les harnais de comparaison du portage
  (voir *Tests*). L'application elle-même n'en a pas besoin, ni dans sa version
  poste fixe ni dans sa version navigateur.
- Les dépendances Python du projet — `pip install -r requirements.txt`. Les versions y sont figées sur celles qui font réellement tourner l'application, et le fichier porte un avertissement à lire : `opencv-contrib-python` et `opencv-python` fournissent tous deux le module `cv2` et s'écrasent mutuellement, il ne faut donc en installer qu'un seul.

## Installation & lancement

```bash
python main.py
```

Au lancement, l'application initialise la base de données d'historique, ouvre la caméra, démarre le serveur Flask en arrière-plan et ouvre automatiquement le navigateur sur `http://127.0.0.1:5000`. La première page est l'**écran de sélection de profil** : rien ne s'affiche ni ne s'enregistre tant qu'un profil n'est pas choisi. Une base d'avant les profils est reprise telle quelle dans un profil nommé « Moi », renommable depuis cet écran. Un profil créé pour la première fois est dirigé vers la prise en main : l'application reste sur ce parcours tant qu'il n'est pas terminé. C'est ensuite depuis cette interface web que l'on choisit et pilote la séance ; le coach vocal et le comptage de répétitions se déclenchent en fonction des mouvements détectés devant la caméra.

## Tests

Il n'y a pas de suite de tests unitaires, mais **neuf harnais de comparaison**
qui répondent à la seule question qui compte pour le portage : les deux
implémentations rendent-elles la même réponse ? Chacun se joue en deux temps —
un script Python écrit l'oracle, un script Node le rejoue et diffe.

```bash
python -m scripts.generer_fixtures      # 5 000 poses au hasard
node scripts/comparer_detections.mjs

python -m scripts.generer_scenarios     # 6 228 pas de seance, images comprises
node scripts/comparer_seances.mjs
```

Les sept autres suivent la même forme : `historique`, `paliers`, `niveaux`,
`ressenti`, `objectifs`, `programmes`, `ligues`. Attention, deux noms ne coïncident pas —
`generer_fixtures` alimente `comparer_detections` et `generer_scenarios`
alimente `comparer_seances` — et les fixtures **ne sont pas versionnées** : un
comparateur lancé sans son générateur compare de vieilles réponses.
`python -m scripts.verifier_hud` vérifie en plus que les deux montages de
l'écran de séance portent les mêmes points d'accroche.
`node scripts/verifier_methodes.mjs` signale les `this.methode()` appelées
mais inexistantes — une erreur que la syntaxe ne révèle pas et qui n'apparaît
qu'à l'exécution, donc souvent en séance.

Ces harnais prouvent que deux codes s'accordent, **pas qu'ils ont raison** : un
défaut présent des deux côtés y passe inaperçu, et c'est arrivé. C'est pourquoi
en saboter délibérément un morceau, pour vérifier qu'il crie, fait partie du
travail et non du zèle.

Les deux outils manuels restent utiles.
`scripts/script_verification_positions.py` ouvre la caméra pour tester
interactivement la détection de pose et les gestes de contrôle.
`scripts/script_niveaux.py` confronte le barème à l'historique réel ; comme il
n'y a pas d'écran de connexion en ligne de commande, il prend le profil en
argument (`python -m scripts.script_niveaux Sophie`) et retombe sinon sur le
premier.

## Notes

- **Déploiement automatique** : `.github/workflows/demo.yml` régénère les
  données dérivées puis publie `web/static` sur GitHub Pages à chaque push sur
  `main` ou `feat/portage-web`. Le site ne peut donc pas être en retard sur le
  code, et rien de dérivé n'a besoin d'être versionné. Le workflow **n'installe
  que numpy**, parce que l'export ne touche qu'au catalogue : si l'arbre
  d'imports s'alourdit un jour, l'étape doit échouer bruyamment plutôt que
  d'être blindée à l'avance.
- **Chaque déploiement marque ses ressources** de l'empreinte du commit
  (`camera.js?v=<sha>`). Un navigateur ne peut donc pas combiner un document
  neuf avec un module gardé en cache — ce qui fait échouer l'application sur
  une fonction disparue, en accusant un code déjà corrigé.
- Cette CI **ne lance aucun harnais de comparaison** : ils restent à lancer à la
  main avant de pousser.
- **La base de données n'est pas versionnée** et ne doit pas le redevenir : un
  clone démarre sans base, elle se crée au premier lancement. Elle l'a été
  longtemps, ce qui publiait un historique d'entraînement réel dans un dépôt
  public.
