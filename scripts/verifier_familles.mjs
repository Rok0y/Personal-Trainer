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

  // La montee vers la forme chargee : refusee sans de quoi charger.
  const seance = {
    statut: "finished",
    exercices: [{
      nom: "Vide", mode: "repetitions", poids: 0, series_cibles: 3, repetitions_cibles: 12,
      series_detaillees: [1, 2, 3].map((serie) => ({ serie, repetitions: 12, poids: 0, completee: true })),
    }],
  };
  egal("montee : pas vers ce que le materiel ne permet pas",
    variantes_pour(AUCUN).montees({ Charge: "Vide" }, seance, CATALOGUE)[1], []);
  egal("montee : faite avec une paire",
    variantes_pour(PAIRE).montees({ Charge: "Vide" }, seance, CATALOGUE)[1],
    [{ original: "Charge", depuis: "Vide", vers: "Charge" }]);
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
