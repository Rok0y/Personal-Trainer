// Jumeau de core/state.py — l'etat d'une seance en cours.
//
// Une fabrique et non une classe : cote Python c'est une `dataclass`, dont
// l'interet est d'interdire un defaut mutable partage entre deux seances. En
// JavaScript un objet neuf par appel donne la meme garantie sans ceremonie.
//
// Le flux video n'est volontairement pas ici (cote Python : `core/flux.py`).
// Il n'existe pas dans le navigateur, ou c'est la camera de l'appareil qui
// affiche sa propre image — la frontiere du portage se lit dans ce qui est
// absent.

export function creer_etat() {
  return {
    // --- Etat du programme ---
    position_actuelle: "Aucune",
    exercice_actuel: "Aucun",
    mode: "Aucun",
    // Jeton brut rendu par la detection. Reste brut : `etape_libelle` en porte
    // la traduction, et le front n'a plus a deviner la posture en comparant
    // des chaines.
    stage: "Aucune",
    etape_libelle: null,
    // `erreur` reproche une faute de forme, `consigne` dit quoi faire. Les
    // deux coexistent a l'ecran, dans deux bandeaux differents.
    erreur: null,
    consigne: null,
    fiche: null,
    // Champ distinct de `fiche` et non son remplacant : pendant une
    // recuperation on refait le meme mouvement et c'est `fiche` qu'il faut
    // relire ; pendant un repos d'exercice on prepare le suivant, et le
    // materiel comme le cadrage se decident avant la premiere repetition.
    fiche_suivante: null,
    test_max: false,

    repetitions: 0,
    repetitions_cibles: 10,
    temps_maintien: 0,
    duree_maintien: 0,
    temps_chrono: 0,
    chrono_termine: false,
    temps_echauffement: 0,
    duree_echauffement: 0,
    prochaine_etape: null,

    // --- Circuit ---
    serie_actuelle: 1,
    nombre_series: 1,
    phase: "exercice",
    temps_repos_restant: 0,
    temps_amrap_restant: 0,
    poids: 0,

    // --- Maintien ---
    maintien_termine: false,
    progression_maintien: 0,
    progression_preparation: 0,
  };
}
