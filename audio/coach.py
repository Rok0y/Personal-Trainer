import random
from audio.lecteur import jouer


messages = {

    "rep": [
        "rep.wav"
    ],
    "debut": [
        "debut.wav"
    ],

    "avant_derniere": [
        "avant_derniere.wav"
    ],

    "derniere_rep": [
        "derniere_rep.wav"
    ],

    "fin_serie": [
        "fin_serie.wav"
    ],

    "repos": [
        "repos.wav"
    ],

    "changement_exercice": [
        "changement_exercice.wav"
    ],

    "fin_seance": [
        "fin_seance.wav"
    ],

    "debut_serie": [
        "debut_serie.wav"
    ],

    "preparation": [
        "preparation.wav"
    ]
}


priorites = {

    "rep": 1,

    "debut_serie": 5,

    "avant_derniere": 5,

    "derniere_rep": 10,

    "fin_serie": 10,

    "repos": 8,

    "changement_exercice": 8,

    "fin_seance": 10
}


def coach(event):

    if event not in messages:
        return

    son = random.choice(
        messages[event]
    )

    jouer(
        son,
        priorites.get(event, 5)
    )

def coach(event, valeur=None):

    if event == "compteur":

        son = f"{valeur}.wav"

        jouer(
            son,
            1
        )

        return


    if event not in messages:
        return


    son = random.choice(
        messages[event]
    )

    jouer(
        son,
        priorites.get(event, 5)
    )