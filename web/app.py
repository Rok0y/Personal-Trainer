from flask import Flask, render_template, jsonify, Response, request, redirect
from historique.database import recuperer_historique
from session.controleur import SessionManager
from session.seances import catalogue_exercices
import webbrowser
import state
import time
import logging

class FiltreEtat(logging.Filter):
    def filter(self, record):
        return "GET /etat" not in record.getMessage()

logging.getLogger("werkzeug").addFilter(FiltreEtat())


app = Flask(__name__)
controleur = SessionManager()


def meilleurs_volumes(seances):
    meilleurs = {}
    for seance in seances:
        if seance.get("statut") == "abandoned":
            continue
        for exercice in seance.get("exercices", []):
            if exercice.get("mode") != "repetitions":
                continue
            volume = (exercice.get("poids") or 0) * (exercice.get("series") or 0) * (exercice.get("repetitions") or 0)
            nom = exercice.get("nom")
            meilleurs[nom] = max(meilleurs.get(nom, 0), volume)
    return meilleurs


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
        return render_template(
            "accueil.html",
            seances=controleur.catalogue(),
            selection=controleur.nom_selectionne,
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
        "poids": state.poids,
        "stage": state.stage,
        "repetitions":state.repetitions,
        "repetitions_cibles":state.repetitions_cibles,
        "serie_actuelle":state.serie_actuelle,
        "nombre_series":state.nombre_series,
        "phase":state.phase,
        "temps_repos_restant": state.temps_repos_restant,
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
        "nombre_series_total": etat_session["nombre_series_total"],
        "commandes_autorisees": etat_session["commandes_autorisees"],
    })


@app.route("/api/seances")
def seances_disponibles():
    return jsonify(controleur.catalogue())


@app.route("/creer-seance")
def creer_seance_page():
    return render_template("creer_seance.html", exercices=catalogue_exercices())


@app.route("/api/seances", methods=["POST"])
def creer_seance_api():
    donnees = request.get_json(silent=True) or {}
    try:
        controleur.creer_seance_personnalisee(donnees.get("nom"), donnees.get("blocs"))
        return jsonify({"ok": True}), 201
    except (KeyError, ValueError) as erreur:
        return jsonify({"ok": False, "erreur": str(erreur)}), 400


@app.route("/api/seance/selectionner", methods=["POST"])
def selectionner_seance():
    donnees = request.get_json(silent=True) or {}
    nom = donnees.get("nom")
    if not nom:
        return jsonify({"ok": False, "erreur": "Le nom de séance est requis"}), 400
    return executer_commande(lambda: controleur.selectionner(nom) and controleur.etat())


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
        seances=donnees,
        meilleurs=meilleurs_volumes(donnees),
        detail=False,
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
