// Rejoue les poses de scripts/fixtures_detections.jsonl dans les detections
// JS et compare chaque jeton a celui qu'a produit le Python.
//
// C'est le garde-fou contre la derive : les deux implementations vivent dans
// deux langages et rien n'empeche l'une d'evoluer sans l'autre. Ici le Python
// fait autorite — il tourne en production depuis des mois.
//
//     python -m scripts.generer_fixtures
//     node scripts/comparer_detections.mjs

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { construire_corps } from "../web/static/js/landmarks.js";
import { DETECTIONS } from "../web/static/js/detections.js";
import {
  bras_droit_leve,
  bras_gauche_leve,
  bras_en_x,
  deux_bras_leves,
} from "../web/static/js/positions.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(ICI, "fixtures_detections.jsonl");

const FONCTIONS = {
  ...DETECTIONS,
  bras_droit_leve,
  bras_gauche_leve,
  bras_en_x,
  deux_bras_leves,
};

let lignes;
try {
  lignes = readFileSync(FIXTURES, "utf-8").trim().split("\n");
} catch {
  console.error(`Fixtures absentes : ${FIXTURES}`);
  console.error("Genere-les d'abord : python -m scripts.generer_fixtures");
  process.exit(2);
}

const premiere = JSON.parse(lignes[0]);
const attendues = Object.keys(premiere.jetons);
const portees = Object.keys(FONCTIONS);

const manquantes = attendues.filter((nom) => !portees.includes(nom));
const en_trop = portees.filter((nom) => !attendues.includes(nom));

if (manquantes.length) {
  console.error("Fonctions Python sans jumelle JS :");
  for (const nom of manquantes) console.error(`  ${nom}`);
}
if (en_trop.length) {
  console.error("Fonctions JS absentes du Python :");
  for (const nom of en_trop) console.error(`  ${nom}`);
}

const ecarts = new Map();
let comparaisons = 0;

lignes.forEach((ligne, index) => {
  const { landmarks, jetons } = JSON.parse(ligne);
  const corps = construire_corps(landmarks);

  for (const [nom, attendu] of Object.entries(jetons)) {
    const fonction = FONCTIONS[nom];
    if (!fonction) continue;

    const obtenu = fonction(corps);
    comparaisons++;

    // Python rend None la ou JS rend null, et True/False la ou JS rend
    // true/false : JSON les a deja alignes, une comparaison stricte suffit.
    if (obtenu !== attendu) {
      if (!ecarts.has(nom)) ecarts.set(nom, []);
      ecarts.get(nom).push({ pose: index + 1, attendu, obtenu });
    }
  }
});

console.log(`${lignes.length} poses, ${comparaisons} comparaisons`);
console.log(`${portees.length} fonctions portees\n`);

if (ecarts.size === 0 && !manquantes.length && !en_trop.length) {
  console.log("Aucun ecart : le portage est fidele.");
  process.exit(0);
}

for (const [nom, liste] of ecarts) {
  const part = ((liste.length / lignes.length) * 100).toFixed(1);
  console.error(`${nom} : ${liste.length} ecarts (${part} %)`);
  for (const e of liste.slice(0, 3)) {
    console.error(`  pose ${e.pose} : Python=${e.attendu}  JS=${e.obtenu}`);
  }
}

process.exit(1);
