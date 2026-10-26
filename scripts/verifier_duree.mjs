// La duree estimee d'une seance (`duree.js`) suit-elle les repos du circuit ?
//
// L'estimation fait jouer le `Circuit` lui-meme sur une horloge simulee : ce
// test ecrit a la main ce que ce jeu doit rendre, superset compris (la pause
// qui suit A est le `repos_entre_series` de B, le `repos_apres` du partenaire
// n'est jamais joue, le dernier bloc n'a pas de repos). Des blocs minimaux,
// des tempos ecrits ici : un reglage de `reglages.json` ne doit rien faire
// rougir.
//
//     node scripts/verifier_duree.mjs

import { BlocExercice, Circuit, Exercice } from "../web/static/js/circuit.js";
import { duree_estimee, libelle_duree } from "../web/static/js/duree.js";

const TEMPO = { A: 3, B: 2 };

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

/** Un bloc : `cible` en repetitions ou en secondes selon le mode. */
function bloc(nom, { mode = "repetitions", series = 1, cible, entre = 0, apres = 0, avec = null }) {
  const en_secondes = mode !== "repetitions";
  return new BlocExercice({
    exercice: new Exercice({ nom }),
    poids: 0,
    mode,
    nombre_series: series,
    repetitions_par_serie: en_secondes ? 0 : cible,
    duree: en_secondes ? cible : 0,
    repos_entre_series: entre,
    repos_apres: apres,
    entrelace_avec: avec,
  });
}
const duree = (...blocs) => duree_estimee(new Circuit(blocs), TEMPO);

// --- Effort et repos
egal("un bloc : 3 x 10 a 3 s, 60 s entre les series, pas de repos final",
  duree(bloc("A", { series: 3, cible: 10, entre: 60, apres: 90 })),
  3 * 30 + 2 * 60);
egal("deux blocs : le repos entre exercices du premier compte, pas celui du dernier",
  duree(
    bloc("A", { series: 2, cible: 10, entre: 30, apres: 90 }),
    bloc("B", { series: 2, cible: 5, entre: 20, apres: 40 }),
  ),
  (30 + 30 + 30) + 90 + (10 + 20 + 10));
egal("repos entre exercices nul : on enchaine",
  duree(bloc("A", { cible: 10, apres: 0 }), bloc("B", { cible: 5 })),
  30 + 10);

// --- Superset : A1, repos de B, B1, repos de A, A2, repos de B, B2, repos
// apres de A (celui de B n'est jamais joue), puis C.
egal("superset",
  duree(
    bloc("A", { series: 2, cible: 10, entre: 30, apres: 90, avec: "B" }),
    bloc("B", { series: 2, cible: 5, entre: 20, apres: 50 }),
    bloc("C", { mode: "maintien", cible: 40 }),
  ),
  30 + 20 + 10 + 30 + 30 + 20 + 10 + 90 + 40);

// --- Circuit de trois AMRAP en deux tours : la transition de chaque membre,
// le repos entre tours de la tete, puis son repos apres (ceux des membres
// ne sont jamais joues).
egal("circuit en tours",
  duree(
    bloc("X", { mode: "amrap", series: 2, cible: 30, entre: 60, apres: 90, avec: "Y" }),
    bloc("Y", { mode: "amrap", series: 2, cible: 30, entre: 10, apres: 45, avec: "Z" }),
    bloc("Z", { mode: "amrap", series: 2, cible: 30, entre: 10, apres: 45 }),
    bloc("C", { mode: "maintien", cible: 40 }),
  ),
  (30 + 10 + 30 + 10 + 30) + 60 + (30 + 10 + 30 + 10 + 30) + 90 + 40);

// --- Cibles en secondes : leur duree, sans tempo
egal("maintien : 3 x 30 s, 15 s entre les series",
  duree(bloc("G", { mode: "maintien", series: 3, cible: 30, entre: 15 })),
  3 * 30 + 2 * 15);
egal("echauffement compte, son repos aussi",
  duree(bloc("E", { mode: "echauffement", cible: 30, apres: 5 }), bloc("A", { cible: 10 })),
  30 + 5 + 30);
egal("AMRAP : sa duree", duree(bloc("Z", { mode: "amrap", cible: 60 })), 60);
egal("chrono : sa duree", duree(bloc("Z", { mode: "chrono", cible: 45 })), 45);

// --- Pas d'estimation plutot qu'une fausse
egal("mouvement compte sans tempo", duree(bloc("A", { cible: 10, apres: 30 }), bloc("Z", { cible: 10 })), null);
egal("seance vide", duree_estimee(new Circuit([]), TEMPO), null);

// --- Libelle
egal("libelle : rien", [libelle_duree(null), libelle_duree(0)], [null, null]);
egal("libelle : au moins une minute", libelle_duree(20), "≈ 1 min");
egal("libelle : a la minute sous un quart d'heure", [libelle_duree(14 * 60 + 29), libelle_duree(14 * 60 + 59)], ["≈ 14 min", "≈ 15 min"]);
egal("libelle : aux cinq minutes au-dela", [libelle_duree(15 * 60), libelle_duree(37 * 60), libelle_duree(38 * 60)], ["≈ 15 min", "≈ 35 min", "≈ 40 min"]);
egal("libelle : en heures", [libelle_duree(60 * 60), libelle_duree(65 * 60), libelle_duree(92 * 60 + 40)], ["≈ 1 h", "≈ 1 h 05", "≈ 1 h 35"]);

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : la duree estimee suit les repos du circuit.`);
}
