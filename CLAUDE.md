# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Coach de fitness temps réel : la webcam détecte la pose (MediaPipe), l'app compte les répétitions, guide l'utilisateur à la voix (annonces françaises pré-enregistrées), enregistre l'historique des séances en SQLite, et expose une interface web locale (Flask) pour piloter la séance et consulter l'historique/records. Aucun clavier/souris n'est nécessaire pendant la séance : des gestes (bras en X, bras levés) pilotent la validation/reset des séries.

## Commands

```bash
python main.py          # lance l'app : caméra + serveur Flask (arrière-plan) + navigateur auto sur http://127.0.0.1:5000
```

Pas de suite de tests automatisée, pas de linter/formatter configuré, pas de CI. `scripts/script_verification_positions.py` est un outil manuel qui ouvre la caméra pour vérifier interactivement la détection de pose/gestes.

`scripts/script_verification_positions.py` et `audio/generer_annonces_manquantes.py` importent des modules du projet par chemin absolu (`mouvements.positions`, `session.seances`, ...) : lance-les avec `python -m` depuis la racine (ex. `python -m scripts.script_verification_positions`), pas en exécutant directement le fichier, sinon ces imports échouent.

## Architecture

Le point d'entrée est `main.py` : il possède la boucle caméra principale (une itération = une frame). Cette boucle orchestre à chaque frame, dans cet ordre : détection de pose → détection des gestes de contrôle (bras en X / bras levés) → avancement de la machine à états de la séance (`seance.update()`) → déclenchement du coach vocal sur changement de phase → exécution du mode d'exercice courant (`executer_mode`) → dessin du squelette → encodage JPEG de la frame pour le flux web.

L'état partagé entre la boucle caméra (thread principal) et le serveur Flask (thread daemon) transite par le module `core/state.py` — un simple espace de noms de variables globales mutables (pas de classe, pas de verrou), lu par `web/app.py` sur la route `/etat` (pollée par le front) et écrit par `main.py`/`session/moteur.py`. Le `SessionManager` (`session/controleur.py`), lui, protège son état interne par un `RLock` car il est appelé à la fois depuis la boucle caméra et depuis les requêtes HTTP.

Machine à états de séance (`session/`) :
- `circuit.py` — `Circuit` (une séance en cours) et `BlocExercice` (un exercice configuré : mode, séries, répétitions/durée, repos). Gère les phases (`preparation` → `exercice` → `recuperation_serie` → ... → `termine`/`abandonne`), la progression entre séries/exercices, et l'entrelacement de deux exercices (`entrelace_avec`, ex. superset gauche/droite) — logique la plus délicate du fichier (`_est_entrelace`, `terminer_serie`).
- `moteur.py` — `executer_mode` dispatche vers `gerer_mode_repetitions` / `gerer_mode_maintien` / `gerer_mode_chrono` / `gerer_mode_amrap` selon `bloc.mode`. Chacune calcule la progression de la série courante et, une fois la cible atteinte, appelle `_finaliser_serie` (termine la série + réinitialise les champs temporels du bloc via `Circuit.reinitialiser_etat_serie` — un seul endroit connaît la liste de ces attributs, à ne pas redupliquer si un mode est ajouté).
- `controleur.py` — `SessionManager` : façade thread-safe entre les commandes web (démarrer/pause/reprendre/naviguer entre séries/abandonner) et le `Circuit` actif.
- `seances.py` — catalogue des séances prédéfinies (code) + séances personnalisées (persistées dans `seances_personnalisees.json`), et construction d'un `Circuit` à partir d'une configuration de blocs.

Détection (`mouvements/`, `vision/`) :
- `vision/detector.py` télécharge au premier lancement le modèle MediaPipe (`pose_landmarker_lite.task`, absent du repo) et expose `PoseDetector.detect(frame)` → un `Body` (`vision/body.py`) qui regroupe les landmarks nommés (`vision/landmarks.py`).
- `mouvements/exercices.py` définit chaque `Exercice` par une fonction `*_detection(corps)` qui retourne une position (`"debut"`/`"fin"`/`"milieu"`/`"maintien"`/`"repos"`) à partir d'angles/distances calculés sur le `Body`. Ces fonctions bilatérales (ex. pompes, développé couché) doivent comparer *les deux* angles gauche/droite au seuil — un bug historique où seul un côté était vérifié (`angle_droit and angle_gauche < seuil`, l'opérateur `and` ne portant que sur l'un des deux) a été corrigé ; rester vigilant si on ajoute un exercice bilatéral sur ce modèle.
- `mouvements/compteur.py` (`CompteurMouvement`) transforme une séquence de positions détectées en comptage de répétitions (arme sur `"debut"`, valide sur `"fin"`). `mouvements/positions.py` définit les gestes de contrôle (bras en X, bras levés). `mouvements/outils.py` (`HoldPosition`) mesure un maintien de position dans le temps (utilisé pour la préparation avant série et pour valider un geste tenu 1.5-3s).

Coach vocal (`audio/`) : `coach.py` associe des clés d'événements (`"debut_serie"`, `"repos"`, `"compteur"`, etc.) à des fichiers `.wav` dans `Fichiers/`, choisis parfois aléatoirement ; `lecteur.py` les joue via `pygame`. `nettoyer_sons.py`/`generer_annonces_manquantes.py` sont des scripts d'outillage (nettoyage de silence, génération de sons manquants) opérant sur `a_traiter/` → `Fichiers/`, pas sur le chemin critique de l'app.

Persistance (`historique/database.py`) : SQLite (`personaltrainer.db`), aucune ORM. `enregistrer_seance` écrit une séance complète avec ses séries détaillées ; `recuperer_historique`/`statistiques_exercices`/`derniere_performance` recalculent volumes/records/PB à la lecture. Pas de gestion d'erreurs SQL (pas de try/except autour des connexions) — à garder en tête si on touche ce fichier.

Web (`web/app.py`) : serveur Flask exposant l'API JSON pilotant le `SessionManager` global (démarrage/pause/navigation de séance, CRUD des séances personnalisées, suppression dans l'historique) et les pages HTML (`templates/`) — accueil, création/édition de séance, historique, records, flux vidéo MJPEG (`/video`, lit `state.latest_frame`).

Outillage racine : `core/` ne contient que `state.py` (l'état partagé décrit plus haut) ; `scripts/` regroupe les outils de développement manuels hors chemin critique (`script_verification_positions.py`). `main.py` reste seul fichier `.py` à la racine du dépôt — c'est le point d'entrée, tout le reste vit dans un sous-module dédié.

## Notes

- `AUDIT_REFACTO.md` documente un audit du code mort et de la dette technique connue à date (dernière mise à jour : voir le fichier) — le consulter avant une refonte de `mouvements/exercices.py`, `session/moteur.py`/`circuit.py`, ou `historique/database.py`.
- La branche `references-archive` conserve un dossier `références/` de scripts de prototypage retiré de `main` (code mort, non branché sur l'application).
