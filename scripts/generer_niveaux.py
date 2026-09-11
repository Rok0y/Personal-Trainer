"""Oracle Python du portage de `progression/niveaux.py`.

Un niveau se déduit d'un **historique**, donc le harnais lui en jette des
dizaines tirés au hasard — pas des séances plausibles, des séances *tordues* :
séries incomplètes, modes qui ne correspondent pas au barème, exercices
répétés dans la même séance, ancrages posés au milieu.

Trois axes, et chacun couvre une règle que le module énonce explicitement :

- **le maillon faible** — `performance_realisee` prend un minimum sur les
  séries `completee`, donc des séries inégales doivent apparaître souvent,
  sinon le minimum vaut le maximum et la règle n'est jamais éprouvée ;
- **les ancrages** — ils font table rase de l'historique antérieur *et*
  servent de plancher. Les deux effets se voient sur des séances de part et
  d'autre de `apres_seance_id`, donc l'ancrage est posé au milieu ;
- **l'unité du mode** — un exercice enregistré en `maintien` ne peut pas
  valider un barème en répétitions. Le tirage mélange donc les modes.

Ni la base ni le profil ne sont lus : l'historique et l'inventaire sont
fabriqués ici, sinon l'oracle dépendrait de ce que la machine contient ce
jour-là.

Usage : `python -m scripts.generer_niveaux`
Sortie : scripts/fixtures_niveaux.jsonl, un historique par ligne.
"""

import json
import random
from pathlib import Path

from progression import niveaux, paliers
from scripts.historiques_au_hasard import (
    INVENTAIRES,
    ancrages as tirer_ancrages,
    historique as tirer_historique,
    injecter_inventaire,
    palier_serialisable,
)

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_niveaux.jsonl"

GRAINE = 20260912

#: Historiques tirés. Chacun est rejoué en entier des deux côtés, avec toutes
#: les fonctions du module.
HISTORIQUES = 120

def main():
    tirage = random.Random(GRAINE)
    noms = list(paliers.exercices_suivis())
    lignes = 0

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        for nom_inventaire, inventaire in INVENTAIRES.items():
            injecter_inventaire(inventaire)

            for numero in range(HISTORIQUES):
                seances = tirer_historique(tirage, noms)
                ancrages = tirer_ancrages(tirage, noms, seances)

                # `etats_niveaux` ne prend pas les ancrages en argument : il
                # les lit en base. On detourne cette lecture, sinon l'oracle
                # reclamerait un profil connecte et une vraie base.
                # Cote JavaScript il n'y a pas de base a lire, donc la
                # signature y est explicite — une divergence d'API forcee, du
                # meme genre que le coach injecte du moteur.
                niveaux.recuperer_ancrages = lambda *_, **__: ancrages

                par_exercice = niveaux.niveaux_par_exercice(seances, ancrages)
                fichier.write(json.dumps({
                    "inventaire": nom_inventaire,
                    "numero": numero,
                    "seances": seances,
                    "ancrages": ancrages,
                    "niveaux_par_exercice": par_exercice,
                    "etats_niveaux": niveaux.etats_niveaux(seances),
                    "montees_de_niveau": {
                        str(cle): valeur
                        for cle, valeur in niveaux.montees_de_niveau(
                            seances, ancrages
                        ).items()
                    },
                    # Une ligne au hasard, jugee pour elle-meme : c'est le
                    # point d'entree que `ressenti.py` consommera.
                    "niveau_prouve_par": [
                        niveaux.niveau_prouve_par(exercice)
                        for seance in seances
                        for exercice in seance["exercices"]
                    ],
                }, ensure_ascii=False, default=_serialiser) + "\n")
                lignes += 1

    print(f"{len(INVENTAIRES)} inventaires x {HISTORIQUES} historiques")
    print(f"{lignes} lignes")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


def _serialiser(objet):
    """Les paliers sont des dataclasses : le module partage sait les rendre."""
    if isinstance(objet, paliers.Palier):
        return palier_serialisable(objet)
    raise TypeError(f"Non serialisable : {type(objet)}")


if __name__ == "__main__":
    main()
