---
name: ajouter-exercice
description: Protocole à deux pour ajouter un exercice ou un échauffement au catalogue de l'application (questionnaire, fiche de suivi dans docs/exercices/, détection et instrument, données, barème, tests, banc d'essai sur l'iPad, vidéo et voix, jusqu'à main). À utiliser dès que l'utilisateur veut ajouter un nouvel exercice, échauffement ou mouvement (« ajouter les talons-fesses »), reprendre un ajout en cours (« on continue l'exercice… »), ou transformer un échauffement en exercice compté.
---

# Ajouter un exercice

Un ajout s'étale sur plusieurs soirées : tournage, prise de son, essais sur l'iPad. Ce protocole
dit **qui fait quoi** et **dans quel ordre**, et garde l'avancement dans une fiche de suivi
versionnée. CLAUDE.md reste la référence des règles ; ce protocole ne fait que les ordonner.

## Les rôles

- **Claude** écrit tout le code et toutes les données : détection, instrument, entrées JSON,
  premier jet de la fiche, barème. Aucun `TODO(human)`, aucune portion déléguée.
- **L'utilisateur** répond au questionnaire, relit la fiche dans `dev/fiches.html`, fait les
  essais sur l'iPad (banc d'essai, puis séance) et colle les résumés, tourne la vidéo,
  enregistre la voix. Il donne aussi le feu vert avant **chaque** poussée.
- Le placement dans les séances **ne fait pas partie de l'ajout** : l'exercice entre au
  catalogue, et l'utilisateur le place lui-même avec les créateurs de séances de l'application.
  On ne touche à `seances.json` ni à `programmes.json`.
- Les **fautes de forme** non plus : un exercice entre en comptant juste. Ses fautes passeront
  plus tard par la commande de `dev/fiches.html`.

## 0. Reprendre ou commencer

1. Partir de `travail` : dans un worktree, `git fetch origin` puis se mettre sur
   `origin/travail` (avance rapide si la branche n'a rien à elle).
2. Regarder dans `docs/exercices/`. Si une fiche de suivi existe pour cet exercice, la lire,
   **dire en deux lignes où on en est**, puis reprendre à la première case non cochée.
   Sinon, passer au questionnaire.

## 1. Le questionnaire

On le pose avec `AskUserQuestion`, par lots de quatre au plus, en proposant chaque fois une
recommandation tirée du code. Avant de le poser, regarder les mouvements voisins dans
`mouvements.json` et `fiches.json`. Les réponses vont dans la fiche de suivi, avec leur pourquoi
quand il n'est pas évident.

| # | Question | Ce qu'elle décide |
|---|---|---|
| 1 | **Nature** : échauffement sans détection, échauffement détecté (pour l'affichage seulement), exercice compté (répétitions ou AMRAP), maintien (secondes) | Le parcours (A ou B), `est_echauffement`, l'unité du barème |
| 2 | **Nom**, et s'il existera un jour **une autre forme** (comptée à côté d'un échauffement, chargée à côté d'une forme à vide) | Le nom est une **clé définitive** (séances perso, historique, `.wav`, `.mp4`). S'il y aura deux formes, décider tout de suite laquelle prend le nom simple. Vérifier qu'aucun mouvement ne porte déjà ce nom et que la longueur ne dépasse pas `longueur_maximale_nom` (`sons.json`) |
| 3 | **Exécution**, décrite librement par l'utilisateur | La fiche, la détection, l'exercice voisin qui pourrait être compté à sa place |
| 4 | **Côté** : bilatéral, alterné, unilatéral | Un mouvement unilatéral en fait **deux** (droite, gauche), reliés par `autre_cote` et filmés une seule fois (`--miroir`) |
| 5 | **Matériel** : rien, un haltère, deux haltères | `materiel` (`baremes.json` : `halteres` et `brut`). Un tirage exige un haltère |
| 6 | **Orientation** : `face`, `profil`, `profil_camera_gauche`, `profil_camera_droite`, `allonge_camera_de_cote`, ou `null` | Ce que le coach **prononce**. Pour un exercice compté, elle se choisit avec la détection (une flexion du genou ou de la hanche ne se lit que de profil). `null` veut dire « rien de sûr à dire », jamais « face » par défaut |
| 7 | **Muscles et chaîne** : Claude propose, l'utilisateur valide | `categories` (`categories.json`). Un muscle nouveau s'ajoute à la table, avec sa partie |
| 8 | **Famille** : est-ce la variante plus facile ou plus dure d'un mouvement existant ? | `variante_facile` / `variante_difficile`, `variantes.retour` et `variantes.depart` (`reglages.json`) |
| 9 | Échauffement : **changements** (changer de sens, de jambe ou de bras à une fraction de la durée) | `changements` |
| 10 | Exercice compté : **position de départ**, ce qui rend le mouvement **difficile**, ce qui **ressemble** à une répétition sans en être une | `depart`, la condition de position et la condition d'effort de la détection, la liste des faux positifs à essayer au banc |

## 2. La fiche de suivi

Copier `modele_suivi.md` (dans ce dossier) vers `docs/exercices/<nom de fichier>.md`. Le nom de
fichier est celui que donne `fichier_video(nom)` sans `.mp4`, par exemple
`talons_fesses.md`. Ne garder que le parcours qui s'applique.

Le titre `# …` est le nom exact du mouvement, ou les deux noms d'un mouvement unilatéral
séparés par ` / ` (« Fente droite / Fente gauche ») : c'est par lui que `dev/suivi.html`
retrouve le mouvement au catalogue, sa vidéo et sa voix. `node scripts/suivi.mjs` (joué par
`tester.mjs`) refuse une fiche sans titre ou sans case.

On coche au fil de l'eau, et chaque commit porte la fiche à jour. L'utilisateur suit
l'avancement depuis l'iPad sur **`dev/suivi.html`** (dans le sommaire) : la page montre les
fiches de la dernière branche poussée, la prochaine case, et ce que le site contient déjà. Une
case cochée sans poussée n'y apparaît donc pas encore. Le journal du banc d'essai y
reçoit les résumés collés et les seuils changés : c'est ce qui permet de reprendre trois jours
plus tard. La fiche est **supprimée** dans le commit qui fusionne l'exercice dans `main`.

## 3. Parcours A — un échauffement

Une seule poussée.

1. **`mouvements.json`** : ajouter l'entrée à la suite des échauffements, avec tous les champs
   (le modèle ci-dessous). Un échauffement détecté réutilise une détection existante (`detection`,
   `analyse_la_pose: true`). Elle n'est jamais une condition d'avancement.
   ```json
   "Nom": {
    "nom": "Nom", "variante_facile": null, "variante_difficile": null,
    "orientation": null, "changements": [], "analyse_la_pose": false,
    "detection": null, "erreurs": [], "amplitude": null, "materiel": "",
    "est_echauffement": true,
    "categories": { "muscles": ["..."], "chaine": "cardio" }
   }
   ```
2. **`fiches.json`** : premier jet des cinq champs, dans le ton des fiches voisines (tutoiement,
   mots de tous les jours, phrases de dix-huit mots au plus). `mise_en_place` comprend le
   cadrage de la caméra, et `sensations` ce qu'on doit sentir et ce qui ne doit pas arriver.
3. **Relecture** : lancer `statique-dev` (`preview_start`) et ouvrir `dev/fiches.html`. Vérifier
   soi-même les avertissements, puis demander à l'utilisateur de relire la fiche. S'il la
   corrige dans la page, il colle le fichier rendu, et on le remplace.
4. **Tests** : `node scripts/tester.mjs` en entier. Puis `node scripts/lister_annonces.mjs`, qui
   ajoute le nom à `audio/A_ENREGISTRER.md` : ce fichier se commite avec.
5. **Poussée** : commiter, puis **demander** avant de pousser `travail`. Essai sur l'iPad :
   l'utilisateur crée une séance perso avec l'échauffement. Il vérifie l'annonce (silence tant
   que le `.wav` manque), la fiche à l'écran, la durée estimée et le passage à l'exercice
   suivant.
6. **Médias** (§ 5), puis **clôture** (§ 6).

## 4. Parcours B — un exercice compté

Deux poussées. Les tests exigent d'un exercice compté son barème, ses bornes de ligue, son
tempo et son matériel : la première poussée porte donc un **barème provisoire**, posé par
analogie, que la seconde règle pour de bon.

### Jalon 1 : il compte juste, au banc d'essai

1. **Concevoir la détection** avant de l'écrire, et la décrire dans la fiche de suivi : mesures,
   seuils, ce que valent `debut` et `fin`. Repasser les règles apprises de CLAUDE.md
   (*Détection*) :
   - lisible dans l'orientation choisie (un angle se lit en 2D) ;
   - rapportée au corps, jamais en fraction d'image ;
   - deux seuils, pour l'hystérésis ;
   - une condition de position commune à `debut` et `fin` ;
   - les deux côtés de face, le membre le mieux vu de profil ;
   - le bon côté vérifié pour un mouvement unilatéral ;
   - `debut` et `fin` désignent des **moments du comptage** (`fin` = fin de la phase
     concentrique) ;
   - `depart` déclaré si la mise en place passe par l'autre extrémité.

   Avant d'écrire une mesure, chercher si `detections.js` en a déjà une qui convient.
2. **`detections.js`** : la fonction `<nom>_detection(corps)`, ses seuils en constantes exportées
   avec un commentaire qui dit d'où vient chaque nombre, et son entrée dans `DETECTIONS`. Un
   helper que l'instrument relit s'exporte avec un alias `_`.
3. **`instruments.js`** : l'instrument (`ordre`, `defaut`, `mesures` et leurs zones). Les
   raisons de « ça ne compte pas » se prennent dans `RAISONS`. Une raison nouvelle est une
   prise de son nouvelle : il faut alors la brique dans `sons.json`, sous forme de constat au
   présent, qui ne s'accorde pas.
4. **Données** :
   - `mouvements.json` : `detection`, `analyse_la_pose: true`, `orientation`, `depart`,
     `autre_cote` (réciproque), `materiel`, `categories`, `erreurs: []`, `amplitude: null` ;
   - `baremes.json` : `materiel` (`halteres`, `brut`) ;
   - `reglages.json` : la spec, les dix-huit bornes et le `tempo`, pris sur l'exercice le plus
     proche **et marqués provisoires** dans la fiche de suivi ;
   - `fiches.json` : premier jet, relu comme en A.3.
5. **Tests** : `node scripts/tester.mjs`. `comparer_detections` doit rougir : c'est attendu,
   parce que la détection n'a pas encore de réponse figée. Lancer alors
   `node scripts/comparer_detections.mjs --mettre-a-jour`, puis
   `node .claude/skills/ajouter-exercice/verifier_ajout_detection.mjs`, qui prouve que la mise à
   jour n'a fait qu'**ajouter**. Si une réponse existante a changé, arrêter et comprendre : un
   helper partagé a bougé. Relancer ensuite `tester.mjs` en entier. Lire ce que
   `verifier_instruments` imprime des jetons peu visités : les seuils de la nouvelle
   détection y sont mal couverts par les poses figées, ce qui fait du banc d'essai la vraie
   preuve.
6. **Saboter** : inverser un seuil de l'instrument et vérifier que `verifier_instruments`
   rougit, puis restaurer. Un test qui n'a jamais échoué ne prouve rien.
7. **Poussée 1**, après accord. **Banc d'essai** sur l'iPad : `demo/`, exercice choisi dans la
   liste. Les quatre preuves, chacune notée dans la fiche de suivi :
   1. **Compte juste** : 10 répétitions honnêtes donnent 10 ;
   2. **Pas de faux positifs** : marcher, se mettre en place, prendre l'haltère, faire l'exercice
      voisin, faire une demi-répétition, tout cela ne compte rien ;
   3. **Refus bien expliqué** : une répétition volontairement incomplète fait dire « ça ne
      compte pas », avec la bonne raison ;
   4. **Mauvais côté signalé** (unilatéral seulement) : faire le mouvement de l'autre membre
      fait dire « c'est l'autre jambe » ou « l'autre bras ».

   L'utilisateur colle le résumé copié du banc d'essai. On ajuste les seuils, en déplaçant
   **ensemble** les deux seuils d'une hystérésis, puis on retourne à l'étape 5 (et on demande à
   nouveau avant de pousser), jusqu'aux quatre preuves.

### Jalon 2 : il progresse, en séance

8. **Barème définitif** : partir de la famille de mouvement de `docs/reglages.md`. Justifier
   `cible_min` (le bas appartient au débutant), `cible_max`, `series`, `poids_min` et
   `poids_max`. Les bornes se jugent **sur la performance qu'elles exigent**, que montre
   `dev/baremes.html`, jamais sur leur nombre. Ouvrir `dev/progression.html` sur l'exercice :
   départ selon la note, parcours, baisses de volume. Écrire les choix dans la fiche de suivi,
   et dans `docs/reglages.md` seulement si une règle nouvelle est apparue.
9. **Tests**, puis **poussée 2** après accord. **Essai en séance** : l'utilisateur crée une
   séance perso qui joue l'exercice. Il vérifie que la mise en place et « c'est parti »
   fonctionnent, que le compte est juste, que la série se termine, puis que l'historique, la
   fiche, le niveau et la ligue sont corrects, et que l'objectif de la séance suivante est
   cohérent.
10. **Médias** (§ 5), puis **clôture** (§ 6).

### Plus tard : d'un échauffement à un exercice compté

C'est un **nouveau mouvement**, sous un autre nom, par le parcours B. L'échauffement garde son
nom, puisque les séances perso et l'historique le nomment. Il peut emprunter la nouvelle
détection pour l'affichage. Un mouvement n'est jamais les deux à la fois : `est_echauffement`
retire tout ce qui le concerne des statistiques.

## 5. Les médias

Ils peuvent arriver après la poussée : une vidéo ou un son absents ne sont qu'un silence.
`dev/fiches.html` compte les vidéos à tourner, et `audio/A_ENREGISTRER.md` liste les sons à
enregistrer.

- **Vidéo** : caméra immobile, cadrée dans l'orientation de la fiche. Pour un exercice à
  haltère, garder quelques secondes de pièce vide au début. On filme **en vue vraie** (ce
  qu'enregistre l'iPad), sans activer « Caméra avant en miroir ». Déposer la prise dans
  `video/a_traiter/<nom de fichier>.mov`, puis lancer `node video/illustrer_tout.mjs`. Pour un
  mouvement unilatéral, filmer un seul côté : le script écrit l'autre avec `--miroir`. Faire
  vérifier le sens sur la planche de contrôle : en vue miroir, le membre « droit » travaille à
  droite de l'image. Seul le `.mp4` de `web/static/videos/` se commite, jamais la prise brute.
- **Voix** : le nom de l'exercice est un `.wav` au nom normalisé (`A_ENREGISTRER.md` le
  donne). On le dit sur un ton **suspendu**, parce qu'il suit une amorce (« prochain exercice »).
  Déposer la prise dans `audio/a_traiter/`, puis lancer `python audio/nettoyer_sons.py`. Une
  raison ou une brique nouvelle s'enregistre de la même façon.
- Relancer `node scripts/lister_annonces.mjs` et `tester.mjs`. Ils passent en « déjà fait », et
  `verifier_donnees` refuse une vidéo dont le nom ne correspond à aucun mouvement.

## 6. Clôture

- Toutes les cases cochées, `tester.mjs` vert, essai validé par l'utilisateur.
- **Docs dans le même commit** : CLAUDE.md seulement si l'ajout a appris une règle (une leçon de
  détection va dans *Règles apprises*), `docs/reglages.md` pour un réglage nouveau, le README
  s'il décrit ce qui a changé. On documente des règles, pas des valeurs.
- Fusion de `travail` dans `main` **sur demande de l'utilisateur**, avec la suppression de la
  fiche de suivi.
- Rappeler les suites possibles : les fautes de forme (commande de `dev/fiches.html`), et la
  forme comptée d'un échauffement.

Les messages de commit sont en français, à l'impératif de la troisième personne, comme dans
l'historique (« Ajoute les talons-fesses en échauffement »).
