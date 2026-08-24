import unittest

from mouvements.compteur import CompteurMouvement


class CompteurMouvementTests(unittest.TestCase):

    def test_position_fin_initiale_ne_compte_pas(self):
        compteur = CompteurMouvement()

        stage, repetitions = compteur.mettre_a_jour("fin")

        self.assertEqual(stage, "fin")
        self.assertEqual(repetitions, 0)

    def test_une_repetition_exige_debut_puis_fin(self):
        compteur = CompteurMouvement()

        compteur.mettre_a_jour("debut")
        stage, repetitions = compteur.mettre_a_jour("fin")

        self.assertEqual(stage, "fin")
        self.assertEqual(repetitions, 1)

    def test_position_milieu_n_arme_pas_le_compteur(self):
        compteur = CompteurMouvement()

        compteur.mettre_a_jour("milieu")
        stage, repetitions = compteur.mettre_a_jour("fin")

        self.assertEqual(stage, "fin")
        self.assertEqual(repetitions, 0)

    def test_reset_exige_une_nouvelle_position_debut(self):
        compteur = CompteurMouvement()
        compteur.mettre_a_jour("debut")
        compteur.mettre_a_jour("fin")

        compteur.reset()
        stage, repetitions = compteur.mettre_a_jour("fin")

        self.assertEqual(stage, "fin")
        self.assertEqual(repetitions, 0)


if __name__ == "__main__":
    unittest.main()