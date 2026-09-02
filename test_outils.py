import unittest
from types import SimpleNamespace

from mouvements.outils import calculer_angle, calculer_distance


def point(x, y):
    return SimpleNamespace(x=x, y=y)


class CalculerDistanceTests(unittest.TestCase):

    def test_distance_entre_deux_points_identiques_est_nulle(self):
        a = point(1, 1)

        self.assertEqual(calculer_distance(a, a), 0)

    def test_distance_horizontale(self):
        a = point(0, 0)
        b = point(3, 0)

        self.assertEqual(calculer_distance(a, b), 3)

    def test_distance_correspond_au_theoreme_de_pythagore(self):
        a = point(0, 0)
        b = point(3, 4)

        self.assertEqual(calculer_distance(a, b), 5)


class CalculerAngleTests(unittest.TestCase):

    def test_angle_droit(self):
        a = point(1, 0)
        b = point(0, 0)
        c = point(0, 1)

        self.assertAlmostEqual(calculer_angle(a, b, c), 90)

    def test_angle_plat(self):
        a = point(-1, 0)
        b = point(0, 0)
        c = point(1, 0)

        self.assertAlmostEqual(calculer_angle(a, b, c), 180)

    def test_angle_ne_depasse_jamais_180_degres(self):
        a = point(1, 0)
        b = point(0, 0)
        c = point(-1, -0.001)

        self.assertLessEqual(calculer_angle(a, b, c), 180)


if __name__ == "__main__":
    unittest.main()
