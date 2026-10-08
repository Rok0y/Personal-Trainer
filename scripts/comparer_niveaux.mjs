// Rejoue les historiques figes dans le calcul des niveaux.
//
// Un niveau se deduit d'un historique : le jeu en contient des dizaines tires
// au hasard, volontairement tordus — series inegales et inachevees, modes qui
// ne correspondent pas au bareme, exercices repetes dans une meme seance,
// ancrages poses au milieu (a la fin ils ne feraient table rase de rien, au
// debut ils ne serviraient jamais de plancher).
//
// Usage : node scripts/comparer_niveaux.mjs [--mettre-a-jour]

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import { Releve, lire_json, lire_lignes } from "./fixtures.mjs";

const INVENTAIRES = (tables) => {
  const complet = {};
  for (const p of tables.echelles.reference) complet[p] = 2;
  return {
    non_declare: null,
    debutant: { halteres: { 2: 2, 3: 2, 4: 2 }, accessoires: ["tapis"] },
    complet: { halteres: complet, accessoires: ["tapis", "chaise"] },
  };
};

function main() {
  const tables = lire_json("donnees/baremes.json");
  const moteurs = {};
  for (const [nom, brut] of Object.entries(INVENTAIRES(tables))) {
    moteurs[nom] = new Niveaux(new Baremes(tables, brut));
  }

  const lignes = lire_lignes("niveaux");
  const releve = new Releve();
  let seances = 0;

  for (const ligne of lignes) {
    const moteur = moteurs[ligne.inventaire];
    const { seances: histoire, ancrages } = ligne;
    seances += histoire.length;

    const obtenu = {
      niveaux_par_exercice: moteur.niveaux_par_exercice(histoire, ancrages),
      etats_niveaux: moteur.etats_niveaux(histoire, ancrages),
      montees_de_niveau: moteur.montees_de_niveau(histoire, ancrages),
      niveau_prouve_par: histoire.flatMap((s) =>
        s.exercices.map((e) => moteur.niveau_prouve_par(e))
      ),
    };

    for (const champ of Object.keys(obtenu)) {
      releve.verifier(
        `historique ${ligne.numero} / ${ligne.inventaire} / ${champ}`,
        ligne, champ, obtenu[champ]
      );
    }
  }

  console.log(
    `${lignes.length} historiques rejoues (${seances} seances), ` +
      `${releve.comparaisons} reponses comparees`
  );
  releve.conclure({
    fichier: "niveaux",
    lignes,
    succes: "Aucun ecart : les niveaux rendent les reponses figees.",
  });
}

main();
