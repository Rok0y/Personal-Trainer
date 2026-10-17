// Apres `node scripts/comparer_detections.mjs --mettre-a-jour` pour une
// detection AJOUTEE : les reponses figees n'ont-elles fait que s'enrichir ?
//
// La mise a jour rejoue toutes les fonctions de DETECTIONS, si bien qu'elle
// reecrirait aussi, sans rien dire, un jeton d'une detection existante qu'on
// aurait touchee en passant (un helper partage modifie, par exemple). Un ajout
// doit laisser chaque ancienne reponse intacte et n'ajouter que des cles.
// Compare au fichier du dernier commit (`git show HEAD:...`).
//
//     node .claude/skills/ajouter-exercice/verifier_ajout_detection.mjs

import { execFileSync } from "node:child_process";
import { gunzipSync } from "node:zlib";

import { lire_lignes } from "../../../scripts/fixtures.mjs";

const CHEMIN = "tests/fixtures/detections.jsonl.gz";

const avant = gunzipSync(execFileSync("git", ["show", `HEAD:${CHEMIN}`], { maxBuffer: 1 << 28 }))
  .toString("utf-8").split("\n").filter(Boolean).map((ligne) => JSON.parse(ligne));
const apres = lire_lignes("detections");

if (avant.length !== apres.length) {
  console.error(`${avant.length} lignes avant, ${apres.length} apres : les poses ont change, ce n'est pas un ajout.`);
  process.exit(1);
}

const modifiees = new Map();
const retirees = new Set();
const ajoutees = new Set();
avant.forEach(({ jetons: anciens }, i) => {
  const { jetons: neufs } = apres[i];
  for (const [nom, jeton] of Object.entries(anciens)) {
    if (!(nom in neufs)) retirees.add(nom);
    else if (neufs[nom] !== jeton) modifiees.set(nom, (modifiees.get(nom) ?? 0) + 1);
  }
  for (const nom of Object.keys(neufs)) if (!(nom in anciens)) ajoutees.add(nom);
});

for (const nom of retirees) console.error(`Retiree : ${nom} (un mouvement retire garde sa detection, voir CLAUDE.md)`);
for (const [nom, n] of modifiees) console.error(`Modifiee : ${nom} — ${n} reponses changees`);
console.log(`Ajoutees : ${[...ajoutees].join(", ") || "aucune"}`);
if (retirees.size || modifiees.size) process.exit(1);
console.log("Les reponses existantes sont intactes : la mise a jour n'a fait qu'ajouter.");
