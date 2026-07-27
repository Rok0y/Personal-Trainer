import time

MODE_REPETITIONS = "repetitions"
MODE_MAINTIEN = "maintien"
MODE_CHRONO = "chrono"
MODE_AMRAP = "amrap"

class Exercice:

    def __init__(
        self,
        nom,
        detection,
        description="",
        instructions=None,
        erreurs=None
    ):
        self.nom = nom
        self.detection = detection
        self.description = description
        self.instructions = instructions or []
        self.erreurs = erreurs or []

class BlocExercice:

    def __init__(self,exercice,poids,mode,nombre_series,repetitions_par_serie,duree,repos_entre_series,repos_apres):
        self.exercice = exercice
        self.poids = poids
        self.mode = mode
        self.nombre_series = nombre_series
        self.repetitions_par_serie = repetitions_par_serie
        self.duree = duree
        self.repos_entre_series = repos_entre_series
        self.repos_apres = repos_apres

        self.temps_maintien = 0


class Circuit:

    def __init__(self, exercices):
        self.exercices = exercices
        self.index_exercice = 0
        self.serie_actuelle = 1
        self.phase = "preparation"
        self.debut_repos = None
        self.historique_enregistre = False
        self.debut = time.time()


    @property
    def bloc_actuel(self):
        if self.index_exercice >= len(self.exercices):
            return None
        return self.exercices[self.index_exercice]

    @property
    def poids(self):
        return self.bloc_actuel.poids

    @property
    def exercice_actuel(self):
        if self.bloc_actuel is None:
            return None
        return self.bloc_actuel.exercice

    @property
    def nombre_series(self):
        if self.bloc_actuel is None:
            return 0

        return self.bloc_actuel.nombre_series

    @property
    def repetitions_cibles(self):
        if self.bloc_actuel is None:
            return 0
        return self.bloc_actuel.repetitions_par_serie

    @property
    def temps_restant(self):
        if self.phase == "exercice":
            return 0
        if self.phase == "recuperation_serie":
            duree = self.bloc_actuel.repos_entre_series
        elif self.phase == "repos_exercice":
            duree = self.bloc_actuel.repos_apres
        else:
            return 0
        temps_ecoule = time.time() - self.debut_repos
        return max(0,duree - temps_ecoule)

    @property
    def duree_totale(self):
        return int(time.time() - self.debut)
    

    def exporter(self):
        exercices = []
        for bloc in self.exercices:
            exercices.append({
                "nom": bloc.exercice.nom,
                "series": bloc.nombre_series,
                "repetitions": bloc.repetitions_par_serie
            })
        return exercices

    def terminer_serie(self):

        """
        Appelée lorsque le nombre de répétitions
        demandé pour la série est atteint.
        """

        # -----------------------------------------
        # Il reste des séries
        # -----------------------------------------

        if self.serie_actuelle < self.nombre_series:
            self.serie_actuelle += 1
            self.phase = "recuperation_serie"
            self.debut_repos = time.time()
            return


        # -----------------------------------------
        # Toutes les séries de cet exercice
        # sont terminées
        # -----------------------------------------

        if self.bloc_actuel.repos_apres > 0:
            self.phase = "repos_exercice"
            self.debut_repos = time.time()
        else:
            self.passer_exercice_suivant()

    def commencer_exercice(self):
        self.phase = "exercice"

    def passer_exercice_suivant(self):
        self.index_exercice += 1


        # -----------------------------------------
        # Fin de la séance
        # -----------------------------------------

        if self.index_exercice >= len(self.exercices):
            self.phase = "termine"
            return


        # -----------------------------------------
        # Nouvel exercice
        # -----------------------------------------

        self.serie_actuelle = 1
        self.phase = "exercice"
        self.debut_repos = None


    def update(self):

        # -----------------------------------------
        # Récupération entre séries
        # -----------------------------------------

        if self.phase == "recuperation_serie":
            if self.temps_restant <= 0:
                self.phase = "exercice"
                self.debut_repos = None


        # -----------------------------------------
        # Repos entre deux exercices
        # -----------------------------------------

        elif self.phase == "repos_exercice":
            if self.temps_restant <= 0:
                self.passer_exercice_suivant()