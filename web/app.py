import json
import logging
import re
import sqlite3
import time
import unicodedata
import webbrowser

from flask import (
    Flask,
    Response,
    abort,
    jsonify,
    redirect,
    render_template,
    request,
)

from core.flux import FluxVideo
from core.utilisateur import (
    connecter,
    deconnecter,
    onboarding_a_faire,
    rafraichir,
    utilisateur_connecte,
)
from historique.database import (
    CHEMIN_DB,
    creer_utilisateur,
    definir_materiel,
    definir_mesures,
    definir_onboarding,
    definir_programme_choisi,
    derniere_performance,
    enregistrer_ancrage,
    enregistrer_ressentis,
    lister_utilisateurs,
    recuperer_ancrages,
    recuperer_historique,
    recuperer_historique_ancrages,
    renommer_seance,
    renommer_utilisateur,
    statistiques_exercices,
    supprimer_ancrage,
    supprimer_ancrages,
    supprimer_exercice_de_seance,
    supprimer_seance,
    supprimer_utilisateur,
)
from core.materiel import ACCESSOIRES, POIDS_REFERENCE, materiel_du_profil, normaliser
# Le format d'une sauvegarde n'a qu'une definition : celle du script qui
# l'ecrit en ligne de commande. La route d'export ne fait que la servir.
from scripts.exporter_profil import exporter as exporter_profil
from progression.niveaux import etat_niveau, etats_niveaux, montees_de_niveau
from progression import ligues as moteur_ligues
from progression.paliers import (
    est_suivi_par_le_moteur,
    exercices_suivis,
    niveau_pour,
    palier,
    unite,
)
from progression.programmes import (
    enregistrer_programme,
    est_personnalise,
    etat_programme,
    etats_programmes,
    liaison_seances,
    LIBELLE_CHARGE,
    libelles_seances,
    prochaine_seance,
    supprimer_programme,
    tous_les_programmes,
)
from progression.ressenti import ECHELLE, evaluation_seance, jugements_par_seance
from session.controleur import SessionManager
from session.moteur import duree_realisee
from session.seances import (
    catalogue,
    catalogue_echauffements,
    catalogue_exercices,
    fiche_mouvement,
)


class FiltreEtat(logging.Filter):
    def filter(self, record):
        return "GET /etat" not in record.getMessage()


logging.getLogger("werkzeug").addFilter(FiltreEtat())


app = Flask(__name__)
controleur = SessionManager()
#: Une camera par processus, alimentee par la boucle de `main.py`.
flux = FluxVideo()

#: Points d'entrée accessibles sans profil connecté : l'écran de connexion
#: lui-même et ce qu'il appelle. Tout le reste passe par `_exiger_un_profil`.
ROUTES_SANS_PROFIL = {
    "static",
    "page_connexion",
    "lister_utilisateurs_api",
    "creer_utilisateur_api",
    "renommer_utilisateur_api",
    # Supprimer un profil et en sauvegarder un se font depuis l'ecran de
    # connexion, donc avant d'etre connecte : les exiger connectes obligerait
    # a entrer dans un profil pour pouvoir l'effacer.
    "supprimer_utilisateur_api",
    "exporter_utilisateur_api",
    "connecter_profil_api",
    "deconnecter_profil_api",
}

#: Les libelles du champ `sexe`, cote ecran. Le stockage garde la valeur brute
#: (`femme`, `homme`, `autre`, ou NULL) : l'affichage se corrige sans toucher
#: aux donnees.
LIBELLES_SEXE = {"femme": "Femme", "homme": "Homme", "autre": "Autre"}


@app.before_request
def _exiger_un_profil():
    """Aucune page ne s'affiche tant qu'un profil n'est pas choisi.

    Un garde global plutôt qu'un test dans chaque vue : la couche données
    lève déjà quand personne n'est connecté (`_profil_courant`), et il y a
    trente routes — en oublier une donnerait une page d'erreur brute au lieu
    de l'écran de connexion.
    """
    if request.endpoint in ROUTES_SANS_PROFIL or utilisateur_connecte():
        return None
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "erreur": "Aucun profil connecté"}), 401
    return redirect("/connexion")


#: Points d'entree accessibles pendant le tunnel d'accueil. Meme piege que
#: `ROUTES_SANS_PROFIL` : une route oubliee ici renvoie l'utilisateur sur
#: /bienvenue en boucle au lieu de le laisser avancer. Y figurent la page du
#: tunnel, ses API, le flux video et /etat (le test de calibration s'en sert),
#: les fiches d'exercice (le tunnel y renvoie) et la selection de seance test.
ROUTES_ONBOARDING = {
    "page_bienvenue",
    "enregistrer_materiel",
    "page_exercice",
    "page_exercices",
}


@app.before_request
def _exiger_onboarding():
    """Un profil neuf passe par le tunnel d'accueil avant tout le reste.

    Second garde plutot qu'une condition ajoutee au premier : les deux ne
    protegent pas la meme chose et n'ont pas la meme liste d'exceptions.
    Celui-ci ne s'applique qu'a quelqu'un de deja connecte, donc il tourne
    apres `_exiger_un_profil` (ordre de declaration).
    """
    if not onboarding_a_faire():
        return None
    if request.endpoint in ROUTES_ONBOARDING or request.endpoint in ROUTES_SANS_PROFIL:
        return None
    if request.path.startswith("/api/"):
        return jsonify({"ok": False, "erreur": "Tunnel d'accueil a terminer"}), 409
    return redirect("/bienvenue")


@app.context_processor
def _profil_dans_les_templates():
    """Rend le profil connecté disponible partout, sans le passer route par route."""
    return {"profil": utilisateur_connecte(), "LIBELLES_SEXE": LIBELLES_SEXE}


def programme_de_l_accueil():
    """Le programme suivi par le profil connecté, et la liste où le choisir.

    Retourne `(état du programme ou None, {clé: nom})`. **Aucun repli sur le
    premier programme** : `NULL` veut dire « aucun choix », et l'accueil invite
    alors à en faire un. Retomber en silence sur le premier priverait
    l'utilisateur de la distinction entre « je suis ce programme » et « je n'en
    suis aucun », qui est exactement ce que le choix sert à exprimer.
    """
    disponibles = {
        cle: donnees.get("nom", cle) for cle, donnees in tous_les_programmes().items()
    }
    if not disponibles:
        return None, {}

    profil = utilisateur_connecte() or {}
    cle = profil.get("programme_choisi")
    if cle not in disponibles:
        return None, disponibles
    return etat_programme(cle), disponibles


def seances_du_programme(cle, catalogue_seances):
    """Les séances du programme jouables dans l'app, dans l'ordre du programme.

    Sert au sélecteur qui permet de démarrer une autre séance que celle
    proposée. Les libellés sans séance correspondante sont écartés :
    `liaison_seances` rend None quand aucune séance ne partage d'exercice avec
    eux, et il n'y aurait donc rien à lancer.
    """
    liaisons = liaison_seances(cle, catalogue_seances)
    libelles = libelles_seances(tous_les_programmes().get(cle, {}))
    # `position` compte sur l'ordre complet du programme, pas sur la liste
    # filtrée : c'est le rang que l'utilisateur lit dans « séance 2/3 », et il
    # ne doit pas se décaler parce qu'un libellé n'a pas de séance jouable.
    return [
        {
            "libelle": libelle,
            "seance": liaisons.get(libelle),
            "position": rang,
            "total": len(libelles),
        }
        for rang, libelle in enumerate(libelles, start=1)
        if liaisons.get(libelle) in catalogue_seances
    ]


def noms_exercices_individuels():
    """Noms d'affichage des exercices du catalogue (utilisés par le mode "test")."""
    return {
        exercice.get("nom")
        for exercice in catalogue_exercices().values()
        if exercice.get("nom")
    }


def est_seance_de_test(seance, noms_exercices):
    """Une "séance" issue du mode test ne contient qu'un seul exercice et porte
    directement le nom de cet exercice : elle ne doit pas apparaitre dans
    l'historique des entrainements, seulement dans les records."""
    return (seance.get("nom") or "").strip() in noms_exercices


def seances_entrainement(donnees):
    noms_exercices = noms_exercices_individuels()
    return [s for s in donnees if not est_seance_de_test(s, noms_exercices)]


def executer_commande(fonction):
    try:
        resultat = fonction()
        return jsonify(
            {
                "ok": True,
                "resultat": resultat,
                "etat": controleur.etat(),
            }
        )
    except (KeyError, RuntimeError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 409


# ==========================================
# PROFILS
# ==========================================


@app.route("/connexion")
def page_connexion():
    """Écran de sélection de profil, affiché à chaque lancement.

    On la sert même si quelqu'un est déjà connecté : c'est aussi par ici que
    passe le bouton « changer de profil ».
    """
    profils = lister_utilisateurs()
    # Le nombre de séances par profil : la confirmation de suppression dit ce
    # qu'on perd plutôt que de demander « es-tu sûr ? ».
    with sqlite3.connect(CHEMIN_DB) as connexion:
        comptes = dict(
            connexion.execute(
                "SELECT utilisateur_id, COUNT(*) FROM seances GROUP BY utilisateur_id"
            )
        )
    return render_template(
        "connexion.html", profils=profils, seances_par_profil=comptes
    )


def _mesures_valides(donnees):
    """Extrait les quatre mesures d'un corps de requête. Rend `(mesures, erreur)`.

    Un champ absent n'est pas touché, une chaîne vide vaut « non renseigné » —
    c'est ce que rend un champ de formulaire qu'on vide à la main, et
    `definir_mesures` la traduit en NULL. Partagée par la création d'un profil
    et la page de profil, pour que les deux acceptent exactement la même chose.
    """
    mesures = {}
    for champ in ("sexe", "date_naissance"):
        if champ in donnees:
            mesures[champ] = (donnees[champ] or "").strip()
    for champ in ("taille_cm", "poids_corps_kg"):
        if champ not in donnees:
            continue
        brut = str(donnees[champ] or "").strip()
        if not brut:
            mesures[champ] = ""
            continue
        try:
            mesures[champ] = float(brut.replace(",", "."))
        except ValueError:
            return {}, f"« {champ} » doit être un nombre"
    return mesures, None


@app.route("/api/utilisateurs")
def lister_utilisateurs_api():
    return jsonify({"ok": True, "utilisateurs": lister_utilisateurs()})


@app.route("/api/utilisateurs", methods=["POST"])
def creer_utilisateur_api():
    """Crée un profil et l'ouvre dans la foulée.

    Créer sans connecter obligerait à recliquer sur la carte qu'on vient de
    faire apparaître ; c'est la même intention en deux gestes.
    """
    donnees = request.get_json(silent=True) or {}
    try:
        profil = creer_utilisateur(donnees.get("nom"))
    except ValueError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400

    # **Les mesures se demandent a la creation.** Elles restent facultatives —
    # rien dans le bareme n'en depend — mais les reclamer plus tard, sur une
    # page de profil qu'on ne visite jamais, revenait a ne jamais les avoir.
    mesures, erreur = _mesures_valides(donnees.get("mesures") or {})
    if erreur:
        return jsonify({"ok": False, "erreur": erreur}), 400
    if mesures:
        definir_mesures(profil["id"], mesures)

    try:
        _ouvrir_session(profil["id"])
    except RuntimeError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 409
    return jsonify({"ok": True, "utilisateur": profil})


@app.route("/api/utilisateurs/<int:utilisateur_id>/export")
def exporter_utilisateur_api(utilisateur_id):
    """La sauvegarde d'un profil, au format que l'application sait relire.

    Meme fonction que `python -m scripts.exporter_profil` : le format n'a
    qu'une definition. Elle sert ici a **proposer un export avant une
    suppression**, qui, elle, ne se rattrape pas.
    """
    profils = {profil["id"]: profil for profil in lister_utilisateurs()}
    if utilisateur_id not in profils:
        return jsonify({"ok": False, "erreur": "Profil introuvable"}), 404

    with sqlite3.connect(CHEMIN_DB) as connexion:
        donnees = exporter_profil(connexion, utilisateur_id)

    nom = profils[utilisateur_id]["nom"].lower().replace(" ", "-")
    return Response(
        json.dumps(donnees, ensure_ascii=False, indent=1),
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="coach-{nom}.json"'},
    )


@app.route("/api/utilisateurs/<int:utilisateur_id>", methods=["DELETE"])
def supprimer_utilisateur_api(utilisateur_id):
    """Supprime un profil et tout son historique. Rien ne le rattrape.

    Le profil connecte n'est pas supprimable : le garde de requete le relit a
    chaque appel, et l'effacer sous ses propres pieds laisserait une session
    qui designe une ligne disparue. Changer de profil d'abord est un geste de
    plus, mais un geste explicite.
    """
    connecte = utilisateur_connecte()
    if connecte and connecte["id"] == utilisateur_id:
        return jsonify({
            "ok": False,
            "erreur": "Connecte-toi sur un autre profil avant de supprimer celui-ci.",
        }), 409
    try:
        nom = supprimer_utilisateur(utilisateur_id)
    except KeyError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404
    except ValueError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400
    return jsonify({"ok": True, "nom": nom})


@app.route("/api/utilisateurs/<int:utilisateur_id>", methods=["PUT"])
def renommer_utilisateur_api(utilisateur_id):
    """Renomme un profil. Purement cosmétique : rien ne le référence par son nom."""
    donnees = request.get_json(silent=True) or {}
    try:
        profil = renommer_utilisateur(utilisateur_id, donnees.get("nom"))
    except ValueError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400
    except KeyError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404
    connecte = utilisateur_connecte()
    if connecte and connecte["id"] == profil["id"]:
        connecter(profil["id"])
    return jsonify({"ok": True, "utilisateur": profil})


def _ouvrir_session(utilisateur_id):
    """Bascule la session sur un profil, après avoir vidé la séance en mémoire.

    `nouvelle_seance` lève si une séance tourne : on ne change pas de profil
    au milieu d'un effort, sinon les séries déjà faites finiraient dans
    l'historique de quelqu'un d'autre. Rien d'autre à invalider — il n'existe
    aucun cache dans l'application, tout est recalculé à chaque lecture.
    """
    controleur.nouvelle_seance()
    return connecter(utilisateur_id)


@app.route("/api/session/connexion", methods=["POST"])
def connecter_profil_api():
    donnees = request.get_json(silent=True) or {}
    try:
        profil = _ouvrir_session(int(donnees.get("id") or 0))
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erreur": "Identifiant invalide"}), 400
    except KeyError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404
    except RuntimeError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 409
    return jsonify({"ok": True, "utilisateur": profil})


@app.route("/api/session/deconnexion", methods=["POST"])
def deconnecter_profil_api():
    try:
        controleur.nouvelle_seance()
    except RuntimeError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 409
    deconnecter()
    return jsonify({"ok": True})


# ==========================================
# PAGE PRINCIPALE
# ==========================================


@app.route("/")
def index():

    if controleur.statut in ("idle", "ready"):
        seances = controleur.catalogue()
        historique = recuperer_historique()
        # Résumé du programme suivi : où j'en suis, et surtout quelle séance
        # enchaîner maintenant. Un seul, parce qu'on n'en fait qu'un à la fois.
        programme, programmes_disponibles = programme_de_l_accueil()
        if programme is not None:
            programme["prochaine"] = prochaine_seance(
                programme["cle"], historique, seances
            )
            programme["seances_liees"] = seances_du_programme(
                programme["cle"], seances
            )
            # Une séance déjà choisie prime sur la proposition automatique : le
            # bandeau annonçait sinon « Jambes et abdos » après un clic sur
            # « Push », et le choix de l'utilisateur n'apparaissait nulle part.
            choisie = next(
                (
                    lien
                    for lien in programme["seances_liees"]
                    if lien["seance"] == controleur.nom_selectionne
                ),
                None,
            )
            if choisie is not None:
                programme["prochaine"] = dict(choisie)
        dernieres_series = {}
        for seance in historique:
            nom = seance.get("nom")
            if (
                nom in seances
                and nom not in dernieres_series
                and seance.get("statut") != "abandoned"
            ):
                dernieres_series[nom] = {
                    exercice["nom"]: {
                        "date": seance["date"],
                        "mode": exercice.get("mode", "repetitions"),
                        "ressenti": exercice.get("ressenti") or "",
                        "series": [
                            serie
                            for serie in exercice.get("series_detaillees", [])
                            if serie.get("completee", True)
                        ],
                    }
                    for exercice in seance.get("exercices", [])
                }
        return render_template(
            "accueil.html",
            seances=seances,
            selection=controleur.nom_selectionne,
            exercices=catalogue_exercices(),
            dernieres_series=dernieres_series,
            programme=programme,
            programmes_disponibles=programmes_disponibles,
        )

    if controleur.statut in ("finished", "abandoned"):
        return render_template(
            "fin.html",
            etat=controleur.etat(),
            exercices=(
                controleur.seance.exporter_resultats() if controleur.seance else []
            ),
        )

    return render_template("index.html")


# ==========================================
# ETAT
# ==========================================


@app.route("/etat")
def etat():

    etat_session = controleur.etat()
    etat = controleur.etat_seance

    return jsonify(
        {
            "position_actuelle": etat.position_actuelle,
            "exercice_actuel": etat.exercice_actuel,
            "commentaire_exercice": (
                controleur.seance.bloc_actuel.commentaire
                if controleur.seance and controleur.seance.bloc_actuel
                else ""
            ),
            "poids": etat.poids,
            "stage": etat.stage,
            "etape_libelle": etat.etape_libelle,
            "erreur": etat.erreur,
            "consigne": etat.consigne,
            "fiche": etat.fiche,
        "fiche_suivante": etat.fiche_suivante,
            "repetitions": etat.repetitions,
            "repetitions_cibles": etat.repetitions_cibles,
            "test_max": etat.test_max,
            "serie_actuelle": etat.serie_actuelle,
            "nombre_series": etat.nombre_series,
            "phase": etat.phase,
            "temps_repos_restant": etat.temps_repos_restant,
            "duree_session": controleur.seance.duree_totale if controleur.seance else 0,
            "temps_amrap_restant": etat.temps_amrap_restant,
            "maintien_termine": etat.maintien_termine,
            "progression_maintien": etat.progression_maintien,
            "progression_preparation": etat.progression_preparation,
            "mode": etat.mode,
            "temps_maintien": etat.temps_maintien,
            "duree_maintien": etat.duree_maintien,
            "temps_chrono": etat.temps_chrono,
            "chrono_termine": etat.chrono_termine,
            "temps_echauffement": etat.temps_echauffement,
            "duree_echauffement": etat.duree_echauffement,
            "prochaine_etape": etat.prochaine_etape,
            "statut_session": etat_session["statut"],
            "seance_id": etat_session["seance_id"],
            "series_terminees": etat_session["series_terminees"],
            "exercices": etat_session["exercices"],
            "echauffements": etat_session["echauffements"],
            "echauffements_termines": etat_session["echauffements_termines"],
            "dans_echauffement": etat_session["dans_echauffement"],
            "nombre_series_total": etat_session["nombre_series_total"],
            "commandes_autorisees": etat_session["commandes_autorisees"],
        }
    )


@app.route("/api/seances")
def seances_disponibles():
    return jsonify(controleur.catalogue())


@app.route("/creer-seance")
def creer_seance_page():
    return render_template(
        "creer_seance.html",
        exercices=catalogue_exercices(),
        echauffements=catalogue_echauffements(),
    )


@app.route("/editer-seance/<nom>")
def editer_seance_page(nom):
    seance = controleur.catalogue().get(nom)
    if seance is None:
        return "Séance introuvable", 404
    return render_template(
        "editer_seance.html",
        exercices=catalogue_exercices(),
        echauffements=catalogue_echauffements(),
        seance_nom=nom,
        seance_exercices=seance["exercices"],
    )


@app.route("/api/seances", methods=["POST"])
def creer_seance_api():
    donnees = request.get_json(silent=True) or {}
    try:
        controleur.creer_seance_personnalisee(donnees.get("nom"), donnees.get("blocs"))
        return jsonify({"ok": True}), 201
    except (KeyError, ValueError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400


@app.route("/api/seances/<nom>", methods=["DELETE"])
def supprimer_seance_api(nom):
    try:
        controleur.supprimer_seance_personnalisee(nom)
        return jsonify({"ok": True})
    except KeyError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404


@app.route("/api/seances/<nom>", methods=["PUT"])
def modifier_seance_api(nom):
    donnees = request.get_json(silent=True) or {}
    nouveau_nom = (donnees.get("nom") or nom).strip()
    blocs = donnees.get("blocs")

    try:
        # La séance est d'abord validée sous son nouveau nom : si un exercice
        # est inconnu, rien n'est supprimé ni renommé.
        controleur.modifier_configuration(nouveau_nom, blocs)
        if nouveau_nom != nom:
            try:
                controleur.supprimer_seance_personnalisee(nom)
            except KeyError:
                pass  # séance intégrée sans surcharge enregistrée
            renommer_seance(nom, nouveau_nom)
        return jsonify({"ok": True, "nom": nouveau_nom})
    except (KeyError, ValueError, RuntimeError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400


@app.route("/api/seances/<nom>/cible-manuelle/<exercice>", methods=["DELETE"])
def retirer_cible_manuelle_api(nom, exercice):
    try:
        controleur.retirer_cible_manuelle(nom, exercice)
        return jsonify({"ok": True})
    except KeyError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404


@app.route("/api/seance/selectionner", methods=["POST"])
def selectionner_seance():
    donnees = request.get_json(silent=True) or {}
    nom = donnees.get("nom")
    if not nom:
        return jsonify({"ok": False, "erreur": "Le nom de séance est requis"}), 400
    if nom == "test" and donnees.get("exercice") and donnees.get("mode"):

        def selectionner_test_et_preparer():
            controleur.selectionner_test(donnees["exercice"], donnees["mode"])
            etat = controleur.etat()
            # Une séance de test est enregistrée sous le nom de son exercice :
            # c'est ce nom-là qu'il faut interroger pour retrouver le dernier
            # essai, « test » n'ayant jamais rien ramené.
            etat["derniere_performance"] = derniere_performance(donnees["exercice"])
            return etat

        return executer_commande(selectionner_test_et_preparer)

    def selectionner_et_preparer():
        controleur.selectionner(nom)
        etat = controleur.etat()
        etat["derniere_performance"] = derniere_performance(nom)
        return etat

    return executer_commande(selectionner_et_preparer)


@app.route("/api/seance/demarrer", methods=["POST"])
def demarrer_seance():
    def demarrer_et_retourner_etat():
        controleur.demarrer()
        return controleur.etat()

    return executer_commande(demarrer_et_retourner_etat)


@app.route("/api/seance/pause", methods=["POST"])
def mettre_en_pause():
    return executer_commande(controleur.mettre_en_pause)


@app.route("/api/seance/reprendre", methods=["POST"])
def reprendre_seance():
    return executer_commande(controleur.reprendre)


@app.route("/api/serie/<commande>", methods=["POST"])
def commander_serie(commande):
    commandes = {
        "reset": controleur.remettre_serie_a_zero,
        "recommencer": controleur.recommencer_serie,
        "precedente": controleur.serie_precedente,
        "suivante": controleur.serie_suivante,
        "refaire": controleur.refaire_derniere_serie,
        "terminer": controleur.terminer_serie,
    }
    if commande not in commandes:
        return jsonify({"ok": False, "erreur": "Commande inconnue"}), 404
    donnees = request.get_json(silent=True) or {}
    if commande == "terminer":
        repetitions = donnees.get("repetitions", controleur.etat_seance.repetitions)
        # Même règle que le geste bras en X : la durée se lit dans le compteur
        # du mode courant, jamais dans le premier compteur non nul venu.
        duree = donnees.get(
            "duree",
            duree_realisee(
                controleur.seance.bloc_actuel if controleur.seance else None,
                controleur.etat_seance,
            ),
        )
        return executer_commande(
            lambda: controleur.terminer_serie(repetitions=repetitions, duree=duree)
        )
    return executer_commande(commandes[commande])


@app.route("/api/pause/passer", methods=["POST"])
def passer_pause():
    return executer_commande(controleur.passer_pause)


@app.route("/api/seance/terminer", methods=["POST"])
def terminer_seance():
    return executer_commande(controleur.terminer_seance)


@app.route("/api/seance/abandonner", methods=["POST"])
def abandonner_seance():
    return executer_commande(controleur.abandonner)


@app.route("/nouvelle")
def nouvelle_seance():
    try:
        controleur.nouvelle_seance()
    except RuntimeError:
        return redirect("/")
    return redirect("/")


# ==========================================
# GENERATEUR VIDEO
# ==========================================


def generer_video():

    dernier_id = -1

    while True:

        frame = flux.latest_frame

        # Sans ce garde-fou, la même image est renvoyée en boucle aussi vite
        # que possible : le flux sature et la vidéo prend du retard.
        if frame is None or flux.frame_id == dernier_id:

            time.sleep(0.005)

            continue

        dernier_id = flux.frame_id

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n"
            b"Content-Length: "
            + str(len(frame)).encode()
            + b"\r\n\r\n"
            + frame
            + b"\r\n"
        )


# ==========================================
# ROUTE VIDEO
# ==========================================


@app.route("/video")
def video():
    return Response(
        generer_video(), mimetype="multipart/x-mixed-replace; boundary=frame"
    )


def ouvrir_navigateur():
    time.sleep(1)  # laisse le temps à Flask de démarrer
    webbrowser.open("http://127.0.0.1:5000")


def lancer_site():
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)


@app.route("/historique")
def historique():

    donnees = recuperer_historique()

    montees = montees_de_niveau(donnees)
    return render_template(
        "historique.html",
        seances=seances_entrainement(donnees),
        montees=montees,
        montees_ligue=moteur_ligues.montees_de_ligue(montees),
        jugements=jugements_par_seance(donnees),
        detail=False,
    )


@app.route("/bienvenue")
def page_bienvenue():
    """Questionnaire de materiel : la seule etape avant la premiere seance.

    Le tunnel de calibration exercice par exercice a disparu : un exercice sans
    donnees se teste desormais **en seance** (`progression.objectifs.a_calibrer`),
    au moment ou on le rencontre. Ne restait donc a demander que ce qu'aucune
    camera ne peut deviner : le materiel.
    """
    return _page_materiel(premiere_fois=True)


@app.route("/materiel")
def page_materiel():
    """Le meme questionnaire, en modification. Meme template, meme API."""
    return _page_materiel(premiere_fois=False)


def _page_materiel(premiere_fois):
    return render_template(
        "bienvenue.html",
        premiere_fois=premiere_fois,
        seances=catalogue() if premiere_fois else {},
        poids_reference=list(POIDS_REFERENCE),
        accessoires=ACCESSOIRES,
        materiel=materiel_du_profil(),
    )


@app.route("/profil")
def page_profil():
    """La page du profil connecté : qui je suis, ce que je possède.

    Volontairement **hors de `ROUTES_ONBOARDING`** : un profil neuf doit
    d'abord déclarer son matériel, et une route de trop dans cet ensemble
    ouvrirait l'application entière.
    """
    profil = utilisateur_connecte()
    donnees = recuperer_historique()
    materiel = normaliser(profil.get("materiel"))
    halteres = materiel.get("halteres") or {}
    paires = sorted(int(p) for p, q in halteres.items() if q >= 2)
    seuls = sorted(int(p) for p, q in halteres.items() if q == 1)

    morceaux = []
    if paires:
        morceaux.append("paires : " + ", ".join(f"{p} kg" for p in paires))
    if seuls:
        morceaux.append("seuls : " + ", ".join(f"{p} kg" for p in seuls))
    if materiel.get("accessoires"):
        morceaux.append("accessoires : " + ", ".join(materiel["accessoires"]))

    etats = etats_niveaux(donnees)
    return render_template(
        "profil.html",
        nombre_seances=len(donnees),
        # Le nombre d'exercices dont l'historique prouve un niveau : c'est ce
        # que le moteur sait de cette personne, pas ce qu'elle a essayé.
        nombre_niveaux=sum(1 for etat in etats.values() if etat["niveau"]),
        # Le niveau général se dérive du même calcul : chaque niveau acquis
        # rapporte de l'XP, et l'XP fait monter le profil. Rien de plus n'est
        # lu, et surtout rien n'est stocké.
        general=moteur_ligues.niveau_general(moteur_ligues.xp_totale(etats)),
        resume_materiel=" · ".join(morceaux) or "Rien de déclaré.",
    )


@app.route("/api/profil", methods=["POST"])
def enregistrer_profil():
    """Les mesures du corps. Aucune ne pilote le barème.

    `rafraichir()` est obligatoire : le profil connecté transporte ces
    colonnes, et le garde de requête les relit sans repasser par la base.
    """
    donnees = request.get_json(silent=True) or {}
    profil = utilisateur_connecte()

    mesures, erreur = _mesures_valides(donnees)
    if erreur:
        return jsonify({"ok": False, "erreur": erreur}), 400

    definir_mesures(profil["id"], mesures)
    rafraichir()
    return jsonify({"ok": True})


@app.route("/api/materiel", methods=["POST"])
def enregistrer_materiel():
    """Enregistre l'inventaire, et referme le tunnel d'accueil au passage.

    Les deux ecritures vont ensemble : declarer son materiel *est* l'accueil,
    et les separer laisserait un profil coince sur /bienvenue apres avoir
    repondu. `rafraichir()` est obligatoire — le profil connecte transporte ces
    deux colonnes, et le garde de requete les relit sans repasser par la base.
    """
    donnees = request.get_json(silent=True) or {}
    materiel = normaliser(donnees.get("materiel"))
    profil = utilisateur_connecte()

    definir_materiel(profil["id"], materiel)

    seance = donnees.get("seance")
    if not profil.get("onboarding_termine"):
        definir_onboarding(
            profil["id"],
            termine=True,
            seance_initiale=seance if seance in catalogue() else None,
        )
    rafraichir()
    return jsonify({"ok": True, "materiel": materiel})


@app.route("/exercices")
def page_exercices():
    """Catalogue des mouvements : la porte d'entrée des fiches.

    Les exercices comptabilisés et les échauffements restent séparés, comme
    partout ailleurs : ils ne se lisent pas de la même façon (les premiers ont
    un niveau, les seconds non).
    """
    etats = etats_niveaux(recuperer_historique())
    return render_template(
        "exercices.html",
        onglet="exercices",
        exercices=catalogue_exercices(),
        echauffements=catalogue_echauffements(),
        niveaux=etats,
        ligues=moteur_ligues.ligues_par_exercice(etats),
    )


@app.route("/exercice/<nom>")
def page_exercice(nom):
    """Fiche d'un mouvement : comment le faire, et où j'en suis dessus.

    Elle a absorbé l'écran des records. Les deux disaient la même chose du
    même mouvement depuis deux pages : un niveau dit **où l'on en est**, le
    graphe **comment on y est arrivé**, et le recalage sert quand l'historique
    ne peut pas le prouver. Il n'y a plus qu'un endroit où lire un exercice.
    """
    fiche = fiche_mouvement(nom)
    if fiche is None:
        abort(404)
    etat = etat_niveau(nom)
    return render_template(
        "exercice.html",
        onglet="exercices",
        fiche=fiche,
        etat=etat,
        ligue=moteur_ligues.ligue_exercice(nom, (etat or {}).get("niveau")),
        statistique=statistiques_exercices(recuperer_historique()).get(nom),
    )


@app.route("/records")
def records():
    """Redirection : les records vivent désormais sur la fiche de l'exercice.

    Une redirection et non une 404 : les liens profonds `/records#exercice-…`
    ont pu être mis en favori, et `historique.html` / `programmes.html` en
    fabriquaient à chaque ligne.
    """
    return redirect("/exercices", code=301)


@app.route("/programmes")
def programmes():
    profil = utilisateur_connecte() or {}
    return render_template(
        "programmes.html",
        programmes=etats_programmes(recuperer_historique()),
        # La page liste tout ; l'accueil n'en montre qu'un. Le marquer ici, c'est
        # rendre visible lequel des deux rôles chaque programme joue.
        programme_suivi=profil.get("programme_choisi"),
    )


def exercices_avec_bareme():
    """Exercices proposables dans un programme, avec l'unité de leur barème.

    L'éditeur s'en sert pour intituler la colonne « cible » — répétitions ou
    secondes — selon l'exercice choisi.
    """
    return {
        nom: {
            "nom": nom,
            "unite": unite(nom),
        }
        for nom in sorted(exercices_suivis())
    }


def _ancre(nom, defaut):
    """Normalise un nom en identifiant d'URL stable (« Rowing penché » -> rowing-penche)."""
    sans_accents = unicodedata.normalize("NFKD", nom or "")
    sans_accents = "".join(c for c in sans_accents if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", sans_accents.lower()).strip("-") or defaut


def _cle_programme(nom):
    """Transforme un nom en clé d'URL stable (« Road to TKT » -> road-to-tkt)."""
    return _ancre(nom, "programme")


@app.route("/api/programme-choisi", methods=["POST"])
def choisir_programme():
    """Le programme que je suis en ce moment. Un seul à la fois, par profil."""
    donnees = request.get_json(silent=True) or {}
    cle = donnees.get("cle") or None
    if cle is not None and cle not in tous_les_programmes():
        return jsonify({"erreur": "Programme inconnu"}), 404

    profil = utilisateur_connecte()
    definir_programme_choisi(profil["id"], cle)
    # Sans ce rafraîchissement, la session garderait l'ancien choix et l'accueil
    # afficherait encore le programme précédent.
    rafraichir()
    return jsonify({"ok": True, "cle": cle})


@app.route("/creer-programme")
def creer_programme_page():
    return render_template(
        "editer_programme.html",
        exercices=exercices_avec_bareme(),
        programme_cle="",
        programme={"nom": "", "description": "", "exigences": []},
        libelle_charge=LIBELLE_CHARGE,
        supprimable=False,
    )


@app.route("/editer-programme/<cle>")
def editer_programme_page(cle):
    programme = tous_les_programmes().get(cle)
    if programme is None:
        return redirect("/programmes")
    return render_template(
        "editer_programme.html",
        exercices=exercices_avec_bareme(),
        programme_cle=cle,
        programme=programme,
        libelle_charge=LIBELLE_CHARGE,
        # Un programme livré dans le code et jamais modifié n'a rien sur le
        # disque : proposer de le supprimer mènerait à une erreur.
        supprimable=est_personnalise(cle),
    )


@app.route("/api/programmes", methods=["POST"])
def creer_programme_api():
    donnees = request.get_json(silent=True) or {}
    try:
        cle = enregistrer_programme(
            donnees.get("cle") or _cle_programme(donnees.get("nom")), donnees
        )
        return jsonify({"ok": True, "cle": cle}), 201
    except (KeyError, ValueError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400


@app.route("/api/programmes/<cle>", methods=["PUT"])
def modifier_programme_api(cle):
    donnees = request.get_json(silent=True) or {}
    try:
        enregistrer_programme(cle, donnees)
        return jsonify({"ok": True, "cle": cle})
    except (KeyError, ValueError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400


@app.route("/api/programmes/<cle>", methods=["DELETE"])
def supprimer_programme_api(cle):
    try:
        supprimer_programme(cle)
        return jsonify({"ok": True})
    except KeyError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404


@app.route("/api/niveaux/<nom>/ancrage", methods=["POST"])
def ancrer_niveau(nom):
    """Recale le niveau d'un exercice à partir d'une performance réalisée.

    On ne demande pas un numéro de niveau — personne ne sait ce que vaut
    « niveau 27 ». On demande une performance (séries, cible, charge), et le
    barème en déduit le niveau : c'est aussi la forme que prendra le test de
    calibration d'un nouvel utilisateur.
    """
    donnees = request.get_json(silent=True) or {}
    if not est_suivi_par_le_moteur(nom):
        return jsonify({"ok": False, "erreur": f"{nom} n'a pas de barème"}), 404

    try:
        series = int(donnees.get("series") or 0)
        cible = float(donnees.get("cible") or 0)
        poids = float(donnees.get("poids") or 0)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "erreur": "Valeurs invalides"}), 400

    niveau = niveau_pour(nom, poids, series, cible)
    if niveau is None:
        premier = palier(nom, 1)
        return (
            jsonify(
                {
                    "ok": False,
                    "erreur": (
                        "Cette performance n'atteint pas le premier palier "
                        f"({premier.resume()})."
                    ),
                }
            ),
            400,
        )

    enregistrer_ancrage(nom, niveau, donnees.get("raison", ""))
    return jsonify({"ok": True, "niveau": niveau, "palier": palier(nom, niveau).resume()})


@app.route("/api/niveaux/<nom>/ancrage", methods=["DELETE"])
def supprimer_ancrage_niveau(nom):
    supprimes = supprimer_ancrages(nom)
    if not supprimes:
        return jsonify({"ok": False, "erreur": "Aucun ancrage à supprimer"}), 404
    return jsonify({"ok": True})


@app.route("/api/niveaux/<nom>/ancrages")
def lister_ancrages_niveau(nom):
    """Journal complet des ancrages posés sur un exercice, le plus récent en tête."""
    ancrages = recuperer_historique_ancrages(nom)
    for ancrage in ancrages:
        ancrage["palier"] = palier(nom, ancrage["niveau"]).resume()
    return jsonify({"ok": True, "ancrages": ancrages})


@app.route("/api/niveaux/<nom>/ancrage/<int:id_ancrage>", methods=["DELETE"])
def supprimer_un_ancrage_niveau(nom, id_ancrage):
    supprimes = supprimer_ancrage(id_ancrage)
    if not supprimes:
        return jsonify({"ok": False, "erreur": "Ancrage introuvable"}), 404
    return jsonify({"ok": True})


@app.route("/historique/<int:seance_id>")
def detail_historique(seance_id):
    donnees = recuperer_historique()
    seance = next(
        (element for element in donnees if element["id"] == seance_id),
        None,
    )
    if seance is None:
        return "Seance introuvable", 404
    return render_template(
        "historique.html",
        seances=[seance],
        montees=montees_de_niveau(donnees),
        jugements=jugements_par_seance(donnees),
        detail=True,
    )


@app.route("/api/historique/<int:seance_id>", methods=["DELETE"])
def supprimer_seance_historique_api(seance_id):
    try:
        supprimer_seance(seance_id)
        return jsonify({"ok": True})
    except (KeyError, ValueError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404


@app.route("/api/historique/<int:seance_id>/exercice/<nom>", methods=["DELETE"])
def supprimer_exercice_historique_api(seance_id, nom):
    try:
        supprimer_exercice_de_seance(seance_id, nom)
        return jsonify({"ok": True})
    except (KeyError, ValueError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404


@app.route("/api/historique/<int:seance_id>/ressentis")
def lire_ressentis_api(seance_id):
    """Réussite et ressenti de chaque exercice d'une séance.

    Sert aux écrans à ne proposer que les réponses qui ont un effet : après
    une réussite on demande si c'était facile, après un échec si c'était trop
    dur. Une séance inconnue renvoie un dictionnaire vide plutôt qu'une 404 —
    l'écran de fin interroge cette route pendant que la séance est peut-être
    encore en cours d'écriture par le thread caméra.
    """
    return jsonify({"ok": True, "echelle": list(ECHELLE),
                    "exercices": evaluation_seance(seance_id)})


@app.route("/api/historique/<int:seance_id>/jalons")
def lire_jalons_api(seance_id):
    """Ce qu'une séance a fait franchir : niveaux, ligues, XP.

    Pendant exact de la route des ressentis, et pour la même raison : la séance
    est écrite par le **thread caméra**, donc `fin.html` n'a pas son identifiant
    au moment du rendu. Il l'attend dans `/etat` puis vient chercher ses jalons
    ici. Ne pas déplacer ce calcul dans `enregistrer_seance` : il arriverait
    toujours trop tôt pour être affiché.

    Une séance inconnue rend des jalons vides plutôt qu'une 404 — l'écran
    interroge cette route pendant que l'écriture est peut-être en cours.
    """
    donnees = recuperer_historique()
    montees = montees_de_niveau(donnees)
    de_la_seance = montees.get(seance_id, {})
    etats = etats_niveaux(donnees)
    return jsonify({
        "ok": True,
        "montees_niveau": de_la_seance,
        "montees_ligue": moteur_ligues.montees_de_ligue(montees).get(seance_id, {}),
        "xp_gagnee": moteur_ligues.xp_gagnee(de_la_seance),
        "niveau_general": moteur_ligues.niveau_general(
            moteur_ligues.xp_totale(etats)
        ),
    })


@app.route("/api/historique/<int:seance_id>/ressentis", methods=["POST"])
def enregistrer_ressentis_api(seance_id):
    donnees = request.get_json(silent=True) or {}
    ressentis = donnees.get("ressentis") or {}
    if not isinstance(ressentis, dict):
        return jsonify({"ok": False, "erreur": "Format attendu : un objet"}), 400
    try:
        modifiees = enregistrer_ressentis(seance_id, ressentis)
    except ValueError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400
    return jsonify({"ok": True, "modifiees": modifiees})
