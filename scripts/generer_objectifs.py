"""Oracle Python du portage de `progression/objectifs.py` et `calibration.py`.

Dernière pièce de l'étape 4, et la seule qui **écrit** : `appliquer_a_blocs`
et `appliquer_a_circuit` modifient les blocs sur place. Le harnais relève donc
les blocs *avant* et *après*, et compare l'état final.

Quatre choses doivent être visitées, et aucune ne l'est par un historique
ordinaire :

- **les exercices sans données**, qui déclenchent un test de calibration
  plutôt qu'un objectif. Ils n'existent que si l'historique ne les mentionne
  pas du tout, donc les séances ne couvrent volontairement qu'une partie du
  catalogue ;
- **les cibles manuelles**, dans leurs trois formats stockables (booléen
  d'avant les profils, entier, liste) — un format mal lu fige une cible pour
  toujours, en silence ;
- **les modes incompatibles**, qui font sortir le bloc du pilotage sans le
  marquer à tester ;
- **les deux formes de bloc**, dictionnaire et `BlocExercice`, qui ont chacune
  leur fonction et ne doivent pas diverger.

Usage : `python -m scripts.generer_objectifs`
Sortie : scripts/fixtures_objectifs.jsonl
"""

import copy
import json
import random
from pathlib import Path

from progression import calibration, niveaux, objectifs, paliers, ressenti
from scripts.historiques_au_hasard import (
    INVENTAIRES,
    ancrages as tirer_ancrages,
    historique as tirer_historique,
    injecter_inventaire,
    palier_serialisable,
)
from session.circuit import BlocExercice, Circuit, Exercice

RACINE = Path(__file__).resolve().parent.parent
DESTINATION = Path(__file__).parent / "fixtures_objectifs.jsonl"

GRAINE = 20260914
HISTORIQUES = 90

#: Le profil qui joue. `est_cible_manuelle` le lit via `identifiant_connecte`,
#: donc sans profil aucun bloc ne serait jamais figé — et le harnais
#: comparerait un Python qui ignore les marques à un JavaScript qui les
#: applique.
PROFIL = 1

MODES = ("repetitions", "maintien", "chrono", "amrap", "echauffement")

#: Les trois formats stockables d'une cible manuelle, plus des valeurs qu'on
#: ne sait pas lire : celles-ci doivent valoir « personne ».
CIBLES_MANUELLES = (None, False, True, 1, 2, [1], [2], [1, 3], "oui", {})


def _bloc(tirage, noms):
    nom = tirage.choice(noms)
    unite_attendue = paliers.unite(nom)
    # Le mode correspond à l'unité deux fois sur trois : le reste éprouve le
    # cas « le moteur ne pilote pas ce bloc », qui laisse la cible du fichier
    # au lieu de marquer un test.
    if tirage.random() < 0.66:
        mode = "maintien" if unite_attendue == paliers.UNITE_SECONDES else "repetitions"
    else:
        mode = tirage.choice(MODES)
    return {
        "exercice": nom,
        "mode": mode,
        "poids": tirage.choice([0, 4, 8, 12]),
        "series": tirage.randint(1, 5),
        "repetitions": tirage.randint(5, 20),
        "duree": tirage.randint(20, 60),
        "repos_entre_series": 45,
        "repos_apres": 60,
        "commentaire": "",
        "cible_manuelle": tirage.choice(CIBLES_MANUELLES),
    }


def _circuit_depuis(blocs):
    """Un `Circuit` équivalent aux blocs, pour comparer les deux chemins."""
    return Circuit([
        BlocExercice(
            exercice=Exercice(nom=bloc["exercice"], detection=_detection_muette),
            poids=bloc["poids"],
            mode=bloc["mode"],
            nombre_series=bloc["series"],
            repetitions_par_serie=bloc["repetitions"],
            duree=bloc["duree"],
            repos_entre_series=bloc["repos_entre_series"],
            repos_apres=bloc["repos_apres"],
            commentaire=bloc["commentaire"],
            cible_manuelle=bloc["cible_manuelle"],
        )
        for bloc in blocs
    ])


def _detection_muette(corps):
    """Le circuit exige une détection pour certains modes ; elle ne sert pas ici."""
    return "milieu"


def _decrire_circuit(circuit):
    return [
        {
            "exercice": bloc.exercice.nom,
            "mode": bloc.mode,
            "poids": bloc.poids,
            "nombre_series": bloc.nombre_series,
            "repetitions_par_serie": bloc.repetitions_par_serie,
            "duree": bloc.duree,
            "test_max": getattr(bloc, "test_max", False),
            "avant_test": getattr(bloc, "avant_test", None),
        }
        for bloc in circuit.exercices
    ]


def _serialiser(objet):
    if isinstance(objet, paliers.Palier):
        return palier_serialisable(objet)
    if isinstance(objet, set):
        return sorted(objet)
    raise TypeError(f"Non serialisable : {type(objet)}")


def _table_des_cibles_manuelles():
    """Les quatre fonctions de cible manuelle, vérifiées hors de tout historique.

    Elles ne dépendent d'aucune séance, et un format mal lu fige une cible en
    silence : les comparer explicitement vaut mieux qu'espérer qu'un tirage
    visite les dix formats.
    """
    return {
        "genre": "cible_manuelle",
        "profils": [
            {"valeur": v, "reponse": sorted(objectifs.profils_cible_manuelle(v))}
            for v in CIBLES_MANUELLES
        ],
        "est": [
            {
                "valeur": v,
                "profil": p,
                "reponse": objectifs.est_cible_manuelle(
                    {"cible_manuelle": v}, utilisateur_id=p
                ),
            }
            for v in CIBLES_MANUELLES
            for p in (1, 2, 3)
        ],
        "definir": [
            {
                "valeur": v,
                "manuelle": m,
                "profil": p,
                "reponse": objectifs.definir_cible_manuelle(v, m, utilisateur_id=p),
            }
            for v in CIBLES_MANUELLES
            for m in (True, False)
            for p in (1, 2)
        ],
        "fusionner": [
            {
                "entrante": e,
                "stockee": s,
                "profil": p,
                "reponse": objectifs.fusionner_cible_manuelle(e, s, utilisateur_id=p),
            }
            for e in (None, True, [1], [2])
            for s in (None, True, [1], [1, 3])
            for p in (1, 2)
        ],
        # `enteriner_cibles_manuelles` **écrit** sur les blocs, et ce qu'elle
        # efface est une marque collante : l'oublier fige une cible pour
        # toujours, l'effacer trop large emporte celle d'un autre profil. Les
        # deux se voient à l'écran des mois plus tard, ou jamais. On relève
        # donc les blocs après l'appel, pas seulement sa valeur de retour.
        "enteriner": [
            {
                "blocs": [{"cible_manuelle": v} for v in CIBLES_MANUELLES],
                "profil": p,
                "reponse": _enteriner_releve(
                    [{"cible_manuelle": v} for v in CIBLES_MANUELLES], p
                ),
            }
            for p in (1, 2, 3)
        ],
    }


def _enteriner_releve(blocs, profil):
    """Joue l'entérinement et rend ce qu'il a laissé, valeur de retour comprise."""
    leve = objectifs.enteriner_cibles_manuelles(blocs, utilisateur_id=profil)
    return {"leve": leve, "apres": [b.get("cible_manuelle") for b in blocs]}


def main():
    tirage = random.Random(GRAINE)
    noms = list(paliers.exercices_suivis())
    lignes = 0

    # Deux lectures implicites à détourner. Les **ancrages** : ni
    # `objectifs_par_exercice` ni `evaluation` ne les prennent en argument, ils
    # les lisent en base. Le **profil connecté** : `est_cible_manuelle` en
    # dépend, et sans lui aucune marque ne s'appliquerait côté Python alors
    # qu'elles s'appliquent côté JavaScript, qui reçoit le profil en argument.
    objectifs.identifiant_connecte = lambda: PROFIL

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        fichier.write(json.dumps(_table_des_cibles_manuelles(), ensure_ascii=False) + "\n")
        lignes += 1

        for nom_inventaire, inventaire in INVENTAIRES.items():
            injecter_inventaire(inventaire)

            for numero in range(HISTORIQUES):
                # L'historique ne couvre volontairement qu'une partie du
                # catalogue : les exercices absents sont « sans données », donc
                # à calibrer, et c'est le seul moyen de visiter ce chemin.
                connus = tirage.sample(noms, k=tirage.randint(2, max(2, len(noms) // 2)))
                seances = tirer_historique(tirage, connus)
                ancrages = tirer_ancrages(tirage, connus, seances)
                niveaux.recuperer_ancrages = lambda *_, **__: ancrages
                ressenti.recuperer_ancrages = lambda *_, **__: ancrages

                objs = objectifs.objectifs_par_exercice(seances)
                sans = objectifs.exercices_sans_donnees(seances)

                blocs_avant = [_bloc(tirage, noms) for _ in range(tirage.randint(2, 6))]
                circuit = _circuit_depuis(blocs_avant)

                fichier.write(json.dumps({
                    "genre": "historique",
                    "inventaire": nom_inventaire,
                    "numero": numero,
                    "seances": seances,
                    "ancrages": ancrages,
                    "blocs_avant": blocs_avant,
                    "objectifs": objs,
                    "sans_donnees": sorted(sans),
                    "charges_de_test": {
                        nom: calibration.charge_de_test(nom) for nom in noms
                    },
                    "niveaux_estimes": [
                        {
                            "exercice": nom,
                            "poids": poids,
                            "maximum": maximum,
                            "reponse": calibration.niveau_estime(nom, poids, maximum),
                        }
                        for nom in tirage.sample(noms, k=4)
                        for poids, maximum in ((0, tirage.randint(0, 40)),
                                               (8, tirage.randint(0, 40)))
                    ],
                    "blocs_apres": objectifs.appliquer_a_blocs(
                        copy.deepcopy(blocs_avant), objs, sans
                    ),
                    "circuit_apres": _decrire_circuit(
                        objectifs.appliquer_a_circuit(circuit, objs, sans)
                    ),
                    # `marquer_cibles_manuelles` n'etait compare par rien, et
                    # c'est exactement la ou un defaut s'est cache : un
                    # exercice a calibrer y etait declare « cible manuelle »,
                    # ce qui le figeait pour toujours et empechait son test de
                    # se declencher. Une fonction qui ecrit une marque
                    # **collante** merite d'etre verifiee comme les autres.
                    "marques": objectifs.marquer_cibles_manuelles(
                        copy.deepcopy(blocs_avant), objs, sans
                    ),
                }, ensure_ascii=False, default=_serialiser) + "\n")
                lignes += 1

    print(f"{len(INVENTAIRES)} inventaires x {HISTORIQUES} historiques")
    print(f"{lignes} lignes (dont les cibles manuelles)")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
