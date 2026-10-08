// Rejoue les programmes figes et compare aux reponses figees.
//
// La moitie des programmes exige des charges hors du materiel declare : seul
// moyen d'eprouver la traduction par le volume, regle centrale du module. Les
// historiques sont allonges et redates (ecarts de sept jours pile, « maintenant »
// pose a sept ou quatorze jours pile) parce que le hasard ne visite pas les
// frontieres de la semaine.
//
// Usage : node scripts/comparer_programmes.mjs [--mettre-a-jour]

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import {
  etat_exigence,
  etat_programme,
  liaison_seances,
  libelles_seances,
  prescription,
  semaine_du_programme,
  volume_exige,
} from "../web/static/js/programmes.js";
import { Releve, lire_json, lire_lignes } from "./fixtures.mjs";

const CATALOGUE = { bras: {}, upper_push: {}, jambes_abdos: {} };

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
    moteurs[nom] = { baremes, niveaux: new Niveaux(baremes) };
  }

  const lignes = lire_lignes("programmes");
  const releve = new Releve();
  let exigences = 0;

  for (const ligne of lignes) {
    const { baremes, niveaux } = moteurs[ligne.inventaire];
    const { programme, seances, cle } = ligne;
    const ou = `programme ${ligne.numero} / ${ligne.inventaire}`;

    const etats = niveaux.etats_niveaux(seances, {});

    releve.verifier(`${ou} / volumes`, ligne, "volumes",
      programme.exigences.map((e) => volume_exige(baremes, e))
    );
    releve.verifier(`${ou} / prescriptions`, ligne, "prescriptions",
      programme.exigences.map((e) => prescription(baremes, e))
    );
    releve.verifier(`${ou} / etats_exigences`, ligne, "etats_exigences",
      programme.exigences.map((e) => etat_exigence(baremes, e, etats))
    );
    releve.verifier(`${ou} / libelles`, ligne, "libelles", libelles_seances(programme));
    releve.verifier(`${ou} / liaison`, ligne, "liaison", liaison_seances(programme, CATALOGUE));
    releve.verifier(`${ou} / semaine`, ligne, "semaine",
      semaine_du_programme(programme, seances, CATALOGUE, ligne.tours, ligne.maintenant)
    );
    releve.verifier(`${ou} / etat_programme`, ligne, "etat_programme",
      etat_programme(baremes, cle, programme, etats)
    );

    exigences += programme.exigences.length;
  }

  console.log(
    `${lignes.length} programmes rejoues, ${exigences} exigences, ` +
      `${releve.comparaisons} reponses comparees`
  );
  releve.conclure({
    fichier: "programmes",
    lignes,
    succes: "Aucun ecart : les programmes rendent les reponses figees.",
  });
}

main();
