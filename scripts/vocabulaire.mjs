// Le vocabulaire du coach, tel que l'outillage de prise de son le lit.
//
// Tout vient des donnees de l'application (`sons.json`, `mouvements.json`,
// `baremes.json`) et des regles d'`annonces.js` : aucun texte ni aucun nom de
// fichier n'est redeclare ici. C'est ce qui permet a la feuille de prise de
// son de nommer exactement le fichier que l'application reclamera.

import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { fichier, nombre_dit } from "../web/static/js/annonces.js";

const ICI = dirname(fileURLToPath(import.meta.url));
export const RACINE = join(ICI, "..");
export const SONS = join(RACINE, "web", "static", "sons");
const DONNEES = join(RACINE, "web", "static", "donnees");

const lire = (nom) => JSON.parse(readFileSync(join(DONNEES, nom), "utf-8"));

export function charger() {
  const sons = lire("sons.json");
  const mouvements = lire("mouvements.json");
  const socle = lire("baremes.json");
  return { sons, mouvements, echelles: socle.echelles };
}

/**
 * « Prépare deux haltères de 8 kilos », ou null s'il n'y a rien a dire.
 *
 * Le **texte** d'une charge, pour la colonne « a prononcer ». L'application,
 * elle, ne coud que des noms de fichiers (`fichier_assemble`) : les deux
 * chemins doivent mener au meme fichier, et `verifier_annonces.mjs` le
 * controle sur toute la gamme.
 */
export function texte_charge(fragments, nombre_halteres, poids) {
  const entier = nombre_dit(poids);
  if (entier === null || ![1, 2].includes(nombre_halteres)) return null;
  const amorce = fragments[nombre_halteres === 1 ? "prepare_un_haltere_de" : "prepare_deux_halteres_de"];
  return `${amorce} ${entier} ${fragments[entier === 1 ? "kilo" : "kilos"]}`;
}

/**
 * Origine -> texte, pour tout ce qui s'enregistre en une prise : les briques,
 * les noms de mouvements (le nom est son propre texte) et les charges de la
 * gamme de reference. Les fragments n'y sont pas : ils ne sont jamais un
 * fichier, ils composent le texte des charges.
 */
export function phrases_enregistrees({ sons, mouvements, echelles }) {
  const phrases = { ...sons.textes };
  for (const nom of Object.keys(mouvements)) phrases[`mouvement:${nom}`] = nom;
  for (const halteres of [1, 2]) {
    for (const poids of echelles.reference) {
      const texte = texte_charge(sons.fragments, halteres, poids);
      if (texte) phrases[`charge:${halteres}x${poids}`] = texte;
    }
  }
  return phrases;
}

export { fichier };
