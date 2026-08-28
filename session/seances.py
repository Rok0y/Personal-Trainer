from copy import deepcopy
import json
from pathlib import Path

from session.circuit import Circuit, BlocExercice,MODE_CHRONO,MODE_MAINTIEN,MODE_REPETITIONS,MODE_AMRAP

from mouvements.exercices import (
    curl_biceps_droit,
    curl_biceps_gauche,
    elevation_laterale,
    pompe,
    extension_triceps_au_dessus_de_la_tete,
    developpe_couche_sol,
    developpe_epaule,
    crunches,
    planche,
    squat,
    fente_droite,
    fente_gauche,
    souleve_roumain,
    planche_laterale_droite,
    planche_laterale_gauche,
    rowing_unilateral_droit,
    rowing_unilateral_gauche,
    rowing_penche,
    oiseau,
)

FICHIER_SEANCES_PERSONNALISEES = Path(__file__).with_name("seances_personnalisees.json")
CATALOGUE_EXERCICES = {
    exercice.nom: exercice
    for exercice in (
        curl_biceps_droit, curl_biceps_gauche, elevation_laterale, pompe,
        extension_triceps_au_dessus_de_la_tete, developpe_couche_sol,
        developpe_epaule, crunches, planche, squat, fente_droite,
        fente_gauche, souleve_roumain, planche_laterale_droite,
        planche_laterale_gauche, rowing_unilateral_droit,rowing_unilateral_gauche, rowing_penche, oiseau,
    )
}

MATERIEL_EXERCICES = {
    "Curl biceps droit": "Un haltère",
    "Curl biceps gauche": "Un haltère",
    "Elevations latérales": "Deux haltères",
    "Pompes": "",
    "Developpé couché altères": "Deux haltères et un tapis",
    "Extension Triceps": "Un haltère",
    "Développé épaule": "Deux haltères",
    "Crunches": "Un tapis",
    "Gainage planche": "Un tapis",
    "Squat": "Deux haltères et un tapis",
    "Fente droite": "Deux haltères et un tapis",
    "Fente gauche": "Deux haltère et un tapis",
    "Souleve de terre roumain": "Deux haltères",
    "Gainage planche laterale gauche": "Un tapis",
    "Gainage planche laterale droite": "Un tapis",
    "Rowing unilateral droit": "Un haltère et une chaise",
    "Rowing unilateral gauche": "Un haltère et une chaise",
    "Rowing penché": "Deux haltères",
    "Oiseau": "Deux haltères"
}


def materiel_exercice(nom, poids):
    materiel = MATERIEL_EXERCICES.get(nom, "A préciser")
    if not poids or "haltère" not in materiel:
        return materiel
    if materiel.startswith("Deux haltères"):
        return materiel.replace("Deux haltères", f"Deux haltères de {poids} kg", 1)
    return materiel.replace("Un haltère", f"Un haltère de {poids} kg", 1)


def formater_materiel(materiels):
    """Regroupe le matériel d'une séance dans une phrase lisible."""
    elements = set()
    poids_deux_haltere = []
    poids_un_haltere = []

    for materiel in materiels:
        if not materiel or materiel == "Aucun matériel":
            continue
        if "tapis" in materiel:
            elements.add("Un tapis")
        if "Deux haltères" in materiel:
            poids = materiel.removeprefix("Deux haltères de ").split(" et un tapis")[0]
            if poids != materiel:
                if poids not in poids_deux_haltere:
                    poids_deux_haltere.append(poids)
            else:
                elements.add("Deux haltères")
        elif "Deux haltère" in materiel:
            elements.add("Deux haltères")
        if "Un haltère" in materiel:
            poids = materiel.removeprefix("Un haltère de ").split(" et un tapis")[0]
            if poids != materiel:
                if poids not in poids_un_haltere:
                    poids_un_haltere.append(poids)
            else:
                elements.add("Un haltère")

    def poids_formates(poids):
        return ", ".join(poids[:-1]) + " et " + poids[-1] if len(poids) > 1 else poids[0]

    if poids_deux_haltere:
        elements.add(f"Deux haltères de {poids_formates(poids_deux_haltere)}")
    if poids_un_haltere:
        elements.add(f"Un haltère de {poids_formates(poids_un_haltere)}")

    ordre = {"Un tapis": 0, "Deux haltères": 1, "Un haltère": 2}
    elements_ordonnes = sorted(
        elements,
        key=lambda element: (ordre.get(element, 3), element),
    )
    elements_ordonnes = [
        element if index == 0 else element[0].lower() + element[1:]
        for index, element in enumerate(elements_ordonnes)
    ]
    if len(elements_ordonnes) <= 1:
        return elements_ordonnes[0] if elements_ordonnes else ""
    if len(elements_ordonnes) == 2:
        return " et ".join(elements_ordonnes)
    return ", ".join(elements_ordonnes[:-1]) + ", et " + elements_ordonnes[-1]

Test_exercice = Circuit([
    BlocExercice(
        exercice=rowing_unilateral_droit,
        poids=0,
        mode=MODE_REPETITIONS,
        nombre_series=1,
        repetitions_par_serie=10,
        duree=0,
        repos_entre_series=20,
        repos_apres=10
    )
])

seance_bras = Circuit([
    BlocExercice(
        exercice=curl_biceps_droit,
        poids=8,
        mode=MODE_REPETITIONS,
        nombre_series=2,
        repetitions_par_serie=5,
        duree=0,
        repos_entre_series=5,
        repos_apres=10
    ),
    BlocExercice(
        exercice=curl_biceps_gauche,
        poids=8,
        mode=MODE_REPETITIONS,
        nombre_series=1,
        repetitions_par_serie=5,
        duree=0,
        repos_entre_series=30,
        repos_apres=0
    )
])

seance_test = Circuit([
    BlocExercice(
        exercice=curl_biceps_droit,
        poids=8,
        mode=MODE_REPETITIONS,
        nombre_series=2,
        repetitions_par_serie=5,
        duree=0,
        repos_entre_series=15,
        repos_apres=30,
    ),
    BlocExercice(
        exercice=planche,
        poids=0,
        mode=MODE_MAINTIEN,
        nombre_series=2,
        repetitions_par_serie=None,
        duree=10,
        repos_entre_series=15,
        repos_apres=30,
    ),
    BlocExercice(
        exercice=curl_biceps_gauche,
        poids=8,
        mode=MODE_AMRAP,
        nombre_series=2,
        repetitions_par_serie=0,
        duree=10,
        repos_entre_series=15,
        repos_apres=30,
    ),
    BlocExercice(
        exercice=elevation_laterale,
        poids=5,
        mode=MODE_REPETITIONS,
        nombre_series=1,
        repetitions_par_serie=5,
        duree=0,
        repos_entre_series=5,
        repos_apres=30,
    ),
    BlocExercice(
        exercice=pompe,
        poids=0,
        mode=MODE_REPETITIONS,
        nombre_series=1,
        repetitions_par_serie=5,
        duree=0,
        repos_entre_series=5,
        repos_apres=30,
    ),
    BlocExercice(
        exercice=extension_triceps_au_dessus_de_la_tete,
        poids=14,
        mode=MODE_REPETITIONS,
        nombre_series=1,
        repetitions_par_serie=5,
        duree=0,
        repos_entre_series=5,
        repos_apres=30,
    ),
    BlocExercice(
        exercice=developpe_couche_sol,
        poids=10,
        mode=MODE_REPETITIONS,
        nombre_series=1,
        repetitions_par_serie=5,
        duree=0,
        repos_entre_series=5,
        repos_apres=0
    )
])

seance_Upper_Push = Circuit([
    BlocExercice(
        exercice=developpe_couche_sol,
        poids=10,
        mode=MODE_REPETITIONS,
        nombre_series=4,
        repetitions_par_serie=12,
        duree=0,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=pompe,
        poids=0,
        mode=MODE_REPETITIONS,
        nombre_series=4,
        repetitions_par_serie=10,
        duree=0,
        repos_entre_series=60,
        repos_apres=90
    ),
    BlocExercice(
        exercice=developpe_epaule,
        poids=8,
        mode=MODE_REPETITIONS,
        nombre_series=3,
        repetitions_par_serie=12,
        duree=0,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=elevation_laterale,
        poids=5,
        mode=MODE_REPETITIONS,
        nombre_series=3,
        repetitions_par_serie=11,
        duree=0,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=extension_triceps_au_dessus_de_la_tete,
        poids=14,
        mode=MODE_REPETITIONS,
        nombre_series=3,
        repetitions_par_serie=10,
        duree=0,
        repos_entre_series=60,
        repos_apres=0
    ),
])

seance_jambes_abdos = Circuit([
    BlocExercice(
        exercice=squat,
        poids=10,
        mode=MODE_REPETITIONS,
        nombre_series=4,
        repetitions_par_serie=10,
        duree=0,
        repos_entre_series=50,
        repos_apres=90
    ),
    BlocExercice(
        exercice=fente_droite,
        poids=10,
        mode=MODE_REPETITIONS,
        nombre_series=4,
        repetitions_par_serie=10,
        duree=0,
        repos_entre_series=45,
        repos_apres=90
    ),    
    BlocExercice(
        exercice=fente_gauche,
        poids=10,
        mode=MODE_REPETITIONS,
        nombre_series=4,
        repetitions_par_serie=10,
        duree=0,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=souleve_roumain,
        poids=10,
        mode=MODE_REPETITIONS,
        nombre_series=4,
        repetitions_par_serie=8,
        duree=0,
        repos_entre_series=60,
        repos_apres=90
    ),
    BlocExercice(
        exercice=crunches,
        poids=0,
        mode=MODE_REPETITIONS,
        nombre_series=3,
        repetitions_par_serie=17,
        duree=0,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=planche,
        poids=0,
        mode=MODE_MAINTIEN,
        nombre_series=3,
        repetitions_par_serie=0,
        duree=40,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=planche_laterale_droite,
        poids=0,
        mode=MODE_MAINTIEN,
        nombre_series=1,
        repetitions_par_serie=0,
        duree=35,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=planche_laterale_gauche,
        poids=0,
        mode=MODE_MAINTIEN,
        nombre_series=1,
        repetitions_par_serie=0,
        duree=35,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=planche_laterale_droite,
        poids=0,
        mode=MODE_MAINTIEN,
        nombre_series=1,
        repetitions_par_serie=0,
        duree=35,
        repos_entre_series=45,
        repos_apres=90
    ),
    BlocExercice(
        exercice=planche_laterale_gauche,
        poids=0,
        mode=MODE_MAINTIEN,
        nombre_series=1,
        repetitions_par_serie=0,
        duree=35,
        repos_entre_series=45,
        repos_apres=90
    ),
])


CATALOGUE_SEANCES = {
    "bras": seance_bras,
    "test": Test_exercice,
    "upper_push": seance_Upper_Push,
    "jambes_abdos": seance_jambes_abdos,
}


def catalogue_exercices():
    return {
        nom: {
            "nom": exercice.nom,
            "description": exercice.description,
            "materiel": materiel_exercice(nom, 0),
        }
        for nom, exercice in CATALOGUE_EXERCICES.items()
    }


def _lire_seances_personnalisees():
    if not FICHIER_SEANCES_PERSONNALISEES.exists():
        return {}
    with FICHIER_SEANCES_PERSONNALISEES.open(encoding="utf-8") as fichier:
        return json.load(fichier)


def enregistrer_seance_personnalisee(nom, blocs):
    donnees = _lire_seances_personnalisees()
    donnees[nom] = blocs
    with FICHIER_SEANCES_PERSONNALISEES.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)


def exporter_blocs(circuit):
    """Produit une définition JSON indépendante des objets Python du catalogue."""
    return [
        {
            "exercice": bloc.exercice.nom,
            "poids": bloc.poids,
            "mode": bloc.mode,
            "series": bloc.nombre_series,
            "repetitions": bloc.repetitions_par_serie,
            "duree": bloc.duree,
            "repos_entre_series": bloc.repos_entre_series,
            "repos_apres": bloc.repos_apres,
            "commentaire": bloc.commentaire,
        }
        for bloc in circuit.exercices
    ]


def enregistrer_configuration_seance(nom, circuit):
    """Persist the current targets, including overrides for built-in workouts."""
    if nom != "test":
        enregistrer_seance_personnalisee(nom, exporter_blocs(circuit))


def supprimer_seance_personnalisee(nom):
    donnees = _lire_seances_personnalisees()
    if nom not in donnees:
        raise KeyError(f"Séance personnalisée inconnue : {nom}")
    del donnees[nom]
    with FICHIER_SEANCES_PERSONNALISEES.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)


def creer_seance_personnalisee(nom):
    blocs = _lire_seances_personnalisees().get(nom)
    if blocs is None:
        raise KeyError(f"Séance inconnue : {nom}")
    return Circuit([
        BlocExercice(
            exercice=CATALOGUE_EXERCICES[bloc["exercice"]],
            poids=bloc["poids"],
            mode=bloc["mode"],
            nombre_series=bloc["series"],
            repetitions_par_serie=bloc.get("repetitions", 0),
            duree=bloc.get("duree", 0),
            repos_entre_series=bloc["repos_entre_series"],
            repos_apres=bloc["repos_apres"],
            commentaire=bloc.get("commentaire", ""),
        ) for bloc in blocs
    ])


def creer_seance(nom):
    """Retourne un circuit neuf, indépendant des séances déjà utilisées."""
    if nom not in CATALOGUE_SEANCES or nom in _lire_seances_personnalisees():
        return creer_seance_personnalisee(nom)
    return deepcopy(CATALOGUE_SEANCES[nom])


def creer_seance_test(nom_exercice, mode):
    if nom_exercice not in CATALOGUE_EXERCICES:
        raise KeyError("Exercice inconnu")
    if mode not in (MODE_REPETITIONS, MODE_MAINTIEN, MODE_CHRONO, MODE_AMRAP):
        raise ValueError("Mode inconnu")

    bloc = deepcopy(Test_exercice.exercices[0])
    bloc.exercice = CATALOGUE_EXERCICES[nom_exercice]
    bloc.mode = mode
    if mode == MODE_REPETITIONS:
        bloc.repetitions_par_serie = 10
        bloc.duree = 0
    else:
        bloc.repetitions_par_serie = 0
        bloc.duree = 10
    return Circuit([bloc])


def catalogue():
    resultats = {
        nom: {
            "nom": nom,
            "exercices": circuit.exporter_configuration(),
            "nombre_exercices": len(circuit.exercices),
        }
        for nom, circuit in CATALOGUE_SEANCES.items()
    }
    for nom, blocs in _lire_seances_personnalisees().items():
        exercices = [
            {
                **bloc,
                "nom": bloc["exercice"],
                "materiel": MATERIEL_EXERCICES.get(
                    bloc["exercice"],
                    "A préciser",
                ),
            }
            for bloc in blocs
        ]
        resultats[nom] = {
            "nom": nom,
            "nombre_exercices": len(blocs),
            "exercices": exercices,
            "materiel": sorted({exercice["materiel"] for exercice in exercices}),
        }
    for seance in resultats.values():
        for exercice in seance["exercices"]:
            exercice["materiel"] = materiel_exercice(
                exercice["nom"],
                exercice.get("poids", 0),
            )
        seance["materiel"] = formater_materiel(
            exercice["materiel"] for exercice in seance["exercices"]
        )
    return resultats
