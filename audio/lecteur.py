import pygame
import os
import threading
import queue
import time

pygame.mixer.init()

DOSSIER_SONS = os.path.join(
    os.path.dirname(__file__),
    "fichiers"
)

file_audio = queue.PriorityQueue()

compteur_audio = 0


def lecteur_audio():

    while True:

        priorite, _, nom = file_audio.get()

        chemin = os.path.join(
            DOSSIER_SONS,
            nom
        )

        if os.path.exists(chemin):

            son = pygame.mixer.Sound(chemin)

            son.play()

            while pygame.mixer.get_busy():
                time.sleep(0.05)

        else:
            print("Son introuvable :", chemin)

        file_audio.task_done()


threading.Thread(
    target=lecteur_audio,
    daemon=True
).start()


def vider_petits_sons():

    temporaire = []

    while not file_audio.empty():

        item = file_audio.get()

        # On garde uniquement les sons importants
        if item[0] <= -5:
            temporaire.append(item)

    for item in temporaire:
        file_audio.put(item)


def jouer(nom, priorite=5):

    global compteur_audio

    # Les événements importants suppriment
    # les petits sons en attente
    if priorite >= 5:
        vider_petits_sons()

    compteur_audio += 1

    file_audio.put(
        (
            -priorite,
            compteur_audio,
            nom
        )
    )