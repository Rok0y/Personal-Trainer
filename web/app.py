import logging
import re
import time
import unicodedata
import webbrowser

from flask import Flask, Response, jsonify, redirect, render_template, request

from core import state
from core.utilisateur import connecter, deconnecter, utilisateur_connecte
from historique.database import (
    creer_utilisateur,
    derniere_performance,
    enregistrer_ancrage,
    enregistrer_ressentis,
    lister_utilisateurs,
    recuperer_historique,
    recuperer_historique_ancrages,
    renommer_seance,
    renommer_utilisateur,
    statistiques_exercices,
    supprimer_ancrage,
    supprimer_ancrages,
    supprimer_exercice_de_seance,
    supprimer_seance,
)
from progression.niveaux import etats_niveaux, montees_de_niveau
from progression.paliers import (
    est_suivi_par_le_moteur,
    exercices_suivis,
    niveau_pour,
    palier,
    unite,
)
from progression.programmes import (
    CHARGE_TOTALE,
    enregistrer_programme,
    est_personnalise,
    etats_programmes,
    libelle_charge,
    prochaine_seance,
    supprimer_programme,
    tous_les_programmes,
)
from progression.ressenti import ECHELLE, evaluation_seance, jugements_par_seance
from session.controleur import SessionManager
from session.moteur import duree_realisee
from session.seances import (
    catalogue_echauffements,
    catalogue_exercices,
    nombre_halteres,
)


class FiltreEtat(logging.Filter):
    def filter(self, record):
        return "GET /etat" not in record.getMessage()


logging.getLogger("werkzeug").addFilter(FiltreEtat())


app = Flask(__name__)
controleur = SessionManager()

#: Points d'entrée accessibles sans profil connecté : l'écran de connexion
#: lui-même et ce qu'il appelle. Tout le reste passe par `_exiger_un_profil`.
ROUTES_SANS_PROFIL = {
    "static",
    "page_connexion",
    "lister_utilisateurs_api",
    "creer_utilisateur_api",
    "renommer_utilisateur_api",
    "connecter_profil_api",
    "deconnecter_profil_api",
}


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


@app.context_processor
def _profil_dans_les_templates():
    """Rend le profil connecté disponible partout, sans le passer route par route."""
    return {"profil": utilisateur_connecte()}


def meilleurs_volumes(seances):
    return {
        nom: stat["meilleur_volume"]["valeur"]
        for nom, stat in statistiques_exercices(seances).items()
        if stat["meilleur_volume"]["valeur"]
    }


def seances_du_record(seances):
    """Id de la séance qui détient le record de volume, par exercice.

    Sert à n'afficher le badge « nouveau record » que sur la séance qui l'a
    réellement établi, plutôt que sur toutes celles qui manient du poids.
    """
    return {
        nom: stat["meilleur_volume"]["seance_id"]
        for nom, stat in statistiques_exercices(seances).items()
        if stat["meilleur_volume"]["valeur"]
    }


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
    return render_template("connexion.html", profils=lister_utilisateurs())


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
    try:
        _ouvrir_session(profil["id"])
    except RuntimeError as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 409
    return jsonify({"ok": True, "utilisateur": profil})


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
        # Résumé des programmes pour l'accueil : où j'en suis, et surtout
        # quelle séance enchaîner maintenant.
        programmes = etats_programmes(historique)
        for cle, programme in programmes.items():
            programme["prochaine"] = prochaine_seance(cle, historique, seances)
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
            programmes=programmes,
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

    return jsonify(
        {
            "position_actuelle": state.position_actuelle,
            "exercice_actuel": state.exercice_actuel,
            "commentaire_exercice": (
                controleur.seance.bloc_actuel.commentaire
                if controleur.seance and controleur.seance.bloc_actuel
                else ""
            ),
            "poids": state.poids,
            "stage": state.stage,
            "erreur": state.erreur,
            "repetitions": state.repetitions,
            "repetitions_cibles": state.repetitions_cibles,
            "serie_actuelle": state.serie_actuelle,
            "nombre_series": state.nombre_series,
            "phase": state.phase,
            "temps_repos_restant": state.temps_repos_restant,
            "duree_session": controleur.seance.duree_totale if controleur.seance else 0,
            "temps_amrap_restant": state.temps_amrap_restant,
            "maintien_termine": state.maintien_termine,
            "progression_maintien": state.progression_maintien,
            "progression_preparation": state.progression_preparation,
            "mode": state.mode,
            "temps_maintien": state.temps_maintien,
            "duree_maintien": state.duree_maintien,
            "temps_chrono": state.temps_chrono,
            "chrono_termine": state.chrono_termine,
            "temps_echauffement": state.temps_echauffement,
            "duree_echauffement": state.duree_echauffement,
            "prochaine_etape": state.prochaine_etape,
            "statut_session": etat_session["statut"],
            "seance_id": etat_session["seance_id"],
            "series_terminees": etat_session["series_terminees"],
            "exercices": etat_session["exercices"],
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
            etat["derniere_performance"] = derniere_performance("test")
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
        "terminer": controleur.terminer_serie,
    }
    if commande not in commandes:
        return jsonify({"ok": False, "erreur": "Commande inconnue"}), 404
    donnees = request.get_json(silent=True) or {}
    if commande == "terminer":
        repetitions = donnees.get("repetitions", state.repetitions)
        # Même règle que le geste bras en X : la durée se lit dans le compteur
        # du mode courant, jamais dans le premier compteur non nul venu.
        duree = donnees.get(
            "duree",
            duree_realisee(
                controleur.seance.bloc_actuel if controleur.seance else None, state
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

        frame = state.latest_frame

        # Sans ce garde-fou, la même image est renvoyée en boucle aussi vite
        # que possible : le flux sature et la vidéo prend du retard.
        if frame is None or state.frame_id == dernier_id:

            time.sleep(0.005)

            continue

        dernier_id = state.frame_id

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

    return render_template(
        "historique.html",
        seances=seances_entrainement(donnees),
        meilleurs=meilleurs_volumes(donnees),
        record_seance_id=seances_du_record(donnees),
        montees=montees_de_niveau(donnees),
        jugements=jugements_par_seance(donnees),
        detail=False,
    )


@app.route("/records")
def records():
    donnees = recuperer_historique()
    return render_template(
        "records.html",
        statistiques=statistiques_exercices(donnees),
        niveaux=etats_niveaux(donnees),
    )


@app.route("/programmes")
def programmes():
    return render_template(
        "programmes.html",
        programmes=etats_programmes(recuperer_historique()),
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
            # Sert à l'éditeur pour afficher l'équivalent par haltère : la
            # division ne s'applique qu'aux mouvements bilatéraux.
            "halteres": nombre_halteres(nom),
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


#: Permet aux templates de fabriquer un lien profond vers la fiche d'un
#: exercice sur `/records` : `/records#exercice-{{ nom|ancre }}`. Les deux
#: extrémités du lien passent par ce filtre, donc elles ne peuvent pas diverger.
app.jinja_env.filters["ancre"] = lambda nom: _ancre(nom, "exercice")


@app.route("/creer-programme")
def creer_programme_page():
    return render_template(
        "editer_programme.html",
        exercices=exercices_avec_bareme(),
        programme_cle="",
        programme={"nom": "", "description": "", "exigences": []},
        libelle_charge=libelle_charge(),
        charge_totale=CHARGE_TOTALE,
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
        libelle_charge=libelle_charge(),
        charge_totale=CHARGE_TOTALE,
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
        meilleurs=meilleurs_volumes(donnees),
        record_seance_id=seances_du_record(donnees),
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
