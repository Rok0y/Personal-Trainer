import time

from session.circuit import (
    MODE_REPETITIONS,
    MODE_MAINTIEN,
    MODE_CHRONO,
    MODE_AMRAP
)


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
    stage_detecte = exercice.detection(corps)

    stage, repetitions = compteur.mettre_a_jour(stage_detecte)

    if repetitions > derniere_rep:

        coach(
            "compteur",
            repetitions
        )

        if repetitions == bloc.repetitions_par_serie:
            coach("derniere_rep")

        elif repetitions == bloc.repetitions_par_serie - 1:
            coach("avant_derniere")

        derniere_rep = repetitions

    state.stage = stage
    state.repetitions = repetitions

    if repetitions >= bloc.repetitions_par_serie:
        seance.terminer_serie()
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

    position = bloc.exercice.detection(corps)


    if position == "maintien":

        bloc.temps_maintien += 1 / 30
        # environ 30 images/seconde

    else:

        pass
        # on ne rajoute rien,
        # le chrono est simplement en pause


    state.repetitions = 0
    state.stage = position
    state.temps_maintien = bloc.temps_maintien
    state.duree_maintien = bloc.duree


    if bloc.temps_maintien >= bloc.duree:

        seance.terminer_serie()

        bloc.temps_maintien = 0

        return 0, 0, True


    return 0, 0, False

def gerer_mode_chrono(
    bloc,
    seance,
    state
):

    if not hasattr(bloc, "temps_chrono"):
        bloc.temps_chrono = 0


    bloc.temps_chrono += 1 / 30


    if bloc.temps_chrono >= bloc.duree:

        bloc.temps_chrono = bloc.duree

        state.temps_chrono = bloc.temps_chrono
        state.chrono_termine = True


        seance.terminer_serie()

        return 0, 0, True


    else:

        state.temps_chrono = bloc.temps_chrono
        state.chrono_termine = False


    return 0, 0, 

def gerer_mode_amrap(
    corps,
    bloc,
    compteur,
    seance,
    state,
    coach,
    derniere_rep
):

    if not hasattr(bloc, "temps_amrap"):
        bloc.temps_amrap = 0


    # temps écoulé
    bloc.temps_amrap += 1 / 30


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

    state.temps_restant = max(
        0,
        bloc.duree - bloc.temps_amrap
    )


    # fin du défi
    if bloc.temps_amrap >= bloc.duree:

        seance.terminer_serie()

        bloc.temps_amrap = 0

        compteur.reset()

        return derniere_rep, repetitions, True


    return derniere_rep, repetitions, False