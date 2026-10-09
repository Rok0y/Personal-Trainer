// Lance toutes les verifications du projet, dans l'ordre, et s'arrete au
// premier rouge.
//
// Usage :
//     node scripts/tester.mjs                  tout verifier
//     node scripts/tester.mjs ressenti ligues  seulement ces tests-la
//     node scripts/tester.mjs --mettre-a-jour  reecrire les reponses figees
//
// `--mettre-a-jour` n'est transmis qu'aux comparateurs (`comparer_*`) : les
// verificateurs controlent des invariants, qu'aucune mise a jour ne fait
// taire. Ne l'utiliser qu'apres avoir lu et compris les ecarts — voir
// `fixtures.mjs`.

import { spawnSync } from "node:child_process";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ICI = dirname(fileURLToPath(import.meta.url));

// Les verificateurs d'abord : ils sont rapides, et un appel orphelin ou une
// donnee invalide explique souvent un rouge plus loin.
const TESTS = [
  "verifier_methodes",
  "verifier_donnees",
  "sommaire",
  "verifier_annonces",
  "verifier_instruments",
  "verifier_semaine",
  "verifier_simulation",
  "comparer_detections",
  "comparer_seances",
  "comparer_historique",
  "comparer_paliers",
  "comparer_niveaux",
  "comparer_ressenti",
  "comparer_objectifs",
  "comparer_programmes",
  "comparer_ligues",
  "comparer_annonces",
  "comparer_variantes",
];

const mise_a_jour = process.argv.includes("--mettre-a-jour");
const filtres = process.argv.slice(2).filter((a) => !a.startsWith("--"));
const choisis = filtres.length
  ? TESTS.filter((t) => filtres.some((f) => t.includes(f)))
  : TESTS;

for (const test of choisis) {
  const args = [join(ICI, `${test}.mjs`)];
  if (mise_a_jour && test.startsWith("comparer_")) args.push("--mettre-a-jour");
  console.log(`\n=== ${test}`);
  const { status } = spawnSync(process.execPath, args, { stdio: "inherit" });
  if (status !== 0) {
    console.log(`\n${test} est rouge.`);
    process.exit(status ?? 1);
  }
}
console.log(`\n${choisis.length} verifications vertes.`);
