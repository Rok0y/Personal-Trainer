# Personal Trainer

Coach de fitness en temps réel : la webcam détecte votre pose grâce à MediaPipe, l'application compte vos répétitions, vous guide à la voix (français), enregistre l'historique de vos séances et affiche tout ça sur une interface web locale.

## Fonctionnalités principales

- **Prise en main guidée pour un nouveau profil** : à sa création, un profil est
  accueilli par un parcours qui présente, un par un, les exercices de la séance
  qu'il a choisie. Pour chacun : une fiche qui explique comment s'installer et
  comment exécuter le mouvement, puis un petit test devant la caméra — une seule
  série, autant de répétitions que possible. L'application en déduit le point de
  départ, l'affiche en clair (« 3x12 à 4 kg ») et laisse le corriger d'un cran
  vers le haut ou vers le bas avant de le valider. Rien à réussir : chaque
  exercice peut être passé, et le parcours reprend là où il s'est arrêté si on
  quitte en cours de route.
- **Fiches d'exercice** : chaque mouvement explique comment se placer (cadrage
  caméra compris), comment l'exécuter et ce qu'il faut éviter. Consultables à
  tout moment depuis l'onglet **Exercices**, et rappelées pendant la séance.
- **Variantes assistées** : pompes inclinées, pompes et gainage sur les genoux,
  squat sur chaise. Ce sont des exercices à part entière — ils ont leur barème,
  leurs records et leur progression — et le test de calibration y renvoie quand
  le mouvement complet est encore hors de portée. Les premiers paliers des
  mouvements au poids du corps sont par ailleurs délibérément bas, pour que
  quelqu'un qui débute ait toujours un objectif à sa mesure.
- **Messages écrits pendant la séance** : en plus des corrections de forme, une
  bande d'aide indique quoi faire — sortir du champ de la caméra le signale
  désormais explicitement au lieu de figer l'écran en silence — et les consignes
  du mouvement en cours restent affichées sur le côté. Ces messages sont
  identifiés par une clé, de la même façon que les annonces vocales, en vue de
  les faire dire par le coach.
- **Détection de pose en temps réel** via la webcam et MediaPipe (squelette dessiné à l'écran).
- **Comptage automatique des répétitions** et gestion des séries/circuits (répétitions, maintien, chrono, AMRAP).
- **Échauffement guidé** : une séance peut commencer par des mouvements d'échauffement minutés (rotations articulaires, jumping jacks, pompes lentes...), annoncés à la voix et décomptés à l'écran. Le chrono se met en pause si vous sortez du champ de la caméra, et l'échauffement n'est comptabilisé ni dans les records ni dans l'historique.
- **Coach vocal** : annonces pré-enregistrées en français (début/fin de série, temps de repos, changement d'exercice, encouragements, etc.).
- **Gestes de contrôle** sans clavier ni souris (ex. bras en X pour valider une série, deux bras levés pour réinitialiser) afin de piloter la séance depuis devant la caméra.
- **Historique des séances et records** stockés en base SQLite, avec suivi de la progression (meilleur volume, dernières performances).
- **Niveaux par exercice** : chaque exercice possède un barème de paliers (poids, séries, répétitions) dont le volume ne redescend jamais, et votre niveau est déduit de votre historique — le plus haut palier jamais validé. La progression monte d'abord les répétitions, puis la charge, puis le nombre de séries (jusqu'à six) ; au-delà, ce sont les répétitions qui montent sans limite, si bien qu'aucun objectif n'est jamais inaccessible faute de matériel. La page Records affiche le niveau atteint, le palier correspondant et le palier suivant.
- **Progression automatique des séances** : chaque séance repart de l'objectif de la précédente. Réussi, il monte d'un palier ; manqué, il revient à l'identique. Vous pouvez toujours saisir une cible à la main : elle est alors figée (badge « cible manuelle » sur l'accueil) jusqu'à ce que vous la remettiez sur la valeur proposée.
- **Ressenti en fin de séance** : chaque exercice vous demande comment c'était, et l'objectif suivant s'ajuste en conséquence. Réussi, « c'était facile » fait sauter deux paliers au lieu d'un et « c'était trop facile » en fait sauter trois ; manqué, « c'était trop dur » redescend d'un palier. Ne rien répondre garde la progression d'un palier par séance réussie. Les réponses proposées dépendent de ce qui s'est passé, et peuvent être saisies ou corrigées plus tard depuis la page Historique.
  Votre **niveau ne recule jamais** pour autant : il reste le plus haut palier que vous ayez validé. Seul l'objectif descend, le temps de repasser la marche.
- **Programmes sportifs** : un programme (« Road to TKT ») liste une performance à atteindre par exercice, et la page Programmes montre où vous en êtes sur chacune. Les prescriptions sont traduites **par le volume** — une répétition à 20 kg en vaut deux à 10 kg — pour rester réalisables avec le matériel dont vous disposez. Un programme ne stocke aucune progression : tout est recalculé depuis votre historique. Les programmes se créent et se modifient depuis l'interface (bouton « Modifier » sur la page Programmes), y compris ceux livrés avec l'application. Les charges s'y saisissent **telles qu'elles sont écrites dans le programme d'origine**, c'est-à-dire les deux haltères réunis ; l'équivalent par haltère s'affiche sous le champ.
- **Recalage du niveau** : si votre historique ne reflète pas votre niveau réel (séance faite sans l'application, reprise après une interruption, premier usage), la page Records permet de le recaler. Vous n'entrez pas un numéro de niveau mais une performance que vous savez tenir — séries, répétitions ou secondes, charge — et le barème en déduit le niveau. L'historique antérieur cesse alors de compter pour cet exercice, ce qui permet aussi bien de monter que de descendre.
- **Interface web locale** (Flask) pour démarrer/mettre en pause une séance, suivre l'état en direct via le flux caméra, consulter l'historique, les records et les programmes — accessibles par des onglets en haut de chaque page.
- **Résumé de programme sur l'accueil** : avancement global — la moyenne de votre progression sur chaque exigence, pas seulement celles déjà bouclées — et, surtout, la prochaine séance à enchaîner, sélectionnable d'un clic. Les trois séances d'un programme se suivent en boucle ; une séance abandonnée est reproposée.
- **Profils** : l'application demande à chaque lancement qui s'entraîne. Chaque profil garde son propre historique, ses records, ses niveaux et ses recalages ; les séances et les programmes, eux, sont communs à tout le monde. Un nouveau profil commence par la prise en main décrite plus haut, qui pose ses niveaux de départ ; ils évoluent ensuite au fil de ses séances, et restent recalables à tout moment depuis la page Records. Le profil connecté s'affiche à droite des onglets, et ce bouton ramène à l'écran de sélection. On ne change pas de profil pendant une séance en cours.
- **Création de séances personnalisées** : composez vos propres circuits d'exercices depuis l'interface web, avec réorganisation des exercices par glisser-déposer.

## Architecture / organisation du code

- `vision/` — Détection de pose avec MediaPipe (`detector.py`), extraction des points clés du corps (`body.py`, `landmarks.py`) et dessin du squelette sur l'image (`dessin.py`).
- `mouvements/` — Règles métier des exercices : comptage des répétitions (`compteur.py`), définitions des exercices (`exercices.py`), mouvements d'échauffement (`echauffements.py`), positions de contrôle comme le bras en X ou les bras levés (`positions.py`), utilitaires de maintien de position (`outils.py`).
- `session/` — Machine à états de la séance : le circuit d'exercices (`circuit.py`), le moteur qui fait avancer une répétition/série/exercice (`moteur.py`), le `SessionManager` qui coordonne les commandes web et la séance en cours (`controleur.py`), et le catalogue des séances prédéfinies/personnalisées (`seances.py`, `seances_personnalisees.json`).
- `audio/` — Coach vocal : sélection et déclenchement des annonces (`coach.py`), lecture des fichiers son (`lecteur.py`), banque de fichiers audio (`Fichiers/`) et outils de génération/nettoyage des sons (`nettoyer_sons.py`, `generer_annonces_manquantes.py`).
- `historique/` — Persistance SQLite des séances, statistiques et records (`database.py`, base `personaltrainer.db`).
- `web/` — Serveur Flask (`app.py`) exposant l'API et les pages (démarrage/pause de séance, historique, records, création/édition de séances) et les templates HTML associés (`templates/`).
- `progression/` — Moteur de progression : le barème de paliers de chaque exercice (`paliers.py`), la déduction du niveau atteint à partir de l'historique (`niveaux.py`), l'application des objectifs aux séances (`objectifs.py`), l'ajustement par le ressenti déclaré en fin de séance (`ressenti.py`), les programmes sportifs (`programmes.py`) et le test de niveau d'un nouveau profil (`calibration.py`).
- `core/` — État partagé entre la boucle caméra et le site web (`state.py`), identité du profil connecté (`utilisateur.py`) et catalogue des messages affichés à l'utilisateur (`messages.py`).
- `scripts/` — Outils de développement manuels, hors du chemin critique de l'application (`script_verification_positions.py`, `script_niveaux.py`).

Le point d'entrée de l'application est `main.py`, qui orchestre la boucle caméra, la machine à séances, le coach vocal et le serveur web. L'état partagé entre la boucle caméra et le site web transite par `core/state.py`.

`audio/generer_annonces_manquantes.py`, `scripts/script_verification_positions.py` et `scripts/script_niveaux.py` important des modules du projet par chemin absolu (`audio.coach`, `session.seances`, `mouvements.positions`...), il faut les lancer avec `python -m`, depuis la racine du dépôt, pour que ces imports se résolvent correctement — par exemple `python -m scripts.script_verification_positions` (un simple `python scripts/script_verification_positions.py` échouerait, Python n'ajoutant que le dossier du script à son chemin d'import).

## Prérequis

- Python 3.11
- Une webcam
- Les dépendances Python du projet (MediaPipe, OpenCV, Flask, pygame, pydub, numpy, notamment) — voir `requirements.txt` (un travail est en cours pour figer la liste précise des dépendances dans ce fichier).

## Installation & lancement

```bash
python main.py
```

Au lancement, l'application initialise la base de données d'historique, ouvre la caméra, démarre le serveur Flask en arrière-plan et ouvre automatiquement le navigateur sur `http://127.0.0.1:5000`. La première page est l'**écran de sélection de profil** : rien ne s'affiche ni ne s'enregistre tant qu'un profil n'est pas choisi. Une base d'avant les profils est reprise telle quelle dans un profil nommé « Moi », renommable depuis cet écran. Un profil créé pour la première fois est dirigé vers la prise en main : l'application reste sur ce parcours tant qu'il n'est pas terminé. C'est ensuite depuis cette interface web que l'on choisit et pilote la séance ; le coach vocal et le comptage de répétitions se déclenchent en fonction des mouvements détectés devant la caméra.

## Tests

Il n'y a pas de suite de tests automatisée dans ce dépôt. `scripts/script_verification_positions.py` est un outil d'exploration manuelle qui ouvre la caméra pour tester interactivement la détection de pose et les gestes de contrôle. `scripts/script_niveaux.py` confronte le barème à l'historique réel ; comme il n'y a pas d'écran de connexion en ligne de commande, il prend le profil en argument (`python -m scripts.script_niveaux Sophie`) et retombe sinon sur le premier.

## Notes

- Il n'y a actuellement aucune intégration continue (CI) configurée sur ce dépôt.
