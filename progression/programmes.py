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

import json
from pathlib import Path

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


FICHIER_PROGRAMMES_PERSONNALISES = Path(__file__).with_name(
    "programmes_personnalises.json"
)


def _exigence(seance, exercice, series, cible, poids=0):
    """Une ligne de programme, telle qu'elle est prescrite sur le papier.

    Les exigences sont une **liste plate** : chacune porte le libellé de la
    séance à laquelle elle appartient, et le regroupement se fait à
    l'affichage. Une structure imbriquée serait plus jolie à lire ici, mais
    beaucoup plus lourde à éditer depuis un formulaire — or un programme se
    modifie depuis le site.
    """
    return {
        "seance": seance,
        "exercice": exercice,
        "series": series,
        "cible": cible,
        "poids": poids,
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
        "exigences": [
            _exigence("Push", "Developpé couché altères", 4, 12, 28),
            _exigence("Push", "Pompes", 3, 35),
            _exigence("Push", "Développé épaule", 3, 12, 20),
            _exigence("Push", "Elevations latérales", 3, 15, 10),
            _exigence("Push", "Extension Triceps", 3, 12, 20),
            _exigence("Jambes et abdos", "Squat", 4, 15, 26),
            _exigence("Jambes et abdos", "Fente droite", 3, 10, 20),
            _exigence("Jambes et abdos", "Fente gauche", 3, 10, 20),
            _exigence("Jambes et abdos", "Souleve de terre roumain", 3, 12, 28),
            _exigence("Jambes et abdos", "Gainage planche", 3, 100),
            _exigence("Jambes et abdos", "Gainage planche laterale droite", 2, 60),
            _exigence("Jambes et abdos", "Gainage planche laterale gauche", 2, 60),
            _exigence("Jambes et abdos", "Crunches", 3, 20),
            _exigence("Pull", "Rowing unilateral droit", 4, 12, 32),
            _exigence("Pull", "Rowing unilateral gauche", 4, 12, 32),
            _exigence("Pull", "Rowing penche", 3, 12, 24),
            _exigence("Pull", "Curl biceps droit", 3, 12, 16),
            _exigence("Pull", "Curl biceps gauche", 3, 12, 16),
            _exigence("Pull", "Oiseau", 3, 15, 8),
        ],
    },
}


def _lire_programmes_personnalises():
    if not FICHIER_PROGRAMMES_PERSONNALISES.exists():
        return {}
    with FICHIER_PROGRAMMES_PERSONNALISES.open(encoding="utf-8") as fichier:
        return json.load(fichier)


def _ecrire_programmes_personnalises(donnees):
    with FICHIER_PROGRAMMES_PERSONNALISES.open("w", encoding="utf-8") as fichier:
        json.dump(donnees, fichier, ensure_ascii=False, indent=2)


def tous_les_programmes():
    """Programmes du code, écrasés par ceux du disque quand la clé existe.

    Même convention que `seances_personnalisees.json` : le fichier **masque**
    le catalogue Python, ce qui permet de modifier un programme livré avec
    l'app sans toucher au code.
    """
    return {**PROGRAMMES, **_lire_programmes_personnalises()}


def est_personnalise(cle):
    """Ce programme existe-t-il sur le disque ?

    Point d'entrée unique de la règle « ce programme est-il supprimable ? » :
    un programme livré dans le code et jamais modifié n'a rien à supprimer, et
    proposer de le faire mènerait à une erreur.
    """
    return cle in _lire_programmes_personnalises()


def valider_programme(donnees):
    """Refuse un programme incohérent avant qu'il n'atteigne le disque.

    Mieux vaut un refus à l'enregistrement qu'une page de programme qui
    plante ou qui affiche des exigences impossibles à évaluer.
    """
    nom = (donnees.get("nom") or "").strip()
    if not nom:
        raise ValueError("Le nom du programme est requis")

    exigences = donnees.get("exigences") or []
    if not exigences:
        raise ValueError("Au moins une exigence est requise")

    propres = []
    for ligne in exigences:
        exercice = ligne.get("exercice")
        if not est_suivi_par_le_moteur(exercice):
            raise ValueError(f"{exercice or 'Exercice vide'} n'a pas de barème")
        try:
            series = int(ligne.get("series") or 0)
            cible = float(ligne.get("cible") or 0)
            poids = float(ligne.get("poids") or 0)
        except (TypeError, ValueError):
            raise ValueError(f"Valeurs invalides pour {exercice}")
        if series < 1 or cible <= 0:
            raise ValueError(f"Séries et cible doivent être positives ({exercice})")
        propres.append(
            _exigence(
                (ligne.get("seance") or "Séance").strip(),
                exercice,
                series,
                cible,
                poids,
            )
        )

    return {
        "nom": nom,
        "description": (donnees.get("description") or "").strip(),
        "exigences": propres,
    }


def enregistrer_programme(cle, donnees):
    """Crée ou remplace un programme personnalisé."""
    cle = (cle or "").strip()
    if not cle:
        raise ValueError("La clé du programme est requise")
    programmes = _lire_programmes_personnalises()
    programmes[cle] = valider_programme(donnees)
    _ecrire_programmes_personnalises(programmes)
    return cle


def supprimer_programme(cle):
    """Supprime un programme personnalisé.

    Un programme livré dans le code et jamais modifié n'a rien sur le disque :
    il n'est donc pas supprimable, et c'est voulu — le supprimer reviendrait à
    éditer le code.
    """
    programmes = _lire_programmes_personnalises()
    if cle not in programmes:
        raise KeyError(f"Programme inconnu : {cle}")
    del programmes[cle]
    _ecrire_programmes_personnalises(programmes)


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
        "seance": exigence.get("seance") or "Séance",
        "series": exigence["series"],
        "cible": exigence["cible"],
        "poids": exigence["poids"],
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
    programme = tous_les_programmes().get(cle)
    if programme is None:
        return None

    niveaux = etats_niveaux(seances) if niveaux is None else niveaux
    par_seance = {}
    exigences = []

    for ligne in programme.get("exigences", []):
        if not est_suivi_par_le_moteur(ligne.get("exercice")):
            continue
        etat = etat_exigence(ligne, niveaux)
        # Regroupement à l'affichage seulement : l'ordre des séances suit
        # l'ordre d'apparition des exigences, donc celui de l'éditeur.
        par_seance.setdefault(etat["seance"], []).append(etat)
        exigences.append(etat)

    atteintes = [etat for etat in exigences if etat["atteint"]]
    return {
        "cle": cle,
        "nom": programme["nom"],
        "description": programme.get("description", ""),
        "personnalise": est_personnalise(cle),
        "exigences_brutes": programme.get("exigences", []),
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
        cle: etat_programme(cle, niveaux=niveaux) for cle in tous_les_programmes()
    }
