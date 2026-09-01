# Personal Trainer

Coach de fitness en temps réel : la webcam détecte votre pose grâce à MediaPipe, l'application compte vos répétitions, vous guide à la voix (français), enregistre l'historique de vos séances et affiche tout ça sur une interface web locale.

## Fonctionnalités principales

- **Détection de pose en temps réel** via la webcam et MediaPipe (squelette dessiné à l'écran).
- **Comptage automatique des répétitions** et gestion des séries/circuits (chrono ou répétitions).
- **Coach vocal** : annonces pré-enregistrées en français (début/fin de série, temps de repos, changement d'exercice, encouragements, etc.).
- **Gestes de contrôle** sans clavier ni souris (ex. bras en X pour valider une série, deux bras levés pour réinitialiser) afin de piloter la séance depuis devant la caméra.
- **Historique des séances et records** stockés en base SQLite, avec suivi de la progression (meilleur volume, dernières performances).
- **Interface web locale** (Flask) pour démarrer/mettre en pause une séance, suivre l'état en direct via le flux caméra, consulter l'historique et les records.
- **Création de séances personnalisées** : composez vos propres circuits d'exercices depuis l'interface web.

## Architecture / organisation du code

- `vision/` — Détection de pose avec MediaPipe (`detector.py`), extraction des points clés du corps (`body.py`, `landmarks.py`) et dessin du squelette sur l'image (`dessin.py`).
- `mouvements/` — Règles métier des exercices : comptage des répétitions (`compteur.py`), définitions des exercices (`exercices.py`), positions de contrôle comme le bras en X ou les bras levés (`positions.py`), utilitaires de maintien de position (`outils.py`).
- `session/` — Machine à états de la séance : le circuit d'exercices (`circuit.py`), le moteur qui fait avancer une répétition/série/exercice (`moteur.py`), le `SessionManager` qui coordonne les commandes web et la séance en cours (`controleur.py`), et le catalogue des séances prédéfinies/personnalisées (`seances.py`, `seances_personnalisees.json`).
- `audio/` — Coach vocal : sélection et déclenchement des annonces (`coach.py`), lecture des fichiers son (`lecteur.py`), banque de fichiers audio (`Fichiers/`) et outils de génération/nettoyage des sons (`nettoyer_sons.py`, `generer_annonces_manquantes.py`).
- `historique/` — Persistance SQLite des séances, statistiques et records (`database.py`, base `personaltrainer.db`).
- `web/` — Serveur Flask (`app.py`) exposant l'API et les pages (démarrage/pause de séance, historique, records, création/édition de séances) et les templates HTML associés (`templates/`).
- `références/` — Scripts de prototypage (détection simple, compteur de curls, etc.) conservés à titre de référence mais **non branchés** sur l'application principale.

Le point d'entrée de l'application est `main.py`, qui orchestre la boucle caméra, la machine à séances, le coach vocal et le serveur web. L'état partagé entre la boucle caméra et le site web transite par `state.py`.

## Prérequis

- Python 3.11
- Une webcam
- Les dépendances Python du projet (MediaPipe, OpenCV, Flask, pygame, pydub, numpy, notamment) — voir `requirements.txt` (un travail est en cours pour figer la liste précise des dépendances dans ce fichier).

## Installation & lancement

```bash
python main.py
```

Au lancement, l'application initialise la base de données d'historique, ouvre la caméra, démarre le serveur Flask en arrière-plan et ouvre automatiquement le navigateur sur `http://127.0.0.1:5000`. C'est depuis cette interface web que l'on choisit et pilote la séance ; le coach vocal et le comptage de répétitions se déclenchent en fonction des mouvements détectés devant la caméra.

## Tests

Les tests sont des fichiers `test_*.py` à la racine du dépôt, écrits avec `unittest` (voir par exemple `test_circuit.py`, `test_compteur.py`, `test_controleur.py`, `test_historique.py`). Ils peuvent être exécutés avec `pytest` :

```bash
pytest
```

(`test_db.py` et `test_position.py` sont plutôt des scripts d'exploration manuelle — le premier affiche l'historique en base, le second ouvre la caméra pour tester interactivement la détection de pose — et non des suites `unittest` à proprement parler.)

## Notes

- Il n'y a actuellement aucune intégration continue (CI) configurée sur ce dépôt.
- Le dossier `références/` contient du code de prototypage (détection de pose simplifiée, compteur d'exercice isolé, etc.) qui n'est pas utilisé par l'application et sert uniquement de matériel de référence pour le développement.
