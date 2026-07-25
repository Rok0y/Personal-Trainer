class CompteurMouvement:

    def __init__(self):

        self.stage = "debut"
        self.repetitions = 0


    def mettre_a_jour(self, nouveau_stage):

        # ---------------------------------------------
        # Début → Fin = 1 répétition
        # ---------------------------------------------

        if (
            self.stage == "debut"
            and nouveau_stage == "fin"
        ):

            self.stage = "fin"
            self.repetitions += 1


        # ---------------------------------------------
        # Fin → Début
        # ---------------------------------------------

        elif (
            self.stage == "fin"
            and nouveau_stage == "debut"
        ):

            self.stage = "debut"
            

        # ---------------------------------------------
        # Toujours retourner les deux valeurs
        # ---------------------------------------------

        return self.stage, self.repetitions


    def reset(self):

        self.stage = "debut"
        self.repetitions = 0