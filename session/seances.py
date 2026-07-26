from session.circuit import Circuit, BlocExercice

from mouvements.exercices import (
    curl_biceps_droit,
    curl_biceps_gauche,
    elevation_laterale,
    pompe,
    extension_triceps_au_dessus_de_la_tete,
    developpe_couche_sol
)

Test_exercice = Circuit([
    BlocExercice(
        exercice=pompe,
        nombre_series=1,
        repetitions_par_serie=1000,
        repos_entre_series=30,
        repos_apres=60
    )
])

seance_bras = Circuit([
    BlocExercice(
        exercice=curl_biceps_droit,
        nombre_series=3,
        repetitions_par_serie=10,
        repos_entre_series=30,
        repos_apres=60
    ),
    BlocExercice(
        exercice=curl_biceps_gauche,
        nombre_series=3,
        repetitions_par_serie=10,
        repos_entre_series=30,
        repos_apres=0
    )
])

seance_test = Circuit([
    BlocExercice(
        exercice=curl_biceps_droit,
        nombre_series=1,
        repetitions_par_serie=5,
        repos_entre_series=5,
        repos_apres=5
    ),
    BlocExercice(
        exercice=curl_biceps_gauche,
        nombre_series=1,
        repetitions_par_serie=5,
        repos_entre_series=5,
        repos_apres=5
    ),
    BlocExercice(
        exercice=elevation_laterale,
        nombre_series=1,
        repetitions_par_serie=5,
        repos_entre_series=5,
        repos_apres=5
    ),
    BlocExercice(
        exercice=pompe,
        nombre_series=1,
        repetitions_par_serie=5,
        repos_entre_series=5,
        repos_apres=5
    ),
    BlocExercice(
        exercice=extension_triceps_au_dessus_de_la_tete,
        nombre_series=1,
        repetitions_par_serie=5,
        repos_entre_series=5,
        repos_apres=5
    ),
    BlocExercice(
        exercice=developpe_couche_sol,
        nombre_series=1,
        repetitions_par_serie=5,
        repos_entre_series=5,
        repos_apres=0
    )
])

seance_bras = Circuit([
    BlocExercice(exercice=curl_biceps_droit,
        nombre_series=3,
        repetitions_par_serie=10,
        repos_entre_series=30,
        repos_apres=60
    ),
    BlocExercice(exercice=curl_biceps_gauche,
        nombre_series=3,
        repetitions_par_serie=10,
        repos_entre_series=30,
        repos_apres=0
    )
])
