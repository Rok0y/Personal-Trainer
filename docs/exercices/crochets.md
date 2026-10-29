# Crochets

Fiche de suivi d'un ajout en cours (protocole : `.claude/skills/ajouter-exercice/`). Supprimée à
la fusion dans `main`. Compté en AMRAP de 30 s dans la séance cardio.

## Questionnaire

| Question | Réponse | Pourquoi |
|---|---|---|
| Nature | Exercice compté (AMRAP) | |
| Nom | « Crochets » | |
| Exécution | Crochets de boxe **par paquets** : quelques-uns d'un bras, puis de l'autre ; chaque crochet compte | Réponse du 2026-10-22 |
| Côté | Les deux bras, un seul mouvement : chaque crochet compte quel que soit le bras | |
| Matériel | Aucun | |
| Orientation | `face` | Le poing qui traverse devant soi se lit de face |
| Muscles, chaîne | Obliques, deltoïdes, pectoraux. Chaîne `cardio` | Proposés par Claude |
| Départ, faux positifs | Départ `debut` (en garde). Faux positifs : un uppercut, un coup droit, les bras qui retombent | |

## Détection (conçue le 2026-10-28)

De face, buste debout. Le poing le plus avancé vers l'autre côté (passage du milieu des épaules,
en largeurs d'épaules ; l'autre côté se lit sur les épaules) :
- `fin` : il a passé le milieu de plus de 0,3 largeur d'épaule **et** il est à hauteur d'épaule
  (à moins de 0,35 buste) ;
- `debut` : la garde — aucun poing passé de plus de 0,1, et les deux poings au-dessus de la
  mi-buste.

Délai propre 0,2 s. Le coude levé n'est pas vérifié : un coup droit qui croise devant soi à
hauteur d'épaule compterait aussi. À surveiller au banc.

## Parcours B — exercice compté

### Jalon 1 : il compte juste

- [x] Détection conçue (ci-dessus)
- [x] `detections.js` + `DETECTIONS`
- [x] `instruments.js`
- [x] `mouvements.json`, `baremes.json`, `reglages.json` (**provisoires**)
- [ ] `fiches.json`, relue par l'utilisateur
- [x] `comparer_detections --mettre-a-jour` + `verifier_ajout_detection` : rien que des ajouts
- [x] Sabotages (hauteur oubliée dans l'instrument, seuil déplacé) : chacun rougit
- [x] Poussée 1 sur `travail` (accord donné, 2026-10-28)
- [ ] Banc d'essai : compte juste, pas de faux positifs, refus expliqué

Barème provisoire : `series = series_max = 3`, cible 10-50 par AMRAP de 30 s. Tempo 0,6 s.

### Jalon 2 : il progresse

- [x] Barème définitif (2026-10-29, chiffres validés par l’utilisateur : quatre repères en 30 s, voir `docs/reglages.md`)
- [ ] Poussée 2 (accord donné)
- [ ] Essai en séance

## Journal du banc d'essai

**2026-10-29, Safari sur Mac, 20 répétitions (10 au sol), 32 img/s.** **Oublis**, et l'utilisateur ne comprend
pas ce qui est lu. 15 « pas revenu au début » : la garde, poing le plus bas à 0,42-0,64 buste
sous l'épaule (seuil < 0,4) ; le poing qui revient n'est pas encore remonté quand part le
suivant. **Changé** : garde < 0,75 (au-dessus de la taille). Le reste tient : croisement médian
1,07 (> 0,3), hauteur 0,05 (< 0,35).

**2026-10-29, second banc, Safari sur Mac, 20 répétitions (10 au sol), 32 img/s.** 20 sur 20, « nickel ». Seuils gardés.

## Médias

- [ ] Vidéo tournée de face
- [ ] Nom enregistré (`crochets.wav`)

## Clôture

- [ ] Docs à jour si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche)
