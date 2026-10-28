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

## Détection (conçue le 2026-10-28)

**Le seul mouvement qui lit un repère extérieur au corps : le centre de l'image.** Une détection
n'a pas de mémoire, et rien dans une image seule ne dit de quel côté on a sauté, sauf la place
dans l'image. L'amplitude se rapporte au corps : l'écart du milieu des chevilles au centre de
l'image, en largeurs d'épaules.
- `fin` : posé à plus de 0,6 largeur d'épaule du centre, d'un côté ou de l'autre ;
- `debut` : à moins de 0,2, le passage par le milieu entre deux sauts.

Buste debout. Délai propre 0,2 s. Limites :
- on doit se placer **au milieu de l'image** (la fiche le demande) ; une dérive au fil des sauts
  fausse le compte ;
- le passage par le milieu se fait en l'air, sur peu d'images.

Repli si le banc d'essai montre que ça ne tient pas : un repère pris à la mise en place (la
position tenue avant « c'est parti »), ce qui demande de donner une mémoire au moteur, ou le
chrono.

## Parcours B — exercice compté

### Jalon 1 : il compte juste

- [x] Détection conçue (ci-dessus)
- [x] `detections.js` + `DETECTIONS`
- [x] `instruments.js`
- [x] `mouvements.json`, `baremes.json`, `reglages.json` (**provisoires**)
- [ ] `fiches.json`, relue par l'utilisateur
- [x] `comparer_detections --mettre-a-jour` + `verifier_ajout_detection` : rien que des ajouts
- [x] Sabotages (seuil inversé dans l'instrument, seuil déplacé) : chacun rougit
- [ ] Poussée 1 sur `travail` (accord donné)
- [ ] Banc d'essai : compte juste (en partant du milieu), pas de faux positifs, refus expliqué

Barème provisoire : `series = series_max = 3`, cible 10-45 par AMRAP de 30 s. Tempo 0,7 s.

### Jalon 2 : il progresse

- [ ] Barème définitif
- [ ] Poussée 2 (accord donné)
- [ ] Essai en séance

## Journal du banc d'essai

(Les résumés collés et les seuils changés viennent ici.)

## Médias

- [ ] Vidéo tournée de face
- [ ] Nom enregistré (`ski.wav`)

## Clôture

- [ ] Docs à jour si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche)
