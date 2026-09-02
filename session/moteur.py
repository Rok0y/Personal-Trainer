import time

from audio.coach import annoncer_progression, annoncer_temps_restant
from session.circuit import (
    MODE_AMRAP,
    MODE_CHRONO,
    MODE_ECHAUFFEMENT,
    MODE_MAINTIEN,
    MODE_REPETITIONS,
)

#: Un écart plus long que ça entre deux images vient forcément d'une
#: interruption du flux (utilisateur hors champ, pause web, frame lente) :
#: on ne le comptabilise pas d'un bloc au retour de l'utilisateur.
INTERVALLE_MAX_ECHAUFFEMENT = 0.5


def executer_mode(seance, corps, compteur, state, coach, derniere_rep):

    bloc = seance.bloc_actuel
    state.mode = bloc.mode

    if bloc.mode == MODE_REPETITIONS:

        return gerer_mode_repetitions(
            corps=corps,
            exercice=bloc.exercice,
            bloc=bloc,
            seance=seance,
            compteur=compteur,
            state=state,
            coach=coach,
            derniere_rep=derniere_rep,
        )
    elif bloc.mode == MODE_MAINTIEN:

        return gerer_mode_maintien(
            corps=corps, bloc=bloc, seance=seance, state=state, coach=coach
        )
    elif bloc.mode == MODE_CHRONO:

        return gerer_mode_chrono(bloc=bloc, seance=seance, state=state)
    elif bloc.mode == MODE_AMRAP:

        return gerer_mode_amrap(
            corps=corps,
            bloc=bloc,
            compteur=compteur,
            seance=seance,
            state=state,
            coach=coach,
            derniere_rep=derniere_rep,
        )
    elif bloc.mode == MODE_ECHAUFFEMENT:

        return gerer_mode_echauffement(
            corps=corps, bloc=bloc, seance=seance, state=state
        )

    raise NotImplementedError(f"Mode inconnu : {bloc.mode}")


def _finaliser_serie(seance, state, bloc):
    """Termine la série en cours et réinitialise les champs temporels du bloc.

    Factorise ce que les quatre gerer_mode_* répétaient (terminer_serie +
    mettre_a_jour_prochain_exercice + reset des attributs temporels), délégué
    à Circuit.reinitialiser_etat_serie pour n'avoir qu'un seul endroit qui
    connaît la liste de ces attributs.
    """
    seance.terminer_serie()
    mettre_a_jour_prochain_exercice(seance, state)
    seance.reinitialiser_etat_serie(bloc)


def mettre_a_jour_erreur(exercice, corps, state):
    state.erreur = next(
        (message for verifier in exercice.erreurs if (message := verifier(corps))),
        None,
    )


def gerer_mode_repetitions(
    corps, exercice, bloc, seance, compteur, state, coach, derniere_rep
):
    serie_terminee = False
    mettre_a_jour_erreur(exercice, corps, state)
    stage_detecte = exercice.detection(corps)

    stage, repetitions = compteur.mettre_a_jour(stage_detecte)

    if repetitions > derniere_rep:
        coach("compteur", repetitions)

        annoncer_progression(repetitions, bloc.repetitions_par_serie)

        derniere_rep = repetitions

    state.stage = stage
    state.repetitions = repetitions

    if repetitions >= bloc.repetitions_par_serie:
        seance.enregistrer_resultat_serie(
            repetitions=repetitions,
            completee=True,
        )
        _finaliser_serie(seance, state, bloc)
        compteur.reset()
        state.repetitions = 0
        derniere_rep = 0

        serie_terminee = True

    return derniere_rep, repetitions, serie_terminee


def gerer_mode_maintien(corps, bloc, seance, state, coach):

    mettre_a_jour_erreur(bloc.exercice, corps, state)
    position = bloc.exercice.detection(corps)
    if position == "maintien":
        bloc.position_maintien_validee = True

    if position != "maintien" and getattr(bloc, "position_maintien_validee", False):
        coach("correction_gainage")
    maintenant = time.monotonic()

    if not hasattr(bloc, "dernier_maintien"):
        bloc.dernier_maintien = maintenant

    temps_ecoule = maintenant - bloc.dernier_maintien
    bloc.dernier_maintien = maintenant

    if position == "maintien":
        bloc.temps_maintien += temps_ecoule

    # Bip chaque seconde
    seconde = int(bloc.temps_maintien)
    if getattr(bloc, "derniere_seconde_bip", -1) != seconde:
        bloc.derniere_seconde_bip = seconde
        coach("bip")

    annoncer_temps_restant(bloc, bloc.duree - bloc.temps_maintien)
    state.repetitions = 0
    state.stage = position
    state.temps_maintien = bloc.temps_maintien
    state.duree_maintien = bloc.duree

    if bloc.temps_maintien >= bloc.duree:

        seance.enregistrer_resultat_serie(
            duree=bloc.temps_maintien,
            completee=True,
        )
        _finaliser_serie(seance, state, bloc)
        return 0, 0, True

    return 0, 0, False


def gerer_mode_chrono(bloc, seance, state):
    maintenant = time.monotonic()

    if not hasattr(bloc, "debut_chrono"):
        bloc.debut_chrono = maintenant

    bloc.temps_chrono = maintenant - bloc.debut_chrono
    annoncer_temps_restant(bloc, bloc.duree - bloc.temps_chrono)
    if bloc.temps_chrono >= bloc.duree:
        bloc.temps_chrono = bloc.duree
        state.temps_chrono = bloc.temps_chrono
        state.chrono_termine = True

        seance.enregistrer_resultat_serie(
            duree=bloc.temps_chrono,
            completee=True,
        )
        _finaliser_serie(seance, state, bloc)

        return 0, 0, True

    state.temps_chrono = bloc.temps_chrono
    state.chrono_termine = False

    return 0, 0, False


def gerer_mode_amrap(corps, bloc, compteur, seance, state, coach, derniere_rep):

    mettre_a_jour_erreur(bloc.exercice, corps, state)
    maintenant = time.monotonic()

    if not hasattr(bloc, "debut_amrap"):
        bloc.debut_amrap = maintenant

    bloc.temps_amrap = maintenant - bloc.debut_amrap
    annoncer_temps_restant(bloc, bloc.duree - bloc.temps_amrap)

    # détection du mouvement
    stage_detecte = bloc.exercice.detection(corps)

    stage, repetitions = compteur.mettre_a_jour(stage_detecte)

    if repetitions > derniere_rep:

        coach("compteur", repetitions)

        derniere_rep = repetitions

    # affichage web
    state.stage = stage
    state.repetitions = repetitions

    state.temps_amrap_restant = max(0, bloc.duree - bloc.temps_amrap)

    # fin du défi
    if bloc.temps_amrap >= bloc.duree:

        seance.enregistrer_resultat_serie(
            repetitions=repetitions,
            completee=True,
        )
        _finaliser_serie(seance, state, bloc)
        compteur.reset()
        derniere_rep = 0
        return derniere_rep, repetitions, True

    return derniere_rep, repetitions, False


def gerer_mode_echauffement(corps, bloc, seance, state):
    """Mouvement d'échauffement : un chrono guidé, la détection est un bonus.

    Deux différences volontaires avec `gerer_mode_chrono` :

    * le temps est accumulé image par image (comme le mode maintien) plutôt que
      mesuré depuis un `debut_chrono` mural. Comme `main.py` n'appelle les modes
      que lorsqu'un corps est visible et hors pause, le chrono se met ainsi de
      lui-même en pause quand l'utilisateur sort du champ — ce qu'un temps
      mural ne fait pas, puisqu'il continue de courir sans nous ;
    * `bloc.exercice.detection` peut être None. Quand elle existe, elle
      n'alimente que l'affichage : elle ne conditionne jamais l'avancement du
      chrono, un échauffement ne doit pas pouvoir se bloquer.
    """
    maintenant = time.monotonic()

    if not hasattr(bloc, "temps_echauffement"):
        bloc.temps_echauffement = 0
        bloc.dernier_tick_echauffement = maintenant

    delta = maintenant - bloc.dernier_tick_echauffement
    bloc.dernier_tick_echauffement = maintenant
    bloc.temps_echauffement += min(delta, INTERVALLE_MAX_ECHAUFFEMENT)

    if bloc.exercice.detection is not None:
        mettre_a_jour_erreur(bloc.exercice, corps, state)
        state.stage = bloc.exercice.detection(corps)
    else:
        state.erreur = None
        state.stage = "Échauffement"

    annoncer_temps_restant(bloc, bloc.duree - bloc.temps_echauffement)

    # affichage web
    state.repetitions = 0
    state.temps_echauffement = bloc.temps_echauffement
    state.duree_echauffement = bloc.duree

    # fin du mouvement
    if bloc.temps_echauffement >= bloc.duree:

        bloc.temps_echauffement = bloc.duree
        state.temps_echauffement = bloc.duree

        seance.enregistrer_resultat_serie(
            duree=bloc.temps_echauffement,
            completee=True,
        )
        _finaliser_serie(seance, state, bloc)
        return 0, 0, True

    return 0, 0, False


def decrire_prochaine_etape(bloc, serie_actuelle, nombre_total_series=None):
    if bloc is None:
        return None

    # Si nombre_total_series n'est pas fourni, utiliser serie_actuelle comme avant (legacy)
    if nombre_total_series is None:
        nombre_total_series = serie_actuelle

    return {
        "exercice": bloc.exercice.nom,
        "poids": bloc.poids,
        "serie_actuelle": serie_actuelle,
        "nombre_total_series": nombre_total_series,
        "series": serie_actuelle,
        "repetitions": bloc.repetitions_par_serie,
        "mode": bloc.mode,
        "duree": bloc.duree,
        "commentaire": bloc.commentaire,
    }


def mettre_a_jour_prochain_exercice(circuit, state):
    if circuit.phase in ("preparation", "exercice"):
        bloc = circuit.bloc_actuel
        state.prochaine_etape = decrire_prochaine_etape(
            bloc,
            circuit.serie_actuelle,
            bloc.nombre_series if bloc else 0,
        )
        return
    # --------------------------------------
    # Repos entre deux séries
    # On reprend le même exercice
    # --------------------------------------

    if circuit.phase == "recuperation_serie":

        bloc = circuit.bloc_actuel

        if bloc:

            state.prochaine_etape = decrire_prochaine_etape(
                bloc,
                circuit.serie_actuelle,
                bloc.nombre_series,
            )

            return

    # --------------------------------------
    # Repos entre deux exercices
    # On prépare le suivant
    # --------------------------------------

    if circuit.phase == "repos_exercice":

        prochain = circuit.prochain_bloc()

        if prochain:
            state.prochaine_etape = decrire_prochaine_etape(
                prochain, 1, prochain.nombre_series
            )

            return

    # --------------------------------------
    # Pas de prochain exercice
    # --------------------------------------

    state.prochaine_etape = None
