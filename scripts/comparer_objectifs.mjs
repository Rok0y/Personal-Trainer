// Rejoue en JavaScript ce que `generer_objectifs.py` a releve.
//
// Deux genres de lignes. Les **cibles manuelles** sont comparees hors de tout
// historique : elles ne dependent d'aucune seance, et un format mal lu fige
// une cible pour toujours, en silence — c'est exactement le genre de defaut
// qu'un tirage ne visite qu'une fois sur dix.
//
// Les **historiques** rejouent le pilotage complet : objectifs par exercice,
// exercices sans donnees, puis l'ecriture sur les deux formes de bloc
// (dictionnaire et `BlocExercice`), qui ont chacune leur fonction et ne
// doivent pas diverger.
//
// Usage : node scripts/comparer_objectifs.mjs
// Prealable : python -m scripts.generer_objectifs

import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import { Ressenti } from "../web/static/js/ressenti.js";
import { Calibration } from "../web/static/js/calibration.js";
import {
  Objectifs,
  profils_cible_manuelle,
  est_cible_manuelle,
  definir_cible_manuelle,
  fusionner_cible_manuelle,
  enteriner_cibles_manuelles,
} from "../web/static/js/objectifs.js";
import { BlocExercice, Circuit, Exercice } from "../web/static/js/circuit.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE = join(ICI, "..");
const FIXTURES = join(ICI, "fixtures_objectifs.jsonl");
const BAREMES = join(RACINE, "web", "static", "donnees", "baremes.json");

const PROFIL = 1;
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

const detection_muette = () => "milieu";

function circuit_depuis(blocs) {
  return new Circuit(
    blocs.map(
      (bloc) =>
        new BlocExercice({
          exercice: new Exercice({ nom: bloc.exercice, detection: detection_muette }),
          poids: bloc.poids,
          mode: bloc.mode,
          nombre_series: bloc.series,
          repetitions_par_serie: bloc.repetitions,
          duree: bloc.duree,
          repos_entre_series: bloc.repos_entre_series,
          repos_apres: bloc.repos_apres,
          commentaire: bloc.commentaire,
          cible_manuelle: bloc.cible_manuelle,
        })
    )
  );
}

function decrire_circuit(circuit) {
  return circuit.exercices.map((bloc) => ({
    exercice: bloc.exercice.nom,
    mode: bloc.mode,
    poids: bloc.poids,
    nombre_series: bloc.nombre_series,
    repetitions_par_serie: bloc.repetitions_par_serie,
    duree: bloc.duree,
    test_max: bloc.test_max ?? false,
    avant_test: bloc.avant_test ?? null,
  }));
}

function main() {
  const tables = JSON.parse(readFileSync(BAREMES, "utf-8"));
  const moteurs = {};
  for (const [nom, brut] of Object.entries(inventaires(tables))) {
    const baremes = new Baremes(tables, brut);
    const niveaux = new Niveaux(baremes);
    moteurs[nom] = {
      calibration: new Calibration(baremes),
      objectifs: new Objectifs(
        baremes,
        niveaux,
        new Ressenti(baremes, niveaux),
        new Calibration(baremes)
      ),
    };
  }

  const lignes = readFileSync(FIXTURES, "utf-8")
    .split("\n")
    .filter((l) => l.trim())
    .map((l) => JSON.parse(l));

  const echecs = [];
  let comparaisons = 0;
  let historiques = 0;

  const verifier = (ou, attendu, obtenu) => {
    comparaisons += 1;
    const a = JSON.stringify(attendu);
    const b = JSON.stringify(obtenu);
    if (a !== b) echecs.push({ ou, attendu: a, rendu: b });
  };

  for (const ligne of lignes) {
    if (ligne.genre === "cible_manuelle") {
      for (const cas of ligne.profils) {
        verifier(
          `profils_cible_manuelle(${JSON.stringify(cas.valeur)})`,
          cas.reponse,
          [...profils_cible_manuelle(cas.valeur)].sort((x, y) => x - y)
        );
      }
      for (const cas of ligne.est) {
        verifier(
          `est_cible_manuelle(${JSON.stringify(cas.valeur)}, ${cas.profil})`,
          cas.reponse,
          est_cible_manuelle({ cible_manuelle: cas.valeur }, cas.profil)
        );
      }
      for (const cas of ligne.definir) {
        verifier(
          `definir_cible_manuelle(${JSON.stringify(cas.valeur)}, ${cas.manuelle}, ${cas.profil})`,
          cas.reponse,
          definir_cible_manuelle(cas.valeur, cas.manuelle, cas.profil)
        );
      }
      for (const cas of ligne.fusionner) {
        verifier(
          `fusionner(${JSON.stringify(cas.entrante)}, ${JSON.stringify(cas.stockee)}, ${cas.profil})`,
          cas.reponse,
          fusionner_cible_manuelle(cas.entrante, cas.stockee, cas.profil)
        );
      }
      for (const cas of ligne.enteriner) {
        const blocs = cas.blocs.map((b) => ({ ...b }));
        const leve = enteriner_cibles_manuelles(blocs, cas.profil);
        verifier(
          `enteriner_cibles_manuelles(profil ${cas.profil})`,
          cas.reponse,
          { leve, apres: blocs.map((b) => b.cible_manuelle ?? null) }
        );
      }
      continue;
    }

    historiques += 1;
    const { objectifs: moteur, calibration } = moteurs[ligne.inventaire];
    const { seances, ancrages } = ligne;
    const ou = `historique ${ligne.numero} / ${ligne.inventaire}`;

    const objs = moteur.objectifs_par_exercice(seances, ancrages);
    const sans = moteur.exercices_sans_donnees(seances, ancrages);

    verifier(`${ou} / objectifs`, ligne.objectifs, objs);
    verifier(`${ou} / sans_donnees`, ligne.sans_donnees, [...sans].sort());

    const charges = {};
    for (const nom of Object.keys(ligne.charges_de_test)) {
      charges[nom] = calibration.charge_de_test(nom);
    }
    verifier(`${ou} / charges_de_test`, ligne.charges_de_test, charges);

    for (const cas of ligne.niveaux_estimes) {
      verifier(
        `${ou} / niveau_estime(${cas.exercice}, ${cas.poids}, ${cas.maximum})`,
        cas.reponse,
        calibration.niveau_estime(cas.exercice, cas.poids, cas.maximum)
      );
    }

    // Les blocs sont copies : `appliquer_a_blocs` ecrit sur place, et
    // comparer l'entree apres coup n'aurait plus de sens.
    const blocs = structuredClone(ligne.blocs_avant);
    verifier(
      `${ou} / blocs_apres`,
      ligne.blocs_apres,
      moteur.appliquer_a_blocs(blocs, objs, sans, PROFIL)
    );

    verifier(
      `${ou} / marques`,
      ligne.marques,
      moteur.marquer_cibles_manuelles(
        structuredClone(ligne.blocs_avant), objs, sans, PROFIL
      )
    );

    const circuit = circuit_depuis(ligne.blocs_avant);
    verifier(
      `${ou} / circuit_apres`,
      ligne.circuit_apres,
      decrire_circuit(moteur.appliquer_a_circuit(circuit, objs, sans, PROFIL))
    );
  }

  console.log(
    `${historiques} historiques rejoues + les cibles manuelles, ` +
      `${comparaisons} reponses comparees`
  );

  if (!echecs.length) {
    console.log("\nAucun ecart : le portage des objectifs est fidele.");
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
