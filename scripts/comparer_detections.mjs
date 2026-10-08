// Rejoue les poses figees dans les detections et les gestes de controle, et
// compare chaque jeton a la reponse figee.
//
// Les poses (`poses_detections`) sont des entrees : tirees au hasard (graine
// fixe) puis completees de familles construites autour des seuils, que le
// hasard n'atteint jamais. Elles ne changent jamais. Les jetons
// (`detections`) sont les reponses, alignees ligne a ligne sur les poses ;
// eux seuls sont reecrits par `--mettre-a-jour`. Les separer evite qu'un
// changement de seuil reecrive dix mega-octets de coordonnees dans Git.
//
// En mise a jour, **toutes** les fonctions de DETECTIONS sont rejouees : une
// detection ajoutee entre d'elle-meme dans le jeu, et une detection retiree en
// sort. Hors mise a jour, l'une comme l'autre est signalee.
//
//     node scripts/comparer_detections.mjs [--mettre-a-jour]

import { construire_corps } from "../web/static/js/landmarks.js";
import { DETECTIONS } from "../web/static/js/detections.js";
import {
  bras_droit_leve,
  bras_gauche_leve,
  bras_en_x,
  deux_bras_leves,
  seul_bras_droit_leve,
  seul_bras_gauche_leve,
} from "../web/static/js/positions.js";
import { METTRE_A_JOUR, ecrire_lignes, lire_lignes } from "./fixtures.mjs";

const FONCTIONS = {
  ...DETECTIONS,
  bras_droit_leve,
  bras_gauche_leve,
  bras_en_x,
  deux_bras_leves,
  seul_bras_droit_leve,
  seul_bras_gauche_leve,
};

const poses = lire_lignes("poses_detections");
const reponses = lire_lignes("detections");
if (poses.length !== reponses.length) {
  console.error(`${poses.length} poses pour ${reponses.length} lignes de reponses : fichiers desaccordes.`);
  process.exit(2);
}

const figees = Object.keys(reponses[0].jetons);
const portees = Object.keys(FONCTIONS);
const sans_reponse = portees.filter((nom) => !figees.includes(nom));
const disparues = figees.filter((nom) => !portees.includes(nom));

const ecarts = new Map();
let comparaisons = 0;
let remplacees = 0;

poses.forEach(({ landmarks }, index) => {
  const corps = construire_corps(landmarks);
  const { jetons } = reponses[index];

  if (METTRE_A_JOUR) {
    const neufs = {};
    for (const [nom, fonction] of Object.entries(FONCTIONS)) {
      neufs[nom] = fonction(corps);
      if (neufs[nom] !== jetons[nom]) remplacees++;
    }
    reponses[index].jetons = neufs;
    return;
  }

  for (const [nom, attendu] of Object.entries(jetons)) {
    const fonction = FONCTIONS[nom];
    if (!fonction) continue;
    const obtenu = fonction(corps);
    comparaisons++;
    if (obtenu !== attendu) {
      if (!ecarts.has(nom)) ecarts.set(nom, []);
      ecarts.get(nom).push({ pose: index + 1, attendu, obtenu });
    }
  }
});

if (METTRE_A_JOUR) {
  if (remplacees || sans_reponse.length || disparues.length) {
    ecrire_lignes("detections", reponses);
    console.log(`${remplacees} jetons remplaces dans detections.jsonl.gz`);
  } else {
    console.log("Rien a mettre a jour.");
  }
  process.exit(0);
}

console.log(`${poses.length} poses, ${comparaisons} comparaisons`);
console.log(`${portees.length} fonctions\n`);

for (const nom of sans_reponse) console.error(`Fonction sans reponse figee (lance --mettre-a-jour) : ${nom}`);
for (const nom of disparues) console.error(`Reponse figee pour une fonction disparue : ${nom}`);

if (ecarts.size === 0 && !sans_reponse.length && !disparues.length) {
  console.log("Aucun ecart : les detections rendent les jetons figes.");
  process.exit(0);
}

for (const [nom, liste] of ecarts) {
  const part = ((liste.length / poses.length) * 100).toFixed(1);
  console.error(`${nom} : ${liste.length} ecarts (${part} %)`);
  for (const e of liste.slice(0, 3)) {
    console.error(`  pose ${e.pose} : fige=${e.attendu}  code=${e.obtenu}`);
  }
}
console.error("\nChangement voulu ? Relance avec --mettre-a-jour, apres avoir lu les ecarts.");
process.exit(1);
