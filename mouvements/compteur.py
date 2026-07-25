class CompteurMouvement:

    def __init__(self):
        self.stage = "debut"
        self.repetitions = 0

    def mettre_a_jour(self, nouveau_stage):

        # Début → Fin
        if (
            self.stage == "debut"
            and nouveau_stage == "fin"
        ):
            self.stage = "fin"

        # Fin → Début = répétition complète
        elif (
            self.stage == "fin"
            and nouveau_stage == "debut"
        ):
            self.stage = "debut"
            self.repetitions += 1

        return self.stage, self.repetitions