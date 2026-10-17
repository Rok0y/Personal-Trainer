// Les regles des createurs de seances et de programmes se tiennent-elles ?
//
// Les createurs (l'outil maitre `dev/createur.html` et ceux de l'application)
// ne font que cabler des fonctions pures, verifiees ici sur des tables
// ecrites dans le script : un reglage de `donnees/` ne doit rien faire rougir.
//
// - les categories d'un mouvement et les etiquettes d'un programme (zone,
//   « sans haltere », « jouable avec mon materiel ») ;
//
//     node scripts/verifier_createurs.mjs

import {
  categories_du_mouvement, etiquettes, exercices_du_programme, nom_zone, zone_des_exercices,
} from "../web/static/js/categories.js";
import { Baremes, composer_baremes } from "../web/static/js/paliers.js";
import { Variantes } from "../web/static/js/variantes.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

// ---------------------------------------------------------------- tables
const CATEGORIES = {
  regions: { haut: { nom: "Haut" }, bas: { nom: "Bas" }, tronc: { nom: "Tronc", accompagne: true } },
  plusieurs_regions: "Partout",
  parties: { bras: { region: "haut" }, jambes: { region: "bas" }, ventre: { region: "tronc" } },
  muscles: { biceps: { partie: "bras" }, quadri: { partie: "jambes" }, abdos: { partie: "ventre" } },
  chaines: { tirer: {}, jambes: {}, gainage: {} },
};
const m = (muscles, chaine, champs = {}) => ({ categories: { muscles, chaine }, ...champs });
const MOUVEMENTS = {
  Curl: m(["biceps"], "tirer"),
  Squat: m(["quadri"], "jambes", { variante_difficile: "Squat charge" }),
  "Squat charge": m(["quadri"], "jambes", { variante_facile: "Squat" }),
  Planche: m(["abdos"], "gainage"),
  Fente: m(["quadri", "abdos"], "jambes"),
  Rotation: m(["biceps", "quadri"], "mobilite", { est_echauffement: true }),
  Muet: {},
};

// --- Categories d'un mouvement : partie et region se deduisent des muscles
egal("categories : deduites des muscles, sans doublon",
  categories_du_mouvement(CATEGORIES, MOUVEMENTS.Fente),
  { muscles: ["quadri", "abdos"], parties: ["jambes", "ventre"], regions: ["bas", "tronc"], chaine: "jambes" });
egal("categories : un mouvement sans categorie rend null", categories_du_mouvement(CATEGORIES, MOUVEMENTS.Muet), null);

// --- Zone : le tronc accompagne, l'echauffement ne compte pas
const zone = (...noms) => zone_des_exercices(CATEGORIES, MOUVEMENTS, noms);
egal("zone : haut seul", zone("Curl"), "haut");
egal("zone : des abdos avec les jambes restent « bas »", zone("Squat", "Planche"), "bas");
egal("zone : le tronc seul est une zone", zone("Planche"), "tronc");
egal("zone : haut et bas font plusieurs regions", zone("Curl", "Fente"), "plusieurs");
egal("zone : l'echauffement n'entre pas", zone("Curl", "Rotation"), "haut");
egal("zone : rien de categorise rend null", zone("Muet", "Inconnu"), null);
egal("zone : les noms", [nom_zone(CATEGORIES, "bas"), nom_zone(CATEGORIES, "plusieurs"), nom_zone(CATEGORIES, null)],
  ["Bas", "Partout", null]);

// --- Exercices d'un programme : seances liees puis exigences, sans doublon
egal("programme : exercices des seances liees puis des exigences",
  exercices_du_programme(
    { seances: { A: "Seance A" }, exigences: [{ exercice: "Curl" }, { exercice: "Planche" }] },
    { "Seance A": [{ exercice: "Rotation" }, { exercice: "Curl" }] },
  ),
  ["Rotation", "Curl", "Planche"]);

// --- Materiel : la regle de `Variantes`, posee a deux inventaires
const spec = (champs) => ({ series: 3, cible_min: 3, cible_max: 12, pas: 1, unite: "repetitions", series_max: 6, poids_min: null, poids_max: null, ...champs });
const TABLES = composer_baremes(
  {
    echelles: { sans_charge: [0], reference: [2, 5, 10], supposes: [2, 5, 10] },
    materiel: { Curl: { halteres: 1 }, Squat: { halteres: 0 }, "Squat charge": { halteres: 2 }, Planche: { halteres: 0 } },
    accessoires: {},
    materiel_par_defaut: { halteres: { 2: 2, 5: 2, 10: 2 }, accessoires: [] },
  },
  {
    specs: { Curl: spec({}), Squat: spec({}), "Squat charge": spec({ poids_min: 5, charge_corps: 15 }), Planche: spec({}) },
    ligues: { ligues: [], divisions: [], seuils_volume: [], seuils_par_exercice: {} },
    xp: { paliers_xp: [], base_niveau_general: 1, increment_niveau_general: 1 },
    note_athlete: { rangs: [] },
  },
);
const CATALOGUE = {
  Curl: { variante_facile: null, analyse_la_pose: true },
  Squat: { variante_facile: null, analyse_la_pose: true },
  "Squat charge": { variante_facile: "Squat", analyse_la_pose: true },
  Planche: { variante_facile: null, analyse_la_pose: true },
};
const question = (materiel) => {
  const variantes = new Variantes(new Baremes(TABLES, materiel));
  return (nom) => variantes.jouable_avec_le_materiel(nom, CATALOGUE);
};
const sans_haltere = question({ halteres: {}, accessoires: [] });
const avec_un = question({ halteres: { 5: 1 }, accessoires: [] });
const etiq = (noms, questions) => etiquettes(CATEGORIES, MOUVEMENTS, noms, questions);

egal("materiel : un squat charge se joue sans haltere (par sa variante a vide)",
  etiq(["Squat charge", "Planche"], { sans_haltere }).sans_haltere, true);
egal("materiel : un curl ne se joue pas sans haltere", etiq(["Curl", "Squat"], { sans_haltere }).sans_haltere, false);
egal("materiel : un seul haltere de 5 kg suffit au curl", etiq(["Curl"], { jouable: avec_un }).jouable, true);
egal("materiel : l'echauffement ne demande rien",
  etiq(["Rotation", "Squat"], { sans_haltere }).sans_haltere, true);
egal("materiel : sans question, on ne sait pas (null, jamais « oui »)",
  etiq(["Curl"], {}), { zone: "haut", sans_haltere: null, jouable: null });

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : les regles des createurs se tiennent.`);
}
