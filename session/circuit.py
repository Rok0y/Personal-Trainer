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

    def __init__(self,exercice,poids,mode,nombre_series,repetitions_par_serie,duree,repos_entre_series,repos_apres,commentaire=""):
        self.exercice = exercice
        self.poids = poids
        self.mode = mode
        self.nombre_series = nombre_series
        self.repetitions_par_serie = repetitions_par_serie
        self.duree = duree
        self.repos_entre_series = repos_entre_series
        self.repos_apres = repos_apres
        self.commentaire = commentaire or ""

        self.temps_maintien = 0
        self.temps_restant_precedent = None

class Circuit:

    def __init__(self, exercices):
        self.exercices = exercices
        self.index_exercice = 0
        self.serie_actuelle = 1
        self.phase = "preparation"
        self.debut_repos = None
        self.historique_enregistre = False
        self.debut = time.time()
        self.resultats_series = []


    @property
    def bloc_actuel(self):
        if self.index_exercice >= len(self.exercices):
            return None
        return self.exercices[self.index_exercice]

    def prochain_bloc(self):
        prochain_index = self.index_exercice + 1

        if prochain_index >= len(self.exercices):
            return None

        return self.exercices[prochain_index]

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

    @property
    def nombre_series_total(self):
        return sum(bloc.nombre_series for bloc in self.exercices)

    @property
    def series_terminees(self):
        return sum(bloc.nombre_series for bloc in self.exercices[:self.index_exercice]) + max(0, self.serie_actuelle - 1)

    def passer_pause(self):
        if self.phase not in ("recuperation_serie", "repos_exercice"):
            return False
        self.debut_repos = None
        if self.phase == "recuperation_serie":
            self.phase = "exercice"
        else:
            self.passer_exercice_suivant()
        return True
    

    def exporter_configuration(self):
        return [
            {
                "nom": bloc.exercice.nom,
                "series": bloc.nombre_series,
                "repetitions": bloc.repetitions_par_serie,
                "poids": bloc.poids,
                "mode": bloc.mode,
                "duree": bloc.duree,
                "commentaire": bloc.commentaire,
            }
            for bloc in self.exercices
        ]

    def exporter_resultats(self):
        exercices = []
        for index, bloc in enumerate(self.exercices):
            resultats = [
                resultat for resultat in self.resultats_series
                if resultat["index_exercice"] == index
            ]
            exercices.append({
                "nom": bloc.exercice.nom,
                "series": len(resultats),
                "repetitions": sum(resultat.get("repetitions", 0) for resultat in resultats),
                "poids": bloc.poids,
                "mode": bloc.mode,
                "duree": resultats[0].get("objectif_duree", bloc.duree) if resultats else bloc.duree,
                "series_cibles": bloc.nombre_series,
                "repetitions_cibles": resultats[0].get("objectif_repetitions", bloc.repetitions_par_serie) if resultats else bloc.repetitions_par_serie,
                "duree_cible": resultats[0].get("objectif_duree", bloc.duree) if resultats else bloc.duree,
                "commentaire": bloc.commentaire,
                "series_detaillees": [
                    {
                        **resultat,
                        "poids": bloc.poids,
                    }
                    for resultat in resultats
                ],
            })
        return exercices

    def a_des_resultats(self):
        return bool(self.resultats_series)

    def objectifs_reussis(self):
        """Indique si chaque bloc a validé toutes ses séries à la cible."""
        for index, bloc in enumerate(self.exercices):
            series = [
                resultat for resultat in self.resultats_series
                if resultat["index_exercice"] == index and resultat.get("completee")
            ]
            if len(series) != bloc.nombre_series:
                return False
            if bloc.mode in (MODE_REPETITIONS, MODE_AMRAP):
                if any(resultat.get("repetitions", 0) < bloc.repetitions_par_serie for resultat in series):
                    return False
            elif bloc.mode in (MODE_MAINTIEN, MODE_CHRONO):
                if any(resultat.get("duree", 0) < bloc.duree for resultat in series):
                    return False
        return bool(self.exercices)

    def appliquer_progression(self):
        """Augmente la cible sans modifier le nombre de séries."""
        if not self.objectifs_reussis():
            return False
        for bloc in self.exercices:
            if bloc.mode in (MODE_REPETITIONS, MODE_AMRAP):
                bloc.repetitions_par_serie += 1
            elif bloc.mode in (MODE_MAINTIEN, MODE_CHRONO):
                bloc.duree += 2
        return True

    def exporter(self):
        """Conserve l'ancien nom pour l'export des résultats réalisés."""
        return self.exporter_resultats()

    def enregistrer_resultat_serie(self, repetitions=0, duree=0, completee=True):
        """Enregistre une seule performance par exercice et par numéro de série.

        Une série refaite après navigation remplace son ancien résultat : elle ne
        peut donc ni disparaître ni être comptée deux fois dans l'historique.
        """
        resultat = {
            "index_exercice": self.index_exercice,
            "serie": self.serie_actuelle,
            "repetitions": repetitions,
            "duree": duree,
            "completee": completee,
            "objectif_repetitions": self.bloc_actuel.repetitions_par_serie,
            "objectif_duree": self.bloc_actuel.duree,
        }
        for index, precedent in enumerate(self.resultats_series):
            if (
                precedent["index_exercice"] == self.index_exercice
                and precedent["serie"] == self.serie_actuelle
            ):
                self.resultats_series[index] = resultat
                return
        self.resultats_series.append(resultat)

    def _reinitialiser_etat_serie(self):
        bloc = self.bloc_actuel
        if bloc is None:
            return

        bloc.temps_maintien = 0
        bloc.temps_restant_precedent = None
        for nom in (
            "dernier_maintien",
            "derniere_seconde_bip",
            "debut_chrono",
            "temps_chrono",
            "debut_amrap",
            "temps_amrap",
        ):
            if hasattr(bloc, nom):
                delattr(bloc, nom)

    def remettre_serie_a_zero(self):
        """Efface la progression de la série courante sans changer d'index."""
        self._reinitialiser_etat_serie()
        if self.phase not in ("termine", "preparation"):
            self.phase = "exercice"
            self.debut_repos = None

    def recommencer_serie(self):
        """Relance entièrement la série courante depuis son état initial."""
        self._reinitialiser_etat_serie()
        self.phase = "exercice"
        self.debut_repos = None

    def serie_precedente(self):
        """Revient à la série précédente, si elle existe."""
        if self.serie_actuelle <= 1 or self.bloc_actuel is None:
            return False

        self.serie_actuelle -= 1
        self._reinitialiser_etat_serie()
        self.phase = "exercice"
        self.debut_repos = None
        return True

    def serie_suivante(self):
        """Avance à la série suivante, sans dépasser le bloc actuel."""
        if self.serie_actuelle >= self.nombre_series or self.bloc_actuel is None:
            return False

        self.serie_actuelle += 1
        self._reinitialiser_etat_serie()
        self.phase = "exercice"
        self.debut_repos = None
        return True

    def terminer_serie_manuellement(self, repetitions=0, duree=0):
        """Enregistre la performance courante puis lance la transition."""
        if self.phase != "exercice":
            return False

        self.enregistrer_resultat_serie(
            repetitions=repetitions,
            duree=duree,
            completee=True,
        )
        self._reinitialiser_etat_serie()
        self.terminer_serie()
        return True

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
