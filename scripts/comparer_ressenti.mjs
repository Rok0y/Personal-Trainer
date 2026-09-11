// Rejoue en JavaScript ce que `generer_ressenti.py` a releve.
//
// Deux genres de lignes. La **table d'ajustement** est comparee telle quelle :
// c'est toute la regle de progression, et la verifier explicitement vaut mieux
// que d'esperer qu'un historique la traverse entierement — les combinaisons
// que l'interface ne propose pas (« facile » apres un echec) n'apparaissent
// autrement qu'au hasard. Les **historiques** sont rejoues en entier.
//
// Usage : node scripts/comparer_ressenti.mjs
// Prealable : python -m scripts.generer_ressenti

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import { Ressenti, ECHELLE, ajustement, est_valide } from "../web/static/js/ressenti.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE = join(ICI, "..");
const FIXTURES = join(ICI, "fixtures_ressenti.jsonl");
const BAREMES = join(RACINE, "web", "static", "donnees", "baremes.json");

const ECARTS_DETAILLES = 4;

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
  const tables = JSON.parse(readFileSync(BAREMES, "utf-8"));
  const moteurs = {};
  for (const [nom, brut] of Object.entries(inventaires(tables))) {
    const baremes = new Baremes(tables, brut);
    moteurs[nom] = new Ressenti(baremes, new Niveaux(baremes));
  }

  const lignes = readFileSync(FIXTURES, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

  const echecs = [];
  let comparaisons = 0;
  let historiques = 0;

  for (const ligne of lignes) {
    if (ligne.genre === "table") {
      const verifier = (nom, attendu, obtenu) => {
        comparaisons += 1;
        if (JSON.stringify(attendu) !== JSON.stringify(obtenu)) {
          echecs.push({ ou: `table / ${nom}`, attendu: JSON.stringify(attendu), rendu: JSON.stringify(obtenu) });
        }
      };
      verifier("echelle", ligne.echelle, ECHELLE);
      for (const cas of ligne.ajustements) {
        verifier(
          `ajustement(${cas.reussi}, ${cas.ressenti})`,
          cas.reponse,
          ajustement(cas.reussi, cas.ressenti)
        );
      }
      for (const cas of ligne.est_valide) {
        verifier(`est_valide(${cas.valeur})`, cas.reponse, est_valide(cas.valeur));
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
      comparaisons += 1;
      const attendu = JSON.stringify(ligne[champ]);
      const rendu = JSON.stringify(obtenu[champ]);
      if (attendu !== rendu) {
        echecs.push({
          ou: `historique ${ligne.numero} / ${ligne.inventaire} / ${champ}`,
          attendu,
          rendu,
        });
      }
    }
  }

  console.log(
    `${historiques} historiques rejoues + la table d'ajustement, ` +
      `${comparaisons} reponses comparees`
  );

  if (!echecs.length) {
    console.log("\nAucun ecart : le portage du ressenti est fidele.");
    return;
  }

  console.log(`\n${echecs.length} reponses divergent. Les ${ECARTS_DETAILLES} premieres :\n`);
  for (const { ou, attendu, rendu } of echecs.slice(0, ECARTS_DETAILLES)) {
    console.log(`  ${ou}`);
    console.log(`    python = ${attendu.slice(0, 280)}`);
    console.log(`    js     = ${rendu.slice(0, 280)}`);
    console.log();
  }
  process.exitCode = 1;
}

main();
