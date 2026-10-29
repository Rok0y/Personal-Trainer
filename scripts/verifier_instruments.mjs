// Verifie que chaque instrument de web/static/js/instruments.js rederive
// exactement le jeton de sa detection, sur les poses figees des tests.
//
// Les instruments recopient les seuils de detections.js pour pouvoir les
// montrer : c'est une duplication, et une duplication ne se signale pas tant
// que les deux copies coincident — seulement a leur premier ecart, a l'ecran,
// sous la forme d'une jauge qui dit « dans la zone » pendant que rien ne
// compte. Ce controle la rend bruyante. Il compare au jeton que rend la
// detection **actuelle**, pas a une reponse figee : l'invariant est « les deux
// copies des seuils coincident », et il doit tenir apres chaque modification.
//
// Il echoue aussi quand une fonction de DETECTIONS n'a pas d'instrument, ou
// l'inverse : une detection ajoutee sans instrument serait sinon muette au
// banc d'essai, sans que rien ne le dise.
//
//     node scripts/verifier_instruments.mjs

import { construire_corps } from "../web/static/js/landmarks.js";
import { DETECTIONS, REPERES } from "../web/static/js/detections.js";
import { INSTRUMENTS, lire_instrument } from "../web/static/js/instruments.js";
import { lire_lignes } from "./fixtures.mjs";

const lignes = lire_lignes("poses_detections");

const sans_instrument = Object.keys(DETECTIONS).filter((nom) => !INSTRUMENTS[nom]);
const orphelins = Object.keys(INSTRUMENTS).filter((nom) => !DETECTIONS[nom]);
for (const nom of sans_instrument) console.error(`Detection sans instrument : ${nom}`);
for (const nom of orphelins) console.error(`Instrument sans detection : ${nom}`);

const ecarts = new Map();
let comparaisons = 0;
// Combien de poses tombent dans chaque jeton, par instrument. Un seuil qui ne
// borde qu'un jeton jamais atteint n'est verifie par rien : mesure, decaler de
// 0,25 a 0,27 le seuil d'appui du gainage lateral passait vert, les poses
// tirees au hasard ne reunissant presque jamais ses quatre conditions. Le
// relever ne comble pas l'angle mort, mais l'empeche de passer pour du vert.
const visites = {};
const PEU_VISITE = 20;

function comparer(nom, instrument, corps, repere, index) {
  const attendu = DETECTIONS[nom](corps, repere);
  const { jeton, valeurs } = lire_instrument(instrument, corps, repere);
  comparaisons++;
  if (jeton !== attendu) {
    const cle = repere ? `${nom} (avec un repere)` : nom;
    if (!ecarts.has(cle)) ecarts.set(cle, []);
    ecarts.get(cle).push({ pose: index + 1, attendu, obtenu: jeton, valeurs });
  }
  return attendu;
}

let precedent = null;
lignes.forEach(({ landmarks }, index) => {
  const corps = construire_corps(landmarks);

  for (const [nom, instrument] of Object.entries(INSTRUMENTS)) {
    if (!DETECTIONS[nom]) continue;
    const attendu = comparer(nom, instrument, corps, null, index);
    visites[nom] ??= {};
    visites[nom][String(attendu)] = (visites[nom][String(attendu)] ?? 0) + 1;
    // Une detection qui lit un repere (`REPERES`) se compare aussi sous un
    // repere qui n'est pas le moyen — celui de la pose precedente : un
    // instrument qui l'ignorerait passerait sinon, le repere moyen etant celui
    // que les deux lisent sans repere.
    if (REPERES[nom] && precedent) {
      comparer(nom, instrument, corps, REPERES[nom](precedent), index);
    }
  }
  precedent = corps;
});

console.log(`${lignes.length} poses, ${comparaisons} comparaisons`);
console.log(`${Object.keys(INSTRUMENTS).length} instruments\n`);

// Seuls les jetons que l'instrument peut rendre sont attendus : `ordre` plus
// le defaut (null pour une fonction d'erreur, qui ne dit rien la plupart du
// temps).
const peu_visites = [];
for (const [nom, instrument] of Object.entries(INSTRUMENTS)) {
  for (const jeton of [...instrument.ordre, instrument.defaut]) {
    const n = visites[nom]?.[String(jeton)] ?? 0;
    if (n < PEU_VISITE) peu_visites.push(`  ${nom} → ${jeton} : ${n} pose(s)`);
  }
}
if (peu_visites.length) {
  console.log(`Jetons peu visites (moins de ${PEU_VISITE} poses) — leurs seuils sont mal verifies :`);
  for (const ligne of peu_visites) console.log(ligne);
  console.log("");
}

if (!ecarts.size && !sans_instrument.length && !orphelins.length) {
  console.log("Aucun ecart : chaque instrument redit exactement sa detection.");
  process.exit(0);
}

for (const [nom, liste] of ecarts) {
  console.error(`${nom} : ${liste.length} ecarts`);
  for (const e of liste.slice(0, 3)) {
    const v = e.valeurs.map((x) => (x === null ? "null" : x.toFixed(4))).join(", ");
    console.error(`  pose ${e.pose} : detection=${e.attendu}  instrument=${e.obtenu}  [${v}]`);
  }
}
process.exit(1);
