"""Oracle Python du portage de `progression/ressenti.py`.

Le module décide **de combien l'objectif bouge**, et toute sa règle tient dans
une table indexée par (réussi, ressenti). Le harnais doit donc visiter les
deux axes de cette table, ce qu'un historique ordinaire ne fait pas :

- **le franchissement du seuil de réussite**, qui fait basculer la moitié de
  la table. Les séries sont tirées *autour* de la cible, des deux côtés ;
- **les cinq ressentis**, y compris les combinaisons que l'interface ne
  propose pas (« facile » après un échec) : l'historique peut en contenir,
  puisque la page d'historique permet de répondre a posteriori sans cette
  contrainte, et la règle est qu'elles retombent sur l'absence de réponse ;
- **les séances abandonnées**, écartées par `evaluation` mais conservées par
  `jugements_par_seance` : les deux chemins doivent être visités.

L'historique vient du générateur partagé, qui prend **une cible sur deux sur
le barème réel** — tirée entièrement au hasard, elle ne correspondrait à aucun
palier, `niveau_pour` rendrait None et `juger` abandonnerait la ligne.

Usage : `python -m scripts.generer_ressenti`
Sortie : scripts/fixtures_ressenti.jsonl
"""

import json
import random
from pathlib import Path

from progression import niveaux, paliers, ressenti
from scripts.historiques_au_hasard import (
    INVENTAIRES,
    ancrages as tirer_ancrages,
    historique as tirer_historique,
    injecter_inventaire,
    palier_serialisable,
)

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_ressenti.jsonl"

GRAINE = 20260913
HISTORIQUES = 120


def _serialiser(objet):
    if isinstance(objet, paliers.Palier):
        return palier_serialisable(objet)
    raise TypeError(f"Non serialisable : {type(objet)}")


def main():
    tirage = random.Random(GRAINE)
    noms = list(paliers.exercices_suivis())
    lignes = 0

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        # La table d'ajustement est relevée telle quelle : c'est **toute** la
        # règle de progression, et la comparer explicitement vaut mieux que
        # d'espérer qu'un historique la traverse entièrement.
        fichier.write(json.dumps({
            "genre": "table",
            "echelle": list(ressenti.ECHELLE),
            "ajustements": [
                {
                    "reussi": reussi,
                    "ressenti": valeur,
                    "reponse": ressenti.ajustement(reussi, valeur),
                }
                for reussi in (True, False)
                for valeur in (None, *ressenti.ECHELLE)
            ],
            "est_valide": [
                {"valeur": v, "reponse": ressenti.est_valide(v)}
                for v in (*ressenti.ECHELLE, "", None, "autre")
            ],
        }, ensure_ascii=False) + "\n")
        lignes += 1

        for nom_inventaire, inventaire in INVENTAIRES.items():
            injecter_inventaire(inventaire)

            for numero in range(HISTORIQUES):
                seances = tirer_historique(tirage, noms)
                ancrages = tirer_ancrages(tirage, noms, seances)
                niveaux_calcules = niveaux.niveaux_par_exercice(seances, ancrages)

                fichier.write(json.dumps({
                    "genre": "historique",
                    "inventaire": nom_inventaire,
                    "numero": numero,
                    "seances": seances,
                    "ancrages": ancrages,
                    "evaluation": ressenti.evaluation(
                        seances, ancrages, niveaux_calcules
                    ),
                    "jugements_par_seance": {
                        str(cle): valeur
                        for cle, valeur in ressenti.jugements_par_seance(
                            seances
                        ).items()
                    },
                    # Ligne par ligne : c'est le point d'entree de tout le
                    # reste, et un ecart y serait noye dans les agregats.
                    "juger": [
                        ressenti.juger(exercice)
                        for seance in seances
                        for exercice in seance["exercices"]
                    ],
                }, ensure_ascii=False, default=_serialiser) + "\n")
                lignes += 1

    print(f"{len(INVENTAIRES)} inventaires x {HISTORIQUES} historiques")
    print(f"{lignes} lignes (dont la table d'ajustement)")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
