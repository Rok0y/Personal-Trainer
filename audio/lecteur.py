import pygame
import os
import threading
import queue
import time

pygame.mixer.init()

DOSSIER_SONS = os.path.join(
    os.path.dirname(__file__),
    "Fichiers"
)

file_audio = queue.PriorityQueue()

compteur_audio = 0


def lecteur_audio():
    while True:
        priorite, _, nom = file_audio.get()

        chemin = nom if os.path.isabs(nom) else os.path.join(DOSSIER_SONS, nom)

        if os.path.exists(chemin):
            son = pygame.mixer.Sound(chemin)
            if os.path.basename(chemin) == "bip.wav":
                son.set_volume(1.0)
            son.play()
            while pygame.mixer.get_busy():
                time.sleep(0.05)
        else:
            print("\n" + "=" * 60)
            print("AUDIO MANQUANT À ENREGISTRER")
            print(os.path.basename(chemin))
            print("=" * 60 + "\n")

        file_audio.task_done()


def jouer_texte(texte, priorite=5):
    """Génère (ou récupère du cache) l'audio TTS pour ce texte, puis le joue."""
    from audio.tts import generer  # import local pour éviter une dépendance circulaire

    global compteur_audio

    if priorite >= 5:
        vider_petits_sons()

    compteur_audio += 1
    chemin = generer(texte)

    file_audio.put((-priorite, compteur_audio, str(chemin)))


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