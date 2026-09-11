// Rejoue en JavaScript les historiques releves par `generer_niveaux.py`.
//
// Un niveau se deduit d'un historique : le harnais lui en jette des dizaines
// tires au hasard, volontairement tordus — series inegales et inachevees,
// modes qui ne correspondent pas au bareme, exercices repetes dans une meme
// seance, ancrages poses au milieu.
//
// Usage : node scripts/comparer_niveaux.mjs
// Prealable : python -m scripts.generer_niveaux

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE = join(ICI, "..");
const FIXTURES = join(ICI, "fixtures_niveaux.jsonl");
const BAREMES = join(RACINE, "web", "static", "donnees", "baremes.json");

const ECARTS_DETAILLES = 4;

const INVENTAIRES = (tables) => {
  const complet = {};
  for (const p of tables.echelles.reference) complet[p] = 2;
  return {
    non_declare: null,
    debutant: { halteres: { 2: 2, 3: 2, 4: 2 }, accessoires: ["tapis"] },
    complet: { halteres: complet, accessoires: ["tapis", "chaise"] },
  };
};

function main() {
  const tables = JSON.parse(readFileSync(BAREMES, "utf-8"));
  const stocks = INVENTAIRES(tables);
  const moteurs = {};
  for (const [nom, brut] of Object.entries(stocks)) {
    moteurs[nom] = new Niveaux(new Baremes(tables, brut));
  }

  const lignes = readFileSync(FIXTURES, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

  const echecs = [];
  let comparaisons = 0;
  let seances = 0;

  for (const ligne of lignes) {
    const moteur = moteurs[ligne.inventaire];
    const { seances: histoire, ancrages } = ligne;
    seances += histoire.length;

    const obtenu = {
      niveaux_par_exercice: moteur.niveaux_par_exercice(histoire, ancrages),
      etats_niveaux: moteur.etats_niveaux(histoire, ancrages),
      montees_de_niveau: moteur.montees_de_niveau(histoire, ancrages),
      niveau_prouve_par: histoire.flatMap((s) =>
        s.exercices.map((e) => moteur.niveau_prouve_par(e))
      ),
    };

    for (const champ of Object.keys(obtenu)) {
      comparaisons += 1;
      const attendu = JSON.stringify(ligne[champ]);
      const rendu = JSON.stringify(obtenu[champ]);
      if (attendu !== rendu) {
        echecs.push({ ligne, champ, attendu, rendu });
      }
    }
  }

  console.log(
    `${lignes.length} historiques rejoues (${seances} seances), ` +
      `${comparaisons} reponses comparees`
  );

  if (!echecs.length) {
    console.log("\nAucun ecart : le portage des niveaux est fidele.");
    return;
  }

  console.log(`\n${echecs.length} reponses divergent. Les ${ECARTS_DETAILLES} premieres :\n`);
  for (const { ligne, champ, attendu, rendu } of echecs.slice(0, ECARTS_DETAILLES)) {
    console.log(`  historique ${ligne.numero} / ${ligne.inventaire} / ${champ}`);
    console.log(`    python = ${attendu.slice(0, 300)}`);
    console.log(`    js     = ${rendu.slice(0, 300)}`);
    console.log();
  }
  process.exitCode = 1;
}

main();
