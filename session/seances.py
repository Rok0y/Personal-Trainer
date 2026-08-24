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
    planche_laterale_gauche
)

FICHIER_SEANCES_PERSONNALISEES = Path(__file__).with_name("seances_personnalisees.json")
CATALOGUE_EXERCICES = {
    exercice.nom: exercice
    for exercice in (
        curl_biceps_droit, curl_biceps_gauche, elevation_laterale, pompe,
        extension_triceps_au_dessus_de_la_tete, developpe_couche_sol,
        developpe_epaule, crunches, planche, squat, fente_droite,
        fente_gauche, souleve_roumain, planche_laterale_droite,
        planche_laterale_gauche,
    )
}

MATERIEL_EXERCICES = {
    "Curl biceps droit": "Deux haltères",
    "Curl biceps gauche": "Deux haltères",
    "Elevations latérales": "Deux haltères",
    "Pompes": "Aucun matériel",
    "Developpé couché altères": "Deux haltères et un tapis ou banc",
    "Extension Triceps": "Un haltère",
    "Développé épaule": "Deux haltères",
    "Crunches": "Un tapis",
    "Gainage planche": "Un tapis",
    "Squat": "Un haltère et un tapis",
    "Fente droite": "Un haltère et un tapis",
    "Fente gauche": "Un haltère et un tapis",
    "Souleve de terre roumain": "Deux haltères",
    "Gainage planche laterale gauche": "Un tapis",
    "Gainage planche laterale droite": "Un tapis",
}


def materiel_exercice(nom, poids):
    materiel = MATERIEL_EXERCICES.get(nom, "A préciser")
    if not poids or "haltère" not in materiel:
        return materiel
    if materiel.startswith("Deux haltères"):
        return materiel.replace("Deux haltères", f"Deux haltères de {poids} kg", 1)
    return materiel.replace("Un haltère", f"Un haltère de {poids} kg", 1)

Test_exercice = Circuit([
    BlocExercice(
        exercice=planche_laterale_droite,
        poids=0,
        mode=MODE_MAINTIEN,
        nombre_series=1,
        repetitions_par_serie=0,
        duree=300,
        repos_entre_series=30,
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
    "test": seance_test,
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
        ) for bloc in blocs
    ])


def creer_seance(nom):
    """Retourne un circuit neuf, indépendant des séances déjà utilisées."""
    if nom not in CATALOGUE_SEANCES:
        return creer_seance_personnalisee(nom)
    return deepcopy(CATALOGUE_SEANCES[nom])


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
        seance["materiel"] = sorted({
            exercice["materiel"]
            for exercice in seance["exercices"]
            if exercice["materiel"] != "Aucun matériel"
        })
    return resultats