// Rejoue en JavaScript les questions relevees par `generer_paliers.py`.
//
// Un bareme est une fonction pure de (spec, echelle) : on peut donc lui jeter
// des entrees au hasard, comme aux detections, sans avoir a lui construire une
// histoire comme au circuit.
//
// Usage : node scripts/comparer_paliers.mjs
// Prealable : python -m scripts.generer_paliers

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Baremes } from "../web/static/js/paliers.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE = join(ICI, "..");
const FIXTURES = join(ICI, "fixtures_paliers.jsonl");
const BAREMES = join(RACINE, "web", "static", "donnees", "baremes.json");
// Specs fictives ecrites par l'oracle : elles couvrent les surcharges de
// palier et le bareme sans fin, deux branches qu'aucun exercice reel
// n'exerce. Elles ne figurent pas dans `baremes.json`, qui decrit le vrai
// catalogue.
const SPECS_HARNAIS = join(ICI, "fixtures_paliers_specs.json");

const ECARTS_DETAILLES = 6;

// Les inventaires ne sont **pas** redeclares ici : ils arrivent avec l'oracle
// (`fixtures_paliers_specs.json`), comme les specs fictives. Ils l'ont ete, et
// c'est un piege qui s'est referme — deux inventaires ajoutes cote Python ont
// rendu ce fichier muet sur eux, `baremes[nom]` valant `undefined`. Un jeu
// d'entrees duplique a le meme defaut que le code qu'il surveille.

function repondre(bareme, ligne) {
  const nom = ligne.exercice;
  switch (ligne.question) {
    case "echelle":
      return bareme.echelle_exercice(nom);
    case "tranches":
      return bareme.tranches(nom, bareme.specs[nom].series_max);
    case "dernier_palier_borne":
      return bareme.dernier_palier_borne(nom);
    case "palier": {
      const p = bareme.palier(nom, ligne.niveau);
      if (p === null) return null;
      return {
        ...p,
        volume: bareme.volume(p.series, p.cible, p.poids),
        resume: resume(p),
      };
    }
    case "niveau_pour":
      return bareme.niveau_pour(nom, ligne.poids, ligne.series, ligne.cible);
    case "niveau_pour_volume":
      return bareme.niveau_pour_volume(nom, ligne.volume);
    default:
      throw new Error(`Question inconnue : ${ligne.question}`);
  }
}

/**
 * Jumeau de `Palier.resume()`.
 *
 * `%g` cote Python retire le zero decimal inutile : 5.0 devient « 5 ». Sans
 * cette traduction, chaque palier charge divergerait sur un caractere.
 */
function resume(p) {
  const suffixe = p.unite === "secondes" ? " s" : "";
  const charge = p.poids ? ` à ${Number(p.poids)} kg` : "";
  return `${p.series}x${p.cible}${suffixe}${charge}`;
}

function main() {
  const tables = JSON.parse(readFileSync(BAREMES, "utf-8"));
  const extra = JSON.parse(readFileSync(SPECS_HARNAIS, "utf-8"));
  tables.specs = { ...tables.specs, ...extra.specs };
  tables.materiel = { ...tables.materiel, ...extra.materiel };
  const stocks = extra.inventaires;
  const lignes = readFileSync(FIXTURES, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

  const baremes = {};
  for (const [nom, brut] of Object.entries(stocks)) {
    // `Baremes` normalise lui-meme : on lui passe le brut, null compris.
    baremes[nom] = new Baremes(tables, brut);
  }

  const echecs = [];
  for (const ligne of lignes) {
    let obtenu;
    try {
      obtenu = repondre(baremes[ligne.inventaire], ligne);
    } catch (erreur) {
      obtenu = `EXCEPTION ${erreur.message}`;
    }
    if (JSON.stringify(ligne.reponse) !== JSON.stringify(obtenu)) {
      echecs.push({ ligne, obtenu });
    }
  }

  const par_question = {};
  for (const l of lignes) par_question[l.question] = (par_question[l.question] ?? 0) + 1;
  console.log(
    `${lignes.length} questions rejouees ` +
      `(${Object.entries(par_question).map(([q, n]) => `${q} ${n}`).join(", ")})`
  );

  if (!echecs.length) {
    console.log("\nAucun ecart : le portage du bareme est fidele.");
    return;
  }

  console.log(`\n${echecs.length} reponses divergent. Les ${ECARTS_DETAILLES} premieres :\n`);
  for (const { ligne, obtenu } of echecs.slice(0, ECARTS_DETAILLES)) {
    const contexte = Object.entries(ligne)
      .filter(([c]) => !["reponse", "question", "inventaire", "exercice"].includes(c))
      .map(([c, v]) => `${c}=${v}`)
      .join(" ");
    console.log(`  ${ligne.exercice} / ${ligne.inventaire} / ${ligne.question} ${contexte}`);
    console.log(`    python = ${JSON.stringify(ligne.reponse)}`);
    console.log(`    js     = ${JSON.stringify(obtenu)}`);
  }
  process.exitCode = 1;
}

main();
