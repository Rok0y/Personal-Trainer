import time
from audio.coach import annoncer_progression, annoncer_temps_restant, annoncer_erreur

from session.circuit import (
    MODE_REPETITIONS,
    MODE_MAINTIEN,
    MODE_CHRONO,
    MODE_AMRAP
)

def mettre_a_jour_erreur(exercice, corps, state):
    message = next(
        (message for verifier in exercice.erreurs if (message := verifier(corps))),
        None,
    )
    state.erreur = message
    annoncer_erreur(message)
    
def executer_mode(
    seance,
    corps,
    compteur,
    state,
    coach,
    derniere_rep
):

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
            derniere_rep=derniere_rep
        )
    elif bloc.mode == MODE_MAINTIEN:

        return gerer_mode_maintien(
            corps=corps,
            bloc=bloc,
            seance=seance,
            state=state,
            coach=coach
        )
    elif bloc.mode == MODE_CHRONO:

        return gerer_mode_chrono(
            bloc=bloc,
            seance=seance,
            state=state
        )
    elif bloc.mode == MODE_AMRAP:

        return gerer_mode_amrap(
            corps=corps,
            bloc=bloc,
            compteur=compteur,
            seance=seance,
            state=state,
            coach=coach,
            derniere_rep=derniere_rep
        )
    
    raise NotImplementedError(
        f"Mode inconnu : {bloc.mode}"
    )


def mettre_a_jour_erreur(exercice, corps, state):
    state.erreur = next(
        (message for verifier in exercice.erreurs if (message := verifier(corps))),
        None,
    )
    
    

def gerer_mode_repetitions(
    corps,
    exercice,
    bloc,
    seance,
    compteur,
    state,
    coach,
    derniere_rep
):
    serie_terminee = False
    mettre_a_jour_erreur(exercice, corps, state)
    stage_detecte = exercice.detection(corps)

    stage, repetitions = compteur.mettre_a_jour(stage_detecte)

    if repetitions > derniere_rep:
        coach(
            "compteur",
            repetitions
        )

        annoncer_progression(
            repetitions,
            bloc.repetitions_par_serie
        )

        derniere_rep = repetitions

    state.stage = stage
    state.repetitions = repetitions

    if repetitions >= bloc.repetitions_par_serie:
        seance.enregistrer_resultat_serie(
            repetitions=repetitions,
            completee=True,
        )
        seance.terminer_serie()
        mettre_a_jour_prochain_exercice(seance,state)
        compteur.reset()
        state.repetitions = 0
        derniere_rep = 0

        serie_terminee = True

    return derniere_rep, repetitions, serie_terminee

def gerer_mode_maintien(
    corps,
    bloc,
    seance,
    state,
    coach
):

    mettre_a_jour_erreur(bloc.exercice, corps, state)
    position = bloc.exercice.detection(corps)
    if position == "maintien":
        bloc.position_maintien_validee = True

    if (
        position != "maintien"
        and getattr(bloc, "position_maintien_validee", False)
    ):
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

    annoncer_temps_restant(
        bloc,
        bloc.duree - bloc.temps_maintien
    )
    state.repetitions = 0
    state.stage = position
    state.temps_maintien = bloc.temps_maintien
    state.duree_maintien = bloc.duree


    if bloc.temps_maintien >= bloc.duree:

        seance.enregistrer_resultat_serie(
            duree=bloc.temps_maintien,
            completee=True,
        )
        seance.terminer_serie()
        mettre_a_jour_prochain_exercice(seance,state)
        bloc.temps_maintien = 0
        del bloc.dernier_maintien
        bloc.temps_restant_precedent = None
        bloc.derniere_seconde_bip = -1
        return 0, 0, True


    return 0, 0, False

def gerer_mode_chrono(
    bloc,
    seance,
    state
):
    maintenant = time.monotonic()

    if not hasattr(bloc, "debut_chrono"):
        bloc.debut_chrono = maintenant

    bloc.temps_chrono = maintenant - bloc.debut_chrono
    annoncer_temps_restant(
        bloc,
        bloc.duree - bloc.temps_chrono
    )
    if bloc.temps_chrono >= bloc.duree:
        bloc.temps_chrono = bloc.duree
        state.temps_chrono = bloc.temps_chrono
        state.chrono_termine = True

        seance.enregistrer_resultat_serie(
            duree=bloc.temps_chrono,
            completee=True,
        )
        seance.terminer_serie()
        mettre_a_jour_prochain_exercice(seance, state)

        bloc.temps_chrono = 0
        del bloc.debut_chrono
        bloc.temps_restant_precedent = None

        return 0, 0, True

    state.temps_chrono = bloc.temps_chrono
    state.chrono_termine = False

    return 0, 0

def gerer_mode_amrap(
    corps,
    bloc,
    compteur,
    seance,
    state,
    coach,
    derniere_rep
):

    mettre_a_jour_erreur(bloc.exercice, corps, state)
    maintenant = time.monotonic()

    if not hasattr(bloc, "debut_amrap"):
        bloc.debut_amrap = maintenant

    bloc.temps_amrap = maintenant - bloc.debut_amrap
    annoncer_temps_restant(
        bloc,
        bloc.duree - bloc.temps_amrap
    )

    # détection du mouvement
    stage_detecte = bloc.exercice.detection(corps)


    stage, repetitions = compteur.mettre_a_jour(stage_detecte)


    if repetitions > derniere_rep:

        coach(
            "compteur",
            repetitions
        )

        derniere_rep = repetitions


    # affichage web
    state.stage = stage
    state.repetitions = repetitions

    state.temps_amrap_restant = max(
        0,
        bloc.duree - bloc.temps_amrap
    )


    # fin du défi
    if bloc.temps_amrap >= bloc.duree:

        seance.enregistrer_resultat_serie(
            repetitions=repetitions,
            completee=True,
        )
        seance.terminer_serie()
        mettre_a_jour_prochain_exercice(seance,state)
        bloc.temps_amrap = 0
        del bloc.debut_amrap
        bloc.temps_restant_precedent = None
        compteur.reset()
        derniere_rep = 0
        return derniere_rep, repetitions, True


    return derniere_rep, repetitions, False

def decrire_prochaine_etape(bloc, nombre_series):
    if bloc is None:
        return None

    return {
        "exercice": bloc.exercice.nom,
        "poids": bloc.poids,
        "series": nombre_series,
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
            circuit.nombre_series - circuit.serie_actuelle + 1
            if bloc else 0,
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
                bloc.nombre_series - circuit.serie_actuelle + 1
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
                prochain,
                prochain.nombre_series
            )

            return


    # --------------------------------------
    # Pas de prochain exercice
    # --------------------------------------

    state.prochaine_etape = None
