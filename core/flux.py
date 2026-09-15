"""Dernière image encodée de la caméra, pour le flux MJPEG du site.

Séparé de `EtatSeance` parce que les deux n'ont pas le même avenir : tout ce
que porte l'état de séance se porte en JavaScript, alors qu'une image encodée
côté serveur n'existe pas dans le navigateur — c'est la caméra de l'appareil
qui affiche la sienne. La frontière du portage est donc lisible dans les
types, et non dans un commentaire.

Il y a une caméra par processus : une instance suffit, et c'est le site qui la
détient (`web/app.py`), la boucle caméra l'alimentant.
"""

from dataclasses import dataclass


@dataclass
class FluxVideo:
    latest_frame: bytes | None = None

    frame_id: int = 0
    """Incrémenté à chaque nouvelle image encodée : permet au flux web de
    n'envoyer une image que lorsqu'elle a réellement changé."""
