import numpy as np
import time
import math


def calculer_distance(point_a, point_b):
    return math.sqrt((point_a.x - point_b.x) ** 2 + (point_a.y - point_b.y) ** 2)

def calculer_angle(a, b, c):
    """
    Calcule l'angle formé par trois points.

    a = premier point
    b = point central (articulation)
    c = troisième point
    """

    a = np.array([a.x, a.y])
    b = np.array([b.x, b.y])
    c = np.array([c.x, c.y])

    radians = (
        np.arctan2(c[1] - b[1], c[0] - b[0])
        -
        np.arctan2(a[1] - b[1], a[0] - b[0])
    )

    angle = abs(radians * 180 / np.pi)

    if angle > 180:
        angle = 360 - angle

    return angle

class HoldPosition:

    def __init__(self, position, duree):

        self.position = position
        self.duree = duree
        self.debut = None
        self.termine = False


    def update(self, corps):

        # La position n'est pas tenue
        if not self.position(corps):

            self.debut = None
            self.termine = False

            return 0, False


        # Début du maintien
        if self.debut is None:

            self.debut = time.time()


        # Temps écoulé
        temps_ecoule = time.time() - self.debut


        # Progression entre 0 et 100
        progression = (temps_ecoule / self.duree) * 100
        progression = min(progression,100)


        # Maintien terminé
        if progression >= 100:

            if not self.termine:

                self.termine = True

                return 100, True

            return 100, False


        return progression, False