import numpy as np
import time

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

    def update(self, corps):

        if self.position(corps):

            if self.debut is None:
                self.debut = time.time()

            if time.time() - self.debut >= self.duree:
                return True

        else:
            self.debut = None

        return False