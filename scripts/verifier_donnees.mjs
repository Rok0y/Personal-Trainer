// Les fichiers de `web/static/donnees/` se tiennent-ils ?
//
// Ces fichiers sont des **sources** editees a la main (ou depuis les pages
// `dev/`) : rien ne les fabrique plus, donc rien ne les valide en les
// fabriquant. L'application, elle, ne leve jamais sur une donnee bancale —
// elle tait une fiche manquante, ignore un exercice inconnu, refuse de
// demarrer une seance. Ce controle pose les memes questions **a froid**,
// avant le deploiement plutot qu'en seance :
//
//  - reglages : chaque bareme a ses champs, et le materiel de son exercice ;
//  - fiches : chaque mouvement a sa fiche, chaque champ a sa forme ;
//  - mouvements : chaque fonction nommee existe dans `detections.js`, chaque
//    variante designe un mouvement du catalogue ;
//  - seances : chaque seance passe `problemes_des_blocs`, le controle que fait
//    l'editeur de l'application a l'enregistrement ;
//  - programmes : chaque exigence vise un exercice qui a un bareme, et chaque
//    libelle est lie a une seance qui existe ;
//  - videos : chaque `.mp4` de `videos/` porte le nom (`fichier_video`) d'un
//    mouvement. Un mouvement renomme rend sa video orpheline, et une video que
//    rien ne lit est aussi invisible qu'une video absente. Une video
//    **manquante**, elle, n'est pas une erreur : on les tourne par lots, et
//    `dev/fiches.html` dit lesquelles restent a faire.
//
//     node scripts/verifier_donnees.mjs

import { existsSync, readdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { DETECTIONS } from "../web/static/js/detections.js";
import { composer_baremes } from "../web/static/js/paliers.js";
import { avec_fiches, problemes_des_blocs } from "../web/static/js/seance.js";
import { fichier_video } from "../web/static/js/videos.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const DONNEES = join(ICI, "..", "web", "static", "donnees");
const VIDEOS = join(ICI, "..", "web", "static", "videos");
const lire = (nom) => JSON.parse(readFileSync(join(DONNEES, nom), "utf-8"));

//: Les champs de texte d'une fiche, et leur forme.
const CHAMPS_FICHE = {
  description: "string",
  mise_en_place: "liste",
  instructions: "liste",
  erreurs_frequentes: "liste",
  sensations: "liste",
};

function main() {
  const problemes = [];
  const signaler = (fichier, message) => problemes.push(`${fichier} : ${message}`);

  const reglages = lire("reglages.json");
  const socle = lire("baremes.json");
  const fiches = lire("fiches.json");
  const bruts = lire("mouvements.json");
  const seances = lire("seances.json");
  const programmes = lire("programmes.json");

  // --- reglages ---
  for (const section of ["specs", "ligues", "xp", "note_athlete"]) {
    if (!reglages[section]) signaler("reglages.json", `section « ${section} » absente`);
  }
  const specs = reglages.specs ?? {};
  if (!Object.keys(specs).length) signaler("reglages.json", "aucun bareme, le moteur n'aurait rien a proposer");
  for (const [nom, spec] of Object.entries(specs)) {
    for (const champ of ["series", "cible_min"]) {
      if (typeof spec[champ] !== "number") signaler("reglages.json", `« ${nom} » : ${champ} doit etre un nombre`);
    }
    if (!socle.materiel?.[nom]) signaler("baremes.json", `« ${nom} » a un bareme mais pas d'entree dans materiel`);
    if (!bruts[nom]) signaler("reglages.json", `« ${nom} » a un bareme mais n'est pas dans mouvements.json`);
  }
  try {
    composer_baremes(socle, reglages);
  } catch (erreur) {
    signaler("reglages.json", `composition impossible : ${erreur.message}`);
  }

  // --- fiches et mouvements ---
  for (const [nom, mouvement] of Object.entries(bruts)) {
    if (mouvement.nom !== nom) signaler("mouvements.json", `cle « ${nom} » mais nom « ${mouvement.nom} »`);
    const fiche = fiches[nom];
    if (!fiche) {
      signaler("fiches.json", `« ${nom} » n'a pas de fiche`);
    } else {
      for (const [champ, forme] of Object.entries(CHAMPS_FICHE)) {
        const valeur = fiche[champ];
        const bonne = forme === "liste"
          ? Array.isArray(valeur) && valeur.every((l) => typeof l === "string")
          : typeof valeur === "string";
        if (!bonne) signaler("fiches.json", `« ${nom} » : ${champ} doit etre ${forme === "liste" ? "une liste de textes" : "un texte"}`);
      }
    }
    const fonctions = [mouvement.detection, ...(mouvement.erreurs ?? []), mouvement.amplitude?.[0]];
    for (const fonction of fonctions) {
      if (fonction && !DETECTIONS[fonction]) {
        signaler("mouvements.json", `« ${nom} » nomme ${fonction}, absente de detections.js`);
      }
    }
    for (const sens of ["variante_facile", "variante_difficile"]) {
      if (mouvement[sens] && !bruts[mouvement[sens]]) {
        signaler("mouvements.json", `« ${nom} » : ${sens} « ${mouvement[sens]} » n'est pas un mouvement`);
      }
    }
  }
  for (const nom of Object.keys(fiches)) {
    if (!bruts[nom]) signaler("fiches.json", `fiche « ${nom} » pour un mouvement inconnu`);
  }

  // --- seances ---
  const mouvements = avec_fiches(bruts, fiches);
  for (const [nom, blocs] of Object.entries(seances)) {
    for (const probleme of problemes_des_blocs(mouvements, blocs)) signaler("seances.json", `« ${nom} » : ${probleme}`);
  }

  // --- programmes ---
  for (const [cle, programme] of Object.entries(programmes)) {
    if (!programme.nom?.trim()) signaler("programmes.json", `« ${cle} » : nom manquant`);
    if (!programme.exigences?.length) signaler("programmes.json", `« ${cle} » : aucune exigence`);
    for (const e of programme.exigences ?? []) {
      if (!specs[e.exercice]) signaler("programmes.json", `« ${cle} » : ${e.exercice} n'a pas de bareme`);
      if (!(e.series >= 1) || !(e.cible > 0)) {
        signaler("programmes.json", `« ${cle} » : series et cible doivent etre positives (${e.exercice})`);
      }
      if (!programme.seances?.[e.seance]) {
        signaler("programmes.json", `« ${cle} » : le libelle « ${e.seance} » n'est lie a aucune seance`);
      }
    }
    for (const [libelle, seance] of Object.entries(programme.seances ?? {})) {
      if (!seances[seance]) signaler("programmes.json", `« ${cle} » : « ${libelle} » est lie a « ${seance} », absente de seances.json`);
    }
  }

  // --- videos ---
  const attendues = new Set(Object.keys(bruts).map(fichier_video));
  const videos = existsSync(VIDEOS) ? readdirSync(VIDEOS).filter((f) => f.endsWith(".mp4")) : [];
  for (const fichier of videos) {
    if (!attendues.has(fichier)) {
      signaler("videos/", `${fichier} ne porte le nom d'aucun mouvement (renomme ?) : aucune fiche ne la montrera`);
    }
  }

  if (problemes.length) {
    console.log(`${problemes.length} problemes :\n`);
    for (const p of problemes) console.log(`  - ${p}`);
    process.exitCode = 1;
    return;
  }
  console.log(
    `${Object.keys(bruts).length} mouvements, ${Object.keys(specs).length} baremes, ` +
      `${Object.keys(seances).length} seances, ${Object.keys(programmes).length} programmes, ` +
      `${videos.length} videos : les donnees se tiennent.`
  );
}

main();
