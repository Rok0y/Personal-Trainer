# Burpees / Suicide jumps

Fiche de suivi d'un ajout en cours (protocole : `.claude/skills/ajouter-exercice/`). Supprimée à
la fusion dans `main`. La famille au sol de la séance cardio, comptée en AMRAP de 30 s.

## Questionnaire

| Question | Réponse | Pourquoi |
|---|---|---|
| Nature | Exercices comptés (AMRAP) | |
| Nom | « Burpees », « Suicide jumps » | Les « drills » du programme sont des burpees : un seul mouvement (2026-10-22) |
| Exécution | Burpee : accroupi, pieds en arrière, **pompe**, pieds devant, debout, saut. Suicide jump : planche **bras tendus**, pieds devant d'un saut, debout, saut | Réponses du 2026-10-22 |
| Côté | Bilatéral | |
| Matériel | Aucun (un tapis aide) | |
| Orientation | `profil` | La pompe et le passage du sol à debout se lisent de profil |
| Muscles, chaîne | Burpees : quadriceps, pectoraux, abdominaux. Suicide jumps : quadriceps, abdominaux, deltoïdes. Chaîne `cardio` | Proposés par Claude |
| Départ, faux positifs | Départ `fin` (debout, immobile). Faux positifs : un burpee sans pompe, un squat sans aller au sol, s'allonger puis se relever lentement | |

## Détections (conçues le 2026-10-28)

De profil, `fin` = **debout** (buste vertical et descente des hanches > 0,8 tibia), commun aux
deux. Le saut final n'est pas vérifié : debout ou en l'air, le corps a la même forme.

- **`burpee_detection`** : `debut` = **le bas d'une pompe** — buste à l'horizontale et coude du
  bras le mieux vu sous `SEUIL_COMPTAGE_POMPE` (120°, le seuil qui arme une pompe : la même
  règle). Une planche bras tendus n'arme pas : un burpee sans pompe ne compte pas, et « ça ne
  compte pas : tu ne descends pas assez bas » le dit.
- **`suicide_jumps_detection`** : `debut` = planche bras tendus (coude > 150°). Un burpee arme
  aussi un suicide jump (il passe par la planche bras tendus) : sans conséquence, on ne les fait
  pas l'un pour l'autre.
- Délai par défaut (0,3 s).

## Parcours B — exercice compté

### Jalon 1 : il compte juste

- [x] Détection conçue (ci-dessus)
- [x] `detections.js` + `DETECTIONS`
- [x] `instruments.js`
- [x] `mouvements.json`, `baremes.json` (matériel), `reglages.json` (spec, bornes, tempo **provisoires**)
- [ ] `fiches.json`, relue par l'utilisateur
- [x] `comparer_detections --mettre-a-jour` + `verifier_ajout_detection` : rien que des ajouts
- [x] Sabotages (la pompe oubliée dans l'instrument, un seuil de détection déplacé) : chacun rougit
- [x] Poussée 1 sur `travail` (accord donné, 2026-10-28)
- [ ] Banc d'essai : compte juste, pas de faux positifs (burpee sans pompe), refus expliqué

Barème provisoire : `series = series_max = 3`, cible 3-12 (burpees), 4-15 (suicide jumps) par
AMRAP de 30 s. Tempo 3 s et 2,5 s.

### Jalon 2 : il progresse

- [ ] Barème définitif, bornes jugées dans `dev/baremes.html`
- [ ] Départ et parcours vus dans `dev/progression.html`
- [ ] Poussée 2 (accord donné)
- [ ] Essai en séance

## Journal du banc d'essai

(Les résumés collés et les seuils changés viennent ici.)

## Médias

- [ ] Vidéos tournées de profil
- [ ] Noms enregistrés (`burpees.wav`, `suicide_jumps.wav`)

## Clôture

- [ ] Docs à jour si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche)
