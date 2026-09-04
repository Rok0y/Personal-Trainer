"""Ce que l'utilisateur a ressenti, et de combien ça déplace l'objectif.

Point d'entrée unique de la règle « trop facile → saute des paliers », sur le
modèle de `est_suivi_par_le_moteur`. Aucun autre module ne doit décider seul
de ce qu'un ressenti vaut.

**Ce module ne touche jamais au niveau.** Le niveau d'un exercice reste le plus
haut palier jamais validé (`progression/niveaux.py`) : c'est un record, il ne
recule pas. L'objectif, lui, est un plan, et il peut reculer — un exercice raté
et déclaré trop dur redescend d'un palier sans que le record en souffre. Toute
la valeur de la feature tient dans cette séparation ; la casser reviendrait à
effacer un record parce que l'utilisateur a eu une mauvaise journée.

Le repère de calcul est le **palier visé à la dernière séance**, et non le
niveau : c'est ce qui rend l'ajustement lisible (« la dernière fois on m'a
demandé le palier 12, je l'ai eu facilement, on me demande 14 »). Ce palier
n'est pas stocké, il est re-dérivé des cibles déjà présentes en base
(`series_cibles`, `repetitions_cibles`, `duree_cible`) par `niveau_pour` —
fidèle à la règle du dossier : rien de ce qui peut être déduit n'est écrit.
"""

from historique.database import recuperer_ancrages, recuperer_historique
from progression.niveaux import (
    UNITE_PAR_MODE,
    niveau_prouve_par,
    niveaux_par_exercice,
)
from progression.paliers import (
    UNITE_SECONDES,
    est_suivi_par_le_moteur,
    niveau_pour,
    unite,
)

#: Les cinq valeurs stockables. L'interface n'en propose que celles qui
#: **changent** quelque chose : « facile » et « trop facile » après une
#: réussite, « trop dur » après un échec. Il n'existe pas de bouton neutre —
#: ne rien sélectionner *est* la réponse neutre, et en offrir un ferait croire
#: qu'une réponse est attendue alors que le cas courant est de passer son
#: chemin. `ok` et `dur` restent acceptés par l'API et lisibles en base (ils
#: valent l'absence de réponse) : les garder évite une migration le jour où on
#: voudra les exploiter.
ECHELLE = ("trop_dur", "dur", "ok", "facile", "trop_facile")

#: Combien de paliers l'objectif gagne, selon ce qui s'est passé ET ce qui a
#: été ressenti. C'est **toute** la règle de progression : la changer, c'est
#: changer cette table, et rien d'autre.
#:
#: `None` est l'absence de réponse, et c'est elle qui reproduit le
#: comportement historique de l'application : +1 après une réussite, rien
#: après un échec. Le ressenti ne fait donc qu'accélérer ou freiner un moteur
#: qui tourne déjà tout seul.
AJUSTEMENT = {
    (True, "trop_facile"): 3,
    (True, "facile"): 2,
    (True, None): 1,
    (False, "trop_dur"): -1,
    (False, None): 0,
}


def est_valide(valeur):
    """Vrai si `valeur` appartient à l'échelle des ressentis."""
    return valeur in ECHELLE


def ajustement(reussi, ressenti=None):
    """Nombre de paliers à ajouter à l'objectif.

    Les combinaisons absentes de `AJUSTEMENT` retombent sur l'absence de
    réponse : dire « c'était facile » après un échec, ou « c'était trop dur »
    après une réussite, ne fait rien plutôt que de produire une règle que
    personne n'a écrite. L'interface ne propose pas ces combinaisons, mais
    l'historique peut en contenir — une réponse saisie a posteriori depuis la
    page d'historique n'est pas contrainte par l'écran de fin de séance.
    """
    reussi = bool(reussi)
    if (reussi, ressenti) in AJUSTEMENT:
        return AJUSTEMENT[(reussi, ressenti)]
    return AJUSTEMENT[(reussi, None)]


def base_apres_echec(base_demandee, niveau_acquis):
    """D'où repartir quand l'objectif de la dernière séance n'a pas été atteint.

    On redemande exactement la même chose. Un échec ne fait pas reculer
    l'objectif : il le fige, et seul un « trop dur » explicite le fait
    redescendre. C'est le rôle du ressenti, et personne d'autre ne doit s'en
    charger à la place de l'utilisateur.

    La tentation serait de plafonner à `niveau_acquis + 1`, ce que faisait
    l'application avant ce module. C'est une erreur, et l'historique le montre :
    un développé épaule à 3x12 à 8 kg manqué de trois répétitions (12, 9, 12)
    renvoyait à 3x15 à **5 kg**, parce que c'était le dernier palier *pleinement*
    validé. Une série ratée faisait perdre deux crans d'haltère. Le niveau est
    une preuve stricte — toutes les séries, sans exception — et il ne fait pas
    un bon objectif : il décrit ce qui est démontré, pas ce sur quoi on
    travaille.

    `niveau_acquis` reste dans la signature parce que c'est lui, et lui seul,
    que voudrait consulter la règle concurrente : la garder visible évite de
    devoir rebrancher un calcul de niveaux jusqu'ici si l'arbitrage change.
    """
    return base_demandee


def _cible_visee(exercice):
    """Ce que la séance demandait : (poids, séries, cible), ou None.

    Lit les colonnes de cible de l'historique, pas les colonnes réalisées.
    `poids` fait exception : c'est la charge configurée du bloc, donc déjà une
    consigne — il n'existe pas de colonne `poids_cible`.
    """
    nom = exercice.get("nom")
    if not est_suivi_par_le_moteur(nom):
        return None

    unite_attendue = unite(nom)
    if UNITE_PAR_MODE.get(exercice.get("mode")) != unite_attendue:
        return None

    series = exercice.get("series_cibles") or 0
    if unite_attendue == UNITE_SECONDES:
        cible = exercice.get("duree_cible") or 0
    else:
        cible = exercice.get("repetitions_cibles") or 0
    if not series or not cible:
        return None

    return exercice.get("poids") or 0, series, cible


def juger(exercice):
    """Ce qu'une ligne d'historique dit du couple (objectif, réussite).

    Retourne `{"base", "reussi", "ressenti"}` ou None si la ligne ne permet
    pas de situer un objectif — exercice hors barème, mode incompatible avec
    son unité, ou cible absente (séance jouée avant le moteur de progression).

    « Réussi » signifie que le palier demandé a bien été validé, au sens du
    barème : `niveau_prouve_par` applique déjà le maillon faible et ne compte
    que les séries menées au bout. Une seule série manquée fait donc basculer
    l'exercice en échec, ce qui est exactement la lecture voulue.
    """
    visee = _cible_visee(exercice)
    if visee is None:
        return None

    base = niveau_pour(exercice["nom"], *visee)
    if base is None:
        return None

    return {
        "base": base,
        "reussi": (niveau_prouve_par(exercice) or 0) >= base,
        "ressenti": exercice.get("ressenti") or None,
    }


def _lignes_retenues(seance, ancrages):
    """Les exercices d'une séance qui peuvent servir de repère, ou rien.

    Une séance abandonnée ne dit rien de l'objectif suivant, et une séance
    antérieure à un ancrage de niveau a été explicitement déclarée périmée par
    l'utilisateur : la reprendre écraserait le recalage qu'elle a motivé.
    """
    if seance.get("statut") == "abandoned":
        return []
    identifiant = seance.get("id") or 0
    return [
        exercice
        for exercice in seance.get("exercices", [])
        if not (
            ancrages.get(exercice.get("nom"))
            and identifiant <= ancrages[exercice["nom"]]["apres_seance_id"]
        )
    ]


def evaluation(seances=None, ancrages=None, niveaux=None):
    """Objectif à viser pour chaque exercice, d'après sa dernière séance.

    `{nom: {"base", "reussi", "ressenti", "ajustement", "vise", "seance_id"}}`

    Un exercice absent du résultat n'a pas de repère exploitable : c'est à
    l'appelant de retomber sur la règle par défaut (`objectifs.py`).

    `recuperer_historique` rend la séance la plus récente en tête : la première
    ligne rencontrée pour un exercice est donc la bonne, et la boucle s'arrête
    d'elle-même sur les suivantes. Un même exercice peut apparaître deux fois
    dans une séance (`jambes_abdos` enchaîne deux planches latérales) ; c'est
    alors l'objectif le plus haut qui fait foi, et à objectif égal la ligne
    réussie l'emporte — comme `niveaux_par_exercice`, jamais une somme.
    """
    seances = recuperer_historique() if seances is None else seances
    ancrages = recuperer_ancrages() if ancrages is None else ancrages
    if niveaux is None:
        niveaux = niveaux_par_exercice(seances, ancrages)

    resultat = {}
    for seance in seances:
        for exercice in _lignes_retenues(seance, ancrages):
            nom = exercice["nom"]
            if nom in resultat and resultat[nom]["seance_id"] != seance.get("id"):
                continue  # déjà tranché par une séance plus récente

            jugement = juger(exercice)
            if jugement is None:
                continue

            precedent = resultat.get(nom)
            if precedent and (
                precedent["base"] > jugement["base"]
                or (precedent["base"] == jugement["base"] and precedent["reussi"])
            ):
                continue

            base = jugement["base"]
            if not jugement["reussi"]:
                acquis = niveaux.get(nom, {}).get("niveau")
                base = base_apres_echec(base, acquis)

            gain = ajustement(jugement["reussi"], jugement["ressenti"])
            resultat[nom] = {
                **jugement,
                "base": base,
                "ajustement": gain,
                "vise": max(1, base + gain),
                "seance_id": seance.get("id"),
            }

    return resultat


def jugements_par_seance(seances=None):
    """Jugement de chaque exercice, séance par séance, pour l'affichage.

    `{seance_id: {nom: {"base", "reussi", "ressenti"}}}`. C'est ce qui permet
    aux écrans de ne proposer que les réponses ayant un sens : après une
    réussite on demande si c'était facile, après un échec si c'était trop dur
    — jamais les cinq d'un coup, qui laisseraient croire à un effet là où il
    n'y en a pas.

    Contrairement à `evaluation`, aucune séance n'est écartée : on décrit ici
    ce qui s'est passé, pas ce qu'il faut viser ensuite. Une séance abandonnée
    mérite tout autant d'être annotée.
    """
    seances = recuperer_historique() if seances is None else seances

    return {
        seance.get("id"): {
            exercice["nom"]: (
                juger(exercice)
                # Hors barème : pas d'objectif chiffré, mais un ressenti reste
                # utile — il pilote la vieille progression « +1 répétition ».
                or {
                    "base": None,
                    "reussi": _reussite_brute(exercice),
                    "ressenti": exercice.get("ressenti") or None,
                }
            )
            for exercice in seance.get("exercices", [])
        }
        for seance in seances
    }


def evaluation_seance(seance_id, seances=None):
    """Jugement des exercices d'une séance précise. Vide si elle est inconnue."""
    return jugements_par_seance(seances).get(seance_id, {})


def _reussite_brute(exercice):
    """Réussite d'un exercice sans barème : toutes les séries, toute la cible.

    Le barème est le juge normal, mais il ne couvre que les exercices qu'il
    connaît. Pour les autres, la seule lecture disponible est la comparaison
    directe des séries réalisées à la consigne — la même que celle de
    `Circuit.objectifs_reussis`, appliquée cette fois à l'historique.
    """
    series = [
        serie
        for serie in exercice.get("series_detaillees", [])
        if serie.get("completee")
    ]
    if not series or len(series) < (exercice.get("series_cibles") or 0):
        return False

    if UNITE_PAR_MODE.get(exercice.get("mode")) == UNITE_SECONDES:
        cible = exercice.get("duree_cible") or 0
        return all((serie.get("duree") or 0) >= cible for serie in series)

    cible = exercice.get("repetitions_cibles") or 0
    return all((serie.get("repetitions") or 0) >= cible for serie in series)
