# Course sur place / Montées de genou / Talons-fesses / Heisman / Mountain climber debout / Switch kicks / Scissor runs

Fiche de suivi d'un ajout en cours (protocole : `.claude/skills/ajouter-exercice/`). Supprimée à
la fusion dans `main`. La famille des jambes alternées de la séance cardio, comptée en AMRAP de
30 s. **Chaque côté compte** (gauche = 1, droite = 2).

## Questionnaire

| Question | Réponse | Pourquoi |
|---|---|---|
| Nature | Exercices comptés (AMRAP). Montées de genou et Talons-fesses restent aussi des échauffements (`aussi_exercice`) | Même nom, le mode du bloc décide |
| Nom | « Course sur place », « Heisman », « Mountain climber debout », « Switch kicks », « Scissor runs » ; existants : « Montées de genou », « Talons-fesses » | Les noms du programme cardio |
| Exécution | Course : petits pas, chaque pied qui quitte le sol. Montées de genou : genou **à hauteur de hanche**. Talons-fesses : talon vers la fesse, genou pointé vers le sol. Heisman : bond de côté, retombée sur un pied, l'autre genou levé. Mountain climber : genou levé et main **opposée au-dessus de la tête**. Switch kicks : saut, coup de pied devant **à hauteur de hanche**, garde haute. Scissor runs : pieds échangés devant/derrière en sautant, sans descendre | Réponses du 2026-10-22 et du 2026-10-28 |
| Côté | Alterné, chaque côté compte | |
| Matériel | Aucun | |
| Orientation | Face : course, Heisman. Profil : montées de genou, talons-fesses, mountain climber, switch kicks, scissor runs | La hauteur du genou devant soi, le talon derrière et l'écart avant-arrière se lisent de profil ; le petit pas et le bond latéral, de face |
| Muscles, chaîne | Course : quadriceps, mollets. Montées : quadriceps, abdominaux. Talons : ischio-jambiers, mollets. Heisman : fessiers, quadriceps, mollets. Climber : abdominaux, quadriceps, deltoïdes. Kicks : quadriceps, abdominaux, mollets. Scissor : quadriceps, ischio-jambiers, mollets. Chaîne `cardio` | Proposés par Claude |
| Départ, faux positifs | Départ `debut` partout (debout, pieds au sol, genoux au même niveau). Faux positifs à essayer : marcher, piétiner, une montée de genou faite aux talons-fesses (et l'inverse), un genou levé sans bond (Heisman), la main du même côté (climber), un talon-fesse aux switch kicks | |

## Détections (conçues le 2026-10-28)

`debut` = la position neutre, `fin` = l'un **ou** l'autre côté à son extrémité (la mesure garde le
côté le plus avancé). Condition de position commune : buste debout. Délai propre entre deux
répétitions (`delai_min_reps`) : 0,15 s (course, montées, talons, scissor), 0,2 s (Heisman,
climber, kicks).

- **Course sur place** (face) : pied le plus levé au-dessus de l'autre > 0,25 tibia (`fin`), < 0,08 (`debut`).
- **Montées de genou** (profil) : genou le plus haut à moins de 0,05 tibia sous sa hanche (`fin`), les deux à plus de 0,7 (`debut`).
- **Talons-fesses** (profil) : pied le plus levé > 0,8 tibia **et** genoux au même niveau (genou le plus levé < 0,3) (`fin`) ; pied < 0,15 (`debut`). La condition des genoux sépare le talon-fesse de la montée de genou.
- **Heisman** (face) : genou le plus levé > 0,5 tibia **et** pied d'appui sorti à l'extérieur de sa hanche > 0,1 épaule (`fin`) ; genoux alignés < 0,15 (`debut`).
- **Mountain climber debout** (profil) : genou le plus levé > 0,5 tibia **et** main opposée au-dessus du nez (`fin`) ; genoux alignés < 0,15 (`debut`).
- **Switch kicks** (profil) : pied le plus haut à moins de 0,5 tibia sous sa hanche **et** lancé à plus d'un tibia d'elle (`fin`) ; à plus de 1,6 sous la hanche (`debut`). La portée sépare le coup de pied du talon-fesse.
- **Scissor runs** (profil) : écart avant-arrière des chevilles > 1 tibia (`fin`), < 0,4 (`debut`).
- Raisons : « tu ne montes pas assez haut » sur le genou, le talon ou le pied. Aucune prise de son nouvelle.

## Parcours B — exercice compté

### Jalon 1 : il compte juste

- [x] Détection conçue (ci-dessus)
- [x] `detections.js` + `DETECTIONS`
- [x] `instruments.js` (tous les jetons visités par au moins vingt poses figées)
- [x] `mouvements.json`, `baremes.json` (matériel), `reglages.json` (spec, bornes, tempo **provisoires**)
- [ ] `fiches.json`, relue par l'utilisateur (aucun avertissement dans `dev/fiches.html`)
- [x] `comparer_detections --mettre-a-jour` + `verifier_ajout_detection` : rien que des ajouts
- [x] Sabotages (seuil inversé, condition oubliée, seuil de détection déplacé) : chacun rougit
- [x] Poussée 1 sur `travail` (accord donné, 2026-10-28)
- [ ] Banc d'essai (40 répétitions, choisies sur la fiche de la démo), pour chacun des sept :
  - [ ] compte juste, **au rythme réel** (3 à 4 pas par seconde pour la course et les montées)
  - [ ] pas de faux positifs (voir le questionnaire)
  - [ ] refus bien expliqué (un genou à mi-cuisse, un coup de pied trop bas)

Barème provisoire : `series = series_max = 3`, en répétitions par AMRAP de 30 s, chaque côté
compté. Cibles : course 20-90, montées et talons 16-80, Heisman 10-40, climber 12-50, kicks
10-40, scissor 16-70. Bornes de 3 × `cible_min` à 3,9 × `cible_max`. Tempo de 0,3 à 0,8 s.

### Jalon 2 : il progresse

- [ ] Barème définitif, bornes jugées dans `dev/baremes.html`
- [ ] Départ et parcours vus dans `dev/progression.html`
- [ ] Poussée 2 (accord donné)
- [ ] Essai en séance

## Journal du banc d'essai

(Les résumés collés et les seuils changés viennent ici.)

## Médias

- [x] Montées de genou : vidéo et voix déjà présentes (vidéo tournée de face : à refaire de profil ?)
- [ ] Talons-fesses : vidéo de profil, voix
- [ ] Course sur place, Heisman, Mountain climber debout, Switch kicks, Scissor runs : vidéos, voix

## Clôture

- [ ] Docs à jour si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche, et de `talons_fesses.md` sur `travail`)
