# Delai minimal, en secondes, entre deux repetitions comptees. Un curl a ete
# compte deux fois d'un coup : un saut d'une ou deux images de la detection
# suffit a refaire un aller-retour "debut" -> "fin" juste apres une vraie
# repetition, et le compteur, sans notion du temps, le prenait pour une
# seconde. Aucune repetition reelle ne tient en 0,3 s, meme enchainee vite.
DELAI_MIN_ENTRE_REPS = 0.3


class CompteurMouvement:

    def __init__(self):
        self.stage = None
        self.repetitions = 0
        self.derniere_rep_a = None

    def mettre_a_jour(self, nouveau_stage, instant=None):
        """`instant` est l'horloge de la seance ; None desactive le delai."""

        if nouveau_stage not in ("debut", "fin"):
            return self.stage, self.repetitions

        # Une répétition exige d'abord une position de départ observée.
        if self.stage == "debut" and nouveau_stage == "fin":
            self.stage = "fin"
            # Trop tot apres la precedente : c'est la meme repetition, vue deux
            # fois. Le stage passe quand meme a "fin", sinon la vraie
            # repetition suivante trouverait le compteur arme d'avance.
            if (
                instant is None
                or self.derniere_rep_a is None
                or instant - self.derniere_rep_a >= DELAI_MIN_ENTRE_REPS
            ):
                self.repetitions += 1
                self.derniere_rep_a = instant
        elif self.stage == "fin" and nouveau_stage == "debut":
            self.stage = "debut"
        elif self.stage is None:
            self.stage = nouveau_stage

        return self.stage, self.repetitions

    def ajuster(self, delta):
        """Corrige le compte à la main (geste bras levé), jamais sous zéro.

        Le `stage` ne bouge pas : la répétition en cours reste armée ou non
        selon ce que la détection a vu, la correction ne porte que sur le
        nombre.
        """
        self.repetitions = max(0, self.repetitions + delta)
        return self.repetitions

    def reset(self):

        self.stage = None
        self.repetitions = 0
        self.derniere_rep_a = None
