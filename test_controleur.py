import unittest

from session.controleur import SessionManager


class SessionManagerTests(unittest.TestCase):

    def test_selection_cree_un_circuit_neuf(self):
        controleur = SessionManager()

        premiere = controleur.selectionner("bras")
        controleur.demarrer()
        premiere.serie_actuelle = 2
        controleur.selectionner("bras")

        self.assertEqual(controleur.seance.serie_actuelle, 1)
        self.assertEqual(controleur.seance.phase, "preparation")

    def test_commandes_de_serie_reinitialisent_la_progression(self):
        resets = []
        controleur = SessionManager(lambda: resets.append(True))
        controleur.selectionner("bras")
        controleur.demarrer()

        controleur.serie_suivante()
        controleur.remettre_serie_a_zero()

        self.assertEqual(controleur.seance.serie_actuelle, 2)
        self.assertEqual(len(resets), 2)


if __name__ == "__main__":
    unittest.main()