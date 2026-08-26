import unittest

from session.circuit import BlocExercice, Circuit, Exercice, MODE_REPETITIONS


def exercice_test(corps):
    return "debut"


def creer_circuit():
    exercice = Exercice("Test", exercice_test)
    bloc = BlocExercice(
        exercice=exercice,
        poids=0,
        mode=MODE_REPETITIONS,
        nombre_series=3,
        repetitions_par_serie=5,
        duree=0,
        repos_entre_series=10,
        repos_apres=10,
    )
    circuit = Circuit([bloc])
    circuit.phase = "exercice"
    return circuit


class CircuitSeriesTests(unittest.TestCase):

    def test_reset_conserve_la_serie(self):
        circuit = creer_circuit()
        circuit.serie_actuelle = 2
        circuit.phase = "recuperation_serie"

        circuit.remettre_serie_a_zero()

        self.assertEqual(circuit.serie_actuelle, 2)
        self.assertEqual(circuit.phase, "exercice")

    def test_navigation_des_series(self):
        circuit = creer_circuit()

        self.assertFalse(circuit.serie_precedente())
        self.assertTrue(circuit.serie_suivante())
        self.assertEqual(circuit.serie_actuelle, 2)
        self.assertTrue(circuit.serie_suivante())
        self.assertEqual(circuit.serie_actuelle, 3)
        self.assertFalse(circuit.serie_suivante())

    def test_terminer_serie_passe_a_la_recuperation(self):
        circuit = creer_circuit()

        self.assertTrue(circuit.terminer_serie_manuellement())

        self.assertEqual(circuit.serie_actuelle, 2)
        self.assertEqual(circuit.phase, "recuperation_serie")

    def test_exporte_les_series_detaillees_avec_le_poids(self):
        circuit = creer_circuit()
        circuit.exercices[0].poids = 10
        circuit.enregistrer_resultat_serie(repetitions=5)
        circuit.serie_actuelle = 2
        circuit.enregistrer_resultat_serie(repetitions=3)

        detail = circuit.exporter_resultats()[0]["series_detaillees"]

        self.assertEqual([serie["repetitions"] for serie in detail], [5, 3])
        self.assertEqual([serie["poids"] for serie in detail], [10, 10])


if __name__ == "__main__":
    unittest.main()