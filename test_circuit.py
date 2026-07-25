import time

from seance.seance_test import seance


print("===================================")
print(" TEST DU CIRCUIT")
print("===================================")

print()
print("Exercice :", seance.exercice_actuel.__name__)
print("Série :", seance.serie_actuelle, "/", seance.nombre_series)
print("Phase :", seance.phase)

print()
print("Appuie sur ENTRÉE pour simuler")
print("la fin de la série actuelle.")
print()


while seance.phase != "termine":

    # --------------------------------------------------
    # EXERCICE
    # --------------------------------------------------

    if seance.phase == "exercice":

        print()
        print("-----------------------------------")
        print(
            "Exercice :",
            seance.exercice_actuel.__name__
        )

        print(
            "Série :",
            seance.serie_actuelle,
            "/",
            seance.nombre_series
        )

        print(
            "Objectif :",
            seance.repetitions_cibles,
            "répétitions"
        )

        input(
            "\n[ENTRÉE] Série terminée → "
        )

        seance.terminer_serie()


    # --------------------------------------------------
    # RÉCUPÉRATION ENTRE LES SÉRIES
    # --------------------------------------------------

    elif seance.phase == "recuperation_serie":

        print()
        print(
            "Récupération entre séries :",
            round(seance.temps_restant, 1),
            "secondes"
        )

        while seance.phase == "recuperation_serie":

            seance.update()

            print(
                "\rTemps restant :",
                round(seance.temps_restant, 1),
                "s",
                end="",
                flush=True
            )

            time.sleep(0.1)

        print()


    # --------------------------------------------------
    # REPOS ENTRE DEUX EXERCICES
    # --------------------------------------------------

    elif seance.phase == "repos_exercice":

        print()
        print(
            "Repos après exercice :",
            round(seance.temps_restant, 1),
            "secondes"
        )

        while seance.phase == "repos_exercice":

            seance.update()

            print(
                "\rTemps restant :",
                round(seance.temps_restant, 1),
                "s",
                end="",
                flush=True
            )

            time.sleep(0.1)

        print()


# ------------------------------------------------------
# FIN
# ------------------------------------------------------

print()
print("===================================")
print("       SÉANCE TERMINÉE")
print("===================================")