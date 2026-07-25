from flask import Flask, render_template, jsonify, Response

import state


app = Flask(__name__)


@app.route("/")
def index():

    return render_template(
        "index.html"
    )


@app.route("/etat")
def etat():

    return jsonify({
        "position_actuelle": state.position_actuelle,
        "exercice_actuel": state.exercice_actuel,
        "stage": state.stage,
        "repetitions": state.repetitions
    })


@app.route("/video")
def video():

    def generer():

        while True:

            if state.frame_actuelle is not None:

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n"
                    + state.frame_actuelle
                    + b"\r\n"
                )

    return Response(
        generer(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )


def lancer_site():

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        threaded=True
    )