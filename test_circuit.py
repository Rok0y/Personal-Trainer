import unittest

from session.circuit import BlocExercice, Circuit, Exercice, MODE_CHRONO, MODE_REPETITIONS


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

    def test_validation_manuelle_conserve_la_performance(self):
        circuit = creer_circuit()

        self.assertTrue(circuit.terminer_serie_manuellement(repetitions=4))

        self.assertEqual(circuit.resultats_series[0]["repetitions"], 4)
        self.assertEqual(circuit.serie_actuelle, 2)

    def test_reset_ne_valide_pas_la_serie(self):
        circuit = creer_circuit()
        circuit.resultats_series = [{"index_exercice": 0, "serie": 1, "repetitions": 3}]

        circuit.remettre_serie_a_zero()

        self.assertEqual(circuit.serie_actuelle, 1)
        self.assertEqual(len(circuit.resultats_series), 1)

    def test_progression_augmente_les_repetitions_sans_augmenter_les_series(self):
        circuit = creer_circuit()
        for serie in range(1, 4):
            circuit.serie_actuelle = serie
            circuit.enregistrer_resultat_serie(repetitions=5)

        self.assertTrue(circuit.appliquer_progression())
        self.assertEqual(circuit.exercices[0].nombre_series, 3)
        self.assertEqual(circuit.exercices[0].repetitions_par_serie, 6)

    def test_progression_est_bloquee_si_une_serie_n_atteint_pas_la_cible(self):
        circuit = creer_circuit()
        for serie, repetitions in enumerate((5, 4, 5), start=1):
            circuit.serie_actuelle = serie
            circuit.enregistrer_resultat_serie(repetitions=repetitions)

        self.assertFalse(circuit.appliquer_progression())
        self.assertEqual(circuit.exercices[0].repetitions_par_serie, 5)

    def test_15_sur_15_fait_passer_l_objectif_a_16(self):
        circuit = creer_circuit()
        circuit.exercices[0].repetitions_par_serie = 15
        for serie in range(1, 4):
            circuit.serie_actuelle = serie
            circuit.enregistrer_resultat_serie(repetitions=15)

        self.assertTrue(circuit.appliquer_progression())
        self.assertEqual(circuit.exercices[0].repetitions_par_serie, 16)

    def test_16_puis_14_conserve_l_objectif_16_et_le_resultat_14(self):
        circuit = creer_circuit()
        circuit.exercices[0].repetitions_par_serie = 16
        circuit.enregistrer_resultat_serie(repetitions=16)
        circuit.serie_actuelle = 2
        circuit.terminer_serie_manuellement(repetitions=14)

        self.assertEqual(circuit.exercices[0].repetitions_par_serie, 16)
        self.assertEqual(circuit.resultats_series[-1]["repetitions"], 14)
        self.assertEqual(circuit.exporter_resultats()[0]["repetitions_cibles"], 16)

    def test_refaire_une_serie_remplace_son_resultat(self):
        circuit = creer_circuit()
        circuit.enregistrer_resultat_serie(repetitions=3)
        circuit.enregistrer_resultat_serie(repetitions=5)

        self.assertEqual(len(circuit.resultats_series), 1)
        self.assertEqual(circuit.resultats_series[0]["repetitions"], 5)

    def test_progression_chrono_ajoute_deux_secondes(self):
        circuit = creer_circuit()
        bloc = circuit.exercices[0]
        bloc.mode = MODE_CHRONO
        bloc.duree = 10
        for serie in range(1, 4):
            circuit.serie_actuelle = serie
            circuit.enregistrer_resultat_serie(duree=10)

        self.assertTrue(circuit.appliquer_progression())
        self.assertEqual(bloc.duree, 12)

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
