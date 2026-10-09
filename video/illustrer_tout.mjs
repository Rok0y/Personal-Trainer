// Traite d'un coup les videos brutes de `video/a_traiter/` par `illustrer.py`.
//
//     node video/illustrer_tout.mjs                 # ce qui n'est pas encore a jour
//     node video/illustrer_tout.mjs squat oiseau    # seulement ces prises-la
//     node video/illustrer_tout.mjs --refaire       # tout, meme ce qui est a jour
//
// Une prise se nomme comme la video qu'elle deviendra, sans extension :
// `squat_charge.mov` est le « Squat charge ». L'exercice se retrouve par
// `fichier_video` — la regle du nom n'existe qu'en JS, d'ou ce script en node.
// Un fichier qui ne porte le nom d'aucun mouvement est signale et laisse.
//
// Une prise d'un cote (« droit », « droite ») ecrit aussi le cote oppose par
// `--miroir`, si ce mouvement existe et qu'il n'a pas sa propre prise : on ne
// filme qu'un cote, mais une prise du cote gauche l'emporte sur le reflet.
//
// Une prise est a jour quand toutes ses videos sont plus recentes qu'elle.
// Pour recadrer une seule boucle (`--debut`, `--fin`), relancer `illustrer.py`
// a la main sur cette prise.

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { fichier_video } from "../web/static/js/videos.js";

const A_TRAITER = "video/a_traiter";
const DESTINATION = "web/static/videos";
const MOUVEMENTS = "web/static/donnees/mouvements.json";
const EXTENSIONS = new Set([".mov", ".mp4", ".m4v"]);

const args = process.argv.slice(2);
const refaire = args.includes("--refaire");
const choisies = new Set(args.filter((a) => !a.startsWith("--")));

const noms = Object.keys(JSON.parse(fs.readFileSync(MOUVEMENTS, "utf8")));
const par_prise = new Map(noms.map((nom) => [path.parse(fichier_video(nom)).name, nom]));

/** Le mouvement du cote oppose (« Fente droite chargee » -> « Fente gauche chargee »), ou null. */
function cote_oppose(nom) {
  if (!/\bdroite?\b/.test(nom)) return null;
  const oppose = nom.replace(/\bdroite?\b/, "gauche");
  return noms.includes(oppose) ? oppose : null;
}

function date(chemin) {
  return fs.existsSync(chemin) ? fs.statSync(chemin).mtimeMs : -Infinity;
}

// Les prises, par nom sans extension : deux fichiers du meme nom sont ambigus.
const prises = new Map();
const inconnues = [];
for (const fichier of fs.readdirSync(A_TRAITER).sort()) {
  const { name, ext } = path.parse(fichier);
  if (!EXTENSIONS.has(ext.toLowerCase())) continue;
  if (!par_prise.has(name)) {
    inconnues.push(fichier);
    continue;
  }
  if (prises.has(name)) {
    console.error(`Deux prises pour ${name} (${prises.get(name)}, ${fichier}) : laquelle ? Aucune n'est traitee.`);
    prises.set(name, null);
    continue;
  }
  prises.set(name, fichier);
}
for (const choisie of choisies) {
  if (!prises.get(choisie)) console.error(`Aucune prise ${choisie} dans ${A_TRAITER}.`);
}

const faites = [];
const echouees = [];
const a_jour = [];
for (const [prise, fichier] of prises) {
  if (!fichier || (choisies.size && !choisies.has(prise))) continue;
  const source = path.join(A_TRAITER, fichier);
  const exercice = par_prise.get(prise);
  const oppose = cote_oppose(exercice);
  const miroir = oppose && !prises.has(path.parse(fichier_video(oppose)).name) ? oppose : null;

  const sorties = [exercice, miroir].filter(Boolean).map((nom) => path.join(DESTINATION, fichier_video(nom)));
  if (!refaire && sorties.every((sortie) => date(sortie) > date(source))) {
    a_jour.push(prise);
    continue;
  }

  console.log(`\n=== ${fichier} -> « ${exercice} »${miroir ? ` et, en miroir, « ${miroir} »` : ""}`);
  const commande = ["video/illustrer.py", source, exercice, ...(miroir ? ["--miroir", miroir] : [])];
  const { status, error } = spawnSync("python", commande, { stdio: "inherit" });
  if (error || status !== 0) echouees.push(fichier);
  else faites.push(prise);
}

console.log("");
if (faites.length) console.log(`Traitees (${faites.length}) : ${faites.join(", ")}`);
if (a_jour.length) console.log(`Deja a jour (${a_jour.length}) : ${a_jour.join(", ")} — --refaire pour les reprendre`);
if (inconnues.length) console.log(`Ignorees, nom d'aucun mouvement (${inconnues.length}) : ${inconnues.join(", ")}`);
if (echouees.length) console.log(`En echec (${echouees.length}) : ${echouees.join(", ")}`);
if (faites.length) console.log(`Verifier le sens et le raccord : video/essais/<prise>/controle.png`);

const manquantes = noms.filter((nom) => !fs.existsSync(path.join(DESTINATION, fichier_video(nom))));
console.log(`Videos encore a tourner : ${manquantes.length} / ${noms.length}`);
process.exitCode = echouees.length ? 1 : 0;
