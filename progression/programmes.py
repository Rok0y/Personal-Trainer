"""Programmes sportifs : une liste d'exigences par-dessus le moteur de niveaux.

Un programme ne stocke **aucune donnée de progression**. Il déclare, pour
chaque exercice, la performance à atteindre ; le niveau requis en est déduit,
le niveau acquis vient de l'historique, et l'écart se recalcule à chaque
lecture. Rien à migrer, rien à tenir à jour : supprimer un programme
n'efface aucune progression, en ajouter un n'en crée aucune.

**La conversion des prescriptions.** Un programme est écrit avec le matériel
de son auteur, pas avec le tien : « développé 4x12 à 28 kg » n'a pas de palier
correspondant si tes haltères s'arrêtent à 10 kg. C'est le **volume** qui sert
de traduction — une répétition à 20 kg en vaut deux à 10 kg —, exactement
l'invariant sur lequel le barème est construit. L'exigence devient donc « le
premier palier qui atteint ce volume », atteignable avec le matériel dont on
dispose réellement.

Quand même le sommet du barème n'atteint pas ce volume, l'exigence est
déclarée **hors d'atteinte** plutôt que silencieusement plafonnée : cela veut
dire qu'il faut du matériel en plus, et c'est une information, pas une erreur.
"""

from progression.niveaux import etats_niveaux
from progression.paliers import (
    UNITE_SECONDES,
    est_suivi_par_le_moteur,
    niveau_pour_volume,
    palier,
    unite,
    volume,
)

#: Comment lire les charges écrites dans un programme : `True` = la valeur est
#: la charge d'un seul haltère, `False` = la charge totale des deux réunis.
#: Bascule cette constante si un programme annonce ses charges autrement — elle
#: divise par deux tous les volumes exigés sur les exercices à deux haltères,
#: et décide donc de ce qui est atteignable.
CHARGE_PAR_HALTERE = True


def _exigence(exercice, series, cible, poids=0, libelle=None):
    """Une ligne de programme, telle qu'elle est prescrite sur le papier."""
    return {
        "exercice": exercice,
        "series": series,
        "cible": cible,
        "poids": poids,
        "libelle": libelle,
    }


#: Les mouvements unilatéraux sont deux exercices dans le catalogue : une
#: prescription « 4x12 par côté » devient donc deux exigences.
PROGRAMMES = {
    "road_to_tkt": {
        "nom": "Road to TKT",
        "description": (
            "Trois séances à boucler intégralement : chaque exercice doit "
            "atteindre le volume prescrit."
        ),
        "seances": {
            "Push": [
                _exigence("Developpé couché altères", 4, 12, 28),
                _exigence("Pompes", 3, 35),
                _exigence("Développé épaule", 3, 12, 20),
                _exigence("Elevations latérales", 3, 15, 10),
                _exigence("Extension Triceps", 3, 12, 20),
            ],
            "Jambes et abdos": [
                _exigence("Squat", 4, 15, 26),
                _exigence("Fente droite", 3, 10, 20),
                _exigence("Fente gauche", 3, 10, 20),
                _exigence("Souleve de terre roumain", 3, 12, 28),
                _exigence("Gainage planche", 3, 100),
                _exigence("Gainage planche laterale droite", 2, 60),
                _exigence("Gainage planche laterale gauche", 2, 60),
                _exigence("Crunches", 3, 20),
            ],
            "Pull": [
                _exigence("Rowing unilateral droit", 4, 12, 32),
                _exigence("Rowing unilateral gauche", 4, 12, 32),
                _exigence("Rowing penche", 3, 12, 24),
                _exigence("Curl biceps droit", 3, 12, 16),
                _exigence("Curl biceps gauche", 3, 12, 16),
                _exigence("Oiseau", 3, 15, 8),
            ],
        },
    },
}


def _charge_par_halteres(nom_exercice, poids):
    """Charge réellement portée par un haltère, selon la convention du programme."""
    if CHARGE_PAR_HALTERE or not poids:
        return poids
    # Import différé : `session.seances` importe déjà le moteur de progression.
    from session.seances import nombre_halteres

    return poids / 2 if nombre_halteres(nom_exercice) >= 2 else poids


def volume_exige(exigence):
    """Volume que la prescription représente, dans l'unité du barème."""
    return volume(
        exigence["series"],
        exigence["cible"],
        _charge_par_halteres(exigence["exercice"], exigence["poids"]),
    )


def prescription(exigence):
    """La ligne telle qu'elle est écrite dans le programme, pour l'affichage."""
    nom = exigence["exercice"]
    suffixe = " s" if unite(nom) == UNITE_SECONDES else ""
    charge = f" à {exigence['poids']:g} kg" if exigence["poids"] else ""
    return f"{exigence['series']}x{exigence['cible']:g}{suffixe}{charge}"


def etat_exigence(exigence, niveaux):
    """Confronte une exigence au niveau acquis."""
    nom = exigence["exercice"]
    etat = niveaux.get(nom)
    acquis = etat["niveau"] if etat else None
    requis = niveau_pour_volume(nom, volume_exige(exigence))

    return {
        "exercice": nom,
        "libelle": exigence["libelle"] or nom,
        "prescription": prescription(exigence),
        "volume": volume_exige(exigence),
        "niveau_requis": requis,
        "palier_requis": palier(nom, requis) if requis else None,
        "niveau_actuel": acquis,
        # Hors d'atteinte : même le sommet du barème n'atteint pas ce volume.
        # Il faut du matériel en plus, aucun entraînement n'y suffira.
        "hors_atteinte": requis is None,
        "atteint": bool(requis and acquis and acquis >= requis),
    }


def etat_programme(cle, seances=None, niveaux=None):
    """Avancement d'un programme, entièrement recalculé à la lecture."""
    programme = PROGRAMMES.get(cle)
    if programme is None:
        return None

    niveaux = etats_niveaux(seances) if niveaux is None else niveaux
    par_seance = {}
    exigences = []

    for nom_seance, lignes in programme["seances"].items():
        etats = [
            etat_exigence(ligne, niveaux)
            for ligne in lignes
            if est_suivi_par_le_moteur(ligne["exercice"])
        ]
        par_seance[nom_seance] = etats
        exigences.extend(etats)

    atteintes = [etat for etat in exigences if etat["atteint"]]
    return {
        "cle": cle,
        "nom": programme["nom"],
        "description": programme["description"],
        "seances": par_seance,
        "total": len(exigences),
        "atteintes": len(atteintes),
        "hors_atteinte": len([e for e in exigences if e["hors_atteinte"]]),
        "pourcentage": (
            round(100 * len(atteintes) / len(exigences)) if exigences else 0
        ),
        "battu": bool(exigences) and len(atteintes) == len(exigences),
    }


def etats_programmes(seances=None):
    """Tous les programmes, en une seule lecture de l'historique."""
    niveaux = etats_niveaux(seances)
    return {
        cle: etat_programme(cle, niveaux=niveaux) for cle in PROGRAMMES
    }
