from flask import Flask, render_template, jsonify, Response
from historique.database import recuperer_historique
import webbrowser
import state
import time


app = Flask(__name__)


# ==========================================
# PAGE PRINCIPALE
# ==========================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# ==========================================
# ETAT
# ==========================================

@app.route("/etat")
def etat():

    return jsonify({

        "position_actuelle":
            state.position_actuelle,

        "exercice_actuel":
            state.exercice_actuel,

        "poids": state.poids,

        "stage": state.stage,

        "repetitions":
            state.repetitions,

        "repetitions_cibles":
            state.repetitions_cibles,

        "serie_actuelle":
            state.serie_actuelle,

        "nombre_series":
            state.nombre_series,

        "phase":
            state.phase,

        "temps_restant":
            state.temps_restant,

        "maintien_termine":
            state.maintien_termine,

        "progression_maintien":
            state.progression_maintien,

        "progression_preparation": state.progression_preparation,
        "mode":
            state.mode,

        "temps_maintien":
            state.temps_maintien,

        "duree_maintien":
            state.duree_maintien,
            
        "temps_chrono": state.temps_chrono,

        "chrono_termine": state.chrono_termine,
    })


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
        seances=donnees
    )