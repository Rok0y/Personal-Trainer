from audio.coach import annoncer_progression, annoncer_temps_restant
from core.messages import libelle_etape, texte
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
#: S'applique à tous les modes qui cumulent des deltas image par image —
#: maintien et échauffement — et non au seul échauffement, d'où le nom.
INTERVALLE_MAX = 0.5


def executer_mode(seance, corps, compteur, etat, coach, derniere_rep):

    bloc = seance.bloc_actuel
    etat.mode = bloc.mode

    if bloc.mode == MODE_REPETITIONS:

        return gerer_mode_repetitions(
            corps=corps,
            exercice=bloc.exercice,
            bloc=bloc,
            seance=seance,
            compteur=compteur,
            etat=etat,
            coach=coach,
            derniere_rep=derniere_rep,
        )
    elif bloc.mode == MODE_MAINTIEN:

        return gerer_mode_maintien(
            corps=corps, bloc=bloc, seance=seance, etat=etat, coach=coach
        )
    elif bloc.mode == MODE_CHRONO:

        return gerer_mode_chrono(bloc=bloc, seance=seance, etat=etat)
    elif bloc.mode == MODE_AMRAP:

        return gerer_mode_amrap(
            corps=corps,
            bloc=bloc,
            compteur=compteur,
            seance=seance,
            etat=etat,
            coach=coach,
            derniere_rep=derniere_rep,
        )
    elif bloc.mode == MODE_ECHAUFFEMENT:

        return gerer_mode_echauffement(
            corps=corps, bloc=bloc, seance=seance, etat=etat
        )

    raise NotImplementedError(f"Mode inconnu : {bloc.mode}")


#: Quel compteur de `core.state` porte la durée réalisée, selon le mode. Un
#: mode absent d'ici ne mesure pas de temps.
COMPTEUR_DUREE_PAR_MODE = {
    MODE_MAINTIEN: "temps_maintien",
    MODE_CHRONO: "temps_chrono",
    MODE_ECHAUFFEMENT: "temps_echauffement",
}


def duree_realisee(bloc, etat):
    """Durée courante du bloc, lue dans le compteur de **son** mode.

    À n'employer que pour terminer une série à la main (geste bras en X ou
    bouton web) : c'est le seul moment où la durée réalisée est lue de
    l'extérieur d'un `gerer_mode_*`.

    Surtout, ne jamais remplacer ça par une chaîne `temps_maintien or
    temps_chrono or temps_echauffement`. Les trois compteurs sont des globales
    partagées, et un gainage abandonné avant la première seconde laisse
    `temps_maintien` à 0 — donc *falsy* : la chaîne retombait alors sur la
    durée du dernier échauffement, enregistrant 30 s pour une série jamais
    tenue. Le mode du bloc est la seule source d'autorité.
    """
    if bloc is None:
        return 0
    return getattr(etat, COMPTEUR_DUREE_PAR_MODE.get(bloc.mode, ""), 0) or 0


def oublier_durees(etat):
    """Remet à zéro les compteurs de durée partagés entre les séries.

    `Circuit.reinitialiser_etat_serie` fait le ménage côté bloc, mais les
    compteurs de `core.state` lui échappent : ils survivaient d'une série à
    l'autre et d'un exercice au suivant, prêts à être relus par erreur.
    """
    for attribut in COMPTEUR_DUREE_PAR_MODE.values():
        setattr(etat, attribut, 0)
    etat.chrono_termine = False


def _finaliser_serie(seance, etat, bloc):
    """Termine la série en cours et réinitialise les champs temporels du bloc.

    Factorise ce que les quatre gerer_mode_* répétaient (terminer_serie +
    mettre_a_jour_prochain_exercice + reset des attributs temporels), délégué
    à Circuit.reinitialiser_etat_serie pour n'avoir qu'un seul endroit qui
    connaît la liste de ces attributs.
    """
    seance.terminer_serie()
    mettre_a_jour_prochain_exercice(seance, etat)
    seance.reinitialiser_etat_serie(bloc)
    oublier_durees(etat)


def mettre_a_jour_erreur(exercice, corps, etat):
    """Publie la première faute de forme détectée, ou efface le bandeau.

    Les fonctions de vérification retournent une **clé** de `core.messages`, pas
    une phrase : c'est ici qu'elle est résolue. Une clé inconnue rend None, donc
    n'affiche rien — un détecteur inachevé qui retournerait `True` reste ainsi
    silencieux, là où il écrivait auparavant « true » en gros dans le bandeau.
    """
    cle = next(
        (cle for verifier in exercice.erreurs if (cle := verifier(corps))),
        None,
    )
    etat.erreur = texte(cle) if cle else None


def poser_etape(etat, jeton):
    """Publie l'étape du mouvement, sous sa forme brute et sous sa forme lisible.

    Les deux, parce qu'elles ne servent pas au même public : le jeton reste la
    donnée du détecteur (et les modes s'en servent), le libellé est ce que lit
    l'utilisateur.
    """
    etat.stage = jeton
    etat.etape_libelle = libelle_etape(jeton)


def gerer_mode_repetitions(
    corps, exercice, bloc, seance, compteur, etat, coach, derniere_rep
):
    serie_terminee = False
    mettre_a_jour_erreur(exercice, corps, etat)
    stage_detecte = exercice.detection(corps)

    stage, repetitions = compteur.mettre_a_jour(stage_detecte)

    if repetitions > derniere_rep:
        coach("compteur", repetitions)

        annoncer_progression(repetitions, bloc.repetitions_par_serie)

        derniere_rep = repetitions

    poser_etape(etat, stage)
    etat.repetitions = repetitions

    if repetitions >= bloc.repetitions_par_serie:
        seance.enregistrer_resultat_serie(
            repetitions=repetitions,
            completee=True,
        )
        _finaliser_serie(seance, etat, bloc)
        compteur.reset()
        etat.repetitions = 0
        derniere_rep = 0

        serie_terminee = True

    return derniere_rep, repetitions, serie_terminee


def gerer_mode_maintien(corps, bloc, seance, etat, coach):

    mettre_a_jour_erreur(bloc.exercice, corps, etat)
    position = bloc.exercice.detection(corps)
    if position == "maintien":
        bloc.position_maintien_validee = True

    if position != "maintien" and getattr(bloc, "position_maintien_validee", False):
        coach("correction_gainage")
    maintenant = seance.maintenant()

    if not hasattr(bloc, "dernier_maintien"):
        bloc.dernier_maintien = maintenant

    temps_ecoule = min(maintenant - bloc.dernier_maintien, INTERVALLE_MAX)
    bloc.dernier_maintien = maintenant

    if position == "maintien":
        bloc.temps_maintien += temps_ecoule

    # Bip chaque seconde
    seconde = int(bloc.temps_maintien)
    if getattr(bloc, "derniere_seconde_bip", -1) != seconde:
        bloc.derniere_seconde_bip = seconde
        coach("bip")

    annoncer_temps_restant(bloc, bloc.duree - bloc.temps_maintien)
    etat.repetitions = 0
    poser_etape(etat, position)
    etat.temps_maintien = bloc.temps_maintien
    etat.duree_maintien = bloc.duree

    if bloc.temps_maintien >= bloc.duree:

        seance.enregistrer_resultat_serie(
            duree=bloc.temps_maintien,
            completee=True,
        )
        _finaliser_serie(seance, etat, bloc)
        return 0, 0, True

    return 0, 0, False


def gerer_mode_chrono(bloc, seance, etat):
    # Un chrono ne juge pas la forme : il n'a aucune faute à signaler, mais il
    # doit effacer celle du bloc précédent, sinon le bandeau reste affiché
    # pendant toute la durée du mouvement.
    etat.erreur = None
    maintenant = seance.maintenant()

    if not hasattr(bloc, "debut_chrono"):
        bloc.debut_chrono = maintenant

    bloc.temps_chrono = maintenant - bloc.debut_chrono
    annoncer_temps_restant(bloc, bloc.duree - bloc.temps_chrono)
    if bloc.temps_chrono >= bloc.duree:
        bloc.temps_chrono = bloc.duree
        etat.temps_chrono = bloc.temps_chrono
        etat.chrono_termine = True

        seance.enregistrer_resultat_serie(
            duree=bloc.temps_chrono,
            completee=True,
        )
        _finaliser_serie(seance, etat, bloc)

        return 0, 0, True

    etat.temps_chrono = bloc.temps_chrono
    etat.chrono_termine = False

    return 0, 0, False


def gerer_mode_amrap(corps, bloc, compteur, seance, etat, coach, derniere_rep):

    mettre_a_jour_erreur(bloc.exercice, corps, etat)
    maintenant = seance.maintenant()

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
    poser_etape(etat, stage)
    etat.repetitions = repetitions

    etat.temps_amrap_restant = max(0, bloc.duree - bloc.temps_amrap)

    # fin du défi
    if bloc.temps_amrap >= bloc.duree:

        seance.enregistrer_resultat_serie(
            repetitions=repetitions,
            completee=True,
        )
        _finaliser_serie(seance, etat, bloc)
        compteur.reset()
        derniere_rep = 0
        return derniere_rep, repetitions, True

    return derniere_rep, repetitions, False


def gerer_mode_echauffement(corps, bloc, seance, etat):
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
    maintenant = seance.maintenant()

    if not hasattr(bloc, "temps_echauffement"):
        bloc.temps_echauffement = 0
        bloc.dernier_tick_echauffement = maintenant

    delta = maintenant - bloc.dernier_tick_echauffement
    bloc.dernier_tick_echauffement = maintenant
    bloc.temps_echauffement += min(delta, INTERVALLE_MAX)

    if bloc.exercice.detection is not None:
        mettre_a_jour_erreur(bloc.exercice, corps, etat)
        poser_etape(etat, bloc.exercice.detection(corps))
    else:
        etat.erreur = None
        poser_etape(etat, "echauffement")

    annoncer_temps_restant(bloc, bloc.duree - bloc.temps_echauffement)

    # affichage web
    etat.repetitions = 0
    etat.temps_echauffement = bloc.temps_echauffement
    etat.duree_echauffement = bloc.duree

    # fin du mouvement
    if bloc.temps_echauffement >= bloc.duree:

        bloc.temps_echauffement = bloc.duree
        etat.temps_echauffement = bloc.duree

        seance.enregistrer_resultat_serie(
            duree=bloc.temps_echauffement,
            completee=True,
        )
        _finaliser_serie(seance, etat, bloc)
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


def mettre_a_jour_prochain_exercice(circuit, etat):
    # La fiche du prochain exercice suit le même calcul que son libellé : elle
    # n'a de sens qu'entre deux exercices, et se recalcule ici plutôt que dans
    # un second parcours du circuit.
    etat.fiche_suivante = None
    if circuit.phase in ("preparation", "exercice"):
        bloc = circuit.bloc_actuel
        etat.prochaine_etape = decrire_prochaine_etape(
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

            etat.prochaine_etape = decrire_prochaine_etape(
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
            etat.prochaine_etape = decrire_prochaine_etape(
                prochain, 1, prochain.nombre_series
            )
            etat.fiche_suivante = prochain.exercice.fiche()

            return

    # --------------------------------------
    # Pas de prochain exercice
    # --------------------------------------

    etat.prochaine_etape = None
