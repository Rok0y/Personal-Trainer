class CompteurMouvement:

    def __init__(self):
        self.stage = "debut"
        self.repetitions = 0

    def mettre_a_jour(self, nouveau_stage):

        # Passage début → fin = mouvement réalisé
        if (
            self.stage == "debut"
            and nouveau_stage == "fin"
        ):
            self.stage = "fin"
            self.repetitions += 1

        # Passage fin → début = nouvelle répétition
        elif (
            self.stage == "fin"
            and nouveau_stage == "debut"
        ):
            self.stage = "debut"
            

        return self.stage, self.repetitions

    def reset(self):

        self.stage = "debut"
        self.repetitions = 0