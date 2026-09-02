import json
from copy import deepcopy
from pathlib import Path

from mouvements.echauffements import (
    elevations_laterales_a_vide,
    jumping_jacks,
    pompes_lentes,
    rotation_cou,
    rotation_coudes,
    rotation_epaules,
    rotation_poignets,
)
from mouvements.exercices import (
    crunches,
    curl_biceps_droit,
    curl_biceps_gauche,
    developpe_couche_sol,
    developpe_epaule,
    elevation_laterale,
    extension_triceps_au_dessus_de_la_tete,
    fente_droite,
    fente_gauche,
    oiseau,
    planche,
    planche_laterale_droite,
    planche_laterale_gauche,
    pompe,
    rowing_penche,
    rowing_unilateral_droit,
    rowing_unilateral_gauche,
    souleve_roumain,
    squat,
)
from session.circuit import (
    MODE_AMRAP,
    MODE_CHRONO,
    MODE_ECHAUFFEMENT,
    MODE_MAINTIEN,
    MODE_REPETITIONS,
    MODES_AVEC_DETECTION_OBLIGATOIRE,
    MODES_CONNUS,
    BlocExercice,
    Circuit,
)

FICHIER_SEANCES_PERSONNALISEES = Path(__file__).with_name("seances_personnalisees.json")
CATALOGUE_EXERCICES = {
    exercice.nom: exercice
    for exercice in (
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
    "Fente gauche": "Deux haltères et un tapis",
    "Souleve de terre roumain": "Deux haltères",
    "Gainage planche laterale gauche": "Un tapis",
    "Gainage planche laterale droite": "Un tapis",
    "Rowing unilateral droit": "Un haltère et une chaise",
    "Rowing unilateral gauche": "Un haltère et une chaise",
    "Rowing penché": "Deux haltères",
    "Oiseau": "Deux haltères",
}

CATALOGUE_ECHAUFFEMENTS = {
    mouvement.nom: mouvement
    for mouvement in (
        rotation_cou,
        rotation_epaules,
        rotation_coudes,
        rotation_poignets,
        elevations_laterales_a_vide,
        pompes_lentes,
        jumping_jacks,
    )
}

# Un échauffement se fait à mains nues : l'entrée vide évite le « A préciser »
# que materiel_exercice colle aux noms absents, et qui se retrouverait dans la
# phrase de matériel de l'accueil.
MATERIEL_EXERCICES.update({nom: "" for nom in CATALOGUE_ECHAUFFEMENTS})


def catalogue_mouvements():
    """Exercices + échauffements : la table de validation des séances.

    Volontairement distincte de CATALOGUE_EXERCICES, qui reste la liste des
    exercices comptabilisés (records, matériel, statistiques) : les deux
    catalogues sont fusionnés pour valider une séance, jamais pour l'afficher.
    """
    return {**CATALOGUE_EXERCICES, **CATALOGUE_ECHAUFFEMENTS}


def materiel_exercice(nom, poids):
    materiel = MATERIEL_EXERCICES.get(nom, "A préciser")
    if not poids or "haltère" not in materiel:
        return materiel
    if materiel.startswith("Deux haltères"):
        return materiel.replace("Deux haltères", f"Deux haltères de {poids} kg", 1)
    return materiel.replace("Un haltère", f"Un haltère de {poids} kg", 1)


def _decomposer_materiel(materiel_brut):
    """Décompose un descriptif brut de matériel (tel que déclaré dans
    MATERIEL_EXERCICES, donc *sans* poids) en ses composants indépendants :
    le nombre d'haltères et les accessoires fixes (tapis, chaise...).

    Travailler sur le texte brut plutôt que sur la phrase déjà assemblée avec
    le poids (ex: "Un haltère de 14 kg et une chaise") est ce qui évite
    qu'un accessoire ne soit confondu avec la valeur du poids lors d'un
    découpage par sous-chaîne — c'était la source du bug où "et une chaise"
    se retrouvait absorbé dans la liste des poids affichés.
    """
    if not materiel_brut:
        return 0, []
    # "Deux haltère" (sans s) reste accepté : un ancien typo du catalogue,
    # et de toute façon un préfixe de "Deux haltères".
    if "Deux haltère" in materiel_brut:
        nb_halteres = 2
    elif "Un haltère" in materiel_brut:
        nb_halteres = 1
    else:
        nb_halteres = 0
    accessoires = []
    if "tapis" in materiel_brut:
        accessoires.append("Un tapis")
    if "chaise" in materiel_brut:
        accessoires.append("Une chaise")
    return nb_halteres, accessoires


def formater_materiel(exercices):
    """Regroupe le matériel d'une séance dans une phrase lisible.

    Reçoit les exercices (avec leur nom et leur poids), pas des phrases déjà
    composées : voir `_decomposer_materiel` pour la raison.
    """
    elements = set()
    poids_par_halteres = {1: [], 2: []}

    for exercice in exercices:
        nom = exercice["nom"] if isinstance(exercice, dict) else exercice[0]
        poids = (exercice.get("poids") if isinstance(exercice, dict) else exercice[1]) or 0
        materiel_brut = MATERIEL_EXERCICES.get(nom, "A préciser")
        if materiel_brut in ("", "Aucun matériel", "A préciser"):
            continue

        nb_halteres, accessoires = _decomposer_materiel(materiel_brut)
        elements.update(accessoires)
        if nb_halteres == 0:
            continue
        if poids:
            if poids not in poids_par_halteres[nb_halteres]:
                poids_par_halteres[nb_halteres].append(poids)
        else:
            elements.add("Un haltère" if nb_halteres == 1 else "Deux haltères")

    def poids_formates(poids):
        libelles = [f"{p} kg" for p in poids]
        if len(libelles) == 1:
            return libelles[0]
        return ", ".join(libelles[:-1]) + " et " + libelles[-1]

    for nb_halteres, poids in poids_par_halteres.items():
        if poids:
            libelle = "Un haltère" if nb_halteres == 1 else "Deux haltères"
            elements.add(f"{libelle} de {poids_formates(poids)}")

    def rang(element):
        for prefixe, valeur in (
            ("Un tapis", 0),
            ("Deux haltères", 1),
            ("Un haltère", 2),
            ("Une chaise", 3),
        ):
            if element.startswith(prefixe):
                return valeur
        return 4

    elements_ordonnes = sorted(elements, key=lambda element: (rang(element), element))
    elements_ordonnes = [
        element if index == 0 else element[0].lower() + element[1:]
        for index, element in enumerate(elements_ordonnes)
    ]
    if len(elements_ordonnes) <= 1:
        return elements_ordonnes[0] if elements_ordonnes else ""
    if len(elements_ordonnes) == 2:
        return " et ".join(elements_ordonnes)
    return ", ".join(elements_ordonnes[:-1]) + ", et " + elements_ordonnes[-1]


Test_exercice = Circuit(
    [
        BlocExercice(
            exercice=rowing_unilateral_droit,
            poids=0,
            mode=MODE_REPETITIONS,
            nombre_series=1,
            repetitions_par_serie=10,
            duree=0,
            repos_entre_series=20,
            repos_apres=10,
        )
    ]
)

seance_bras = Circuit(
    [
        BlocExercice(
            exercice=curl_biceps_droit,
            poids=8,
            mode=MODE_REPETITIONS,
            nombre_series=2,
            repetitions_par_serie=5,
            duree=0,
            repos_entre_series=5,
            repos_apres=10,
        ),
        BlocExercice(
            exercice=curl_biceps_gauche,
            poids=8,
            mode=MODE_REPETITIONS,
            nombre_series=1,
            repetitions_par_serie=5,
            duree=0,
            repos_entre_series=30,
            repos_apres=0,
        ),
    ]
)

seance_test = Circuit(
    [
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
            repos_apres=0,
        ),
    ]
)

seance_Upper_Push = Circuit(
    [
        BlocExercice(
            exercice=developpe_couche_sol,
            poids=10,
            mode=MODE_REPETITIONS,
            nombre_series=4,
            repetitions_par_serie=12,
            duree=0,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=pompe,
            poids=0,
            mode=MODE_REPETITIONS,
            nombre_series=4,
            repetitions_par_serie=10,
            duree=0,
            repos_entre_series=60,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=developpe_epaule,
            poids=8,
            mode=MODE_REPETITIONS,
            nombre_series=3,
            repetitions_par_serie=12,
            duree=0,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=elevation_laterale,
            poids=5,
            mode=MODE_REPETITIONS,
            nombre_series=3,
            repetitions_par_serie=11,
            duree=0,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=extension_triceps_au_dessus_de_la_tete,
            poids=14,
            mode=MODE_REPETITIONS,
            nombre_series=3,
            repetitions_par_serie=10,
            duree=0,
            repos_entre_series=60,
            repos_apres=0,
        ),
    ]
)

seance_jambes_abdos = Circuit(
    [
        BlocExercice(
            exercice=squat,
            poids=10,
            mode=MODE_REPETITIONS,
            nombre_series=4,
            repetitions_par_serie=10,
            duree=0,
            repos_entre_series=50,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=fente_droite,
            poids=10,
            mode=MODE_REPETITIONS,
            nombre_series=4,
            repetitions_par_serie=10,
            duree=0,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=fente_gauche,
            poids=10,
            mode=MODE_REPETITIONS,
            nombre_series=4,
            repetitions_par_serie=10,
            duree=0,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=souleve_roumain,
            poids=10,
            mode=MODE_REPETITIONS,
            nombre_series=4,
            repetitions_par_serie=8,
            duree=0,
            repos_entre_series=60,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=crunches,
            poids=0,
            mode=MODE_REPETITIONS,
            nombre_series=3,
            repetitions_par_serie=17,
            duree=0,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=planche,
            poids=0,
            mode=MODE_MAINTIEN,
            nombre_series=3,
            repetitions_par_serie=0,
            duree=40,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=planche_laterale_droite,
            poids=0,
            mode=MODE_MAINTIEN,
            nombre_series=1,
            repetitions_par_serie=0,
            duree=35,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=planche_laterale_gauche,
            poids=0,
            mode=MODE_MAINTIEN,
            nombre_series=1,
            repetitions_par_serie=0,
            duree=35,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=planche_laterale_droite,
            poids=0,
            mode=MODE_MAINTIEN,
            nombre_series=1,
            repetitions_par_serie=0,
            duree=35,
            repos_entre_series=45,
            repos_apres=90,
        ),
        BlocExercice(
            exercice=planche_laterale_gauche,
            poids=0,
            mode=MODE_MAINTIEN,
            nombre_series=1,
            repetitions_par_serie=0,
            duree=35,
            repos_entre_series=45,
            repos_apres=90,
        ),
    ]
)


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


def catalogue_echauffements():
    """Mouvements d'échauffement, pour l'optgroup dédié des éditeurs de séance."""
    return {
        nom: {
            "nom": mouvement.nom,
            "description": mouvement.description,
            "materiel": "",
        }
        for nom, mouvement in CATALOGUE_ECHAUFFEMENTS.items()
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
            "entrelace_avec": bloc.entrelace_avec,
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


def construire_circuit(blocs):
    """Construit un circuit à partir d'une définition JSON, en validant les noms."""
    if not blocs:
        raise ValueError("Au moins un exercice est requis")
    mouvements = catalogue_mouvements()
    inconnus = [
        bloc.get("exercice") for bloc in blocs if bloc.get("exercice") not in mouvements
    ]
    if inconnus:
        raise KeyError(f"Exercice inconnu : {inconnus[0]}")

    modes_inconnus = [
        bloc.get("mode")
        for bloc in blocs
        if bloc.get("mode", MODE_REPETITIONS) not in MODES_CONNUS
    ]
    if modes_inconnus:
        raise ValueError(f"Mode inconnu : {modes_inconnus[0]}")

    # `Exercice.detection` est facultative depuis l'ajout de l'échauffement :
    # on refuse ici les combinaisons qui planteraient devant la caméra, plutôt
    # que de laisser un TypeError surgir en pleine séance.
    sans_detection = [
        bloc["exercice"]
        for bloc in blocs
        if bloc.get("mode", MODE_REPETITIONS) in MODES_AVEC_DETECTION_OBLIGATOIRE
        and mouvements[bloc["exercice"]].detection is None
    ]
    if sans_detection:
        raise ValueError(
            f"{sans_detection[0]} n'analyse pas la pose : "
            f"choisissez le mode {MODE_ECHAUFFEMENT} ou {MODE_CHRONO}"
        )

    return Circuit(
        [
            BlocExercice(
                exercice=mouvements[bloc["exercice"]],
                poids=bloc.get("poids", 0),
                mode=bloc.get("mode", MODE_REPETITIONS),
                nombre_series=bloc.get("series", 1),
                repetitions_par_serie=bloc.get("repetitions", 0),
                duree=bloc.get("duree", 0),
                repos_entre_series=bloc.get("repos_entre_series", 0),
                repos_apres=bloc.get("repos_apres", 0),
                commentaire=bloc.get("commentaire", ""),
                entrelace_avec=bloc.get("entrelace_avec"),
            )
            for bloc in blocs
        ]
    )


def creer_seance_personnalisee(nom):
    blocs = _lire_seances_personnalisees().get(nom)
    if blocs is None:
        raise KeyError(f"Séance inconnue : {nom}")
    return construire_circuit(blocs)


def creer_seance(nom):
    """Retourne un circuit neuf, indépendant des séances déjà utilisées."""
    if nom not in CATALOGUE_SEANCES or nom in _lire_seances_personnalisees():
        return creer_seance_personnalisee(nom)
    return deepcopy(CATALOGUE_SEANCES[nom])


def creer_seance_test(nom_exercice, mode):
    mouvements = catalogue_mouvements()
    if nom_exercice not in mouvements:
        raise KeyError("Exercice inconnu")
    if mode not in MODES_CONNUS:
        raise ValueError("Mode inconnu")
    if (
        mode in MODES_AVEC_DETECTION_OBLIGATOIRE
        and mouvements[nom_exercice].detection is None
    ):
        raise ValueError(f"{nom_exercice} n'analyse pas la pose")

    bloc = deepcopy(Test_exercice.exercices[0])
    bloc.exercice = mouvements[nom_exercice]
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
            seance["exercices"]
        )
    return resultats
