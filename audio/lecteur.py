import os
import queue
import threading
import time

DOSSIER_SONS = os.path.join(os.path.dirname(__file__), "Fichiers")

_lecteur_demarre = False
_audio_disponible = True
"""L'ouverture de la carte son et le démarrage du thread se font au premier
son joué, pas à l'import.

Ce module ouvrait le périphérique audio et lançait son thread dès qu'on
l'importait, si bien qu'importer `audio.coach` — ce que font `session/` et
`main.py` — suffisait à réclamer une carte son. Un serveur qui n'en a pas
plantait donc à l'import, sans avoir jamais demandé à jouer quoi que ce soit.
Une machine sans audio se contente désormais du silence.
"""

file_audio = queue.PriorityQueue()

compteur_audio = 0


def _demarrer_lecteur():
    """Ouvre la carte son et lance le thread, une seule fois.

    Une machine sans périphérique audio n'est pas une erreur : c'est le cas
    d'un serveur. On coupe le son et l'application continue.
    """
    global _lecteur_demarre, _audio_disponible

    if _lecteur_demarre:
        return _audio_disponible

    _lecteur_demarre = True
    try:
        import pygame

        pygame.mixer.init()
    except Exception as erreur:
        _audio_disponible = False
        print(f"Audio indisponible, les annonces seront muettes : {erreur}")
        return False

    threading.Thread(target=lecteur_audio, daemon=True).start()
    return True


def lecteur_audio():

    import pygame

    while True:

        priorite, _, noms = file_audio.get()

        # Une entrée de la file est une **séquence**, pas un son : les morceaux
        # d'une phrase composée se jouent à la suite sans que rien ne puisse
        # s'intercaler entre eux. Voir `jouer_sequence`.
        for nom in noms:

            chemin = os.path.join(DOSSIER_SONS, nom)

            if os.path.exists(chemin):

                son = pygame.mixer.Sound(chemin)

                # Les annonces courtes doivent rester clairement audibles.
                if nom == "bip.wav":
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


def vider_petits_sons():

    temporaire = []

    while not file_audio.empty():

        item = file_audio.get()

        # On garde uniquement les sons importants
        if item[0] <= -5:
            temporaire.append(item)

    for item in temporaire:
        file_audio.put(item)


def jouer_sequence(noms, priorite=5):
    """Empile une phrase composée de plusieurs fichiers, **comme un seul son**.

    C'est l'indivisibilité qui compte. Empiler quatre `jouer()` d'affilée
    ordonnerait bien les morceaux — `compteur_audio` départage les priorités
    égales — mais rien n'empêcherait un événement urgent de se glisser au
    milieu : on entendrait « prochain exercice… 12 répétitions ». Une séquence
    est donc **une** entrée de la file, que `vider_petits_sons` garde ou jette
    en entier.
    """
    global compteur_audio

    noms = tuple(noms)

    if not noms:
        return

    if not _demarrer_lecteur():
        return

    # Les événements importants suppriment
    # les petits sons en attente
    if priorite >= 5:
        vider_petits_sons()

    compteur_audio += 1

    file_audio.put((-priorite, compteur_audio, noms))


def jouer(nom, priorite=5):
    """Un son seul : la séquence à un élément."""
    jouer_sequence((nom,), priorite)
