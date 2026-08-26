import os
import tempfile
import unittest

from historique import database


class HistoriqueTests(unittest.TestCase):

    def setUp(self):
        self.fichier_db = tempfile.NamedTemporaryFile(delete=False)
        self.fichier_db.close()
        self.ancien_chemin = database.CHEMIN_DB
        database.CHEMIN_DB = self.fichier_db.name
        database.initialiser()

    def tearDown(self):
        database.CHEMIN_DB = self.ancien_chemin
        os.unlink(self.fichier_db.name)

    def test_sauvegarde_et_statistiques_par_serie(self):
        database.enregistrer_seance(
            duree=120,
            nom_seance="test",
            exercices=[{
                "nom": "Developpe couche",
                "series": 2,
                "repetitions": 21,
                "poids": 10,
                "mode": "repetitions",
                "series_detaillees": [
                    {"serie": 1, "repetitions": 12, "poids": 10, "completee": True},
                    {"serie": 2, "repetitions": 9, "poids": 10, "completee": True},
                ],
            }],
        )

        historique = database.recuperer_historique()
        statistiques = database.statistiques_exercices(historique)["Developpe couche"]

        self.assertEqual(len(historique[0]["exercices"][0]["series_detaillees"]), 2)
        self.assertEqual(statistiques["repetitions"], 21)
        self.assertEqual(statistiques["volume"], 210)
        self.assertEqual(statistiques["series"], 2)
        self.assertEqual(statistiques["pb"]["valeur"], 210)

    def test_seance_abandonnee_exclue_des_statistiques(self):
        database.enregistrer_seance(
            duree=30,
            statut="abandoned",
            exercices=[{
                "nom": "Pompes",
                "series": 1,
                "repetitions": 8,
                "series_detaillees": [
                    {"serie": 1, "repetitions": 8, "completee": True},
                ],
            }],
        )

        historique = database.recuperer_historique()

        self.assertEqual(historique[0]["statut"], "abandoned")
        self.assertEqual(database.statistiques_exercices(historique), {})

    def test_duree_est_le_pb_des_exercices_chronometres(self):
        database.enregistrer_seance(
            duree=45,
            exercices=[{
                "nom": "Planche",
                "series": 1,
                "repetitions": 0,
                "mode": "maintien",
                "series_detaillees": [
                    {"serie": 1, "duree": 45, "completee": True},
                ],
            }],
        )

        stat = database.statistiques_exercices()["Planche"]

        self.assertEqual(stat["pb"]["valeur"], 45)
        self.assertEqual(stat["duree"], 45)


if __name__ == "__main__":
    unittest.main()
