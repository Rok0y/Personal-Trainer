"""Oracle Python du portage de `progression/objectifs.py` et `calibration.py`.

Dernière pièce de l'étape 4, et la seule qui **écrit** : `appliquer_a_blocs`
et `appliquer_a_circuit` modifient les blocs sur place. Le harnais relève donc
les blocs *avant* et *après*, et compare l'état final.

Six choses doivent être visitées, et aucune ne l'est par un historique
ordinaire :

- **les exercices jamais faits**, qui partent du palier de la note d'athlète.
  Ils n'existent que si l'historique ne les mentionne pas du tout, donc les
  séances ne couvrent volontairement qu'une partie du catalogue ;
- **la note relevée**, dont le repère est posé *au milieu* de l'historique,
  comme les ancrages : au bout il ne s'appliquerait à rien de joué, au début
  il serait toujours consommé — c'est entre les deux que le plancher se voit ;
- **la frontière de la note mesurée** (deux tiers des exercices, cinq au
  moins), que des historiques au hasard n'effleurent jamais exactement : des
  historiques construits la visitent des deux côtés ;
- **les cibles manuelles**, dans leurs trois formats stockables (booléen
  d'avant les profils, entier, liste) — un format mal lu fige une cible pour
  toujours, en silence ;
- **les modes incompatibles**, qui font sortir le bloc du pilotage : il garde
  la cible de son fichier ;
- **les deux formes de bloc**, dictionnaire et `BlocExercice`, qui ont chacune
  leur fonction et ne doivent pas diverger.

Usage : `python -m scripts.generer_objectifs`
Sortie : scripts/fixtures_objectifs.jsonl
"""

import copy
import json
import random
from pathlib import Path

import math

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
        }
        for bloc in circuit.exercices
    ]


def _serialiser(objet):
    if isinstance(objet, paliers.Palier):
        return palier_serialisable(objet)
    if isinstance(objet, set):
        return sorted(objet)
    raise TypeError(f"Non serialisable : {type(objet)}")


#: Notes balayées par `niveau_de_depart` : l'échelle entière, plus ce qu'une
#: note n'est pas — absente, hors bornes — et qui doit rendre le palier 1 des
#: deux côtés.
NOTES_BALAYEES = (None, 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)


def _note_au_hasard(tirage, seances):
    """Une note de profil, avec son repère de hausse posé au milieu de l'historique."""
    ids = sorted(s["id"] for s in seances)
    milieu = ids[len(ids) // 2] if ids else 0
    return {
        "declaree": tirage.choice([None, *range(1, 11)]),
        "relevee_apres": tirage.choice([None, None, 0, milieu, max(ids, default=0)]),
    }


def _ligne_prouvant(nom, niveau, tirage):
    """Une ligne d'historique qui prouve exactement `niveau`, toutes séries menées."""
    palier = paliers.palier(nom, niveau)
    maintien = palier.unite == paliers.UNITE_SECONDES
    series = [
        {
            "serie": numero,
            "repetitions": 0 if maintien else palier.cible,
            "poids": palier.poids,
            "duree": palier.cible if maintien else 0,
            "completee": True,
        }
        for numero in range(1, palier.series + 1)
    ]
    return {
        "nom": nom,
        "mode": "maintien" if maintien else "repetitions",
        "poids": palier.poids,
        "series": palier.series,
        "repetitions": sum(x["repetitions"] for x in series),
        "duree": sum(x["duree"] for x in series),
        "series_cibles": palier.series,
        "repetitions_cibles": 0 if maintien else palier.cible,
        "duree_cible": palier.cible if maintien else 0,
        "commentaire": "",
        "entrelace_avec": None,
        "repos_entre_series": 45,
        "repos_apres": 60,
        "ressenti": tirage.choice(["", "facile"]),
        "series_detaillees": series,
    }


def _historique_frontiere(tirage, noms):
    """Un historique dont la note mesurée tombe pile sur la frontière.

    `total` exercices récents, dont `atteints` au départ exact d'une note et
    les autres un cran dessous : selon le tirage, on est juste à deux tiers,
    juste en dessous, ou sous le minimum d'exercices. Le hasard seul n'y tombe
    jamais exactement, et c'est là qu'un `>=` devenu `>` se cache.
    """
    note = tirage.randint(2, 10)
    total = tirage.choice([calibration.EXERCICES_MIN - 1, calibration.EXERCICES_MIN, 6, 9])
    total = min(total, len(noms))
    juste = math.ceil(calibration.PART_EXERCICES * total)
    atteints = max(0, min(total, juste + tirage.choice([-1, 0, 0, 1])))
    choisis = tirage.sample(noms, k=total)
    exercices = []
    for index, nom in enumerate(choisis):
        depart = calibration.niveau_de_depart(nom, note)
        niveau = depart if index < atteints else max(1, depart - 1)
        exercices.append(_ligne_prouvant(nom, niveau, tirage))
    return [{
        "id": 1,
        "date": "01/03/2026 08:00",
        "duree": 1800,
        "statut": "finished",
        "nom": None,
        "exercices": exercices,
    }]


def _table_des_notes():
    """`note_effective` sur toute la grille, hors de tout historique."""
    return [
        {"declaree": d, "mesuree": m, "reponse": calibration.note_effective(d, m)}
        for d in (None, *range(1, 11))
        for m in (None, *range(1, 11))
    ]


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
        # Les inventaires **voyagent avec l'oracle** au lieu d'être redéclarés
        # côté JavaScript : la leçon des paliers, où deux copies ont divergé
        # au premier inventaire ajouté d'un seul côté.
        fichier.write(json.dumps({
            "genre": "entete",
            "inventaires": INVENTAIRES,
            "notes_effectives": _table_des_notes(),
        }, ensure_ascii=False) + "\n")
        fichier.write(json.dumps(_table_des_cibles_manuelles(), ensure_ascii=False) + "\n")
        lignes += 2

        for nom_inventaire, inventaire in INVENTAIRES.items():
            injecter_inventaire(inventaire)

            fichier.write(json.dumps({
                "genre": "departs",
                "inventaire": nom_inventaire,
                "departs": {
                    nom: [calibration.niveau_de_depart(nom, n) for n in NOTES_BALAYEES]
                    for nom in noms
                },
                "notes": list(NOTES_BALAYEES),
            }, ensure_ascii=False) + "\n")
            lignes += 1

            for numero in range(HISTORIQUES):
                # L'historique ne couvre volontairement qu'une partie du
                # catalogue : les exercices absents n'ont jamais été faits, et
                # c'est le seul moyen de visiter le départ par la note. Un
                # historique sur cinq est construit sur la frontière de la
                # note mesurée plutôt que tiré au hasard.
                if numero % 5 == 4:
                    seances = _historique_frontiere(tirage, noms)
                    ancrages = {}
                else:
                    connus = tirage.sample(noms, k=tirage.randint(2, max(2, len(noms) // 2)))
                    seances = tirer_historique(tirage, connus)
                    ancrages = tirer_ancrages(tirage, connus, seances)
                niveaux.recuperer_ancrages = lambda *_, **__: ancrages
                ressenti.recuperer_ancrages = lambda *_, **__: ancrages
                objectifs.recuperer_ancrages = lambda *_, **__: ancrages
                note = _note_au_hasard(tirage, seances)

                objs = objectifs.objectifs_par_exercice(seances, note)
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
                    "note": note,
                    "niveaux_recents": calibration.niveaux_recents(seances, ancrages),
                    "note_mesuree": calibration.note_mesuree(seances, ancrages),
                    "objectifs": objs,
                    "sans_donnees": sorted(sans),
                    "blocs_apres": objectifs.appliquer_a_blocs(
                        copy.deepcopy(blocs_avant), objs
                    ),
                    "circuit_apres": _decrire_circuit(
                        objectifs.appliquer_a_circuit(circuit, objs)
                    ),
                    # `marquer_cibles_manuelles` n'etait compare par rien, et
                    # c'est exactement la ou un defaut s'est cache : un
                    # exercice du temps des tests y etait declare « cible
                    # manuelle », ce qui le figeait pour toujours. Une fonction
                    # qui ecrit une marque **collante** merite d'etre verifiee
                    # comme les autres.
                    "marques": objectifs.marquer_cibles_manuelles(
                        copy.deepcopy(blocs_avant), objs
                    ),
                }, ensure_ascii=False, default=_serialiser) + "\n")
                lignes += 1

    print(f"{len(INVENTAIRES)} inventaires x {HISTORIQUES} historiques")
    print(f"{lignes} lignes (dont les cibles manuelles)")
    print(f"Ecrit dans {DESTINATION.relative_to(RACINE).as_posix()}")


if __name__ == "__main__":
    main()
