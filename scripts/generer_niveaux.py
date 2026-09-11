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

import core.materiel as materiel
from progression import niveaux, paliers

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_niveaux.jsonl"

GRAINE = 20260912

#: Historiques tirés. Chacun est rejoué en entier des deux côtés, avec toutes
#: les fonctions du module.
HISTORIQUES = 120

MODES = ("repetitions", "maintien", "chrono", "amrap", "echauffement")

#: Inventaires balayés, comme pour le barème : l'échelle de poids décale les
#: niveaux, donc un port juste avec des haltères complets peut être faux pour
#: un débutant.
INVENTAIRES = {
    "non_declare": None,
    "debutant": {"halteres": {2: 2, 3: 2, 4: 2}, "accessoires": ["tapis"]},
    "complet": {"halteres": {p: 2 for p in materiel.POIDS_REFERENCE},
                "accessoires": ["tapis", "chaise"]},
}


def _exercice(tirage, noms):
    nom = tirage.choice(noms)
    spec = paliers.SPECS.get(nom)
    mode = tirage.choice(MODES)
    maintien = mode in ("maintien", "chrono")
    cible = tirage.randint(5, 40) if maintien else tirage.randint(3, 25)
    nb_series = tirage.randint(1, 6)

    series = []
    for numero in range(1, nb_series + 1):
        # Des séries **inégales**, et parfois inachevées : c'est le seul moyen
        # d'éprouver la règle du maillon faible. Des séries identiques et
        # toutes complètes rendraient `min` équivalent à `max`.
        realise = max(0, cible + tirage.randint(-5, 3))
        series.append({
            "serie": numero,
            "repetitions": 0 if maintien else realise,
            "poids": tirage.choice([0, 2, 4, 5, 6, 8, 10, 14, 18]),
            "duree": realise if maintien else 0,
            "completee": tirage.random() > 0.25,
        })

    return {
        "nom": nom,
        "mode": mode,
        "poids": series[0]["poids"],
        "series": nb_series,
        "repetitions": sum(s["repetitions"] for s in series),
        "duree": sum(s["duree"] for s in series),
        "series_cibles": nb_series,
        "repetitions_cibles": 0 if maintien else cible,
        "duree_cible": cible if maintien else 0,
        "commentaire": "",
        "entrelace_avec": None,
        "repos_entre_series": 45,
        "repos_apres": 60,
        "ressenti": tirage.choice(["", "ok", "facile", "trop_dur", "trop_facile"]),
        "series_detaillees": series,
    }


def _historique(tirage, noms):
    """Un historique au format de `recuperer_historique` : le plus récent en tête."""
    nombre = tirage.randint(1, 12)
    seances = []
    for index in range(nombre, 0, -1):
        seances.append({
            "id": index,
            "date": f"{index:02d}/03/2026 08:00",
            "duree": tirage.randint(300, 3600),
            "statut": tirage.choice(["finished", "finished", "abandoned"]),
            "nom": tirage.choice(["bras", "Upper Pull", None]),
            # Un exercice peut apparaître deux fois dans la même séance : la
            # meilleure ligne l'emporte, jamais leur somme.
            "exercices": [_exercice(tirage, noms) for _ in range(tirage.randint(1, 4))],
        })
    return seances


def _ancrages(tirage, noms, seances):
    """Des ancrages posés **au milieu** de l'historique.

    Posés à la fin, ils ne feraient jamais table rase de rien ; posés au
    début, ils ne serviraient jamais de plancher. C'est entre les deux que
    leurs deux effets se voient.
    """
    if tirage.random() < 0.3:
        return {}
    ids = sorted(s["id"] for s in seances)
    milieu = ids[len(ids) // 2] if ids else 0
    return {
        nom: {
            "niveau": tirage.randint(1, 40),
            "date": "15/03/2026 08:00",
            "apres_seance_id": tirage.choice([0, milieu, max(ids, default=0)]),
            "raison": "harnais",
        }
        for nom in tirage.sample(noms, k=min(3, len(noms)))
    }


def main():
    tirage = random.Random(GRAINE)
    noms = list(paliers.exercices_suivis())
    lignes = 0

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        for nom_inventaire, inventaire in INVENTAIRES.items():
            materiel.materiel_du_profil = (
                lambda _=None, brut=inventaire: materiel.normaliser(brut)
            )

            for numero in range(HISTORIQUES):
                seances = _historique(tirage, noms)
                ancrages = _ancrages(tirage, noms, seances)

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
    """Les paliers sont des dataclasses : on les rend sous la forme que le JS produit."""
    if isinstance(objet, paliers.Palier):
        return {
            "niveau": objet.niveau,
            "poids": objet.poids,
            "series": objet.series,
            "cible": objet.cible,
            "unite": objet.unite,
        }
    raise TypeError(f"Non serialisable : {type(objet)}")


if __name__ == "__main__":
    main()
