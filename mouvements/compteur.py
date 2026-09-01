class CompteurMouvement:

    def __init__(self):
        self.stage = None
        self.repetitions = 0

    def mettre_a_jour(self, nouveau_stage):

        if nouveau_stage not in ("debut", "fin"):
            return self.stage, self.repetitions

        # Une répétition exige d'abord une position de départ observée.
        if self.stage == "debut" and nouveau_stage == "fin":
            self.stage = "fin"
            self.repetitions += 1
        elif self.stage == "fin" and nouveau_stage == "debut":
            self.stage = "debut"
        elif self.stage is None:
            self.stage = nouveau_stage

        return self.stage, self.repetitions

    def reset(self):

        self.stage = None
        self.repetitions = 0
