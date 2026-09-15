// Rejoue en JavaScript les questions relevees par `generer_ligues.py`.
//
// Deux natures de questions, et le fichier les melange volontairement : des
// fonctions pures (le rang d'un volume relatif, l'XP d'un niveau, le niveau
// general d'une XP) bombardees d'entrees au hasard **et** des abords de chaque
// seuil ; et des fonctions qui lisent une histoire, rejouees sur des
// historiques tordus.
//
// Les specs fictives du harnais des paliers (`Surcharge`, `SansFin`) sont
// fusionnees ici comme le fait `comparer_paliers.mjs` : le catalogue reel
// n'exerce ni les surcharges de palier ni le bareme sans fin.
//
// Usage : node scripts/comparer_ligues.mjs
// Prealable : python -m scripts.generer_ligues

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import { Ligues } from "../web/static/js/ligues.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE = join(ICI, "..");
const FIXTURES = join(ICI, "fixtures_ligues.jsonl");
const SPECS_DU_HARNAIS = join(ICI, "fixtures_paliers_specs.json");
const BAREMES = join(RACINE, "web", "static", "donnees", "baremes.json");

const ECARTS_DETAILLES = 6;

//: Les cinq memes inventaires que `generer_paliers.inventaires()`, dans le
//: meme ordre de richesse : l'echelle de poids decale toutes les tranches,
//: donc tous les volumes, donc toutes les ligues.
const INVENTAIRES = (tables) => {
  const complet = {};
  for (const p of tables.echelles.reference) complet[p] = 2;
  return {
    non_declare: null,
    vide: { halteres: {}, accessoires: [] },
    debutant: { halteres: { 2: 2, 3: 2, 4: 2 }, accessoires: ["tapis"] },
    une_paire_moyenne: { halteres: { 6: 2, 8: 2, 10: 1 }, accessoires: [] },
    complet: { halteres: complet, accessoires: ["tapis", "chaise"] },
  };
};

function repondre(moteur, ligne) {
  switch (ligne.question) {
    case "rang_pour_volume":
      return moteur.ligues.rang_pour_volume(ligne.volume, ligne.seuils);
    case "seuils_exercice": {
      const seuils = moteur.ligues.seuils_exercice(ligne.exercice);
      return seuils ? [...seuils] : null;
    }
    case "ligue_pour_rang":
      return moteur.ligues.ligue_pour_rang(ligne.rang);
    case "xp":
      return {
        du_niveau: moteur.ligues.xp_du_niveau(ligne.niveau),
        cumulee: moteur.ligues.xp_cumulee(ligne.niveau),
      };
    case "cout_du_niveau_general":
      return moteur.ligues.cout_du_niveau_general(ligne.niveau);
    case "niveau_general":
      return moteur.ligues.niveau_general(ligne.xp);
    case "ligue_exercice":
      return {
        volume_relatif: moteur.ligues.volume_relatif(ligne.exercice, ligne.niveau),
        ligue: moteur.ligues.ligue_exercice(ligne.exercice, ligne.niveau),
      };
    case "historique": {
      const { seances, ancrages } = ligne;
      const etats = moteur.niveaux.etats_niveaux(seances, ancrages);
      const montees = moteur.niveaux.montees_de_niveau(seances, ancrages);
      const xp_gagnee = {};
      for (const [cle, valeur] of Object.entries(montees)) {
        xp_gagnee[cle] = moteur.ligues.xp_gagnee(valeur);
      }
      return {
        ligues_par_exercice: moteur.ligues.ligues_par_exercice(etats),
        xp_totale: moteur.ligues.xp_totale(etats),
        montees_de_ligue: moteur.ligues.montees_de_ligue(montees),
        xp_gagnee,
      };
    }
    default:
      throw new Error(`Question inconnue : ${ligne.question}`);
  }
}

function main() {
  const tables = JSON.parse(readFileSync(BAREMES, "utf-8"));
  // Les exercices fictifs entrent dans le bareme pour la duree du harnais,
  // exactement comme cote Python. Ils ne sont jamais dans `baremes.json`.
  const fictifs = JSON.parse(readFileSync(SPECS_DU_HARNAIS, "utf-8"));
  Object.assign(tables.specs, fictifs.specs);
  Object.assign(tables.materiel, fictifs.materiel);

  const moteurs = {};
  for (const [nom, brut] of Object.entries(INVENTAIRES(tables))) {
    const baremes = new Baremes(tables, brut);
    moteurs[nom] = {
      niveaux: new Niveaux(baremes),
      ligues: new Ligues(baremes, tables.ligues),
    };
  }

  const lignes = readFileSync(FIXTURES, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

  const echecs = [];
  for (const ligne of lignes) {
    const attendu = JSON.stringify(ligne.reponse);
    const rendu = JSON.stringify(repondre(moteurs[ligne.inventaire], ligne));
    if (attendu !== rendu) echecs.push({ ligne, attendu, rendu });
  }

  console.log(`${lignes.length} reponses comparees`);

  if (!echecs.length) {
    console.log("\nAucun ecart : le portage des ligues est fidele.");
    return;
  }

  console.log(
    `\n${echecs.length} reponses divergent. Les ${ECARTS_DETAILLES} premieres :\n`,
  );
  for (const { ligne, attendu, rendu } of echecs.slice(0, ECARTS_DETAILLES)) {
    const repere = [ligne.question, ligne.exercice, ligne.inventaire]
      .filter(Boolean)
      .join(" / ");
    console.log(`  ${repere}`);
    console.log(`    python = ${attendu.slice(0, 300)}`);
    console.log(`    js     = ${rendu.slice(0, 300)}`);
    console.log();
  }
  process.exitCode = 1;
}

main();
