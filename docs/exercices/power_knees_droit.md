# Power knees droit / Power knees gauche

Fiche de suivi d'un ajout en cours (protocole : `.claude/skills/ajouter-exercice/`). Supprimée à
la fusion dans `main`. Comptés en AMRAP de 30 s dans la séance cardio.

## Questionnaire

| Question | Réponse | Pourquoi |
|---|---|---|
| Nature | Exercices comptés (AMRAP) | |
| Nom | « Power knees droit », « Power knees gauche » | Un côté par série (2026-10-22) : deux mouvements |
| Exécution | Mains jointes au-dessus de la tête ; le genou monte avec force et **les mains descendent le toucher** ; les mains remontent au-dessus de la tête | Réponses du 2026-10-22 |
| Côté | Unilatéral : `autre_cote` réciproque, membre `jambe` (« c'est l'autre jambe ») | |
| Matériel | Aucun | |
| Orientation | `face` | La hauteur du genou et les mains qui le rejoignent se lisent de face |
| Muscles, chaîne | Abdominaux, quadriceps, deltoïdes. Chaîne `cardio` | Proposés par Claude |
| Départ, faux positifs | Départ `debut` (debout, mains au-dessus de la tête, genoux au même niveau). Faux positifs : le genou monte sans les mains, l'autre genou | |

## Détections (conçues le 2026-10-28)

De face, buste debout. Pour le genou mesuré :
- `fin` : genou levé > 0,5 tibia au-dessus de l'autre **et** la main la plus loin du genou à
  moins de 0,8 tibia de lui (les deux mains le touchent) ;
- `debut` : genoux au même niveau (< 0,15) **et** les deux mains au-dessus des épaules.

Délai par défaut (0,3 s). **Geste de contrôle** : deux bras tendus au-dessus de la tête, tenus
trois secondes, remettent le compte à zéro. La mise en place, mains en haut, dure 1,5 s : la
fiche demande de ne pas rester bras en l'air plus de deux secondes. À surveiller au banc.

## Parcours B — exercice compté

### Jalon 1 : il compte juste

- [x] Détection conçue (ci-dessus)
- [x] `detections.js` + `DETECTIONS`
- [x] `instruments.js`
- [x] `mouvements.json` (avec `autre_cote`), `baremes.json`, `reglages.json` (**provisoires**)
- [ ] `fiches.json`, relue par l'utilisateur
- [x] `comparer_detections --mettre-a-jour` + `verifier_ajout_detection` : rien que des ajouts
- [x] Sabotages (mains oubliées dans l'instrument, seuil déplacé, autre côté non réciproque) : chacun rougit
- [ ] Poussée 1 sur `travail` (accord donné)
- [ ] Banc d'essai : compte juste ; pas de faux positifs ; refus expliqué ; **mauvais côté signalé** (« c'est l'autre jambe »)

Barème provisoire : `series = series_max = 3`, cible 6-25 par AMRAP de 30 s. Tempo 1,2 s.

### Jalon 2 : il progresse

- [ ] Barème définitif
- [ ] Poussée 2 (accord donné)
- [ ] Essai en séance

## Journal du banc d'essai

(Les résumés collés et les seuils changés viennent ici.)

## Médias

- [ ] Vidéo du côté droit, tournée de face ; le gauche vient en miroir (`--miroir`)
- [ ] Noms enregistrés (`power_knees_droit.wav`, `power_knees_gauche.wav`)

## Clôture

- [ ] Docs à jour si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche)
