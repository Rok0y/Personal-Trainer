# Jumping jacks / Power jacks / Stance jacks

Fiche de suivi d'un ajout en cours (protocole : `.claude/skills/ajouter-exercice/`). Supprimée à
la fusion dans `main`. La famille des sauts de la séance cardio, comptés en AMRAP de 30 s.

## Questionnaire

| Question | Réponse | Pourquoi |
|---|---|---|
| Nature | Exercices comptés (AMRAP). Jumping jacks reste aussi un échauffement (`aussi_exercice`) | Décision du 2026-10-22 : même nom, le mode du bloc décide |
| Nom (et autre forme à venir) | « Jumping jacks » (existant), « Power jacks », « Stance jacks » | Les noms du programme cardio |
| Exécution | Jumping jack : pieds écartés et bras au-dessus de la tête, puis pieds joints bras en bas. Power jack : on retombe jambes écartées en squat, on remonte d'un saut bras au-dessus de la tête. Stance jack : saut pieds joints, puis une main touche le pied opposé, en alternant | Réponses du 2026-10-28 |
| Côté | Bilatéral (jumping, power). Stance : alterné, chaque toucher compte | |
| Matériel | Aucun | |
| Orientation | `face` pour les trois | L'écart des pieds, les bras et le toucher croisé se lisent de face |
| Muscles, chaîne | Jumping : `mollets`, `deltoides`. Power : `quadriceps`, `fessiers`, `mollets`. Stance : `quadriceps`, `fessiers`, `obliques`. Chaîne `cardio` | Validé le 2026-10-28 |
| Famille (variantes) | Aucune | |
| Départ, difficulté, faux positifs | Jumping : départ `debut` (pieds joints, bras en bas). Power : départ `fin` (debout, bras en haut). Stance : départ `debut` (debout). Faux positifs à essayer : marcher, lever les bras sans sauter, un squat sans saut, toucher le pied du même côté | |

## Détections (conçues le 2026-10-28)

Toutes rapportées au corps, deux seuils par mesure de chemin, de face.

- **`jumping_jacks_detection`** — position : buste debout (`buste_vertical > 0`).
  - `fin` : écart des chevilles > `JACK_ECART_ECARTE` (1,3 largeur d'épaules) **et** main la plus basse au-dessus de l'épaule (`bras_le_plus_bas < 0`, en bustes).
  - `debut` : écart < `JACK_ECART_JOINT` (0,9) **et** main la plus haute nettement sous l'épaule (`bras_le_plus_haut > 0,6`).
  - Un bras à mi-hauteur ou des pieds à peine écartés restent en `milieu`.
- **`power_jacks_detection`** — position : buste debout.
  - `debut` : descente des hanches < 0,6 (moyenne des deux jambes, en tibias) **et** écart des chevilles > 1,3.
  - `fin` : descente > 0,8 **et** les deux mains au-dessus des épaules.
- **`stance_jacks_detection`** — pas de condition de buste (il se penche pour toucher). La main qui touche est le poignet le plus bas ; le pied visé est l'opposé.
  - `fin` : cette main à moins de 0,6 tibia au-dessus du pied opposé **et** passée de l'autre côté de l'axe des hanches (> 0,05 largeur d'épaules).
  - `debut` : à plus de 1,4 tibia (debout).
  - Le passage de l'axe distingue le toucher croisé d'une main au pied du même côté. L'alternance gauche/droite n'est pas vérifiée.
- Délai entre deux répétitions : celui par défaut (0,3 s). Ces sauts ne dépassent pas une répétition par seconde.
- Raisons de « ça ne compte pas » : bras pas assez haut (« tu ne montes pas assez haut ») ; power jack pas assez bas, ou pas remonté (« tu ne descends pas assez bas », « tu ne remontes pas complètement ») ; stance jack main pas assez basse, ou pas redressé. Aucune prise de son nouvelle.

## Parcours B — exercice compté

### Jalon 1 : il compte juste

- [x] Détection conçue (ci-dessus)
- [x] `detections.js` + `DETECTIONS`
- [x] `instruments.js` (tous les jetons visités par au moins vingt poses figées)
- [x] `mouvements.json`, `baremes.json` (matériel), `reglages.json` (spec, bornes, tempo **provisoires**)
- [ ] `fiches.json`, relue par l'utilisateur
- [x] `comparer_detections --mettre-a-jour` + `verifier_ajout_detection` : rien que des ajouts
- [x] Sabotages : un seuil d'instrument inversé, le croisement oublié, un seuil de détection déplacé — chacun rougit
- [ ] Poussée 1 sur `travail` (accord donné)
- [ ] Banc d'essai sur l'iPad (`demo/?cible=40`), pour chacun des trois :
  - [ ] compte juste (40 honnêtes donnent 40)
  - [ ] pas de faux positifs (marcher, se mettre en place, lever les bras sans sauter, un squat sans saut, le pied du même côté)
  - [ ] refus bien expliqué (un saut bras à moitié levé, un power jack sans descendre)

Barème provisoire, pris par analogie et à régler au jalon 2 : `series = series_max = 3` (les trois
tours du circuit), cible de 10 à 40 (jumping), 4 à 20 (power), 6 à 30 (stance), en répétitions
par AMRAP de 30 s. Bornes de ligue réparties de 3 × `cible_min` à 3,9 × `cible_max`. Tempo 1 s
(jumping), 1,5 s (power, stance).

### Jalon 2 : il progresse

- [ ] Barème définitif (`docs/reglages.md`), bornes jugées dans `dev/baremes.html`
- [ ] Départ et parcours vus dans `dev/progression.html`
- [ ] Poussée 2 (accord donné)
- [ ] Essai en séance : mise en place, « c'est parti », compte, historique, niveau, ligue, objectif suivant

## Journal du banc d'essai

(Les résumés collés et les seuils changés viennent ici.)

## Médias

- [x] Jumping jacks : vidéo et voix déjà présentes
- [ ] Power jacks, Stance jacks : vidéos tournées de face
- [ ] Noms enregistrés (`power_jacks.wav`, `stance_jacks.wav`, ton suspendu)

## Clôture

- [ ] Docs à jour si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche)
