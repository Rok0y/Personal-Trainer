// Rejoue les questions figees sur les ligues, divisions et XP.
//
// Deux natures de questions, melangees volontairement : des fonctions pures
// (le rang d'un volume relatif, l'XP d'un niveau, le niveau general d'une XP)
// bombardees d'entrees au hasard **et** des abords de chaque seuil, a epsilon
// pres — c'est la que `>=` se distingue de `>`, et des tirages uniformes n'y
// tombent jamais ; et des fonctions qui lisent une histoire, rejouees sur des
// historiques tordus.
//
// Les exercices fictifs de `paliers_specs.json` (`Surcharge`, `SansFin`) sont
// fusionnes comme dans `comparer_paliers.mjs` : le catalogue reel n'exerce ni
// les surcharges de palier ni le bareme sans fin.
//
// Usage : node scripts/comparer_ligues.mjs [--mettre-a-jour]

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import { Ligues } from "../web/static/js/ligues.js";
import { Releve, lire_json, lire_lignes } from "./fixtures.mjs";

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
  const tables = lire_json("donnees/baremes.json");
  const fictifs = lire_json("paliers_specs.json");
  Object.assign(tables.specs, fictifs.specs);
  Object.assign(tables.materiel, fictifs.materiel);

  const moteurs = {};
  for (const [nom, brut] of Object.entries(fictifs.inventaires)) {
    const baremes = new Baremes(tables, brut);
    moteurs[nom] = {
      niveaux: new Niveaux(baremes),
      ligues: new Ligues(baremes, tables.ligues),
    };
  }

  const lignes = lire_lignes("ligues");
  const releve = new Releve();
  for (const ligne of lignes) {
    const repere = [ligne.question, ligne.exercice, ligne.inventaire]
      .filter(Boolean)
      .join(" / ");
    releve.verifier(repere, ligne, "reponse", repondre(moteurs[ligne.inventaire], ligne));
  }

  console.log(`${releve.comparaisons} reponses comparees`);
  releve.conclure({
    fichier: "ligues",
    lignes,
    succes: "Aucun ecart : les ligues rendent les reponses figees.",
    detail: 6,
  });
}

main();
