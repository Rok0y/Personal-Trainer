import time

from progression.paliers import est_suivi_par_le_moteur

MODE_REPETITIONS = "repetitions"
MODE_MAINTIEN = "maintien"
MODE_CHRONO = "chrono"
MODE_AMRAP = "amrap"
MODE_ECHAUFFEMENT = "echauffement"

MODES_CONNUS = (
    MODE_REPETITIONS,
    MODE_MAINTIEN,
    MODE_CHRONO,
    MODE_AMRAP,
    MODE_ECHAUFFEMENT,
)

#: Modes dont le déroulement dépend d'une fonction de détection : pour eux,
#: `Exercice.detection` ne peut pas être None. Le chrono et l'échauffement en
#: sont absents parce qu'ils avancent au temps, sans analyser la pose.
MODES_AVEC_DETECTION_OBLIGATOIRE = (
    MODE_REPETITIONS,
    MODE_MAINTIEN,
    MODE_AMRAP,
)


def est_echauffement(bloc):
    """Un bloc d'échauffement guide un mouvement sans compter nulle part.

    Point d'entrée unique de la règle « invisible dans les stats » : progression
    de la séance, progression automatique des objectifs et export vers
    l'historique s'y réfèrent tous, pour qu'un seul endroit décide de ce qu'est
    un échauffement.
    """
    return bloc.mode == MODE_ECHAUFFEMENT


class Exercice:
    """Un mouvement : comment le détecter, et comment l'expliquer.

    Les champs pédagogiques ne se recouvrent pas, et les confondre appauvrit la
    fiche :

    - `description` — une phrase, ce qu'est le mouvement ;
    - `mise_en_place` — comment s'installer *avant* de commencer, cadrage
      caméra compris : c'est ce qui manque le plus à quelqu'un qui découvre, et
      ce qu'aucune détection ne saura jamais dire ;
    - `instructions` — l'exécution, geste par geste ;
    - `erreurs_frequentes` — de la pédagogie écrite, lue au calme avant l'effort ;
    - `erreurs` — des **fonctions** de vérification temps réel, qui retournent
      une clé de `core.messages`. Rien à voir avec la liste précédente : l'une
      se lit, l'autre s'exécute trente fois par seconde.

    `variante_facile` / `variante_difficile` nomment un autre exercice du
    catalogue. C'est ce qui permet au test de calibration de rediriger quelqu'un
    qui ne tient pas le premier palier, au lieu de le laisser « hors barème ».
    """

    def __init__(
        self,
        nom,
        detection=None,
        description="",
        instructions=None,
        erreurs=None,
        mise_en_place=None,
        erreurs_frequentes=None,
        variante_facile=None,
        variante_difficile=None,
    ):
        """`detection` à None décrit un mouvement guidé sans analyse de pose
        (échauffement) : seuls les modes de `MODES_AVEC_DETECTION_OBLIGATOIRE`
        l'exigent, et `construire_circuit` refuse les combinaisons invalides."""
        self.nom = nom
        self.detection = detection
        self.description = description
        self.instructions = instructions or []
        self.erreurs = erreurs or []
        self.mise_en_place = mise_en_place or []
        self.erreurs_frequentes = erreurs_frequentes or []
        self.variante_facile = variante_facile
        self.variante_difficile = variante_difficile

    def fiche(self):
        """Ce que l'exercice a à dire, sous une forme sérialisable.

        Point d'entrée unique de « qu'affiche-t-on d'un exercice ? » : la page
        catalogue, la fiche détaillée, l'overlay de préparation et le tunnel
        d'onboarding lisent tous ceci, donc enrichir la fiche se fait ici et
        nulle part ailleurs.
        """
        return {
            "nom": self.nom,
            "description": self.description,
            "mise_en_place": list(self.mise_en_place),
            "instructions": list(self.instructions),
            "erreurs_frequentes": list(self.erreurs_frequentes),
            "variante_facile": self.variante_facile,
            "variante_difficile": self.variante_difficile,
            "analyse_la_pose": self.detection is not None,
        }


class BlocExercice:

    def __init__(
        self,
        exercice,
        poids,
        mode,
        nombre_series,
        repetitions_par_serie,
        duree,
        repos_entre_series,
        repos_apres,
        commentaire="",
        entrelace_avec=None,
        cible_manuelle=False,
    ):
        #: Cible saisie à la main : le moteur de progression ne la touche plus,
        #: et elle reste collante jusqu'à ce qu'elle soit resynchronisée.
        #: La valeur est conservée **telle qu'elle a été stockée** (une liste
        #: d'identifiants de profils) et non réduite à un booléen : les séances
        #: étant partagées, une marque appartient à un profil, et l'aplatir ici
        #: ferait perdre celles des autres au premier réenregistrement.
        #: `progression.objectifs.est_cible_manuelle` la lit pour un profil.
        self.cible_manuelle = cible_manuelle
        self.exercice = exercice
        self.poids = poids
        self.mode = mode
        self.nombre_series = nombre_series
        self.repetitions_par_serie = repetitions_par_serie
        self.duree = duree
        self.repos_entre_series = repos_entre_series
        self.repos_apres = repos_apres
        self.commentaire = commentaire or ""
        self.entrelace_avec = entrelace_avec

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
        # Identifiant de la ligne écrite en base, connu seulement une fois la
        # séance enregistrée. C'est lui qui permet à l'écran de fin d'annoter
        # les exercices d'un ressenti.
        self.seance_id = None
        # Profil auquel cette séance appartiendra, fixé au moment où elle est
        # choisie. Une séance appartient à celui qui l'a faite, pas à celui qui
        # se trouve connecté quand le thread caméra l'écrit : entre la dernière
        # répétition et l'écriture en base, il y a le temps de changer de profil.
        self.utilisateur_id = None
        self.debut = time.time()
        self.resultats_series = []
        self.paires_entrelacees = self._detecter_paires_entrelacees()
        self.serie_actuelle_locale = 1
        self._exercice_precedent_entrelace = (
            None  # Track l'exercice avant un partenaire
        )

    def _detecter_paires_entrelacees(self):
        """Détecte les paires d'exercices entrelacés.
        Retourne un dict {index: nom_du_partenaire} pour les exercices qui ont un partenaire.
        """
        paires = {}
        for index, bloc in enumerate(self.exercices):
            if bloc.entrelace_avec:
                partenaire_index = self._trouver_exercice_par_nom(
                    bloc.entrelace_avec,
                    index,
                )
                if partenaire_index is not None:
                    paires[index] = partenaire_index
        return paires

    def _trouver_exercice_par_nom(self, nom_exercice, depuis=-1):
        """Indice du premier exercice portant ce nom après `depuis`.

        La recherche est strictement vers l'avant : un partenaire situé plus
        haut dans la séance (ou l'exercice lui-même) créerait une boucle
        infinie entre les deux blocs.
        """
        for index in range(depuis + 1, len(self.exercices)):
            if self.exercices[index].exercice.nom == nom_exercice:
                return index
        return None

    def _est_entrelace(self, index):
        """Vérifie si un exercice est entrelacé."""
        return index in self.paires_entrelacees

    def _obtenir_partenaire_entrelace(self, index):
        """Retourne l'indice du partenaire entrelacé."""
        return self.paires_entrelacees.get(index)

    def _obtenir_vrai_prochain_exercice_index(self):
        """Retourne l'indice du vrai prochain exercice, en sautant le partenaire entrelacé.

        Si l'exercice courant A a un partenaire B, le prochain exercice est celui après B.
        """
        prochain_index = self.index_exercice + 1
        partenaire_direct = self._obtenir_partenaire_entrelace(self.index_exercice)

        # Sauter le partenaire direct s'il existe
        if partenaire_direct is not None:
            prochain_index = max(prochain_index, partenaire_direct + 1)

        return prochain_index

    @property
    def bloc_actuel(self):
        if self.index_exercice >= len(self.exercices):
            return None
        return self.exercices[self.index_exercice]

    def prochain_bloc(self):
        prochain_index = self._obtenir_vrai_prochain_exercice_index()

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
        return max(0, duree - temps_ecoule)

    @property
    def duree_totale(self):
        return int(time.time() - self.debut)

    @property
    def blocs_comptabilises(self):
        """Blocs qui comptent dans la progression, les objectifs et l'historique."""
        return [bloc for bloc in self.exercices if not est_echauffement(bloc)]

    def _est_comptabilise(self, index):
        return 0 <= index < len(self.exercices) and not est_echauffement(
            self.exercices[index]
        )

    @property
    def nombre_series_total(self):
        return sum(bloc.nombre_series for bloc in self.blocs_comptabilises)

    @property
    def series_terminees(self):
        """Compte les séries terminées en utilisant les résultats enregistrés."""
        # Si on a entrelacement, utiliser les résultats pour compter correctement
        if self.paires_entrelacees:
            # Compter les séries complètes de tous les indices entrelacés
            return sum(
                1
                for resultat in self.resultats_series
                if self._est_comptabilise(resultat["index_exercice"])
            )

        # Cas normal : pas d'entrelacement. Le second terme est neutralisé
        # pendant un échauffement, sinon la barre avancerait avant même que le
        # premier exercice comptabilisé ait commencé.
        return sum(
            bloc.nombre_series
            for bloc in self.exercices[: self.index_exercice]
            if not est_echauffement(bloc)
        ) + (
            max(0, self.serie_actuelle - 1)
            if self._est_comptabilise(self.index_exercice)
            else 0
        )

    def passer_pause(self):
        if self.phase not in ("recuperation_serie", "repos_exercice"):
            return False
        self.debut_repos = None
        if self.phase == "recuperation_serie":
            self.phase = "exercice"
        else:
            self.passer_exercice_suivant()
        return True

    def exporter_configuration(self, inclure_echauffement=True):
        """Décrit les blocs configurés.

        `inclure_echauffement=False` sert à la barre de progression du front,
        qui indexe les segments à plat avec `series_terminees` : garder les
        échauffements dans la liste alors qu'ils sortent du compteur décalerait
        tous les segments.
        """
        # Import différé : `progression.niveaux` importe ce module, un import
        # en tête de fichier fermerait le cycle.
        from progression.objectifs import est_cible_manuelle

        return [
            {
                "nom": bloc.exercice.nom,
                "series": bloc.nombre_series,
                "repetitions": bloc.repetitions_par_serie,
                "poids": bloc.poids,
                "mode": bloc.mode,
                "duree": bloc.duree,
                "commentaire": bloc.commentaire,
                "repos_entre_series": bloc.repos_entre_series,
                "repos_apres": bloc.repos_apres,
                "entrelace_avec": bloc.entrelace_avec,
                # Résolu pour le profil connecté : cet export alimente
                # l'affichage, où la question est « ce bloc est-il figé *pour
                # moi* ? ». La valeur brute, elle, ne quitte jamais
                # `exporter_blocs`, qui écrit sur le disque.
                "cible_manuelle": est_cible_manuelle(bloc),
            }
            for bloc in self.exercices
            if inclure_echauffement or not est_echauffement(bloc)
        ]

    def exporter_resultats(self):
        exercices = []
        for index, bloc in enumerate(self.exercices):
            # Filtré à la source : ainsi aucune ligne d'échauffement n'atteint
            # jamais SQLite, et ni l'historique ni les records n'ont à les
            # exclure de leur côté.
            if est_echauffement(bloc):
                continue
            resultats = [
                resultat
                for resultat in self.resultats_series
                if resultat["index_exercice"] == index
            ]
            exercices.append(
                {
                    "nom": bloc.exercice.nom,
                    "series": len(resultats),
                    "repetitions": sum(
                        resultat.get("repetitions", 0) for resultat in resultats
                    ),
                    "poids": bloc.poids,
                    "mode": bloc.mode,
                    "duree": (
                        resultats[0].get("objectif_duree", bloc.duree)
                        if resultats
                        else bloc.duree
                    ),
                    "series_cibles": bloc.nombre_series,
                    "repetitions_cibles": (
                        resultats[0].get(
                            "objectif_repetitions", bloc.repetitions_par_serie
                        )
                        if resultats
                        else bloc.repetitions_par_serie
                    ),
                    "duree_cible": (
                        resultats[0].get("objectif_duree", bloc.duree)
                        if resultats
                        else bloc.duree
                    ),
                    "commentaire": bloc.commentaire,
                    "entrelace_avec": bloc.entrelace_avec,
                    "repos_entre_series": bloc.repos_entre_series,
                    "repos_apres": bloc.repos_apres,
                    "series_detaillees": [
                        {
                            **resultat,
                            "poids": bloc.poids,
                        }
                        for resultat in resultats
                    ],
                }
            )
        return exercices

    def a_des_resultats(self):
        """Un échauffement seul ne fait pas une séance : sans ce filtre, un
        abandon pendant l'échauffement insérerait en base une séance dont la
        liste d'exercices est vide."""
        return any(
            self._est_comptabilise(resultat["index_exercice"])
            for resultat in self.resultats_series
        )

    def objectifs_reussis(self, index=None):
        """Indique si un bloc précis (ou tous, si index=None) a validé
        toutes ses séries à la cible."""
        indices = range(len(self.exercices)) if index is None else [index]
        for i in indices:
            bloc = self.exercices[i]
            if est_echauffement(bloc):
                # Un échauffement n'a pas d'objectif : il ne peut ni faire
                # échouer la séance, ni déclencher de progression.
                if index is None:
                    continue
                return False
            series = [
                resultat
                for resultat in self.resultats_series
                if resultat["index_exercice"] == i and resultat.get("completee")
            ]
            if len(series) != bloc.nombre_series:
                return False
            if bloc.mode in (MODE_REPETITIONS, MODE_AMRAP):
                if any(
                    resultat.get("repetitions", 0) < bloc.repetitions_par_serie
                    for resultat in series
                ):
                    return False
            elif bloc.mode in (MODE_MAINTIEN, MODE_CHRONO):
                if any(resultat.get("duree", 0) < bloc.duree for resultat in series):
                    return False
        return bool(self.blocs_comptabilises)

    def appliquer_progression(self):
        """Augmente la cible des seuls exercices que le moteur ne pilote pas.

        Un exercice doté d'un barème progresse tout seul : sa cible est le
        premier palier non validé, et valider ce palier fait monter le niveau
        à la lecture suivante de l'historique. Lui appliquer en plus un `+1`
        ici le ferait sauter un cran à chaque séance réussie.

        Ne subsistent donc que les exercices sans barème, pour lesquels la
        vieille règle « +1 répétition, +2 secondes » reste la seule
        progression disponible.
        """
        progression_appliquee = False
        for index, bloc in enumerate(self.exercices):
            # Ceinture et bretelles : sans ce filtre explicite, un échauffement
            # traverserait les deux branches sans rien changer mais mettrait
            # `progression_appliquee` à True, faisant réécrire le JSON pour rien.
            if est_echauffement(bloc):
                continue
            if est_suivi_par_le_moteur(bloc.exercice.nom):
                continue
            if not self.objectifs_reussis(index):
                continue
            if bloc.mode in (MODE_REPETITIONS, MODE_AMRAP):
                bloc.repetitions_par_serie += 1
            elif bloc.mode in (MODE_MAINTIEN, MODE_CHRONO):
                bloc.duree += 2
            progression_appliquee = True
        return progression_appliquee

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

    def reinitialiser_etat_serie(self, bloc=None):
        """Remet à zéro les champs temporels d'un bloc (par défaut le bloc courant).

        Utilisée à la fois en interne (navigation entre séries) et par
        `session/moteur.py` à la fin de chaque mode, pour éviter que les deux
        modules ne dupliquent la liste des attributs à réinitialiser.
        """
        bloc = bloc if bloc is not None else self.bloc_actuel
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
            "temps_echauffement",
            "dernier_tick_echauffement",
        ):
            if hasattr(bloc, nom):
                delattr(bloc, nom)

    def remettre_serie_a_zero(self):
        """Efface la progression de la série courante sans changer d'index."""
        self.reinitialiser_etat_serie()
        if self.phase not in ("termine", "preparation"):
            self.phase = "exercice"
            self.debut_repos = None

    def recommencer_serie(self):
        """Relance entièrement la série courante depuis son état initial."""
        self.reinitialiser_etat_serie()
        self.phase = "exercice"
        self.debut_repos = None

    def serie_precedente(self):
        """Revient à la série précédente, si elle existe."""
        if self.serie_actuelle <= 1 or self.bloc_actuel is None:
            return False

        self.serie_actuelle -= 1
        self.reinitialiser_etat_serie()
        self.phase = "exercice"
        self.debut_repos = None
        return True

    def serie_suivante(self):
        """Avance à la série suivante, sans dépasser le bloc actuel."""
        if self.serie_actuelle >= self.nombre_series or self.bloc_actuel is None:
            return False

        self.serie_actuelle += 1
        self.reinitialiser_etat_serie()
        self.phase = "exercice"
        self.debut_repos = None
        return True

    def objectif_serie_atteint(self, repetitions=0, duree=0):
        """La performance donnée atteint-elle la consigne du bloc courant ?

        Point d'entrée unique de « cette série compte-t-elle ». Le seuil dépend
        du mode : une durée pour un maintien ou un chrono, un nombre de
        répétitions sinon.
        """
        bloc = self.bloc_actuel
        if bloc is None:
            return False
        if bloc.mode in (MODE_MAINTIEN, MODE_CHRONO):
            return duree >= bloc.duree
        return repetitions >= bloc.repetitions_par_serie

    def terminer_serie_manuellement(self, repetitions=0, duree=0):
        """Enregistre la performance courante puis lance la transition.

        La série n'est marquée `completee` que si elle atteint sa consigne.
        Terminer à la main, c'est justement le cas où l'objectif peut ne pas
        être atteint — un gainage lâché à mi-parcours, une série écourtée —, et
        le forcer à `True` faisait passer un abandon pour une réussite. C'était
        le seul chemin capable de produire un `completee` faux, si bien que le
        filtre de `progression.niveaux.performance_realisee` n'avait jusqu'ici
        jamais rien à écarter.
        """
        if self.phase != "exercice":
            return False

        self.enregistrer_resultat_serie(
            repetitions=repetitions,
            duree=duree,
            completee=self.objectif_serie_atteint(repetitions, duree),
        )
        self.reinitialiser_etat_serie()
        self.terminer_serie()
        return True

    def terminer_serie(self):
        """
        Appelée lorsque le nombre de répétitions
        demandé pour la série est atteint.
        """

        # -----------------------------------------
        # Vérifier l'entrelacement
        # -----------------------------------------

        # Cas 1 : On est en train d'exécuter un exercice avec un partenaire entrelacé
        if self._est_entrelace(self.index_exercice):
            partenaire_index = self._obtenir_partenaire_entrelace(self.index_exercice)

            if self._exercice_precedent_entrelace is None:
                # On n'a pas encore visité le partenaire pour cette série
                # Aller au partenaire ET garder le même serie_actuelle
                self._exercice_precedent_entrelace = {
                    "index": self.index_exercice,
                    "serie": self.serie_actuelle,
                }
                self.index_exercice = partenaire_index
                # GARDER le même serie_actuelle pour que l'affichage reste cohérent
                self.phase = "recuperation_serie"
                self.debut_repos = time.time()
                return
            else:
                # On revient du partenaire
                # Revenir à l'exercice original avec la série suivante
                self.index_exercice = self._exercice_precedent_entrelace["index"]
                self.serie_actuelle = self._exercice_precedent_entrelace["serie"] + 1
                self._exercice_precedent_entrelace = None

                # Vérifier si c'est la dernière série
                if self.serie_actuelle > self.nombre_series:
                    # Toutes les séries de la paire sont complétées
                    # Passer à l'exercice suivant
                    if self.bloc_actuel.repos_apres > 0:
                        self.phase = "repos_exercice"
                        self.debut_repos = time.time()
                    else:
                        self.passer_exercice_suivant()
                else:
                    # Il y a encore des séries
                    self.phase = "recuperation_serie"
                    self.debut_repos = time.time()
                return

        # Cas 2 : On revient du partenaire entrelacé (dans le cas où le partenaire est celui-ci)
        elif self._exercice_precedent_entrelace is not None:
            # Cela ne devrait pas arriver ici mais on gère juste au cas où
            self.index_exercice = self._exercice_precedent_entrelace["index"]
            self.serie_actuelle = self._exercice_precedent_entrelace["serie"] + 1
            self._exercice_precedent_entrelace = None

            if self.serie_actuelle > self.nombre_series:
                if self.bloc_actuel.repos_apres > 0:
                    self.phase = "repos_exercice"
                    self.debut_repos = time.time()
                else:
                    self.passer_exercice_suivant()
            else:
                self.phase = "recuperation_serie"
                self.debut_repos = time.time()
            return

        # -----------------------------------------
        # Il reste des séries (cas normal, pas entrelacé)
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
        self.index_exercice = self._obtenir_vrai_prochain_exercice_index()

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
        self._exercice_precedent_entrelace = None

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
