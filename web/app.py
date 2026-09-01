from flask import Flask, render_template, jsonify, Response, request, redirect
from historique.database import (
    recuperer_historique,
    statistiques_exercices,
    derniere_performance,
    renommer_seance,
)
from session.controleur import SessionManager
from session.seances import catalogue_exercices
import webbrowser
import state
import time
import logging

# Ces deux fonctions doivent être ajoutées à historique/database.py pour que la
# suppression fonctionne (voir le gabarit fourni séparément). Import protégé pour
# ne pas empêcher le lancement du site tant qu'elles n'existent pas.
try:
    from historique.database import supprimer_seance, supprimer_exercice_de_seance
except ImportError:
    supprimer_seance = None
    supprimer_exercice_de_seance = None

class FiltreEtat(logging.Filter):
    def filter(self, record):
        return "GET /etat" not in record.getMessage()

logging.getLogger("werkzeug").addFilter(FiltreEtat())


app = Flask(__name__)
controleur = SessionManager()


def meilleurs_volumes(seances):
    return {
        nom: stat["meilleur_volume"]["valeur"]
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
        return jsonify({
            "ok": True,
            "resultat": resultat,
            "etat": controleur.etat(),
        })
    except (KeyError, RuntimeError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 409


# ==========================================
# PAGE PRINCIPALE
# ==========================================

@app.route("/")
def index():

    if controleur.statut in ("idle", "ready"):
        seances = controleur.catalogue()
        dernieres_series = {}
        for seance in recuperer_historique():
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
        )

    if controleur.statut in ("finished", "abandoned"):
        return render_template(
            "fin.html",
            etat=controleur.etat(),
            exercices=controleur.seance.exporter_resultats() if controleur.seance else [],
        )

    return render_template(
        "index.html"
    )


# ==========================================
# ETAT
# ==========================================

@app.route("/etat")
def etat():

    etat_session = controleur.etat()

    return jsonify({

        "position_actuelle":state.position_actuelle,
        "exercice_actuel":state.exercice_actuel,
        "commentaire_exercice": controleur.seance.bloc_actuel.commentaire if controleur.seance and controleur.seance.bloc_actuel else "",
        "poids": state.poids,
        "stage": state.stage,
        "erreur": state.erreur,
        "repetitions":state.repetitions,
        "repetitions_cibles":state.repetitions_cibles,
        "serie_actuelle":state.serie_actuelle,
        "nombre_series":state.nombre_series,
        "phase":state.phase,
        "temps_repos_restant": state.temps_repos_restant,
        "duree_session": controleur.seance.duree_totale if controleur.seance else 0,
        "temps_amrap_restant": state.temps_amrap_restant,
        "maintien_termine":state.maintien_termine,
        "progression_maintien":state.progression_maintien,
        "progression_preparation": state.progression_preparation,
        "mode":state.mode,
        "temps_maintien":state.temps_maintien,
        "duree_maintien":state.duree_maintien,
        "temps_chrono": state.temps_chrono,
        "chrono_termine": state.chrono_termine,
        "prochaine_etape": state.prochaine_etape,
        "statut_session": etat_session["statut"],
        "series_terminees": etat_session["series_terminees"],
        "exercices": etat_session["exercices"],
        "nombre_series_total": etat_session["nombre_series_total"],
        "commandes_autorisees": etat_session["commandes_autorisees"],
    })


@app.route("/api/seances")
def seances_disponibles():
    return jsonify(controleur.catalogue())


@app.route("/creer-seance")
def creer_seance_page():
    return render_template("creer_seance.html", exercices=catalogue_exercices())


@app.route("/editer-seance/<nom>")
def editer_seance_page(nom):
    seance = controleur.catalogue().get(nom)
    if seance is None:
        return "Séance introuvable", 404
    return render_template(
        "editer_seance.html",
        exercices=catalogue_exercices(),
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
        duree = donnees.get("duree", state.temps_maintien or state.temps_chrono)
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

    while True:

        frame = state.latest_frame

        if frame is None:

            time.sleep(0.01)

            continue


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
    return Response(generer_video(),mimetype="multipart/x-mixed-replace; boundary=frame")

def ouvrir_navigateur():
    time.sleep(1)  # laisse le temps à Flask de démarrer
    webbrowser.open("http://127.0.0.1:5000")

def lancer_site():
    app.run(host="127.0.0.1",port=5000,debug=False,threaded=True)

@app.route("/historique")
def historique():

    donnees = recuperer_historique()

    return render_template(
        "historique.html",
        seances=seances_entrainement(donnees),
        meilleurs=meilleurs_volumes(donnees),
        detail=False,
    )


@app.route("/records")
def records():
    donnees = recuperer_historique()
    return render_template(
        "records.html",
        statistiques=statistiques_exercices(donnees),
    )


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
        detail=True,
    )


@app.route("/api/historique/<int:seance_id>", methods=["DELETE"])
def supprimer_seance_historique_api(seance_id):
    if supprimer_seance is None:
        return jsonify({
            "ok": False,
            "erreur": "Fonction supprimer_seance manquante dans historique/database.py",
        }), 501
    try:
        supprimer_seance(seance_id)
        return jsonify({"ok": True})
    except (KeyError, ValueError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404


@app.route("/api/historique/<int:seance_id>/exercice/<nom>", methods=["DELETE"])
def supprimer_exercice_historique_api(seance_id, nom):
    if supprimer_exercice_de_seance is None:
        return jsonify({
            "ok": False,
            "erreur": "Fonction supprimer_exercice_de_seance manquante dans historique/database.py",
        }), 501
    try:
        supprimer_exercice_de_seance(seance_id, nom)
        return jsonify({"ok": True})
    except (KeyError, ValueError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 404