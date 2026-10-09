# Personal Trainer

Coach de fitness en temps réel, dans le navigateur : la caméra de l'appareil détecte votre pose (MediaPipe), l'application compte vos répétitions, vous guide à la voix (en français), enregistre l'historique de vos séances et fait progresser vos objectifs séance après séance.

**Tout tourne sur l'appareil**, y compris la détection de pose. L'image ne quitte jamais le téléphone ou la tablette, l'historique vit dans IndexedDB, et le site est purement statique : il n'y a aucun serveur à qui parler. L'application s'installe sur un iPad depuis Safari (« Sur l'écran d'accueil »).

## Fonctionnalités principales

- **Prise en main d'un nouveau profil** : prénom et mesures, puis six étapes d'une ou deux phrases — comment ça marche, votre **matériel** (haltères possédés, poids par poids, et accessoires), votre **note d'athlète** de 1 à 10 (avec un aperçu de vos paliers de départ), votre programme, les gestes, où poser l'appareil. Elle se termine par une mise en pratique caméra ouverte, où l'on se cadre et où l'on essaie les quatre gestes pour de vrai. Les écrans de texte sont **muets** : la voix ne reprend qu'une fois que vous vous êtes éloigné de l'appareil.
- **Pas de test d'entrée** : un exercice jamais fait démarre au palier de votre note, traduit par les bornes de ligue pour qu'un même chiffre demande le même effort sur chaque mouvement. La note **monte toute seule** quand la plupart des exercices la dépassent nettement. Elle ne valide jamais un niveau.
- **Fiches d'exercice** : chaque mouvement explique comment se placer (cadrage caméra compris), comment l'exécuter, **ce que vous devez sentir** et ce qu'il faut éviter, avec des mots de tous les jours. Elles sont consultables depuis l'onglet **Exercices** et rappelées pendant la séance. Chaque fiche montre aussi le niveau atteint, la ligue et la courbe de progression.
- **Détection de pose et comptage automatique** des répétitions, en quatre modes : répétitions, maintien, chrono, AMRAP.
- **Gestes de contrôle**, sans toucher l'écran :
  - bras en croix pour valider une série, ou pour passer une pause ;
  - bras droit levé pour ajouter une répétition oubliée, bras gauche pour en retirer une ;
  - deux bras levés pour remettre le compteur à zéro.
- **Guidage d'installation** : la caméra s'ouvre avant l'effort et vérifie que vous tenez entièrement dans l'image avant de laisser commencer.
- **Échauffement guidé** : des mouvements minutés en tête de séance, annoncés à la voix. Le coach dit quand changer de sens ou de jambe. L'échauffement n'entre ni dans les records ni dans l'historique.
- **Coach vocal** : annonces pré-enregistrées, composées de briques (« prochain exercice » · « curl biceps droit » · « prépare un haltère de 8 kilos »). Brancher ou retirer des écouteurs en pleine séance ne coupe pas le son : il est relancé tout seul.
- **Niveaux et ligues** : chaque exercice a un barème de paliers dont le volume ne redescend jamais, et votre niveau — le plus haut palier jamais validé — se déduit de l'historique. Il ne recule jamais. Une ligue (Bronze → Maître) traduit le volume produit, et l'XP fait monter un niveau général.
- **Progression automatique** : chaque séance repart de l'objectif de la précédente. Réussi, il monte d'un palier (deux si « c'était facile », trois si « trop facile ») ; manqué, il revient à l'identique, ou descend si « c'était trop dur ». Une cible saisie à la main est figée (badge orange) jusqu'à ce que la séance soit menée à son terme.
- **Variantes plus faciles** : pompes sur les genoux, inclinées, contre le mur, planche sur les genoux, squat sur chaise. On peut choisir sa version avant de démarrer, basculer en pleine séance, ou l'accepter après un échec. On **remonte ensuite tout seul**, un cran par séance réussie.
- **Programmes** : un programme liste une performance à atteindre par exercice et se vit à la semaine — une case par séance, dans l'ordre que tu choisis, sur une semaine qui commence le jour que tu choisis, et une série de semaines réussies. Rien n'est stocké : tout se recalcule depuis l'historique.
- **Profils** : chaque profil garde son historique, ses niveaux et ses recalages ; les séances et les programmes sont communs. L'écran « Qui s'entraîne ? » s'impose à chaque lancement.
- **Recalage du niveau** : depuis la fiche d'un exercice, on déclare une performance qu'on sait tenir, et le barème en déduit le niveau.
- **Séances modifiables sur l'appareil** : l'éditeur de l'application garde ses modifications sur l'appareil, où elles masquent la version déployée (un badge le signale).
- **Sauvegarde** : l'historique s'exporte et se réimporte en un fichier, depuis l'onglet Historique. À faire régulièrement : Safari peut purger les données d'un site.

`web/static/demo/` est un second livrable, plus petit : un **banc d'essai** d'un exercice isolé, qui sert à faire tester la détection par quelqu'un d'autre et à diagnostiquer un comptage qui ne démarre pas.

## Organisation du code

Tout ce qui tourne vit dans `web/static/` :

- `app/` — l'application. `demo/` — le banc d'essai. `dev/` — deux pages de réglage (`baremes.html`, `fiches.html`), voir plus bas.
- `js/` — les modules : la séance (`circuit.js`, `moteur.js`, `seance.js`), la détection (`detections.js`, `positions.js`, `compteur.js`, `camera.js`, `cadrage.js`), la progression (`paliers.js`, `niveaux.js`, `objectifs.js`, `ressenti.js`, `calibration.js`, `ligues.js`, `programmes.js`, `variantes.js`), l'historique (`historique.js`, `stockage.js`), le coach (`annonces.js`, `lecteur.js`), l'affichage (`hud.js` et les `*_ui.js`).
- `donnees/` — les **données**, éditées à la main. Chaque fait n'a qu'une source :
  - `reglages.json` — tous les nombres réglables (barèmes, ligues, XP, note d'athlète). Le **pourquoi** de chaque réglage est dans [docs/reglages.md](docs/reglages.md) ;
  - `baremes.json` — ce qui ne se règle pas (échelles d'haltères, matériel par exercice) ;
  - `fiches.json` — le texte des fiches d'exercice ;
  - `mouvements.json` — ce qui est couplé au code (détection, orientation, variantes) ;
  - `seances.json`, `programmes.json`, `sons.json` — les séances, les programmes, les tables du coach.
- `sons/` — les annonces enregistrées. Le nom d'un fichier est le texte prononcé.
- `videos/` — la boucle de chaque mouvement, montrée sur sa fiche, dans le guide du premier passage et pendant les pauses. Le nom d'un fichier vient du nom du mouvement ; une vidéo absente n'affiche simplement rien, et `dev/fiches.html` dit lesquelles restent à tourner.

En dehors : `scripts/` (vérifications et outils), `tests/fixtures/` (les réponses figées des tests), `audio/` (prise de son), `video/` (illustration des fiches : `python video/illustrer.py <vidéo> "<exercice>"` détoure, redessine en aplats et écrit la boucle dans `web/static/videos/` ; demande `onnxruntime`, `imageio-ffmpeg` et le modèle RobustVideoMatting dont le script donne l'adresse), `docs/`.

**Régler sans toucher au code** : `dev/baremes.html` et `dev/fiches.html` rechargent les données déployées, les rendent éditables, recalculent tout sous les yeux, et rendent le fichier prêt à coller dans `web/static/donnees/`. On colle, on pousse, c'est déployé.

## Lancer en local

L'application est un site statique : n'importe quel serveur fait l'affaire.

```bash
python -m scripts.servir_statique 8001
```

Puis ouvrir `http://localhost:8001/app/`. Ce serveur interdit au navigateur de garder les modules en cache, ce qui évite de tester une ancienne version d'un fichier qu'on vient de modifier.

## Tests

```bash
node scripts/tester.mjs
```

Une quinzaine de vérifications, en quelques secondes :
- les **données** se tiennent (`verifier_donnees.mjs`) : chaque séance est jouable, chaque mouvement a sa fiche, chaque programme vise un exercice qui a un barème ;
- les **tables du coach** se tiennent (`verifier_annonces.mjs`) ;
- aucune **méthode appelée n'est absente** et les modules inline n'ont pas de faute de syntaxe (`verifier_methodes.mjs`) ;
- les **tests figés** (`comparer_*.mjs`) rejouent des milliers de questions — poses, séances entières, historiques, barèmes — et comparent aux réponses de `tests/fixtures/`. Ces réponses ont été produites par l'ancienne implémentation Python, puis figées.

Un rouge signale un **changement de comportement**. S'il est voulu, après avoir lu les écarts :

```bash
node scripts/tester.mjs --mettre-a-jour
```

Jamais pour faire taire un rouge qu'on ne comprend pas : c'est exactement la régression que ces tests existent pour attraper. On peut cibler un test (`node scripts/tester.mjs ligues`). La CI lance la batterie avant chaque déploiement.

## Prise de son

Toutes les voix sont enregistrées à la main.

1. `node scripts/lister_annonces.mjs` écrit `audio/A_ENREGISTRER.md` : ce qu'il reste à dire au micro, avec le nom exact de chaque fichier.
2. Enregistrer dans `audio/a_traiter/` (non versionné).
3. `python audio/nettoyer_sons.py` rogne les silences et écrit dans `web/static/sons/`. Il demande `pip install -r requirements.txt` (pydub) et ffmpeg.

Un fichier absent est un silence, jamais une panne : on peut enregistrer par lots.

## Déploiement

**Le point d'entrée est https://rok0y.github.io/Personal-Trainer/sommaire.html** (la racine montre la même page) : un sommaire de toutes les pages (application, banc d'essai, outils de réglage), généré au déploiement par `scripts/sommaire.mjs`. Une nouvelle page y apparaît d'elle-même, à condition d'avoir un `<title>` et une `<meta name="description">` — les tests refusent une page qui n'en a pas.

`.github/workflows/demo.yml` publie `web/static` sur GitHub Pages à chaque push sur une des branches qu'il liste, après avoir lancé les tests. Chaque ressource est marquée de l'empreinte du commit (`camera.js?v=<sha>`), pour qu'un navigateur ne combine jamais un document neuf avec un module gardé en cache.

## Historique du projet

L'application a d'abord existé en version **ordinateur** (Python : boucle caméra OpenCV, serveur Flask, SQLite), dont la version navigateur était un portage vérifié par comparaison. Elle a été retirée : son code reste consultable au tag `derniere-version-desktop`.
