// Un circuit en tours (A B C D, A B C D…) se joue-t-il comme il faut ?
//
// Les scenarios figes de `comparer_seances` ne connaissent que des paires
// (supersets) : un circuit de plus de deux blocs n'y est jamais visite. Ces
// cas sont donc ecrits ici a la main, avec leur reponse attendue — et une
// paire y rend la suite d'avant la generalisation, ecrite elle aussi en clair.
//
// La regle des repos : avant chaque serie, le `repos_entre_series` **du bloc
// qu'on va jouer** (sur la tete : le repos entre deux tours ; sur un membre :
// la transition). Apres le dernier tour, le `repos_apres` de la tete ; celui
// des membres n'est jamais joue.
//
//     node scripts/verifier_circuit_tours.mjs

import { BlocExercice, Circuit, Exercice } from "../web/static/js/circuit.js";
import { problemes_des_blocs, resultats_par_exercice } from "../web/static/js/seance.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

/** Un bloc minimal : 10 repetitions par serie. */
function bloc(nom, { series = 3, entre = 0, apres = 0, avec = null, mode = "repetitions", facile = null } = {}) {
  return new BlocExercice({
    exercice: new Exercice({ nom, variante_facile: facile }),
    poids: 0,
    mode,
    nombre_series: series,
    repetitions_par_serie: mode === "repetitions" ? 10 : 0,
    duree: mode === "repetitions" ? 0 : 30,
    repos_entre_series: entre,
    repos_apres: apres,
    entrelace_avec: avec,
  });
}

/** Un circuit sur une horloge qu'on avance a la main. */
function circuit(...blocs) {
  const horloge = { t: 1000 };
  const c = new Circuit(blocs);
  c.maintenant = () => horloge.t;
  c.debut = horloge.t;
  c.horloge = horloge;
  c.commencer_exercice();
  return c;
}

/** Laisse passer le repos en cours, et rend sa duree. */
function laisser_reposer(c) {
  const repos = c.temps_restant;
  c.horloge.t += repos;
  c.update();
  return repos;
}

/**
 * Joue la seance jusqu'au bout (ou `pas` series), en notant chaque serie
 * (« B2 ») et chaque repos (« ~10 »). `avant_serie(c, trace)` peut agir avant
 * qu'une serie se termine.
 */
function jouer(c, { pas = 100, avant_serie = null } = {}) {
  const trace = [];
  let series = 0;
  for (let garde = 0; garde < 400 && c.phase !== "termine" && series < pas; garde++) {
    if (c.phase === "exercice") {
      if (avant_serie && avant_serie(c, trace)) continue;
      trace.push(`${c.bloc_actuel.exercice.nom}${c.serie_actuelle}`);
      c.enregistrer_resultat_serie({ repetitions: 10 });
      c.terminer_serie();
      series += 1;
    } else {
      trace.push(`~${laisser_reposer(c)}`);
    }
  }
  return trace;
}

const quatre = () => [
  bloc("A", { entre: 60, apres: 90, avec: "B" }),
  bloc("B", { entre: 10, apres: 45, avec: "C" }),
  bloc("C", { entre: 10, apres: 45, avec: "D" }),
  bloc("D", { entre: 10, apres: 45 }),
];

// --- L'ordre et les repos
egal("circuit de quatre en trois tours, suivi d'un bloc seul",
  jouer(circuit(...quatre(), bloc("E", { series: 1 }))),
  ["A1", "~10", "B1", "~10", "C1", "~10", "D1", "~60",
   "A2", "~10", "B2", "~10", "C2", "~10", "D2", "~60",
   "A3", "~10", "B3", "~10", "C3", "~10", "D3", "~90", "E1"]);
egal("circuit en fin de seance : pas de repos apres le dernier tour",
  jouer(circuit(bloc("Z", { series: 1, apres: 30 }), ...quatre())),
  ["Z1", "~30", "A1", "~10", "B1", "~10", "C1", "~10", "D1", "~60",
   "A2", "~10", "B2", "~10", "C2", "~10", "D2", "~60",
   "A3", "~10", "B3", "~10", "C3", "~10", "D3"]);
egal("une paire rend la suite d'avant (le repos de B avant B, celui de A avant A, le repos apres de A)",
  jouer(circuit(
    bloc("A", { series: 2, entre: 30, apres: 90, avec: "B" }),
    bloc("B", { series: 2, entre: 20, apres: 50 }),
    bloc("C", { series: 1 }),
  )),
  ["A1", "~20", "B1", "~30", "A2", "~20", "B2", "~90", "C1"]);
egal("la tete fait le nombre de tours",
  jouer(circuit(bloc("A", { series: 2, avec: "B" }), bloc("B", { series: 3, avec: "C" }), bloc("C", { series: 1 }))),
  ["A1", "~0", "B1", "~0", "C1", "~0", "A2", "~0", "B2", "~0", "C2"]);

// --- Les series enregistrees : chaque bloc garde les siennes
{
  const c = circuit(...quatre());
  jouer(c);
  egal("chaque bloc a ses trois series, dans l'ordre",
    resultats_par_exercice(c).map((l) => [l.nom, l.series_detaillees.map((s) => s.serie)]),
    [["A", [1, 2, 3]], ["B", [1, 2, 3]], ["C", [1, 2, 3]], ["D", [1, 2, 3]]]);
  egal("la barre de progression remplit chaque bloc", c.etat_des_series(c.exercices).map((e) => e.series.map(Boolean)),
    Array(4).fill([true, true, true]));
  egal("series terminees", c.series_terminees, 12);
}
{
  const c = circuit(bloc("Jumping jacks", { mode: "echauffement", series: 1 }), ...quatre());
  c.exercices[1].exercice = new Exercice({ nom: "Jumping jacks" });
  jouer(c);
  egal("le meme mouvement en echauffement puis compte : une seule ligne, celle du bloc compte",
    resultats_par_exercice(c).map((l) => [l.nom, l.series]),
    [["Jumping jacks", 3], ["B", 3], ["C", 3], ["D", 3]]);
}

// --- Ce que dit et propose le circuit en route
{
  const c = circuit(...quatre(), bloc("E", { series: 1 }));
  const vus = [];
  jouer(c, {
    avant_serie(c) {
      vus.push([
        `${c.bloc_actuel.exercice.nom}${c._tour}`,
        c.change_de_bloc(),
        c.prochain_bloc()?.exercice.nom ?? null,
        c.variante_possible(),
      ]);
      return false;
    },
  });
  const dans_le_circuit = vus.filter((v) => !v[0].startsWith("E"));
  egal("le prochain exercice est E depuis tout le circuit", [...new Set(dans_le_circuit.map((v) => v[2]))], ["E"]);
  egal("aucune variante dans un circuit", [...new Set(dans_le_circuit.map((v) => v[3]))], [null]);
}
{
  const c = circuit(
    bloc("A", { avec: "B", entre: 60, facile: "a" }),
    bloc("B", { avec: "C", entre: 10, facile: "b" }),
    bloc("C", { entre: 10, facile: "c" }),
  );
  const variantes = [];
  const transitions = [];
  for (let garde = 0; garde < 100 && c.phase !== "termine"; garde++) {
    if (c.phase === "exercice") {
      variantes.push(c.variante_possible());
      c.enregistrer_resultat_serie({ repetitions: 10 });
      c.terminer_serie();
    } else {
      transitions.push(c.change_de_bloc() ? c.bloc_actuel.exercice.nom : "-");
      laisser_reposer(c);
    }
  }
  egal("variante refusee sur tous les membres, tete comprise", [...new Set(variantes)], [null]);
  egal("chaque pause du circuit change de bloc", transitions, ["B", "C", "A", "B", "C", "A", "B", "C"]);
}
{
  const c = circuit(bloc("A", { series: 2, entre: 10 }), bloc("B", { series: 1 }));
  c.enregistrer_resultat_serie({ repetitions: 10 });
  c.terminer_serie();
  egal("un bloc seul : la pause entre deux series ne change pas de bloc", c.change_de_bloc(), false);
}
{
  const c = circuit(...quatre());
  const amorces = [];
  amorces.push(["A", c.amorce_annonce(c.exercices[0])]);
  jouer(c, {
    avant_serie(c) {
      amorces.push([`${c.bloc_actuel.exercice.nom}${c._tour}`, c.amorce_annonce(c.bloc_actuel)]);
      return false;
    },
  });
  egal("amorces : premier a l'entree seulement, pour finir au dernier tour seulement",
    amorces.filter(([, a]) => a !== "prochain_exercice"),
    [["A", "premier_exercice"], ["A1", "premier_exercice"], ["D3", "dernier_exercice"]]);
}

// --- Refaire la derniere serie
{
  const c = circuit(...quatre(), bloc("E", { series: 1 }));
  jouer(c, { pas: 2 });
  c.refaire_derniere_serie();
  egal("refaire en plein tour : B1 de nouveau, puis la suite",
    jouer(c, { pas: 3 }), ["B1", "~10", "C1", "~10", "D1"]);
  c.refaire_derniere_serie();
  egal("refaire a la frontiere d'un tour : D1, puis A2", jouer(c, { pas: 2 }), ["D1", "~60", "A2"]);
}
{
  const c = circuit(...quatre(), bloc("E", { series: 1, apres: 0 }));
  jouer(c, { pas: 12 });
  egal("apres D3 : le repos apres de la tete", c.phase, "repos_exercice");
  c.refaire_derniere_serie();
  egal("refaire D3 : D3 de nouveau, puis le repos et E", jouer(c), ["D3", "~90", "E1"]);
  egal("une seule serie par case, refaite ou non",
    resultats_par_exercice(c).map((l) => l.series), [3, 3, 3, 3, 1]);
}

// --- Terminer une serie a la main
{
  const c = circuit(...quatre());
  jouer(c, { pas: 1 });
  laisser_reposer(c);
  c.terminer_serie_manuellement({ repetitions: 4 });
  egal("B1 terminee a la main sous sa cible : manquee, et le tour continue",
    [c.resultats_series.at(-1).exercice, c.resultats_series.at(-1).completee, laisser_reposer(c), c.bloc_actuel.exercice.nom],
    ["B", false, 10, "C"]);
}

// --- Ce qu'on refuse a l'enregistrement
{
  const mouvements = {
    A: { detection: "x" }, B: { detection: "x" }, C: { detection: "x" },
    Sprint: { detection: null },
  };
  const json = (exercice, extra = {}) => ({ exercice, mode: "amrap", series: 3, duree: 30, repetitions: 0, ...extra });
  egal("circuit de trois AMRAP, un chrono sans detection au bout : accepte",
    problemes_des_blocs(mouvements, [
      json("A", { entrelace_avec: "B" }), json("B", { entrelace_avec: "C" }), json("C", { entrelace_avec: "Sprint" }),
      json("Sprint", { mode: "chrono" }),
    ]), []);
  egal("series inegales dans un circuit : refuse",
    problemes_des_blocs(mouvements, [json("A", { entrelace_avec: "B" }), json("B", { series: 2 })]).length, 1);
  egal("un echauffement dans un circuit : refuse",
    problemes_des_blocs(mouvements, [json("A", { entrelace_avec: "Sprint" }), json("Sprint", { mode: "echauffement" })]).length, 1);
  egal("deux circuits separes, chacun ses series : accepte",
    problemes_des_blocs(mouvements, [
      json("A", { entrelace_avec: "B" }), json("B"),
      json("C", { series: 2, entrelace_avec: "A" }), json("A", { series: 2 }),
    ]), []);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : les circuits se jouent en tours.`);
}
