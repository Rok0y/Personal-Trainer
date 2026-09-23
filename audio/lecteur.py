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

SILENCE_ENTRE_ANNONCES = 0.8
"""Le blanc minimal entre deux **phrases**, en secondes.

Rien ne jouait jamais littéralement en même temps — le thread attend
`mixer.get_busy()` —, et pourtant le coach « se chevauchait » à l'oreille :
la file enchaînait l'entrée suivante à la milliseconde où la précédente se
taisait, si bien que « Repose-toi » et « Prochain exercice : curl biceps
droit » n'en faisaient plus qu'une. *Deux phrases collées s'entendent comme
une phrase coupée.* Le silence se pose donc **dans le lecteur**, point de
passage unique, plutôt que dans chaque site d'appel qui aurait à s'en
souvenir.

**Il sépare deux phrases, et jamais un chiffre de quoi que ce soit.** Il se
prenait d'abord après *chaque* entrée de la file, chiffres compris : « 7 »,
0,8 s, « encore 5 », 0,8 s, « 8 »… À une répétition toutes les deux secondes,
le comptage prenait du retard à chaque chiffre et ne le rattrapait jamais —
le coach annonçait « 8 » pendant la dixième. Un son de rythme (voir
`PRIORITE_RYTHME_MAX`) part donc tout de suite, et une phrase n'attend que la
fin de la phrase précédente.
"""

PRIORITE_RYTHME_MAX = 2
"""Jusqu'à cette priorité, un son est un son de **rythme** : un chiffre (1) ou
un bip (2). Il suit le geste, donc il ne prend ni ne laisse de blanc, et il
remplace ceux de son espèce encore en attente — un chiffre dit où l'on en est,
pas où l'on en était.

La frontière passe par la priorité plutôt que par une liste de clés parce que
la table des priorités le disait déjà : ce sont les sons qu'on sacrifie les
premiers, précisément parce qu'ils ne valent qu'à l'instant où on les demande.
"""

SILENCE_PRESENTATION = 2.5
"""Le blanc demandé par l'annonce du prochain exercice, avant de commencer.

C'est la seule annonce longue du projet, et la seule qui arrive collée
derrière une autre (« Repose-toi »). Elle porte son propre silence plutôt
que d'être déclenchée plus tard dans la pause : un délai transporté par
l'entrée de la file ne demande ni drapeau « déjà annoncé », ni état de plus
sur `Circuit` — que le harnais de scénarios observe pas à pas.
"""

REPOS_MINIMAL_PRESENTATION = 15
"""En deçà de ce repos (secondes), l'annonce du prochain exercice part seule.

« Repose-toi », le blanc de présentation puis l'annonce prennent une dizaine
de secondes de parole (≈ 1,5 + 0,8 + 2,5 + 5 à 6 s). Sur les cinq secondes de
repos entre deux échauffements, l'annonce tombait donc **pendant** l'exercice
qu'elle présentait. Sur un repos court, on garde l'essentiel — ce qui vient —
et on le dit dès la fin de la série ; le reste n'a pas le temps d'exister.
"""


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


def est_rythme(priorite):
    """Un chiffre ou un bip : un son qui suit le geste. Voir `PRIORITE_RYTHME_MAX`."""
    return priorite <= PRIORITE_RYTHME_MAX


def lecteur_audio():

    import pygame

    # L'instant où la dernière **phrase** s'est tue. Le blanc se compte depuis
    # lui, et non depuis le dernier son : un chiffre joué entre deux phrases
    # ne doit pas repousser la suivante.
    fin_phrase = 0.0

    while True:

        priorite, _, noms, silence_avant = file_audio.get()
        rythme = est_rythme(-priorite)

        if not rythme:
            attente = fin_phrase + SILENCE_ENTRE_ANNONCES - time.monotonic()
            if attente > 0:
                time.sleep(attente)

        if silence_avant:
            time.sleep(silence_avant)

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

        if not rythme:
            fin_phrase = time.monotonic()

        file_audio.task_done()


def _retirer_de_la_file(a_retirer):
    """Retire de la file les entrées dont la priorité satisfait `a_retirer`."""

    temporaire = []

    while not file_audio.empty():

        item = file_audio.get()

        if not a_retirer(-item[0]):
            temporaire.append(item)

    for item in temporaire:
        file_audio.put(item)


def vider_petits_sons():
    """On garde uniquement les sons importants."""
    _retirer_de_la_file(lambda priorite: priorite < 5)


def jouer_sequence(noms, priorite=5, silence_avant=0.0):
    """Empile une phrase composée de plusieurs fichiers, **comme un seul son**.

    C'est l'indivisibilité qui compte. Empiler quatre `jouer()` d'affilée
    ordonnerait bien les morceaux — `compteur_audio` départage les priorités
    égales — mais rien n'empêcherait un événement urgent de se glisser au
    milieu : on entendrait « prochain exercice… 12 répétitions ». Une séquence
    est donc **une** entrée de la file, que `vider_petits_sons` garde ou jette
    en entier.

    `silence_avant` retarde cette entrée-là, et elle seule : c'est ce qui
    permet à l'annonce du prochain exercice de laisser un vrai blanc après
    « repose-toi » sans qu'aucun appelant ait à tenir une horloge.
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

    # Un chiffre remplace le chiffre qui attendait encore : deux en file, c'est
    # déjà un de retard.
    if est_rythme(priorite):
        _retirer_de_la_file(est_rythme)

    compteur_audio += 1

    file_audio.put((-priorite, compteur_audio, noms, silence_avant))


def jouer(nom, priorite=5, silence_avant=0.0):
    """Un son seul : la séquence à un élément."""
    jouer_sequence((nom,), priorite, silence_avant)
