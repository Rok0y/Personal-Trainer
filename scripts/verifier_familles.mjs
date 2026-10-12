// Les familles de variantes suivent-elles la note et le materiel ?
//
// Deux regles que les reponses figees de `comparer_variantes` ne visitent
// pas (leurs entrees datent d'avant) :
// - **le mouvement de depart** d'une famille jamais jouee vient de la note
//   d'athlete (`selon_la_note`) ;
// - **le materiel** l'emporte sur la preference : un mouvement charge que le
//   profil ne peut pas charger se joue sous sa variante a vide, ne se
//   propose pas, et on n'y monte pas.
//
// Les tables sont ecrites ici, minimales, et non lues dans `donnees/` : un
// reglage de bareme ne doit pas faire rougir une regle.
//
//     node scripts/verifier_familles.mjs

import { Baremes, composer_baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import { Variantes } from "../web/static/js/variantes.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

const spec = (champs) => ({ series: 3, cible_min: 3, cible_max: 12, pas: 1, unite: "repetitions", series_max: 6, poids_min: null, poids_max: null, ...champs });
const SOCLE = {
  echelles: { sans_charge: [0], reference: [2, 5, 10], supposes: [2, 5, 10] },
  materiel: {
    Chaise: { halteres: 0 }, Vide: { halteres: 0 }, Charge: { halteres: 2 },
    Mur: { halteres: 0 }, Pompe: { halteres: 0 },
  },
  accessoires: {},
  materiel_par_defaut: { halteres: { 2: 2, 5: 2, 10: 2 }, accessoires: [] },
};
const REGLAGES = {
  specs: {
    Chaise: spec({}), Vide: spec({}), Charge: spec({ poids_min: 5, charge_corps: 15 }),
    Mur: spec({}), Pompe: spec({}),
  },
  ligues: { ligues: [], divisions: [], seuils_volume: [], seuils_par_exercice: {} },
  xp: { paliers_xp: [], base_niveau_general: 1, increment_niveau_general: 1 },
  note_athlete: { rangs: [] },
  variantes: {
    retour: { Vide: [3, 12], Mur: [3, 12] },
    depart: { Charge: { Vide: 1, Charge: 5 }, Pompe: { Mur: 1, Pompe: 3 } },
  },
};
const CATALOGUE = {
  Chaise: { variante_facile: null, variante_difficile: "Vide", analyse_la_pose: true },
  Vide: { variante_facile: "Chaise", variante_difficile: "Charge", analyse_la_pose: true },
  Charge: { variante_facile: "Vide", variante_difficile: null, analyse_la_pose: true },
  Mur: { variante_facile: null, variante_difficile: "Pompe", analyse_la_pose: true },
  Pompe: { variante_facile: "Mur", variante_difficile: null, analyse_la_pose: true },
};
const tables = composer_baremes(SOCLE, REGLAGES);
const variantes_pour = (materiel) => {
  const baremes = new Baremes(tables, materiel);
  return new Variantes(baremes, tables.variantes.retour, new Niveaux(baremes), tables.variantes.depart);
};
const AUCUN = { halteres: {}, accessoires: [] };
const UN_SEUL = { halteres: { 10: 1 }, accessoires: [] };
const LEGERS = { halteres: { 2: 2 }, accessoires: [] };
const PAIRE = { halteres: { 5: 2 }, accessoires: [] };

// --- Le materiel
for (const [nom, materiel, attendu] of [
  ["aucun haltere", AUCUN, "Vide"],
  ["un seul haltere", UN_SEUL, "Vide"],
  ["des halteres trop legers pour la fourchette", LEGERS, "Vide"],
  ["une paire dans la fourchette", PAIRE, null],
  ["profil muet (materiel suppose)", null, null],
]) {
  egal(`materiel, ${nom} : ce qui se joue a la place du mouvement charge`,
    variantes_pour(materiel).substitution("Charge", "repetitions", {}, CATALOGUE), attendu);
}
{
  const v = variantes_pour(AUCUN);
  egal("materiel : la preference « chaise » reste jouee", v.substitution("Charge", "repetitions", { Charge: "Chaise" }, CATALOGUE), "Chaise");
  egal("materiel : un mouvement sans haltere n'est jamais remplace", v.substitution("Vide", "repetitions", {}, CATALOGUE), null);
  egal("materiel : un echauffement n'est jamais remplace", v.substitution("Charge", "echauffement", {}, CATALOGUE), null);
  egal("materiel : rien a choisir pour un original injouable", v.versions("Charge", "repetitions", CATALOGUE), []);
  egal("materiel : le choix reste offert avec une paire",
    variantes_pour(PAIRE).versions("Charge", "repetitions", CATALOGUE), ["Charge", "Vide", "Chaise"]);

  // La montee vers la forme chargee. Le seuil (3x12) se lit « avec le
  // premier haltere » : a vide, il demande 3x12 x (5 + 15) / 15 = 48, soit
  // 3x16, avec des 5 kg ; 3x12 x 25 / 15 = 60, soit 3x20, avec des 10 kg.
  const seance = (repetitions) => ({
    statut: "finished",
    exercices: [{
      nom: "Vide", mode: "repetitions", poids: 0, series_cibles: 3, repetitions_cibles: repetitions,
      series_detaillees: [1, 2, 3].map((serie) => ({ serie, repetitions, poids: 0, completee: true })),
    }],
  });
  const MONTEE = [{ original: "Charge", depuis: "Vide", vers: "Charge" }];
  const LOURDS = { halteres: { 10: 2 }, accessoires: [] };
  egal("montee : pas vers ce que le materiel ne permet pas",
    variantes_pour(AUCUN).montees({ Charge: "Vide" }, seance(30), CATALOGUE)[1], []);
  egal("montee, paire de 5 kg : 3x12 a vide ne suffit plus",
    variantes_pour(PAIRE).montees({ Charge: "Vide" }, seance(12), CATALOGUE)[1], []);
  egal("montee, paire de 5 kg : 3x16 a vide suffit",
    variantes_pour(PAIRE).montees({ Charge: "Vide" }, seance(16), CATALOGUE)[1], MONTEE);
  egal("montee, paire de 10 kg : 3x16 a vide ne suffit pas",
    variantes_pour(LOURDS).montees({ Charge: "Vide" }, seance(16), CATALOGUE)[1], []);
  egal("montee, paire de 10 kg : 3x20 a vide suffit",
    variantes_pour(LOURDS).montees({ Charge: "Vide" }, seance(20), CATALOGUE)[1], MONTEE);
  egal("montee entre variantes sans charge : le seuil se lit tel quel",
    variantes_pour(PAIRE).montees({ Pompe: "Mur" }, { ...seance(12), exercices: [{ ...seance(12).exercices[0], nom: "Mur" }] }, CATALOGUE)[1],
    [{ original: "Pompe", depuis: "Mur", vers: "Pompe" }]);

  // Le palier d'entree : meme volume, la repetition a vide pesant 15.
  const resume = (p) => (p ? `${p.series}x${p.cible}@${p.poids}` : null);
  const entree = (materiel, cible) =>
    resume(new Baremes(tables, materiel).palier_d_entree("Vide", { series: 3, cible, poids: 0 }, "Charge"));
  egal("entree, paire de 5 kg, depuis 3x16 a vide : 3x12 a 5 kg", entree(PAIRE, 16), "3x12@5");
  egal("entree, paire de 10 kg, depuis 3x20 a vide : 3x12 a 10 kg", entree(LOURDS, 20), "3x12@10");
  egal("entree : rien entre variantes sans charge",
    new Baremes(tables, PAIRE).palier_d_entree("Mur", { series: 3, cible: 12, poids: 0 }, "Pompe"), null);
}

// --- Le mouvement de depart selon la note
{
  const v = variantes_pour(PAIRE);
  const depart = (note, seances = [], ancrages = {}, table = {}) => v.selon_la_note(table, note, seances, ancrages, CATALOGUE);
  egal("note 1 : le bas de chaque table", depart(1), { Charge: "Vide", Pompe: "Mur" });
  egal("note 3 : pompes completes, squat a vide", depart(3), { Charge: "Vide" });
  egal("note 5 : les deux formes completes", depart(5), {});
  egal("sans note : le bas de chaque table", depart(null), { Charge: "Vide", Pompe: "Mur" });
  egal("famille deja jouee : la note n'y touche plus",
    depart(5, [{ exercices: [{ nom: "Mur" }] }], {}, { Pompe: "Mur" }), { Pompe: "Mur" });
  egal("famille ancree : la note n'y touche plus", depart(1, [], { Pompe: { niveau: 3 } }), { Charge: "Vide" });
  egal("une preference d'une famille jamais jouee suit la note", depart(5, [], {}, { Charge: "Chaise" }), {});
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : les familles suivent la note et le materiel.`);
}
