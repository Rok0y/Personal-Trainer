// Les regles des createurs de seances et de programmes se tiennent-elles ?
//
// Les createurs (l'outil maitre `dev/createur.html` et ceux de l'application)
// ne font que cabler des fonctions pures, verifiees ici sur des tables
// ecrites dans le script : un reglage de `donnees/` ne doit rien faire rougir.
//
// - les categories d'un mouvement et les etiquettes d'un programme (zone,
//   « sans haltere », « jouable avec mon materiel ») ;
// - les seances et programmes perso, rattaches au profil : un autre profil
//   n'en voit rien, un renommage emporte les programmes qui citent la
//   seance, une seance citee ne se supprime pas en laissant un programme
//   sans rien a jouer ;
// - l'entrelacement « avec le bloc suivant », recalcule ;
// - les exigences preremplies depuis les seances, et les refus d'un
//   programme (les memes que `verifier_donnees` pose aux programmes deployes) ;
// - la promotion d'une creation perso en version commune (outil maitre).
//
//     node scripts/verifier_createurs.mjs

import {
  categories_du_mouvement, etiquettes, exercices_du_programme, nom_zone, zone_des_exercices,
} from "../web/static/js/categories.js";
import {
  base_vide, creer_utilisateur, enregistrer_programme_perso, enregistrer_seance_perso,
  est_programme_perso, oublier_seance_perso, programmes_perso, renommer_seance_perso,
  seances_perso, supprimer_programme_perso,
} from "../web/static/js/historique.js";
import { Baremes, composer_baremes } from "../web/static/js/paliers.js";
import {
  completer_exigences, exigences_depuis_seances, problemes_du_programme, programmes_effectifs,
} from "../web/static/js/programmes.js";
import { cle_depuis_nom, promouvoir_programme, promouvoir_seance } from "../web/static/js/promotion.js";
import { catalogue_effectif, normaliser_entrelacement } from "../web/static/js/seance.js";
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
  // Un echauffement aussi exercice : il compte comme un exercice.
  Jacks: m(["quadri"], "cardio", { est_echauffement: true, aussi_exercice: true, detection: "jacks" }),
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
egal("zone : un echauffement aussi exercice entre", zone("Curl", "Jacks"), "plusieurs");
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
    specs: { Curl: spec({}), Squat: spec({}), "Squat charge": spec({ poids_min: 5, charge_corps: 15 }), Planche: spec({ unite: "secondes" }) },
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

// ---------------------------------------------------------------- perso
/** Le message d'erreur que leve `f`, ou null. */
function refus(f) {
  try {
    f();
    return null;
  } catch (erreur) {
    return erreur.message;
  }
}
{
  const base = base_vide();
  const a = creer_utilisateur(base, "A").id;
  const b = creer_utilisateur(base, "B").id;
  const profil = (id) => base.utilisateurs.find((u) => u.id === id);
  const BLOCS = [{ exercice: "Curl", mode: "repetitions", series: 3, repetitions: 10 }];

  egal("perso : un profil sans champ n'a rien", [seances_perso(profil(a)), programmes_perso(profil(a))], [{}, {}]);
  egal("perso : le nom est nettoye", enregistrer_seance_perso(base, a, "  Bras  ", BLOCS), "Bras");
  enregistrer_seance_perso(base, a, "Push", BLOCS);
  egal("perso : un autre profil n'en voit rien", Object.keys(seances_perso(profil(b))), []);
  egal("perso : un nom vide est refuse", refus(() => enregistrer_seance_perso(base, a, " ", BLOCS)) !== null, true);
  egal("perso : la copie du meme nom remplace la commune, pour ce profil seulement",
    [catalogue_effectif({ Push: [], Pull: [] }, seances_perso(profil(a))).Push, catalogue_effectif({ Push: [] }, seances_perso(profil(b))).Push],
    [BLOCS, []]);

  const cle = enregistrer_programme_perso(base, a, null, { nom: "Mon prog", seances: { Haut: "Bras", Bas: "Push" }, exigences: [] });
  egal("programme perso : cle prefixee", [cle, est_programme_perso(cle), est_programme_perso("road_to_tkt")], ["perso-1", true, false]);
  egal("programme perso : la cle suivante est neuve", enregistrer_programme_perso(base, a, null, { nom: "Autre", seances: {} }), "perso-2");
  egal("programme perso : une cle commune est refusee", refus(() => enregistrer_programme_perso(base, a, "road_to_tkt", {})) !== null, true);
  egal("programme perso : a cote des communs", Object.keys(programmes_effectifs({ commun: {} }, programmes_perso(profil(a)))), ["commun", "perso-1", "perso-2"]);

  // Renommer : le programme suit, l'ordre de la liste aussi
  renommer_seance_perso(base, a, "Bras", "Bras et epaules");
  egal("renommer : le programme perso suit", programmes_perso(profil(a))[cle].seances, { Haut: "Bras et epaules", Bas: "Push" });
  egal("renommer : la place dans la liste est gardee", Object.keys(seances_perso(profil(a))), ["Bras et epaules", "Push"]);
  egal("renommer : vers un nom deja pris, refuse", refus(() => renommer_seance_perso(base, a, "Push", "Bras et epaules")) !== null, true);

  // Oublier : refuse si un programme perso la cite et qu'aucune commune ne prend le relais
  const message = refus(() => oublier_seance_perso(base, a, "Push"));
  egal("oublier : refuse, et nomme le programme qui la cite", message?.includes("« Mon prog »"), true);
  egal("oublier : la seance est toujours la", "Push" in seances_perso(profil(a)), true);
  egal("oublier : permis quand la commune du meme nom prend le relais",
    oublier_seance_perso(base, a, "Push", { reste_commune: true }), true);

  // Supprimer le programme suivi le libere
  profil(a).programme_choisi = cle;
  profil(a).programmes_ordre = { [cle]: ["Bas", "Haut"] };
  supprimer_programme_perso(base, a, cle);
  egal("supprimer le programme suivi : le profil est libere, son ordre oublie",
    [profil(a).programme_choisi, profil(a).programmes_ordre], [null, {}]);
  egal("supprimer : la cle n'est jamais reprise", enregistrer_programme_perso(base, a, null, { nom: "Neuf", seances: {} }), "perso-3");
  egal("oublier : sans programme qui la cite, permis", oublier_seance_perso(base, a, "Bras et epaules"), true);
}

// ---------------------------------------------------------------- entrelacement
egal("entrelacement : le partenaire se recalcule, le dernier bloc n'en a pas",
  normaliser_entrelacement([
    { exercice: "A", entrelace_avec: "?" },
    { exercice: "B", entrelace_avec: "vieux nom" },
    { exercice: "C", entrelace_avec: "A" },
  ]).map((b) => b.entrelace_avec),
  ["B", "C", null]);
egal("entrelacement : un bloc sans drapeau reste seul",
  normaliser_entrelacement([{ exercice: "A", entrelace_avec: null }, { exercice: "B" }]).map((b) => b.entrelace_avec),
  [null, null]);

// ---------------------------------------------------------------- exigences
const BAREMES = new Baremes(TABLES, null);
const SEANCES = {
  Haut: [
    { exercice: "Rotation", mode: "echauffement", series: 1, repetitions: 10, duree: 30, poids: 0 },
    { exercice: "Curl", mode: "repetitions", series: 3, repetitions: 12, duree: 0, poids: 5 },
    { exercice: "Curl", mode: "repetitions", series: 5, repetitions: 5, duree: 0, poids: 10 },
    { exercice: "Planche", mode: "repetitions", series: 3, repetitions: 10, duree: 30, poids: 0 },
  ],
  Bas: [
    { exercice: "Planche", mode: "maintien", series: 2, repetitions: 0, duree: 45, poids: 0 },
    { exercice: "Squat", series: 4, repetitions: 15, duree: 0 },
  ],
};
const proposees = exigences_depuis_seances(BAREMES, { "Jour 1": "Haut", "Jour 2": "Bas" }, SEANCES);
egal("exigences : l'echauffement, le doublon et le mode hors bareme sont ecartes ; la cible suit le mode",
  proposees,
  [
    { seance: "Jour 1", exercice: "Curl", series: 3, cible: 12, poids: 5 },
    { seance: "Jour 2", exercice: "Planche", series: 2, cible: 45, poids: 0 },
    { seance: "Jour 2", exercice: "Squat", series: 4, cible: 15, poids: 0 },
  ]);
egal("exigences : une seance absente ne propose rien", exigences_depuis_seances(BAREMES, { X: "Inconnue" }, SEANCES), []);
egal("completer : ce qui est ecrit gagne, le nouveau s'ajoute, le disparu s'en va",
  completer_exigences(
    [
      { seance: "Jour 1", exercice: "Curl", series: 6, cible: 20, poids: 10 },
      { seance: "Jour 3", exercice: "Squat", series: 1, cible: 1, poids: 0 },
    ],
    proposees,
  ).map((e) => [e.seance, e.exercice, e.series, e.cible]),
  [["Jour 1", "Curl", 6, 20], ["Jour 2", "Planche", 2, 45], ["Jour 2", "Squat", 4, 15]]);

// ---------------------------------------------------------------- problemes d'un programme
const bon = { nom: "P", seances: { "Jour 1": "Haut", "Jour 2": "Bas" }, exigences: proposees };
egal("programme : un programme complet passe", problemes_du_programme(BAREMES, bon, SEANCES), []);
for (const [cas, programme, attendu] of [
  ["nom vide", { ...bon, nom: "  " }, "nom"],
  ["aucune exigence", { ...bon, exigences: [] }, "Au moins une"],
  ["exercice sans bareme", { ...bon, exigences: [...proposees, { seance: "Jour 1", exercice: "Rotation", series: 1, cible: 1, poids: 0 }] }, "barème"],
  ["cible nulle", { ...bon, exigences: [{ ...proposees[0], cible: 0 }, ...proposees.slice(1)] }, "supérieures à zéro"],
  ["libelle sans seance", { ...bon, exigences: [...proposees, { ...proposees[0], seance: "Jour 9" }] }, "« Jour 9 » n'est lié"],
  ["seance liee absente", { ...bon, seances: { ...bon.seances, "Jour 1": "Disparue" } }, "« Disparue », qui n'existe pas"],
  ["libelle lie sans exigence", { ...bon, seances: { ...bon.seances, "Jour 3": "Haut" } }, "« Jour 3 » n'a aucune performance"],
]) {
  const trouves = problemes_du_programme(BAREMES, programme, SEANCES);
  egal(`programme : refuse (${cas})`, trouves.some((p) => p.includes(attendu)), true);
}

// ---------------------------------------------------------------- promotion
{
  const profil = {
    seances_perso: {
      Haut: [{ exercice: "Curl", mode: "repetitions", series: 3, repetitions: 12, cible_manuelle: [1] }],
      "Ma seance": [{ exercice: "Squat", series: 4, repetitions: 15 }],
    },
    programmes_perso: { "perso-1": { nom: "Mon été léger", seances: { A: "Haut", B: "Commune" }, exigences: [] } },
  };
  const brouillon = { seances: { Haut: [{ exercice: "Curl" }], Commune: [] }, programmes: { "mon-ete-leger": {} } };

  const seance = promouvoir_seance(brouillon, profil, "Ma seance");
  egal("promotion : la seance devient commune", seance.brouillon.seances["Ma seance"], [{ exercice: "Squat", series: 4, repetitions: 15 }]);
  egal("promotion : le brouillon d'origine n'est pas touche", "Ma seance" in brouillon.seances, false);
  egal("promotion : une collision est refusee et nommee",
    refus(() => promouvoir_seance(brouillon, profil, "Haut"))?.includes("« Haut » existe déjà"), true);
  const remplacee = promouvoir_seance(brouillon, profil, "Haut", { remplacer: true });
  egal("promotion : remplacer sur demande, sans la cible figee (donnee de profil)",
    remplacee.brouillon.seances.Haut, [{ exercice: "Curl", mode: "repetitions", series: 3, repetitions: 12 }]);
  egal("promotion : la seance perso garde sa cible figee", profil.seances_perso.Haut[0].cible_manuelle, [1]);
  egal("promotion : sous un autre nom", Object.keys(promouvoir_seance(brouillon, profil, "Haut", { nom: "Haut v2" }).brouillon.seances), ["Haut", "Commune", "Haut v2"]);

  egal("cle : tiree du nom, sans accent", [cle_depuis_nom("Mon été léger !"), cle_depuis_nom("Perso 2"), cle_depuis_nom("")],
    ["mon-ete-leger", "programme-perso-2", "programme"]);
  egal("promotion programme : la cle commune deja prise est refusee",
    refus(() => promouvoir_programme(brouillon, profil, "perso-1"))?.includes("« mon-ete-leger » existe déjà"), true);
  egal("promotion programme : une seance perso du meme nom qu'une commune est refusee sans « remplacer »",
    refus(() => promouvoir_programme(brouillon, profil, "perso-1", { cle: "neuf" }))?.includes("« Haut »"), true);
  const programme = promouvoir_programme(brouillon, profil, "perso-1", { cle: "neuf", remplacer: true });
  egal("promotion programme : il emporte ses seances perso, pas les communes",
    [programme.cle, programme.seances, programme.brouillon.programmes.neuf.seances], ["neuf", ["Haut"], { A: "Haut", B: "Commune" }]);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : les regles des createurs se tiennent.`);
}
