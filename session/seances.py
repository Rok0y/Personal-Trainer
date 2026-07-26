from seance.circuit import Circuit, BlocExercice

from mouvements.exercices import (
    curl_biceps_droit,
    curl_biceps_gauche
)


seance = Circuit([
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