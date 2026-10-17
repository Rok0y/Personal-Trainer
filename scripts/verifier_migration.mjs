// Une base des versions precedentes arrive-t-elle intacte dans la version
// courante ?
//
// Les reponses figees de `comparer_historique` rejouent des ecritures faites
// par la version courante : elles ne visitent jamais une base ancienne. Or
// c'est la, sur l'appareil, que vit l'historique reel — et une migration
// ratee ne se rattrape pas. Ces cas sont ecrits a la main, avec leur reponse
// attendue.
//
//     node scripts/verifier_migration.mjs

import {
  VERSION_BASE,
  base_vide,
  exporter,
  importer,
  migrer,
} from "../web/static/js/historique.js";

const problemes = [];
let controles = 0;
function egal(nom, obtenu, attendu) {
  controles += 1;
  const [o, a] = [JSON.stringify(obtenu), JSON.stringify(attendu)];
  if (o !== a) problemes.push(`${nom}\n      attendu ${a}\n      obtenu  ${o}`);
}

/** Une base de version 1, telle que l'ecrivait l'application avant la separation. */
function base_v1() {
  return {
    version: 1,
    prochains_id: { utilisateurs: 2, seances: 3, exercices: 6, series_realisees: 1, corrections_niveaux: 3 },
    utilisateurs: [{ id: 1, nom: "A", variantes: { Squat: "Squat sur chaise", Pompes: "Pompes sur les genoux" } }],
    seances: [
      { id: 1, utilisateur_id: 1, date: "01/09/2026 18:00", statut: "finished" },
      { id: 2, utilisateur_id: 1, date: "03/09/2026 18:00", statut: "finished" },
    ],
    exercices: [
      { id: 1, seance_id: 1, nom: "Squat", poids: 0, entrelace_avec: null },
      { id: 2, seance_id: 2, nom: "Squat", poids: 10, entrelace_avec: null },
      { id: 3, seance_id: 2, nom: "Fente droite", poids: 8, entrelace_avec: "Fente gauche" },
      { id: 4, seance_id: 2, nom: "Fente gauche", poids: 8, entrelace_avec: null },
      { id: 5, seance_id: 2, nom: "Pompes", poids: 0, entrelace_avec: null },
    ],
    series_realisees: [],
    corrections_niveaux: [
      { id: 1, nom_exercice: "Squat", niveau: 30, utilisateur_id: 1, apres_seance_id: 2 },
      { id: 2, nom_exercice: "Pompes", niveau: 4, utilisateur_id: 1, apres_seance_id: 2 },
    ],
    seances_locales: {
      Jambes: [
        { exercice: "Squat", poids: 0, entrelace_avec: null },
        { exercice: "Fente droite", poids: 0, entrelace_avec: "Fente gauche" },
        { exercice: "Fente gauche", poids: 0 },
      ],
    },
  };
}

// --- Version 1 -> 3 : la separation du squat et des fentes, puis les seances
// locales rangees sur les profils
{
  const base = migrer(base_v1());
  egal("version", base.version, 3);
  egal("version courante", VERSION_BASE, 3);
  egal("lignes : les chargees prennent le nom charge, les autres gardent le leur",
    base.exercices.map((e) => e.nom),
    ["Squat", "Squat chargé", "Fente droite chargée", "Fente gauche chargée", "Pompes"]);
  egal("lignes : l'entrelacement d'une ligne chargee suit", base.exercices[2].entrelace_avec, "Fente gauche chargée");
  egal("ancrages : celui du squat devient inerte, les autres ne bougent pas",
    base.corrections_niveaux.map((a) => [a.nom_exercice, a.niveau]),
    [["Squat (barème d'avant la séparation)", 30], ["Pompes", 4]]);
  egal("seances locales : la forme chargee, entrelacement compris, sur le profil",
    base.utilisateurs[0].seances_perso.Jambes.map((b) => [b.exercice, b.entrelace_avec ?? null]),
    [["Squat chargé", null], ["Fente droite chargée", "Fente gauche chargée"], ["Fente gauche chargée", null]]);
  egal("variantes : la preference suit la tete de la chaine",
    base.utilisateurs[0].variantes, { Pompes: "Pompes sur les genoux", "Squat chargé": "Squat sur chaise" });

  // Une seule fois : relancee, la migration ne touche plus rien.
  const avant = JSON.stringify(base);
  migrer(base);
  egal("une seconde migration ne change rien", JSON.stringify(base), avant);
}

// --- Version 2 -> 3 : les seances de l'appareil deviennent celles de chaque profil
/** Une base de version 2 : deux profils, des seances modifiees sur l'appareil. */
function base_v2() {
  return {
    version: 2,
    prochains_id: { utilisateurs: 3, seances: 1, exercices: 1, series_realisees: 1, corrections_niveaux: 1 },
    utilisateurs: [
      { id: 1, nom: "A" },
      { id: 2, nom: "B", seances_perso: { Push: [{ exercice: "Pompes", poids: 0 }] } },
    ],
    seances: [], exercices: [], series_realisees: [], corrections_niveaux: [],
    seances_locales: {
      Push: [{ exercice: "Pompes", poids: 0, repetitions: 12, cible_manuelle: [1] }],
      Bras: [{ exercice: "Curl biceps droit", poids: 5 }],
    },
  };
}
{
  const base = migrer(base_v2());
  const [a, b] = base.utilisateurs;
  egal("v2 : version 3", base.version, 3);
  egal("v2 : chaque profil recoit les seances de l'appareil, sous le meme nom",
    [Object.keys(a.seances_perso), Object.keys(b.seances_perso).sort()], [["Push", "Bras"], ["Bras", "Push"]]);
  egal("v2 : la cible figee voyage telle quelle", a.seances_perso.Push[0].cible_manuelle, [1]);
  egal("v2 : une seance perso deja la du meme nom l'emporte", b.seances_perso.Push, [{ exercice: "Pompes", poids: 0 }]);
  a.seances_perso.Bras[0].poids = 8;
  egal("v2 : une copie par profil (modifier l'une ne touche pas l'autre)", b.seances_perso.Bras[0].poids, 5);
  egal("v2 : seances_locales disparait", "seances_locales" in base, false);
  const avant = JSON.stringify(base);
  migrer(base);
  egal("v2 : une seconde migration ne change rien", JSON.stringify(base), avant);
}
{
  const base = migrer({ ...base_v2(), seances_locales: undefined });
  egal("v2 sans seance locale : aucun champ ajoute aux profils", "seances_perso" in base.utilisateurs[0], false);
  const importee = importer(JSON.stringify(base_v2()));
  egal("import v2 : migree, seances rangees sur les profils",
    [importee.version, Object.keys(importee.utilisateurs[0].seances_perso)], [3, ["Push", "Bras"]]);
  const v3 = importer(JSON.stringify({ ...importee, seances_locales: { Fantome: [] } }));
  egal("import v3 : une seances_locales egaree n'est pas relue",
    [Object.keys(v3.utilisateurs[0].seances_perso), "seances_locales" in v3], [["Push", "Bras"], false]);
}

// --- Une base neuve est deja a jour, et la migration la laisse telle quelle
{
  const neuve = base_vide();
  neuve.exercices.push({ id: 1, seance_id: 1, nom: "Squat", poids: 5 });
  egal("base neuve : version courante", neuve.version, VERSION_BASE);
  egal("base neuve : un squat a vide charge par erreur n'est pas renomme", migrer(neuve).exercices[0].nom, "Squat");
}

// --- L'import relit une sauvegarde de version 1 et la migre
{
  const sauvegarde = JSON.stringify(base_v1());
  const base = importer(sauvegarde);
  egal("import v1 : migree", [base.version, base.exercices[1].nom], [3, "Squat chargé"]);
  egal("import v1 : compteurs recalcules", base.prochains_id.exercices, 6);
  egal("aller-retour v3", importer(exporter(base)).exercices.map((e) => e.nom), base.exercices.map((e) => e.nom));
  let refus = null;
  try {
    importer(JSON.stringify({ ...base_v1(), version: 99 }));
  } catch (erreur) {
    refus = erreur.message;
  }
  egal("import d'une version inconnue : refuse", refus !== null, true);
}

if (problemes.length) {
  console.log(`${problemes.length} ecarts sur ${controles} controles :\n`);
  for (const p of problemes) console.log(`  - ${p}`);
  process.exitCode = 1;
} else {
  console.log(`${controles} controles : une base ancienne arrive intacte dans la version ${VERSION_BASE}.`);
}
