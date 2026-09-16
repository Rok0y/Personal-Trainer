# Tous les imports
import ctypes
import threading
import time

import cv2

import session.seances
from audio.coach import annoncer_prochaine_etape, annoncer_temps_repos, coach
from audio.lecteur import jouer
from core.messages import texte
from historique.database import enregistrer_seance, initialiser
from mouvements.compteur import CompteurMouvement
from mouvements.outils import HoldPosition
from mouvements.positions import (
    bras_droit_leve,
    bras_en_x,
    bras_gauche_leve,
    deux_bras_leves,
)
from session.moteur import (
    duree_realisee,
    executer_mode,
    mettre_a_jour_prochain_exercice,
    oublier_durees,
    poser_etape,
)
from vision.dessin import dessiner_squelette
from vision.detector import PoseDetector
from web.app import controleur, flux, lancer_site, ouvrir_navigateur

# Définition des variables
cap = cv2.VideoCapture(0)
# La caméra ouvre en 1920x1080 par défaut : les JPEG font alors ~380 KB
# et saturent le flux MJPEG. 1280x720 suffit largement pour la détection.
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
QUALITE_JPEG = [cv2.IMWRITE_JPEG_QUALITY, 70]
# L'etat de la seance appartient au controleur, qui est l'objet « une
# session ». On en garde une reference : il est remis a zero, jamais
# remplace.
etat = controleur.etat_seance
compteur = CompteurMouvement()
hold_bras_x = HoldPosition(bras_en_x, 3)
hold_deux_bras_leves = HoldPosition(deux_bras_leves, 3)
preparation = HoldPosition(bras_en_x, 1.5)
detection = PoseDetector()
ancienne_phase = None
derniere_rep = 0
fin_preparation = None
DELAI_AVANT_EXERCICE = 3


def empecher_veille():
    if hasattr(ctypes, "windll"):
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001 | 0x00000002)


def autoriser_veille():
    if hasattr(ctypes, "windll"):
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


def publier_fin_de_seance(seance):
    """Publie l'état final et enregistre l'historique.

    Doit être appelée à chaque frame, y compris quand aucun corps n'est
    détecté : une séance terminée depuis le site (ou pendant que l'utilisateur
    est hors champ) doit malgré tout être écrite dans l'historique.
    """
    controleur.marquer_terminee()

    etat.phase = seance.phase
    etat.serie_actuelle = 0
    etat.nombre_series = 0
    etat.repetitions_cibles = 0
    etat.temps_repos_restant = 0
    etat.poids = 0
    etat.exercice_actuel = "Séance terminée"
    poser_etape(etat, "termine")
    etat.consigne = None
    etat.test_max = False
    etat.fiche = None
    etat.fiche_suivante = None

    if seance.historique_enregistre or not seance.a_des_resultats():
        return

    print(">>> ENREGISTREMENT HISTORIQUE <<<")

    seance.seance_id = enregistrer_seance(
        duree=seance.duree_totale,
        exercices=seance.exporter_resultats(),
        nom_seance=controleur.nom_selectionne,
        statut="abandoned" if seance.phase == "abandonne" else "finished",
        # Profil fixé au choix de la séance : passer par le profil connecté
        # ici crédite le mauvais athlète si quelqu'un a changé de profil entre
        # la fin de l'effort et cette écriture — ou lève, personne n'étant
        # connecté, et emporte la boucle caméra avec.
        utilisateur_id=seance.utilisateur_id,
    )

    seance.historique_enregistre = True


controleur.definir_reset_progression(lambda: compteur.reset())

seance = None
"""La séance active est partagée avec l'API web.

Rien n'est sélectionné au démarrage : aucun profil n'est encore connecté, et
construire une séance ici lui appliquerait les objectifs de personne — le
moteur de progression lit l'historique du profil courant. C'est l'écran de
connexion qui ouvre la session, puis l'accueil qui choisit la séance.
"""


# Initialisation de la base de données
initialiser()

# Lancement du site
threading.Thread(target=lancer_site, daemon=True).start()
threading.Thread(target=ouvrir_navigateur, daemon=True).start()


if not cap.isOpened():
    print("Impossible d'ouvrir la caméra.")
    detection.close()
    raise SystemExit

# ==========================================
# BOUCLE PRINCIPALE
# ==========================================

coach("debut")

try:

    while True:

        # LECTURE DE LA CAMERA
        ret, frame = cap.read()

        if not ret:
            print("Impossible de lire la caméra.")
            break

        seance = controleur.seance
        if controleur.statut in ("running", "paused"):
            empecher_veille()
        else:
            autoriser_veille()

        # DETECTION DU CORPS
        corps = detection.detect(frame) if controleur.statut == "running" else None
        if corps is None:
            etat.erreur = None
            # Sans ce message, une sortie du champ fige l'affichage sans rien
            # dire : compteurs gelés, dernière étape figée, indistinguable de
            # quelqu'un qui ne bouge simplement plus.
            etat.consigne = (
                texte("corps_absent") if controleur.statut == "running" else None
            )
        else:
            etat.consigne = None
        """cette variable dit si il y a un corps à l'écran ou non"""

        if seance is not None and controleur.statut == "running" and corps is None:
            seance.update()
            mettre_a_jour_prochain_exercice(seance, etat)

        if controleur.statut == "paused":
            etat.phase = "pause"
            poser_etape(etat, "pause")
            etat.consigne = texte("pause")
            corps = None
        if corps is not None:
            """soit si il détecte un corps à l'écran"""

            # Détection des positions de controle
            if deux_bras_leves(corps):
                etat.position_actuelle = "Deux bras levés"
            elif bras_droit_leve(corps):
                etat.position_actuelle = "Bras droit levé"
            elif bras_gauche_leve(corps):
                etat.position_actuelle = "Bras gauche levé"
            elif bras_en_x(corps):
                etat.position_actuelle = "Bras en X"
            else:
                etat.position_actuelle = "Aucune"

            # Bras en X valide une série uniquement pendant l'exercice.
            progression_x, termine_x = hold_bras_x.update(corps)
            etat.progression_maintien = progression_x
            etat.maintien_termine = termine_x

            # Deux bras levés réinitialisent la série sans valider le résultat.
            _, reset = hold_deux_bras_leves.update(corps)
            if reset and seance.phase == "exercice":
                compteur.reset()
                etat.repetitions = 0
                derniere_rep = 0

            if termine_x and seance.phase == "exercice":
                seance.terminer_serie_manuellement(
                    repetitions=etat.repetitions,
                    duree=duree_realisee(seance.bloc_actuel, etat),
                )
                oublier_durees(etat)
                compteur.reset()
                etat.repetitions = 0
                derniere_rep = 0

            # ==================================
            # MACHINE DU CIRCUIT
            # ==================================
            seance.update()
            mettre_a_jour_prochain_exercice(seance, etat)

            # ==================================
            # Le coach (une seule fois par changement de phase)
            # ==================================

            if seance.phase != ancienne_phase:

                if seance.phase == "preparation":
                    coach("preparation")

                elif seance.phase == "exercice":

                    if ancienne_phase in ("recuperation_serie", "repos_exercice"):
                        coach("debut_serie")

                    seance.repos_restant_precedent = None

                elif seance.phase == "recuperation_serie":

                    coach("repos")

                    seance.repos_restant_precedent = int(seance.temps_restant)

                elif seance.phase == "repos_exercice":

                    coach("repos")

                    # Le nombre d'haltères et l'orientation sont fournis ici
                    # plutôt que lus par le coach : `audio.annonces` n'importe
                    # que la bibliothèque standard, et c'est ce qui permet à
                    # `preparer_demo` de l'exporter vers le navigateur sans
                    # tirer tout le catalogue ni pygame.
                    prochain = seance.prochain_bloc()

                    annoncer_prochaine_etape(
                        etat.prochaine_etape,
                        nombre_halteres=(
                            session.seances.nombre_halteres(prochain.exercice.nom)
                            if prochain
                            else 0
                        ),
                        orientation=(
                            prochain.exercice.orientation if prochain else None
                        ),
                    )

                    seance.repos_restant_precedent = int(seance.temps_restant)

                elif seance.phase == "termine":

                    coach("fin_seance")

            ancienne_phase = seance.phase

            if seance.phase == "recuperation_serie":
                annoncer_temps_repos(seance, etat, annoncer_exercice=False)

            elif seance.phase == "repos_exercice":

                annoncer_temps_repos(seance, etat, annoncer_exercice=False)
            # ==================================
            # SEANCE EN COURS
            # (la fin de séance est traitée plus bas, hors du bloc
            #  « un corps est détecté »)
            # ==================================

            if seance.phase not in ("termine", "abandonne"):

                etat.phase = seance.phase
                etat.serie_actuelle = seance.serie_actuelle
                etat.nombre_series = seance.nombre_series
                etat.repetitions_cibles = seance.repetitions_cibles
                etat.temps_repos_restant = seance.temps_restant
                etat.poids = seance.poids

                # ----------------------------------
                # PREPARATION (doit tourner à CHAQUE frame
                # tant qu'on est en phase "preparation", pour
                # accumuler le temps de maintien du bras en X)
                # ----------------------------------
                if seance.phase == "preparation":

                    if fin_preparation is None:
                        # Étape 1 : on attend que le maintien bras en X soit validé
                        progression, termine = preparation.update(corps)
                        etat.progression_preparation = progression
                        poser_etape(etat, "preparation")
                        etat.consigne = texte("preparation_bras_en_x")

                        if termine:
                            # Le premier exercice de la séance : en phase
                            # `preparation`, `prochaine_etape` décrit le bloc
                            # **courant** et non le suivant, donc on lit
                            # `bloc_actuel`.
                            bloc = seance.bloc_actuel

                            annoncer_prochaine_etape(
                                etat.prochaine_etape,
                                nombre_halteres=(
                                    session.seances.nombre_halteres(
                                        bloc.exercice.nom
                                    )
                                    if bloc
                                    else 0
                                ),
                                orientation=(
                                    bloc.exercice.orientation if bloc else None
                                ),
                            )
                            fin_preparation = time.time()

                    else:
                        # Étape 2 : compte à rebours avant de vraiment démarrer
                        temps_ecoule = time.time() - fin_preparation
                        etat.progression_preparation = 100
                        poser_etape(etat, "preparation_prete")
                        etat.consigne = texte("preparation_decompte")

                        if temps_ecoule >= DELAI_AVANT_EXERCICE:
                            coach("debut_serie")
                            seance.commencer_exercice()
                            fin_preparation = None

                # ----------------------------------
                # EXERCICE EN COURS
                # ----------------------------------
                # Ne vaut que pour la phase exercice : sans cette remise à
                # zéro le drapeau survivrait aux repos et à l'exercice suivant.
                etat.test_max = False

                if seance.phase == "exercice":
                    exercice = seance.exercice_actuel

                    if exercice is not None:

                        # NOM DE L'EXERCICE
                        etat.exercice_actuel = exercice.nom
                        # Les consignes du mouvement existent depuis toujours
                        # dans le catalogue ; c'est ici qu'elles atteignent
                        # enfin l'écran.
                        etat.fiche = exercice.fiche()

                        # Sur un test de calibration la cible affichée est un
                        # plafond hors d'atteinte : sans cette consigne, l'écran
                        # demanderait 999 répétitions sans expliquer pourquoi.
                        bloc = seance.bloc_actuel
                        etat.test_max = bool(
                            bloc is not None and getattr(bloc, "test_max", False)
                        )
                        if etat.test_max:
                            etat.consigne = texte("test_calibration")

                        # Execution du moteur d'exo
                        derniere_rep, repetitions, serie_terminee = executer_mode(
                            seance=seance,
                            corps=corps,
                            compteur=compteur,
                            etat=etat,
                            coach=coach,
                            derniere_rep=derniere_rep,
                        )

                        # SERIE TERMINEE
                        if serie_terminee:
                            continue

                # ----------------------------------
                # RECUPERATION ENTRE SERIES
                # ----------------------------------

                elif seance.phase == "recuperation_serie":
                    etat.exercice_actuel = "Récupération"
                    poser_etape(etat, "recuperation")

                # ----------------------------------
                # REPOS ENTRE EXERCICES
                # ----------------------------------

                elif seance.phase == "repos_exercice":
                    etat.exercice_actuel = "Repos"
                    poser_etape(etat, "repos")

            # ==================================
            # DESSIN DU SQUELETTE
            # ==================================

            frame = dessiner_squelette(frame, corps)

        # La fin doit être publiée même si la pose disparaît à la dernière frame.
        if seance is not None and seance.phase in ("termine", "abandonne"):
            publier_fin_de_seance(seance)

        # ==========================================
        # ENCODAGE POUR LE FEED WEB
        # ==========================================

        succes, buffer = cv2.imencode(".jpg", frame, QUALITE_JPEG)

        if succes:
            flux.latest_frame = buffer.tobytes()
            flux.frame_id += 1


# ==========================================
# ARRET PROPRE
# ==========================================

except KeyboardInterrupt:

    print("Arrêt du programme...")

finally:

    cap.release()

    detection.close()
    autoriser_veille()

    print("Caméra arrêtée.")