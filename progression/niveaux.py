"""Déduction du niveau d'un exercice à partir de l'historique.

Le niveau n'est jamais stocké : il est recalculé depuis les séances déjà
enregistrées, selon une règle unique — **le plus haut palier jamais validé**.
Cette règle est idempotente (recalculable de zéro à tout moment), insensible à
l'ordre des séances, et applique d'elle-même la règle « pas de recul ».

Le jugement se fait **par exercice**, pas par séance : une séance abandonnée
après avoir bouclé ses quatre séries de développé couché prouve tout de même
quelque chose. Le statut `abandoned` est donc volontairement ignoré ici, à la
différence de `historique.database.statistiques_exercices`.
"""

from historique.database import recuperer_historique
from progression.paliers import (
    UNITE_REPETITIONS,
    UNITE_SECONDES,
    est_suivi_par_le_moteur,
    exercices_suivis,
    niveau_pour,
    palier,
    unite,
)
from session.circuit import (
    MODE_AMRAP,
    MODE_CHRONO,
    MODE_MAINTIEN,
    MODE_REPETITIONS,
)

#: Ce qu'un mode mesure. Un exercice enregistré en `maintien` ne peut pas
#: valider un barème en répétitions : les deux ne parlent pas de la même chose.
UNITE_PAR_MODE = {
    MODE_REPETITIONS: UNITE_REPETITIONS,
    MODE_AMRAP: UNITE_REPETITIONS,
    MODE_MAINTIEN: UNITE_SECONDES,
    MODE_CHRONO: UNITE_SECONDES,
}


def performance_realisee(exercice, unite_attendue):
    """Réduit un exercice de l'historique à ce qu'il *prouve* : (poids, séries, cible).

    `exercice` est une entrée de `recuperer_historique()` :
        {"nom", "mode", "poids", "series", "repetitions", "duree",
         "series_detaillees": [
             {"serie", "repetitions", "poids", "duree", "completee"}, ...
         ]}

    `unite_attendue` vaut UNITE_REPETITIONS ou UNITE_SECONDES et indique quel
    champ d'une série porte la performance (`repetitions` ou `duree`).

    Retourne un triplet `(poids, nombre_de_series, cible)` exploitable par
    `niveau_pour`, ou None si la ligne ne prouve rien.

    Deux règles gouvernent la lecture :

    - seules les séries menées au bout comptent (`completee`) — une série
      interrompue par un abandon ou par la navigation web ne prouve rien ;
    - c'est le **maillon faible** qui commande, pas la moyenne ni le maximum.
      « Objectif atteint sur TOUTES les séries » se traduit par un minimum sur
      les séries retenues, pour la cible comme pour le poids : 12, 12, 10, 12
      répétitions prouve 10, pas 12.

    Une ligne sans série détaillée retourne None plutôt que de se rabattre sur
    les colonnes agrégées : `exercices.repetitions` est une *somme* sur toutes
    les séries, dont la performance de la plus faible ne se déduit pas.
    """
    champ = "duree" if unite_attendue == UNITE_SECONDES else "repetitions"

    series = [
        serie
        for serie in exercice.get("series_detaillees", [])
        if serie.get("completee")
    ]
    if not series:
        return None

    poids = min((serie.get("poids") or 0) for serie in series)
    cible = min((serie.get(champ) or 0) for serie in series)
    return poids, len(series), cible


def niveau_prouve_par(exercice):
    """Le plus haut niveau qu'un exercice de l'historique valide, ou None."""
    nom = exercice.get("nom")
    if not est_suivi_par_le_moteur(nom):
        return None

    unite_attendue = unite(nom)
    if UNITE_PAR_MODE.get(exercice.get("mode")) != unite_attendue:
        return None

    performance = performance_realisee(exercice, unite_attendue)
    if performance is None:
        return None

    poids, series, cible = performance
    return niveau_pour(nom, poids, series, cible)


def niveaux_par_exercice(seances=None):
    """Niveau actuel de chaque exercice suivi, avec la séance qui l'a établi.

    Un même exercice peut apparaître deux fois dans une séance (`jambes_abdos`
    enchaîne deux fois la planche latérale) : chaque ligne est jugée pour
    elle-même et c'est la meilleure qui l'emporte, jamais leur somme.
    """
    seances = recuperer_historique() if seances is None else seances
    niveaux = {}

    for seance in seances:
        for exercice in seance.get("exercices", []):
            niveau = niveau_prouve_par(exercice)
            if niveau is None:
                continue
            meilleur = niveaux.get(exercice["nom"])
            if meilleur is None or niveau > meilleur["niveau"]:
                niveaux[exercice["nom"]] = {
                    "niveau": niveau,
                    "palier": palier(exercice["nom"], niveau),
                    "seance_id": seance.get("id"),
                    "date": seance.get("date"),
                }

    return niveaux


def niveau_actuel(nom_exercice, seances=None):
    """Niveau d'un exercice, ou None s'il est hors barème ou non suivi."""
    entree = niveaux_par_exercice(seances).get(nom_exercice)
    return entree["niveau"] if entree else None


def etat_niveau(nom_exercice, seances=None, niveaux=None):
    """Tout ce qu'un écran a besoin de savoir sur le niveau d'un exercice.

    Trois situations distinctes, qu'un affichage ne doit pas confondre :
    `niveau` à None = **hors barème** (aucune performance n'atteint le premier
    palier, ce qui n'est pas « niveau 0 ») ; `maximum_atteint` = le barème est
    épuisé, il n'y a plus de palier au-dessus ; sinon `suivant` décrit le
    palier suivant.

    Volontairement sans notion de « pourcentage d'avancement » : un niveau dit
    où l'on en est, pas ce qu'il reste à faire. La part de barème parcourue
    n'aurait de sens que face à un objectif, ce qui relève de la couche
    programme.
    """
    if not est_suivi_par_le_moteur(nom_exercice):
        return None

    niveaux = niveaux_par_exercice(seances) if niveaux is None else niveaux
    entree = niveaux.get(nom_exercice)
    niveau = entree["niveau"] if entree else None
    suivant = palier(nom_exercice, (niveau or 0) + 1)

    return {
        "niveau": niveau,
        "actuel": palier(nom_exercice, niveau) if niveau else None,
        "suivant": suivant,
        "premier": palier(nom_exercice, 1),
        "maximum_atteint": niveau is not None and suivant is None,
        "date": entree["date"] if entree else None,
        "seance_id": entree["seance_id"] if entree else None,
    }


def etats_niveaux(seances=None):
    """État de niveau de tous les exercices suivis, en une seule lecture."""
    niveaux = niveaux_par_exercice(seances)
    return {
        nom: etat_niveau(nom, niveaux=niveaux) for nom in exercices_suivis()
    }
