# Ski

Fiche de suivi d'un ajout en cours (protocole : `.claude/skills/ajouter-exercice/`). Supprimée à
la fusion dans `main`. Compté en AMRAP de 30 s dans la séance cardio.

## Questionnaire

| Question | Réponse | Pourquoi |
|---|---|---|
| Nature | Exercice compté (AMRAP) | |
| Nom | « Ski » | |
| Exécution | Sauts latéraux pieds joints, d'un côté à l'autre, comme un slalom ; chaque réception compte | Réponse du 2026-10-28 (« ce sont des sauts latéraux ») |
| Côté | Alterné, chaque côté compte | |
| Matériel | Aucun | |
| Orientation | `face` | Le déplacement latéral se lit de face |
| Muscles, chaîne | Quadriceps, fessiers, mollets. Chaîne `cardio` | Proposés par Claude |
| Départ, faux positifs | Départ `debut` (au milieu de l'image, immobile). Faux positifs : marcher sur le côté, un petit saut sur place | |

## Détection (conçue le 2026-10-28, refaite le 2026-10-29)

Chaque réception compte, **cuisses fléchies** :
- `fin` : hanches sous 0,9 de **soi debout** **et** milieu des chevilles à plus de 0,3 largeur
  d'épaule de **sa place de départ** ;
- `debut` : jambes tendues (> 0,95 de soi debout), à l'impulsion ou debout.

Les deux se lisent au **repère pris à la mise en place** (`REPERES`, `repere_du_bloc`) : la
position tenue immobile avant « c'est parti ». Buste debout, délai par défaut. La place de départ
ne sert qu'à refuser un squat sauté sur place. La première version comptait au passage par le
milieu, qui se fait en l'air (voir le journal).

## Parcours B — exercice compté

### Jalon 1 : il compte juste

- [x] Détection conçue (ci-dessus)
- [x] `detections.js` + `DETECTIONS`
- [x] `instruments.js`
- [x] `mouvements.json`, `baremes.json`, `reglages.json` (**provisoires**)
- [ ] `fiches.json`, relue par l'utilisateur
- [x] `comparer_detections --mettre-a-jour` + `verifier_ajout_detection` : rien que des ajouts
- [x] Sabotages (seuil inversé dans l'instrument, seuil déplacé) : chacun rougit
- [x] Poussée 1 sur `travail` (accord donné, 2026-10-28)
- [ ] Banc d'essai : compte juste (en partant du milieu), pas de faux positifs, refus expliqué

Barème provisoire : `series = series_max = 3`, cible 10-45 par AMRAP de 30 s. Tempo 0,7 s.

### Jalon 2 : il progresse

- [ ] Barème définitif
- [ ] Poussée 2 (accord donné)
- [ ] Essai en séance

## Journal du banc d'essai

**2026-10-29, Safari sur Mac, 20 répétitions (10 au sol), 32 img/s.** 20 comptés, mais **une réception sur deux** :
placé d'un côté de l'image, une réception tombait au « centre » (37 % du temps en `debut`).
Et sauter sans plier les jambes comptait. **Refait, sur décision de l'utilisateur** (flexion et
hors du centre) : `fin` = cuisses fléchies (descente des hanches < 1) **et** pieds à plus de
0,4 épaule du centre ; `debut` = jambes tendues (> 1,15), à l'impulsion. Plus de passage par le
milieu. Délai par défaut. Fiche mise à jour.

**2026-10-29, second banc, Safari sur Mac, 20 répétitions (10 au sol), 32 img/s.** **6 sur 20**, et pas de voix (normal : elle ne
dit que les dizaines). 16 réceptions refusées : pieds à 0,19-0,37 épaule du centre (décalé,
une réception sur deux tombait près du milieu), ou flexion arrêtée entre 1 et 1,1. **Changé** :
centre > 0,15, fléchi < 1,1, tendu > 1,25. Si le décalage revient, passer au repère pris à la
mise en place.

**2026-10-29, troisième banc, Safari sur Mac, 10 répétitions, 32 img/s.** 10 comptés, 17 réceptions refusées, « trop loin sur le côté ou descendre trop
bas » : flexion arrêtée à 1,13-1,19 (seuil < 1,1) pour 1,35 debout, et trois réceptions près du
centre de l'image. **Changé, sur décision de l'utilisateur** : le repère pris à la mise en place.
Fléchi < 0,9 de soi debout (ses réceptions : 0,84 à 0,88), tendu > 0,95, côtés à plus de 0,3
épaule de sa place de départ. Fiche mise à jour (plus de « reste centré »).

## Médias

- [ ] Vidéo tournée de face
- [ ] Nom enregistré (`ski.wav`)

## Clôture

- [ ] Docs à jour si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche)
