"""Ce que le moteur propose de viser, et comment il pilote une séance.

Le principe tient en une phrase : **une séance vise le premier palier non
encore validé**. Le niveau dit ce qui est acquis (`progression/niveaux.py`),
l'objectif est le cran juste au-dessus.

La double progression en découle sans être codée nulle part. Objectif atteint
sur toutes les séries → l'historique le prouve → le niveau monte → la séance
suivante propose le palier d'après. Objectif manqué → le niveau ne bouge pas →
la même cible revient. « Pas de recul, pas d'avancée » n'est pas une règle
implémentée ici, c'est une conséquence de la déduction.

Trois raisons, et trois seulement, font qu'un bloc échappe au moteur :
- son exercice n'a pas de barème (`est_suivi_par_le_moteur`) ;
- son mode ne mesure pas la même chose que son barème (un exercice en
  `chrono` ne peut pas recevoir une cible en répétitions) ;
- sa cible a été saisie à la main (`cible_manuelle`), auquel cas elle est
  **collante** : le moteur ne la touche plus jusqu'à resynchronisation.
"""

from progression.niveaux import UNITE_PAR_MODE, etats_niveaux
from progression.paliers import (
    UNITE_SECONDES,
    est_suivi_par_le_moteur,
    unite,
)


def objectifs_par_exercice(seances=None):
    """Palier à viser pour chaque exercice suivi.

    C'est `suivant` — le premier palier non validé —, sauf quand le barème est
    épuisé : on reste alors sur le dernier palier atteint plutôt que de ne rien
    proposer.
    """
    return {
        nom: (etat["suivant"] or etat["actuel"])
        for nom, etat in etats_niveaux(seances).items()
    }


def objectif_pour(nom_exercice, mode, objectifs):
    """Palier à viser pour un bloc, ou None si le moteur ne le pilote pas."""
    if not est_suivi_par_le_moteur(nom_exercice):
        return None
    if UNITE_PAR_MODE.get(mode) != unite(nom_exercice):
        return None
    return objectifs.get(nom_exercice)


def _nom_exercice(bloc):
    """Les blocs JSON nomment l'exercice `exercice`, les blocs exportés `nom`."""
    return bloc.get("exercice") or bloc.get("nom")


def appliquer_a_blocs(blocs, objectifs=None):
    """Réécrit les cibles des blocs (dictionnaires) pilotés par le moteur.

    Modifie les dictionnaires sur place et les retourne, pour servir aussi bien
    à la construction d'une séance qu'à son affichage — les deux doivent
    montrer la même chose, sinon l'accueil annonce une cible que la séance ne
    joue pas.
    """
    objectifs = objectifs_par_exercice() if objectifs is None else objectifs

    for bloc in blocs:
        if bloc.get("cible_manuelle"):
            continue
        palier_vise = objectif_pour(
            _nom_exercice(bloc), bloc.get("mode"), objectifs
        )
        if palier_vise is None:
            continue
        bloc["poids"] = palier_vise.poids
        bloc["series"] = palier_vise.series
        if palier_vise.unite == UNITE_SECONDES:
            bloc["duree"] = palier_vise.cible
        else:
            bloc["repetitions"] = palier_vise.cible

    return blocs


def appliquer_a_circuit(circuit, objectifs=None):
    """Même chose sur un `Circuit` déjà construit.

    Nécessaire parce que les séances du catalogue Python sont des `Circuit`
    écrits à la main, jamais passés par `construire_circuit`.
    """
    objectifs = objectifs_par_exercice() if objectifs is None else objectifs

    for bloc in circuit.exercices:
        if getattr(bloc, "cible_manuelle", False):
            continue
        palier_vise = objectif_pour(bloc.exercice.nom, bloc.mode, objectifs)
        if palier_vise is None:
            continue
        bloc.poids = palier_vise.poids
        bloc.nombre_series = palier_vise.series
        if palier_vise.unite == UNITE_SECONDES:
            bloc.duree = palier_vise.cible
        else:
            bloc.repetitions_par_serie = palier_vise.cible

    return circuit


def marquer_cibles_manuelles(blocs, objectifs=None):
    """Repère les cibles saisies à la main, en les comparant au moteur.

    L'utilisateur n'a pas à déclarer qu'il fait une exception : éditer une
    cible, c'est s'écarter de ce que le moteur propose, et c'est cet écart qui
    est détecté. Corriger la valeur pour la remettre sur le palier proposé
    efface la marque et rebranche le bloc sur le moteur.
    """
    objectifs = objectifs_par_exercice() if objectifs is None else objectifs

    for bloc in blocs:
        palier_vise = objectif_pour(
            _nom_exercice(bloc), bloc.get("mode"), objectifs
        )
        if palier_vise is None:
            bloc.pop("cible_manuelle", None)
            continue

        if palier_vise.unite == UNITE_SECONDES:
            cible = bloc.get("duree") or 0
        else:
            cible = bloc.get("repetitions") or 0

        identique = (
            (bloc.get("poids") or 0) == palier_vise.poids
            and (bloc.get("series") or 0) == palier_vise.series
            and cible == palier_vise.cible
        )
        if identique:
            bloc.pop("cible_manuelle", None)
        else:
            bloc["cible_manuelle"] = True

    return blocs
