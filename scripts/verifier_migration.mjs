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

// --- Version 1 -> 2 : la separation du squat et des fentes
{
  const base = migrer(base_v1());
  egal("version", base.version, 2);
  egal("version courante", VERSION_BASE, 2);
  egal("lignes : les chargees prennent le nom charge, les autres gardent le leur",
    base.exercices.map((e) => e.nom),
    ["Squat", "Squat chargé", "Fente droite chargée", "Fente gauche chargée", "Pompes"]);
  egal("lignes : l'entrelacement d'une ligne chargee suit", base.exercices[2].entrelace_avec, "Fente gauche chargée");
  egal("ancrages : celui du squat devient inerte, les autres ne bougent pas",
    base.corrections_niveaux.map((a) => [a.nom_exercice, a.niveau]),
    [["Squat (barème d'avant la séparation)", 30], ["Pompes", 4]]);
  egal("seances locales : la forme chargee, entrelacement compris",
    base.seances_locales.Jambes.map((b) => [b.exercice, b.entrelace_avec ?? null]),
    [["Squat chargé", null], ["Fente droite chargée", "Fente gauche chargée"], ["Fente gauche chargée", null]]);
  egal("variantes : la preference suit la tete de la chaine",
    base.utilisateurs[0].variantes, { Pompes: "Pompes sur les genoux", "Squat chargé": "Squat sur chaise" });

  // Une seule fois : relancee, la migration ne touche plus rien.
  const avant = JSON.stringify(base);
  migrer(base);
  egal("une seconde migration ne change rien", JSON.stringify(base), avant);
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
  egal("import v1 : migree", [base.version, base.exercices[1].nom], [2, "Squat chargé"]);
  egal("import v1 : compteurs recalcules", base.prochains_id.exercices, 6);
  egal("aller-retour v2", importer(exporter(base)).exercices.map((e) => e.nom), base.exercices.map((e) => e.nom));
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
