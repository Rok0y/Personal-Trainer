// Rejoue le ressenti sur les historiques figes et compare aux reponses figees.
//
// Deux genres de lignes. La **table d'ajustement** est comparee telle quelle :
// c'est toute la regle de progression, et la verifier explicitement vaut mieux
// que d'esperer qu'un historique la traverse entierement — les combinaisons
// que l'interface ne propose pas (« facile » apres un echec) n'apparaissent
// autrement qu'au hasard. Les **historiques** sont rejoues en entier.
//
// Usage : node scripts/comparer_ressenti.mjs [--mettre-a-jour]

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import { Ressenti, ECHELLE, ajustement, est_valide } from "../web/static/js/ressenti.js";
import { Releve, lire_json, lire_lignes } from "./fixtures.mjs";

function inventaires(tables) {
  const complet = {};
  for (const p of tables.echelles.reference) complet[p] = 2;
  return {
    non_declare: null,
    debutant: { halteres: { 2: 2, 3: 2, 4: 2 }, accessoires: ["tapis"] },
    complet: { halteres: complet, accessoires: ["tapis", "chaise"] },
  };
}

function main() {
  const tables = lire_json("donnees/baremes.json");
  const moteurs = {};
  for (const [nom, brut] of Object.entries(inventaires(tables))) {
    const baremes = new Baremes(tables, brut);
    moteurs[nom] = new Ressenti(baremes, new Niveaux(baremes));
  }

  const lignes = lire_lignes("ressenti");
  const releve = new Releve();
  let historiques = 0;

  for (const ligne of lignes) {
    if (ligne.genre === "table") {
      releve.verifier("table / echelle", ligne, "echelle", ECHELLE);
      for (const cas of ligne.ajustements) {
        releve.verifier(
          `table / ajustement(${cas.reussi}, ${cas.ressenti})`,
          cas, "reponse",
          ajustement(cas.reussi, cas.ressenti)
        );
      }
      for (const cas of ligne.est_valide) {
        releve.verifier(`table / est_valide(${cas.valeur})`, cas, "reponse", est_valide(cas.valeur));
      }
      continue;
    }

    historiques += 1;
    const moteur = moteurs[ligne.inventaire];
    const { seances, ancrages } = ligne;
    const niveaux = moteur.niveaux.niveaux_par_exercice(seances, ancrages);

    const obtenu = {
      evaluation: moteur.evaluation(seances, ancrages, niveaux),
      jugements_par_seance: moteur.jugements_par_seance(seances),
      juger: seances.flatMap((s) => s.exercices.map((e) => moteur.juger(e))),
    };

    for (const champ of Object.keys(obtenu)) {
      releve.verifier(
        `historique ${ligne.numero} / ${ligne.inventaire} / ${champ}`,
        ligne, champ, obtenu[champ]
      );
    }
  }

  console.log(
    `${historiques} historiques rejoues + la table d'ajustement, ` +
      `${releve.comparaisons} reponses comparees`
  );
  releve.conclure({
    fichier: "ressenti",
    lignes,
    succes: "Aucun ecart : le ressenti rend les reponses figees.",
  });
}

main();
