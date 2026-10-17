# <Nom de l'exercice>

Fiche de suivi d'un ajout en cours (protocole : `.claude/skills/ajouter-exercice/`). Supprimée à
la fusion dans `main`. Le titre est le nom exact du mouvement (ou « Nom droit / Nom gauche ») :
`dev/suivi.html` le retrouve par lui.

## Questionnaire

| Question | Réponse | Pourquoi |
|---|---|---|
| Nature | | |
| Nom (et autre forme à venir) | | |
| Exécution | | |
| Côté | | |
| Matériel | | |
| Orientation | | |
| Muscles, chaîne | | |
| Famille (variantes) | | |
| Changements (échauffement) | | |
| Départ, difficulté, faux positifs (compté) | | |

## Parcours A — échauffement

- [ ] `mouvements.json`
- [ ] `fiches.json`, premier jet
- [ ] Fiche relue dans `dev/fiches.html` par l'utilisateur
- [ ] `tester.mjs` vert, `A_ENREGISTRER.md` régénéré
- [ ] Poussée sur `travail` (accord donné)
- [ ] Essai en séance perso sur l'iPad

## Parcours B — exercice compté

### Jalon 1 : il compte juste

- [ ] Détection conçue (ci-dessous)
- [ ] `detections.js` + `DETECTIONS`
- [ ] `instruments.js`
- [ ] `mouvements.json`, `baremes.json` (matériel), `reglages.json` (spec, bornes, tempo **provisoires**)
- [ ] `fiches.json`, relue par l'utilisateur
- [ ] `comparer_detections --mettre-a-jour` + `verifier_ajout_detection` : rien que des ajouts
- [ ] `tester.mjs` vert ; sabotage d'un seuil vu rouge
- [ ] Poussée 1 (accord donné)
- [ ] Banc d'essai : compte juste (10 → 10)
- [ ] Banc d'essai : pas de faux positifs
- [ ] Banc d'essai : refus bien expliqué
- [ ] Banc d'essai : mauvais côté signalé (unilatéral)

### Jalon 2 : il progresse

- [ ] Barème définitif, bornes, tempo (justifiés ci-dessous)
- [ ] Parcours lu dans `dev/progression.html`
- [ ] Poussée 2 (accord donné)
- [ ] Essai en séance perso sur l'iPad

### Détection

Mesures, seuils et leur origine, ce que valent `debut` et `fin`, `depart`.

### Barème

Exercice de référence, valeurs et leur justification.

### Journal du banc d'essai

Date, résumé collé, ce qui a été changé.

## Médias

- [ ] Vidéo tournée, illustrée, sens vérifié sur la planche
- [ ] Nom enregistré (`.wav`)
- [ ] Briques nouvelles enregistrées (raisons)

## Clôture

- [ ] Docs à jour (CLAUDE.md, `docs/reglages.md`, README) si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche)
