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

from core.utilisateur import identifiant_connecte
from historique.database import recuperer_ancrages, recuperer_historique
from progression.niveaux import UNITE_PAR_MODE, etats_niveaux
from progression.paliers import (
    UNITE_SECONDES,
    est_suivi_par_le_moteur,
    palier,
    unite,
)
from progression.calibration import (
    niveau_de_depart,
    niveau_plancher,
    note_du_profil,
    note_effective,
    note_mesuree,
)
from progression.ressenti import evaluation


def profils_cible_manuelle(valeur):
    """Normalise la valeur stockée en ensemble d'identifiants de profils.

    Les séances sont partagées entre profils : une cible figée à la main
    appartient donc à **celui qui l'a figée**, pas à la séance. La valeur
    stockée est une liste d'identifiants ; l'ancien booléen doit continuer à
    se lire, sans quoi les marques posées avant les profils disparaîtraient
    silencieusement au premier chargement.

    Une valeur qu'aucun format connu ne couvre est lue comme « personne » : un
    faux positif fige une cible que le moteur ne fera plus jamais bouger, et
    c'est un blocage silencieux, alors qu'un faux négatif se voit dès le
    prochain affichage et se corrige d'un clic.
    """
    if valeur is None or valeur is False:
        return set()
    # `True` date d'avant les profils : la marque appartient au profil 1, celui
    # qui a hérité de tout l'historique à la migration.
    if valeur is True:
        return {1}
    if isinstance(valeur, int):
        return {valeur}
    if isinstance(valeur, (list, tuple, set)):
        return {int(profil) for profil in valeur if isinstance(profil, int)}
    return set()


def fusionner_cible_manuelle(valeur_entrante, valeur_stockee, utilisateur_id=None):
    """Combine la décision du profil connecté et les marques déjà sur le disque.

    Indispensable parce qu'un enregistrement de séance **réécrit tous les
    blocs** : le formulaire d'objectifs de l'accueil renvoie ce que le profil
    connecté voit, c'est-à-dire rien des autres. Sans fusion, la première
    sauvegarde du second profil effacerait les cibles figées du premier — sur
    des blocs qu'il n'a jamais touchés.

    La règle : les autres profils viennent du disque, qui fait autorité pour
    eux ; seul le bit du profil connecté est repris de la valeur entrante. Un
    client n'a donc jamais à transporter l'état de quelqu'un d'autre.
    """
    if utilisateur_id is None:
        utilisateur_id = identifiant_connecte()
    autres = profils_cible_manuelle(valeur_stockee)
    if utilisateur_id is None:
        return sorted(autres) or None
    utilisateur_id = int(utilisateur_id)
    autres.discard(utilisateur_id)
    if utilisateur_id in profils_cible_manuelle(valeur_entrante):
        autres.add(utilisateur_id)
    return sorted(autres) or None


def _valeur_cible_manuelle(bloc):
    """Lit l'attribut, que le bloc soit un dictionnaire ou un `BlocExercice`."""
    if isinstance(bloc, dict):
        return bloc.get("cible_manuelle")
    return getattr(bloc, "cible_manuelle", None)


def est_cible_manuelle(bloc, utilisateur_id=None):
    """Ce bloc est-il figé à la main **pour ce profil** ?"""
    if utilisateur_id is None:
        utilisateur_id = identifiant_connecte()
    if utilisateur_id is None:
        return False
    return int(utilisateur_id) in profils_cible_manuelle(_valeur_cible_manuelle(bloc))


def definir_cible_manuelle(valeur_actuelle, manuelle, utilisateur_id=None):
    """Nouvelle valeur à stocker après décision pour un seul profil.

    Retourne None quand plus personne ne fige ce bloc, pour que l'appelant
    retire la clé plutôt que d'écrire une liste vide. Les identifiants des
    autres profils sont conservés : c'est tout l'objet du changement de
    format.
    """
    if utilisateur_id is None:
        utilisateur_id = identifiant_connecte()
    profils = profils_cible_manuelle(valeur_actuelle)
    if utilisateur_id is not None:
        if manuelle:
            profils.add(int(utilisateur_id))
        else:
            profils.discard(int(utilisateur_id))
    return sorted(profils) or None


def objectifs_par_exercice(seances=None, note=None):
    """Palier à viser pour chaque exercice suivi.

    Trois règles, dans cet ordre.

    1. **Le repère de la dernière séance** (`progression/ressenti.py`) : le
       palier alors demandé, plus ou moins ce que la réussite et le ressenti
       lui valent. C'est ce qui permet de sauter plusieurs crans quand c'était
       trop facile, et de reculer quand c'était trop dur.
    2. **Un exercice jamais fait** — aucun repère, aucun niveau prouvé — part
       du palier de la note d'athlète (`calibration.niveau_de_depart`, sur la
       note *effective* : la note déclarée, ou la note mesurée quand
       l'historique la dépasse nettement). Il n'y a plus de test au maximum.
    3. À défaut — cible d'époque indéchiffrable, ou ancrage de niveau plus
       récent que la dernière séance —, `suivant` : le premier palier non
       validé. Et si le barème est épuisé, le dernier palier atteint plutôt
       que rien.

    Par-dessus les règles 1 et 3, une **note relevée à la main** pose un
    plancher sur la prochaine séance (`calibration.niveau_plancher`) : un
    exercice déjà fait sous le départ de la nouvelle note y monte, une fois,
    sans que rien ne soit validé.

    Un objectif peut donc se retrouver **sous** le niveau de l'exercice. C'est
    voulu : le niveau est un record, l'objectif est un plan.

    `note` vaut `{"declaree", "relevee_apres"}` ; absente, elle est lue sur le
    profil connecté — lecture implicite que le harnais détourne, comme celle
    des ancrages.
    """
    seances = recuperer_historique() if seances is None else seances
    note = note_du_profil() if note is None else note
    ancrages = recuperer_ancrages()
    reperes = evaluation(seances, ancrages)
    depart = note_effective(note.get("declaree"), note_mesuree(seances, ancrages))

    objectifs = {}
    for nom, etat in etats_niveaux(seances).items():
        repere = reperes.get(nom)
        vise = palier(nom, repere["vise"]) if repere else None
        if vise is None and etat["niveau"] is None:
            objectifs[nom] = palier(nom, niveau_de_depart(nom, depart))
            continue
        objectif = vise or etat["suivant"] or etat["actuel"]
        plancher = niveau_plancher(nom, note, repere)
        if objectif is not None and plancher and objectif.niveau < plancher:
            objectif = palier(nom, plancher)
        objectifs[nom] = objectif
    return objectifs


def exercices_sans_donnees(seances=None):
    """Exercices dont rien ne prouve le niveau : ni historique, ni ancrage.

    Ne sert plus qu'à l'affichage : un badge « 1re fois » sur les exercices
    dont la cible vient de la note d'athlète et non de l'historique. Le signal
    fiable est `niveau is None`, que `progression.niveaux` documente comme
    « hors barème » et non « niveau 0 ».
    """
    seances = recuperer_historique() if seances is None else seances
    return {
        nom
        for nom, etat in etats_niveaux(seances).items()
        if etat["niveau"] is None
    }


def _pilote_par_le_moteur(nom_exercice, mode):
    """Ce couple exercice/mode relève-t-il du moteur ?

    Un bloc qui n'en relève pas garde la cible de son fichier : exercice sans
    barème, ou mode qui ne mesure pas la même chose que le barème.
    """
    if not est_suivi_par_le_moteur(nom_exercice):
        return False
    return UNITE_PAR_MODE.get(mode) == unite(nom_exercice)


def objectif_pour(nom_exercice, mode, objectifs):
    """Palier à viser pour un bloc, ou None si le moteur ne le pilote pas."""
    if not _pilote_par_le_moteur(nom_exercice, mode):
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
        if est_cible_manuelle(bloc):
            continue
        palier_vise = objectif_pour(_nom_exercice(bloc), bloc.get("mode"), objectifs)
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
        if est_cible_manuelle(bloc):
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

    Un exercice jamais fait n'a plus de cas à part : il reçoit le palier de la
    note d'athlète, qui est un vrai palier, donc la comparaison est juste. Du
    temps du test au maximum, il gardait les valeurs du fichier et se faisait
    figer à chaque enregistrement — il fallait l'écarter ici à la main.
    """
    objectifs = objectifs_par_exercice() if objectifs is None else objectifs

    for bloc in blocs:
        nom = _nom_exercice(bloc)
        palier_vise = objectif_pour(nom, bloc.get("mode"), objectifs)
        if palier_vise is None:
            _ecrire_cible_manuelle(bloc, False)
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
        _ecrire_cible_manuelle(bloc, not identique)

    return blocs


def _ecrire_cible_manuelle(bloc, manuelle):
    """Pose ou retire la marque du profil connecté, sans toucher aux autres."""
    valeur = definir_cible_manuelle(bloc.get("cible_manuelle"), manuelle)
    if valeur is None:
        bloc.pop("cible_manuelle", None)
    else:
        bloc["cible_manuelle"] = valeur


def enteriner_cibles_manuelles(blocs, utilisateur_id=None):
    """Une séance jouée jusqu'au bout fait de sa cible figée la référence.

    Figer une cible est une exception provisoire : le moteur propose autre
    chose, l'utilisateur impose sa valeur, et le badge orange rend ce
    décrochage visible. Mais une fois la séance **terminée** à cette cible,
    l'exception n'en est plus une — l'historique porte désormais la
    performance réalisée, et c'est d'elle que `ressenti._cible_visee` repartira
    pour proposer la suite. Lever la marque ne perd donc pas la valeur : elle
    rebranche le moteur *sur* elle.

    Une séance abandonnée ne prouve rien et garde sa marque. C'est pourquoi
    l'appel se fait sur la phase `termine`, jamais sur `abandonne`.

    Ne surtout pas confondre avec `marquer_cibles_manuelles`, qui *détecte* un
    écart au palier proposé : appliquée ici, elle effacerait aussi les marques
    des blocs que la séance n'a pas joués.

    Retourne True si au moins une marque a été levée — l'appelant n'a alors
    qu'une raison d'écrire le fichier.
    """
    leve = False
    for bloc in blocs:
        if not est_cible_manuelle(bloc, utilisateur_id):
            continue
        valeur = definir_cible_manuelle(
            _valeur_cible_manuelle(bloc), False, utilisateur_id
        )
        if isinstance(bloc, dict):
            if valeur is None:
                bloc.pop("cible_manuelle", None)
            else:
                bloc["cible_manuelle"] = valeur
        else:
            bloc.cible_manuelle = valeur
        leve = True
    return leve
