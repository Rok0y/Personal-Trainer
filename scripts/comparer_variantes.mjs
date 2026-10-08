// Rejoue les variantes sur les catalogues et historiques figes.
//
// Cinq genres de lignes. Les **catalogues** (reel et tordu) voyagent avec
// les questions plutot que d'etre redeclares ici, avec les seuils de retour —
// compares a ceux du `baremes.json` fige, seule facon de savoir que les
// reponses ont ete figees avec les memes. Les **tables**
// croisent `definir`, `substitution`, `original_de` et surtout
// `appliquer_au_circuit`, compare avant et apres sur des circuits montes par
// `circuit_pour`. Les **historiques** construits visent les propositions, et
// le **retour** vise le seuil au niveau pres.
//
// Usage : node scripts/comparer_variantes.mjs [--mettre-a-jour]

import { Baremes } from "../web/static/js/paliers.js";
import { Niveaux } from "../web/static/js/niveaux.js";
import { Ressenti } from "../web/static/js/ressenti.js";
import { Variantes, chaine, normaliser, original_de } from "../web/static/js/variantes.js";
import { circuit_pour, exercice_pour } from "../web/static/js/seance.js";
import { Releve, lire_json, lire_lignes } from "./fixtures.mjs";

function relever(circuit) {
  return circuit.exercices.map((bloc) => ({
    exercice: bloc.exercice.nom,
    mode: bloc.mode,
    remplace: bloc.remplace,
    cible_manuelle: bloc.cible_manuelle,
    entrelace_avec: bloc.entrelace_avec,
  }));
}

function main() {
  const tables = lire_json("donnees/baremes.json");
  const mouvements = lire_json("donnees/mouvements.json");
  const baremes = new Baremes(tables, null);
  const niveaux = new Niveaux(baremes);
  const ressenti = new Ressenti(baremes, niveaux);
  const moteur = new Variantes(baremes, tables.variantes?.retour ?? {}, niveaux);

  const lignes = lire_lignes("variantes");
  const releve = new Releve();
  const verifier = (ou, cible, cle, obtenu) => releve.verifier(ou, cible, cle, obtenu);
  const tenter = (fonction) => {
    try {
      return fonction();
    } catch {
      return "refus";
    }
  };

  let catalogues = {};
  for (const ligne of lignes) {
    switch (ligne.genre) {
      case "catalogues":
        catalogues = ligne.catalogues;
        verifier("seuils de retour exportes", ligne, "seuils_retour", tables.variantes?.retour ?? null);
        break;

      case "normaliser":
        for (const q of ligne.questions) {
          verifier(`normaliser(${JSON.stringify(q.entree)})`, q, "reponse", normaliser(q.entree));
        }
        break;

      case "chaines":
        for (const q of ligne.questions) {
          verifier(
            `${ligne.catalogue} / chaine(${q.original})`,
            q, "reponse",
            chaine(q.original, catalogues[ligne.catalogue])
          );
        }
        break;

      case "table": {
        const catalogue = catalogues[ligne.catalogue];
        const ou = `${ligne.catalogue} / table ${ligne.numero}`;
        for (const q of ligne.definir) {
          verifier(
            `${ou} / definir(${q.original}, ${q.joue})`,
            q, "reponse",
            tenter(() => moteur.definir(ligne.table, q.original, q.joue, catalogue))
          );
        }
        for (const q of ligne.substitution) {
          verifier(
            `${ou} / substitution(${q.nom}, ${q.mode})`,
            q, "reponse",
            moteur.substitution(q.nom, q.mode, ligne.table, catalogue)
          );
        }
        for (const q of ligne.versions ?? []) {
          verifier(
            `${ou} / versions(${q.nom}, ${q.mode})`,
            q, "reponse",
            moteur.versions(q.nom, q.mode, catalogue)
          );
        }
        for (const q of ligne.original_de) {
          verifier(`${ou} / original_de(${q.nom})`, q, "reponse", original_de(q.nom, ligne.table));
        }
        ligne.circuits.forEach((cas, index) => {
          const circuit = circuit_pour(mouvements, cas.blocs);
          verifier(`${ou} / circuit ${index} avant`, cas, "avant", relever(circuit));
          moteur.appliquer_au_circuit(
            circuit, ligne.table, catalogue, (nom) => exercice_pour(mouvements, nom)
          );
          verifier(`${ou} / circuit ${index} apres`, cas, "apres", relever(circuit));
        });
        break;
      }

      case "historique": {
        const catalogue = catalogues[ligne.catalogue];
        const jugements = ressenti.jugements_par_seance(ligne.seances);
        verifier(
          `${ligne.catalogue} / historique ${ligne.numero} / propositions`,
          ligne, "propositions",
          moteur.propositions(ligne.seances, jugements, ligne.table, catalogue)
        );
        break;
      }

      case "montees": {
        const catalogue = catalogues[ligne.catalogue];
        ligne.cas.forEach((cas, index) => {
          verifier(
            `${ligne.catalogue} / montees ${index} (${JSON.stringify(cas.table)})`,
            cas, "reponse",
            moteur.montees(cas.table, cas.seance, catalogue)
          );
        });
        break;
      }

      case "retour":
        for (const q of ligne.questions) {
          verifier(
            `retour_prouve_par(${q.ligne.nom}, ${q.ligne.series_cibles}x${q.ligne.repetitions_cibles || q.ligne.duree_cible})`,
            q, "reponse",
            moteur.retour_prouve_par(q.ligne)
          );
        }
        break;

      default:
        releve.echecs.push({ ou: `genre inconnu : ${ligne.genre}`, attendu: "", rendu: "" });
    }
  }

  console.log(`${releve.comparaisons} reponses comparees sur ${lignes.length} lignes`);
  releve.conclure({
    fichier: "variantes",
    lignes,
    succes: "Aucun ecart : les variantes rendent les reponses figees.",
    detail: 6,
  });
}

main();
