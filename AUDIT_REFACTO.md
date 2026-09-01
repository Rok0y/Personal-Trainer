# Audit du code — Personal-Trainer

Audit en lecture seule, réalisé le 2026-09-01. Aucun fichier de code n'a été modifié.

## Résumé exécutif

Le dossier `références/` (curl_counter.py, fonctions.py, simple_detection.py) est du code mort confirmé, supprimable sans risque. `audio/a_traiter/` est un dossier de staging légitime (source pour `audio/nettoyer_sons.py`), pas du code mort. La dette la plus significative est la duplication de logique dans `mouvements/exercices.py` (détections miroir gauche/droite, patterns copiés-collés avec un bug latent d'opérateur booléen) et l'absence totale de gestion d'erreurs SQL dans `historique/database.py`. Les tests couvrent correctement `session/circuit.py` et `historique/database.py` pour les cas de base, mais laissent `mouvements/exercices.py` (661 lignes) sans aucune couverture automatisée, et `test_db.py`/`test_position.py` ne sont pas de véritables tests automatisés.

## Code mort identifié

| Élément | Chemin | Confiance | Détail |
|---|---|---|---|
| Dossier prototypes obsolète | `références/curl_counter.py`, `références/fonctions.py`, `références/simple_detection.py` | **Haute** | Grep confirmé : aucun import depuis l'app principale (main.py, session/, mouvements/, vision/, web/, audio/, historique/). Seul `curl_counter.py` importe `fonctions.py` en interne au dossier. Supprimable sans impact. |
| Guard d'import mort | `web/app.py` lignes 15-22 (`try/except ImportError` pour `supprimer_seance`, `supprimer_exercice_de_seance`) | **Haute** | Le commentaire dit que ces fonctions "doivent être ajoutées" à `historique/database.py` — elles existent déjà (lignes 440 et 466 de `historique/database.py`). Le garde défensif et son commentaire sont obsolètes ; le code fonctionne mais le bloc n'a plus lieu d'être. |
| `test_db.py` | racine, 6 lignes | **Haute** | Ce n'est pas un test : pas d'assertion, juste un script `print(recuperer_historique())`. Ne peut jamais échouer de façon significative. Candidat à suppression ou à transformation en vrai test. |
| `test_position.py` | racine, 107 lignes | **Moyenne** | Script interactif OpenCV (boucle caméra + touches clavier), pas un test `unittest`/`pytest` automatisable en CI. Utile comme outil de debug manuel mais mal nommé (`test_*.py` suggère une suite automatique). |
| `audio/a_traiter/` (~76 fichiers .wav) | `audio/a_traiter/` | **Confiance faible sur "à nettoyer"** | Ce n'est PAS du code mort : c'est la source consommée par `audio/nettoyer_sons.py` (ligne 6 : `SOURCE = "audio/a_traiter"`) qui nettoie le silence et exporte vers `audio/fichiers`. À vérifier avec l'utilisateur : si tous les fichiers ont déjà été traités, le dossier peut être vidé/archivé, mais rien dans le code ne l'indique. |

## Refactos proposées (par priorité)

### Priorité 1 — Quick wins, faible risque
1. **Supprimer `références/`** (3 fichiers). Justification : code mort confirmé par grep, aucune dépendance. Risque : nul.
2. **Nettoyer le guard `try/except ImportError` dans `web/app.py:15-22`** et importer directement `supprimer_seance`/`supprimer_exercice_de_seance` depuis `historique/database.py`, en supprimant aussi les branches `if supprimer_seance is None: return 501` (lignes 401-405, 415-419) devenues mortes.
3. **Remplacer ou supprimer `test_db.py`** : soit en faire un vrai test avec assertions, soit le retirer de la racine (il n'apporte aucune valeur de non-régression actuellement).
4. **Renommer `test_position.py`** en `script_verification_positions.py` ou équivalent, pour ne pas le confondre avec la suite de tests automatisée (aucun changement de logique, juste éviter le préfixe `test_` trompeur).

### Priorité 2 — Refacto plus lourde, à discuter avant de toucher
1. **Dédupliquer les fonctions `*_detection` de `mouvements/exercices.py`** (661 lignes). Plusieurs détections (pompe, développé couché, extension triceps, développé épaule ; rowing gauche/droite lignes ~484-564 ; gainage latérale gauche/droite lignes ~425-478) répètent le même squelette (calcul d'angle + comparaison de seuils), y compris un bug hérité par copier-coller : des conditions du type `if angle_coude_droit and angle_coude_gauche < 100` où l'opérateur `<` ne s'applique qu'à la variable de droite (ex. lignes ~118, ~149, ~179, ~209) — `angle_coude_droit` n'est testé que comme booléen (toujours vrai si non nul), donc le seuil du côté droit n'est probablement jamais réellement vérifié. **À valider en priorité avant tout refactoring** : ce n'est pas qu'une question de style, c'est un bug fonctionnel potentiel sur la détection bilatérale des mouvements.
2. **Factoriser le cycle de vie des séries entre `session/moteur.py` et `session/circuit.py`** : les 4 fonctions `gerer_mode_*` de `moteur.py` (lignes ~108-120, ~169-184, ~201-217, ~274-287) répètent le même bloc (enregistrer résultat, terminer série, mettre à jour prochain exercice, reset des champs temporels), et gèrent en partie les mêmes attributs dynamiques (`dernier_maintien`, `debut_chrono`, `debut_amrap`, etc. via `hasattr`/`del`) que `circuit.py._reinitialiser_etat_serie` (lignes ~297-313). Deux endroits différents gèrent le même cycle de vie d'état — risque de désynchronisation future.
3. **Ajouter une gestion d'erreurs autour des accès SQL dans `historique/database.py`** (489 lignes, aucun try/except dans tout le fichier). Les opérations `enregistrer_seance`, `supprimer_seance`, `supprimer_exercice_de_seance`, `renommer_seance` ouvrent une connexion et font commit/close sans protection : une erreur SQLite (verrou, disque plein) provoque une fuite de connexion (le `conn.close()` n'est jamais atteint) et remonte une exception non gérée jusqu'aux routes Flask (`/historique`, `/records`, `/historique/<id>` dans `web/app.py` n'ont pas de try/except autour de `recuperer_historique()`).
4. **Étendre la couverture de tests** : `mouvements/exercices.py` (661 lignes, module de production le plus volumineux) n'a aucun test automatisé ; `test_circuit.py` ne couvre pas l'entrelacement (`paires_entrelacees`, `passer_exercice_suivant`) ; `test_controleur.py` ne teste que 2 scénarios sur `SessionManager` (191 lignes) et laisse `abandonner`, `terminer_serie`, `passer_pause` et les gardes `RuntimeError` sans couverture.

## Risques / à valider avant de toucher

- **Bug potentiel dans `mouvements/exercices.py`** (opérateur `<` mal parenthésé sur les conditions bilatérales) : à confirmer par un test manuel/caméra avant correction, car cela peut changer le comportement observé par l'utilisateur en séance (une correction peut rendre la détection plus stricte que ce à quoi l'utilisateur est habitué).
- **`audio/a_traiter/`** : ne pas supprimer sans confirmation — impossible de savoir depuis le code seul si le traitement a déjà été fait pour tous les fichiers présents.
- **Couplage `state.py`** : le module est un état global mutable partagé entre `main.py`, `web/app.py` et passé en paramètre à `session/moteur.py`. Ce n'est pas franchement dangereux aujourd'hui (accès simples, pas de multi-threading concurrent visible sur les mêmes champs), mais toute évolution vers plus de concurrence (plusieurs sessions, tests parallèles) nécessiterait de revoir ce pattern — à surveiller, pas urgent.
- **Suppression du guard `ImportError` dans `web/app.py`** : vérifier qu'aucun environnement de déploiement ne tourne encore avec une version antérieure de `historique/database.py` sans ces fonctions avant de retirer le filet de sécurité.
