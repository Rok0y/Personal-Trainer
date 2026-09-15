// Rejoue en JavaScript ce que `generer_programmes.py` a releve.
//
// Usage : node scripts/comparer_programmes.mjs
// Prealable : python -m scripts.generer_programmes

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import {
  etat_exigence,
  etat_programme,
  liaison_seances,
  libelles_seances,
  prescription,
  prochaine_seance,
  volume_exige,
} from "../web/static/js/programmes.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE = join(ICI, "..");
const FIXTURES = join(ICI, "fixtures_programmes.jsonl");
const BAREMES = join(RACINE, "web", "static", "donnees", "baremes.json");

const CATALOGUE = { bras: {}, upper_push: {}, jambes_abdos: {} };
const ECARTS_DETAILLES = 4;

function inventaires(tables) {
  const complet = {};
  for (const p of tables.echelles.reference) complet[p] = 2;
  return {
    non_declare: null,
    debutant: { halteres: { 2: 2, 3: 2, 4: 2 }, accessoires: ["tapis"] },
    complet: { halteres: complet, accessoires: ["tapis", "chaise"] },
  };
}

function main() {
  const tables = JSON.parse(readFileSync(BAREMES, "utf-8"));
  const moteurs = {};
  for (const [nom, brut] of Object.entries(inventaires(tables))) {
    const baremes = new Baremes(tables, brut);
    moteurs[nom] = { baremes, niveaux: new Niveaux(baremes) };
  }

  const lignes = readFileSync(FIXTURES, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

  const echecs = [];
  let comparaisons = 0;
  let exigences = 0;

  const verifier = (ou, attendu, obtenu) => {
    comparaisons += 1;
    const a = JSON.stringify(attendu);
    const b = JSON.stringify(obtenu);
    if (a !== b) echecs.push({ ou, attendu: a, rendu: b });
  };

  for (const ligne of lignes) {
    const { baremes, niveaux } = moteurs[ligne.inventaire];
    const { programme, seances, cle } = ligne;
    const ou = `programme ${ligne.numero} / ${ligne.inventaire}`;

    const etats = niveaux.etats_niveaux(seances, {});

    verifier(
      `${ou} / volumes`,
      ligne.volumes,
      programme.exigences.map((e) => volume_exige(baremes, e))
    );
    verifier(
      `${ou} / prescriptions`,
      ligne.prescriptions,
      programme.exigences.map((e) => prescription(baremes, e))
    );
    verifier(
      `${ou} / etats_exigences`,
      ligne.etats_exigences,
      programme.exigences.map((e) => etat_exigence(baremes, e, etats))
    );
    verifier(`${ou} / libelles`, ligne.libelles, libelles_seances(programme));
    verifier(`${ou} / liaison`, ligne.liaison, liaison_seances(programme, CATALOGUE));
    verifier(
      `${ou} / prochaine`,
      ligne.prochaine,
      prochaine_seance(programme, seances, CATALOGUE)
    );
    verifier(
      `${ou} / etat_programme`,
      ligne.etat_programme,
      etat_programme(baremes, cle, programme, etats)
    );

    exigences += programme.exigences.length;
  }

  console.log(
    `${lignes.length} programmes rejoues, ${exigences} exigences, ` +
      `${comparaisons} reponses comparees`
  );

  if (!echecs.length) {
    console.log("\nAucun ecart : le portage des programmes est fidele.");
    return;
  }

  console.log(`\n${echecs.length} reponses divergent. Les ${ECARTS_DETAILLES} premieres :\n`);
  for (const { ou, attendu, rendu } of echecs.slice(0, ECARTS_DETAILLES)) {
    console.log(`  ${ou}`);
    console.log(`    python = ${attendu.slice(0, 300)}`);
    console.log(`    js     = ${rendu.slice(0, 300)}`);
    console.log();
  }
  process.exitCode = 1;
}

main();
