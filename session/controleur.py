import threading

from session.seances import catalogue, creer_seance


class SessionManager:
    """Coordonne les commandes web et la séance traitée par la caméra."""

    def __init__(self, reset_progression=None):
        self._verrou = threading.RLock()
        self._reset_progression = reset_progression
        self.nom_selectionne = None
        self.seance = None
        self.statut = "idle"

    def catalogue(self):
        with self._verrou:
            return catalogue()

    def definir_reset_progression(self, callback):
        with self._verrou:
            self._reset_progression = callback

    def selectionner(self, nom):
        with self._verrou:
            if self.statut in ("running", "paused"):
                raise RuntimeError("Une séance est déjà en cours")
            self.seance = creer_seance(nom)
            self.nom_selectionne = nom
            self.statut = "ready"
            if self._reset_progression is not None:
                self._reset_progression()
            return self.seance

    def demarrer(self):
        with self._verrou:
            if self.seance is None:
                raise RuntimeError("Aucune séance sélectionnée")
            if self.statut not in ("ready", "paused"):
                raise RuntimeError("La séance ne peut pas démarrer")
            self.statut = "running"
            return self.seance

    def mettre_en_pause(self):
        with self._verrou:
            if self.statut != "running":
                raise RuntimeError("Aucune séance en cours")
            self.statut = "paused"

    def reprendre(self):
        with self._verrou:
            if self.statut != "paused":
                raise RuntimeError("La séance n'est pas en pause")
            self.statut = "running"

    def _preparer_commande_serie(self):
        if self.seance is None or self.statut not in ("running", "paused"):
            raise RuntimeError("Aucune séance active")
        if self._reset_progression is not None:
            self._reset_progression()

    def remettre_serie_a_zero(self):
        with self._verrou:
            self._preparer_commande_serie()
            self.seance.remettre_serie_a_zero()

    def recommencer_serie(self):
        with self._verrou:
            self._preparer_commande_serie()
            self.seance.recommencer_serie()

    def serie_precedente(self):
        with self._verrou:
            self._preparer_commande_serie()
            return self.seance.serie_precedente()

    def serie_suivante(self):
        with self._verrou:
            self._preparer_commande_serie()
            return self.seance.serie_suivante()

    def terminer_serie(self):
        with self._verrou:
            self._preparer_commande_serie()
            resultat = self.seance.terminer_serie_manuellement()
            if self.seance.phase == "termine":
                self.statut = "finished"
            return resultat

    def abandonner(self):
        with self._verrou:
            if self.seance is None or self.statut not in ("running", "paused"):
                raise RuntimeError("Aucune séance active")
            self.statut = "abandoned"

    def marquer_terminee(self):
        with self._verrou:
            if self.seance is not None and self.seance.phase == "termine":
                self.statut = "finished"

    def nouvelle_seance(self):
        with self._verrou:
            if self.statut in ("running", "paused"):
                raise RuntimeError("Une séance est déjà en cours")
            self.seance = None
            self.nom_selectionne = None
            self.statut = "idle"

    def etat(self):
        with self._verrou:
            return {
                "statut": self.statut,
                "seance": self.nom_selectionne,
                "phase": self.seance.phase if self.seance else "idle",
                "serie_actuelle": self.seance.serie_actuelle if self.seance else 0,
            }