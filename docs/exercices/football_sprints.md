# Football sprints / Suicide drills

Fiche de suivi d'un ajout en cours (protocole : `.claude/skills/ajouter-exercice/`). Supprimée à
la fusion dans `main`. Deux mouvements de la séance cardio, ajoutés ensemble parce qu'ils suivent
le même parcours : des exercices **au chrono**, sans détection ni barème.

## Questionnaire

| Question | Réponse | Pourquoi |
|---|---|---|
| Nature | Exercice au chrono, sans détection (`est_echauffement: false`, mode `chrono`) | Un piétinement très rapide ne se compte pas à 24-36 images/s, et un aller-retour sort du champ : décision du 2026-10-22 |
| Nom (et autre forme à venir) | « Football sprints », « Suicide drills » | Les noms du programme cardio que l'utilisateur suit ; aucune autre forme prévue |
| Exécution | Football sprints : piétiner sur place, jambes écartées et pliées, le plus vite possible. Suicide drills : trois pas en courant sur le côté, toucher le sol, repartir de l'autre côté | |
| Côté | Bilatéral (sprints), alterné d'un côté à l'autre (drills) : un seul mouvement chacun | |
| Matériel | Aucun | |
| Orientation | `face` pour les deux | Les pieds écartés et le déplacement latéral se voient de face |
| Muscles, chaîne | Sprints : `quadriceps`, `mollets`. Drills : `quadriceps`, `fessiers`. Chaîne `cardio` | Position basse et appuis rapides ; les drills s'arrêtent et repartent jambes pliées |
| Famille (variantes) | Aucune | |
| Changements (échauffement) | Sans objet | Ce ne sont pas des échauffements |

## Parcours A — exercice au chrono

- [x] `mouvements.json` (catégories comprises, pour la fusion dans `travail`)
- [x] `fiches.json`, premier jet, sans avertissement dans `dev/fiches.html`
- [ ] Fiches relues dans `dev/fiches.html` par l'utilisateur
- [x] `tester.mjs` vert, `A_ENREGISTRER.md` régénéré
- [ ] Poussée sur `travail` (accord donné)
- [ ] Essai en séance perso sur l'iPad (en mode chrono)

## Médias

- [ ] Vidéos tournées de face, illustrées
- [ ] Noms enregistrés (`football_sprints.wav`, `suicide_drills.wav`, ton suspendu)

## Clôture

- [ ] Docs à jour si une règle a été apprise
- [ ] Fusion dans `main` (avec suppression de cette fiche)

## Notes

- Le chrono avance au temps mural, mais sa fin ne se constate qu'à une image où le corps est vu :
  un suicide drill qui sort un instant du champ ne perd rien, la série se termine au retour.
  D'où la consigne « reste dans l'image » de la fiche.
- Sans barème, ni niveau, ni ligue : la carte d'exercice reste neutre (« Sans analyse de la
  caméra »), et la fiche dit « suis le chrono ».
