// Rejoue les questions figees sur le bareme.
//
// Un bareme est une fonction pure de (spec, echelle) : on peut donc lui jeter
// des entrees au hasard, comme aux detections, sans avoir a lui construire une
// histoire comme au circuit. Les questions montent jusqu'au niveau 200, bien
// au-dela du dernier palier borne : la tranche ouverte est une autre regle.
//
// Usage : node scripts/comparer_paliers.mjs [--mettre-a-jour]

import { Baremes } from "../web/static/js/paliers.js";
import { Releve, lire_json, lire_lignes } from "./fixtures.mjs";

// `paliers_specs.json` porte deux exercices fictifs — ils couvrent les
// surcharges de palier et le bareme sans fin, deux branches qu'aucun exercice
// reel n'exerce — et les inventaires balayes. Les inventaires voyagent avec
// les questions plutot que d'etre redeclares ici : un jeu d'entrees duplique a
// le meme defaut que le code qu'il surveille.

function repondre(bareme, ligne) {
  const nom = ligne.exercice;
  switch (ligne.question) {
    case "echelle":
      return bareme.echelle_exercice(nom);
    case "tranches":
      return bareme.tranches(nom, bareme.specs[nom].series_max);
    case "dernier_palier_borne":
      return bareme.dernier_palier_borne(nom);
    case "palier": {
      const p = bareme.palier(nom, ligne.niveau);
      if (p === null) return null;
      return {
        ...p,
        volume: bareme.volume_exercice(nom, p.series, p.cible, p.poids),
        resume: resume(p),
      };
    }
    case "niveau_pour":
      return bareme.niveau_pour(nom, ligne.poids, ligne.series, ligne.cible);
    case "niveau_pour_volume":
      return bareme.niveau_pour_volume(nom, ligne.volume);
    default:
      throw new Error(`Question inconnue : ${ligne.question}`);
  }
}

/**
 * Le resume fige d'un palier (« 4x12 à 5 kg »), sans zero decimal inutile :
 * 5.0 s'ecrit « 5 ».
 */
function resume(p) {
  const suffixe = p.unite === "secondes" ? " s" : "";
  const charge = p.poids ? ` à ${Number(p.poids)} kg` : "";
  return `${p.series}x${p.cible}${suffixe}${charge}`;
}

function main() {
  const tables = lire_json("donnees/baremes.json");
  const extra = lire_json("paliers_specs.json");
  tables.specs = { ...tables.specs, ...extra.specs };
  tables.materiel = { ...tables.materiel, ...extra.materiel };
  const lignes = lire_lignes("paliers");

  const baremes = {};
  for (const [nom, brut] of Object.entries(extra.inventaires)) {
    // `Baremes` normalise lui-meme : on lui passe le brut, null compris.
    baremes[nom] = new Baremes(tables, brut);
  }

  const releve = new Releve();
  for (const ligne of lignes) {
    let obtenu;
    try {
      obtenu = repondre(baremes[ligne.inventaire], ligne);
    } catch (erreur) {
      obtenu = `EXCEPTION ${erreur.message}`;
    }
    const contexte = Object.entries(ligne)
      .filter(([c]) => !["reponse", "question", "inventaire", "exercice"].includes(c))
      .map(([c, v]) => `${c}=${v}`)
      .join(" ");
    releve.verifier(
      `${ligne.exercice} / ${ligne.inventaire} / ${ligne.question} ${contexte}`,
      ligne, "reponse", obtenu
    );
  }

  const par_question = {};
  for (const l of lignes) par_question[l.question] = (par_question[l.question] ?? 0) + 1;
  console.log(
    `${lignes.length} questions rejouees ` +
      `(${Object.entries(par_question).map(([q, n]) => `${q} ${n}`).join(", ")})`
  );
  releve.conclure({
    fichier: "paliers",
    lignes,
    succes: "Aucun ecart : le bareme rend les reponses figees.",
    detail: 6,
  });
}

main();
