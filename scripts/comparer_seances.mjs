// Rejoue en JavaScript les scenarios releves par `scripts/generer_scenarios.py`
// et signale le moindre ecart.
//
// Pendant de `comparer_detections.mjs`, pour une classe qui a de la memoire :
// la ou les detections se comparent pose par pose, un circuit se compare
// **pas a pas sur une histoire**. Un ecart est donc date — il nomme la seance,
// le scenario, le numero de pas et le champ — parce qu'apres une divergence
// tous les pas suivants divergent aussi, et seul le premier renseigne.
//
// Usage : node scripts/comparer_seances.mjs
// Prealable : python -m scripts.generer_scenarios

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { Circuit, BlocExercice, Exercice, MODE_REPETITIONS } from "../web/static/js/circuit.js";
import { DETECTIONS } from "../web/static/js/detections.js";
import { construire_corps } from "../web/static/js/landmarks.js";
import { CompteurMouvement } from "../web/static/js/compteur.js";
import { creer_etat } from "../web/static/js/etat.js";
import { executer_mode } from "../web/static/js/moteur.js";
import { texte, libelle_etape } from "../web/static/js/messages.js";

const ICI = dirname(fileURLToPath(import.meta.url));
const RACINE = join(ICI, "..");
const FIXTURES = join(ICI, "fixtures_seances.jsonl");
const SEANCES = join(RACINE, "session", "seances_personnalisees.json");
const POSES = join(ICI, "fixtures_poses.jsonl");
// Le catalogue exporte par `preparer_demo` : il donne, pour chaque exercice,
// le *nom* de sa fonction de detection et celui de ses verifications de
// forme. Les fonctions elles-memes vivent dans `detections.js` et portent les
// memes noms — c'est ce qui evite une table de correspondance a maintenir.
const CATALOGUE = join(ICI, "fixtures_catalogue.json");

// Doit valoir INSTANT_INITIAL cote Python : les instants sont releves en
// *ecart* depuis cette valeur, mais `debut` est pose dessus.
const INSTANT_INITIAL = 1000.0;

// Nombre d'ecarts detailles avant de s'arreter de detailler. Au-dela, tout
// derive du premier et le bruit masque le signal.
const ECARTS_DETAILLES = 5;

/**
 * Le meme releve que `observer()` cote Python, champ pour champ et dans le
 * meme ordre. Les deux doivent etre modifies ensemble : un champ ajoute d'un
 * seul cote n'est pas une erreur bruyante, c'est une verification qui
 * disparait en silence.
 */
function observer(circuit) {
  const bloc = circuit.bloc_actuel;
  const prochain = circuit.prochain_bloc();
  const exercice = circuit.exercice_actuel;
  return {
    phase: circuit.phase,
    index_exercice: circuit.index_exercice,
    serie_actuelle: circuit.serie_actuelle,
    serie_actuelle_locale: circuit.serie_actuelle_locale,
    exercice: exercice === null ? null : exercice.nom,
    bloc: bloc === null ? null : bloc.exercice.nom,
    prochain_bloc: prochain === null ? null : prochain.exercice.nom,
    mode: bloc === null ? null : bloc.mode,
    nombre_series: circuit.nombre_series,
    repetitions_cibles: circuit.repetitions_cibles,
    poids: circuit.poids,
    temps_restant: Math.round(circuit.temps_restant * 1000) / 1000,
    duree_totale: circuit.duree_totale,
    dans_echauffement: circuit.dans_echauffement,
    blocs_comptabilises: circuit.blocs_comptabilises.map((b) => b.exercice.nom),
    series_terminees: circuit.series_terminees,
    nombre_series_total: circuit.nombre_series_total,
    blocs_echauffement: circuit.blocs_echauffement.map((b) => b.exercice.nom),
    nombre_series_echauffement: circuit.nombre_series_echauffement,
    series_echauffement_terminees: circuit.series_echauffement_terminees,
    peut_refaire: circuit.peut_refaire_derniere_serie(),
    // Voir le commentaire jumeau cote Python : observer la cause plutot que
    // d'attendre que son effet remonte a la surface.
    entrelace_en_cours:
      circuit._exercice_precedent_entrelace === null
        ? null
        : { ...circuit._exercice_precedent_entrelace },
    repere_derniere_serie:
      circuit._derniere_serie_terminee === null
        ? null
        : {
            index_exercice: circuit._derniere_serie_terminee.index_exercice,
            serie: circuit._derniere_serie_terminee.serie,
            entrelace: circuit._derniere_serie_terminee.entrelace,
          },
    resultats: circuit.resultats_series.length,
    a_des_resultats: circuit.a_des_resultats(),
  };
}

/**
 * Construit le circuit comme `construire_circuit` cote Python, mais sans
 * catalogue : le harnais compare la machine a etats, pas la validation des
 * noms d'exercices. Un exercice se reduit donc a son nom, seule chose que
 * `observer` en lit.
 */
function circuit_pour(blocs, horloge, catalogue) {
  const circuit = new Circuit(
    blocs.map(
      (bloc) =>
        new BlocExercice({
          exercice: catalogue[bloc.exercice],
          poids: bloc.poids ?? 0,
          mode: bloc.mode ?? MODE_REPETITIONS,
          nombre_series: bloc.series ?? 1,
          repetitions_par_serie: bloc.repetitions ?? 0,
          duree: bloc.duree ?? 0,
          repos_entre_series: bloc.repos_entre_series ?? 0,
          repos_apres: bloc.repos_apres ?? 0,
          commentaire: bloc.commentaire ?? "",
          entrelace_avec: bloc.entrelace_avec ?? null,
          cible_manuelle: bloc.cible_manuelle ?? false,
        })
    )
  );
  circuit.maintenant = () => horloge.t;
  circuit.debut = horloge.t;
  return circuit;
}

/**
 * Le catalogue JS : nom d'exercice vers un `Exercice` porteur de sa detection
 * et de ses verifications de forme, retrouvees dans `detections.js` par leur
 * nom.
 */
function catalogue_pour(fiches) {
  const table = {};
  for (const fiche of Object.values(fiches)) {
    table[fiche.nom] = new Exercice({
      nom: fiche.nom,
      detection: DETECTIONS[fiche.detection] ?? null,
      description: fiche.description,
      instructions: fiche.instructions,
      mise_en_place: fiche.mise_en_place,
      erreurs_frequentes: fiche.erreurs_frequentes,
      erreurs: (fiche.erreurs ?? []).map((nom) => DETECTIONS[nom]),
      variante_facile: fiche.variante_facile,
      variante_difficile: fiche.variante_difficile,
    });
  }
  return table;
}

/** Meme contrat que `jouer()` cote Python : une exception est une donnee. */
function jouer(circuit, horloge, nom, arguments_, boucle, banque) {
  if (nom === "avancer") {
    horloge.t += arguments_.secondes;
    return [null, null];
  }
  if (nom === "image") {
    // Meme garde que `main.py` : les modes ne tournent que pendant la phase
    // « exercice » et sur un bloc existant.
    if (circuit.phase !== "exercice" || circuit.bloc_actuel === null) {
      return [null, null];
    }
    const corps = banque[arguments_.pose];
    let triplet;
    try {
      triplet = executer_mode({
        seance: circuit,
        corps,
        compteur: boucle.compteur,
        etat: boucle.etat,
        coach: boucle.coach,
        derniere_rep: boucle.derniere_rep,
        messages: { texte, libelle_etape },
      });
    } catch (erreur) {
      return [null, erreur.constructor.name];
    }
    boucle.derniere_rep = triplet[0];
    if (triplet[2]) {
      boucle.compteur.reset();
      boucle.derniere_rep = 0;
    }
    return [triplet, null];
  }

  if (nom === "aller_au_superset") {
    // Commande du harnais, pas du circuit — jumelle de celle du Python.
    for (let i = 0; i < circuit.exercices.length; i++) {
      if (circuit.bloc_actuel === null || circuit._est_entrelace(circuit.index_exercice)) break;
      circuit.passer_exercice_suivant();
    }
    return [null, null];
  }
  let resultat;
  try {
    resultat =
      Object.keys(arguments_).length > 0
        ? circuit[nom](arguments_)
        : circuit[nom]();
  } catch (erreur) {
    return [null, erreur.constructor.name];
  }
  if (
    resultat === null ||
    resultat === undefined ||
    ["boolean", "number", "string"].includes(typeof resultat)
  ) {
    // Python rend None la ou JavaScript rend undefined : on ramene les deux au
    // meme, sinon chaque methode sans retour compterait pour un ecart.
    return [resultat === undefined ? null : resultat, null];
  }
  return [resultat.constructor.name, null];
}

// Jumeau de CHAMPS_ETAT cote Python : la surface verifiee du portage de
// `moteur.js`. Les deux listes se modifient ensemble.
const CHAMPS_ETAT = [
  "mode", "stage", "etape_libelle", "erreur", "repetitions",
  "temps_maintien", "duree_maintien", "temps_chrono", "chrono_termine",
  "temps_echauffement", "duree_echauffement", "temps_amrap_restant",
  "prochaine_etape", "fiche_suivante",
];

function observer_etat(etat) {
  const releve = {};
  for (const champ of CHAMPS_ETAT) {
    const valeur = etat[champ];
    // Meme arrondi que cote Python : deux langages ne s'accordent pas au
    // dernier bit sur un flottant accumule image par image.
    releve[champ] =
      typeof valeur === "number" && !Number.isInteger(valeur)
        ? Math.round(valeur * 1e6) / 1e6
        : valeur;
  }
  return releve;
}

function comparer(attendu, obtenu) {
  const ecarts = [];
  for (const champ of Object.keys(attendu)) {
    const a = JSON.stringify(attendu[champ]);
    const b = JSON.stringify(obtenu[champ]);
    if (a !== b) ecarts.push({ champ, attendu: a, obtenu: b });
  }
  return ecarts;
}

function main() {
  const texte_des_seances = readFileSync(SEANCES, "utf-8");
  const seances = JSON.parse(texte_des_seances);
  const catalogue = catalogue_pour(JSON.parse(readFileSync(CATALOGUE, "utf-8")));
  const banque = readFileSync(POSES, "utf-8")
    .split("\n")
    .filter((ligne) => ligne.trim())
    .map((ligne) => construire_corps(JSON.parse(ligne)));
  const pas = readFileSync(FIXTURES, "utf-8")
    .split("\n")
    .filter((ligne) => ligne.trim())
    .map((ligne) => JSON.parse(ligne));

  // Les seances sont reecrites a chaque fin de seance jouee : des fixtures
  // generees avant produiraient un diff authentique et trompeur. On le dit
  // plutot que de laisser chercher.
  const empreinte = createHash("sha256")
    // Voir le commentaire jumeau cote Python : sans ce nettoyage, les fins de
    // ligne suffisent a faire diverger deux empreintes du meme contenu.
    .update(texte_des_seances.replaceAll("\r", ""), "utf-8")
    .digest("hex")
    .slice(0, 16);
  if (pas[0]?.empreinte_seances && pas[0].empreinte_seances !== empreinte) {
    console.log(
      "Les seances ont change depuis la generation des fixtures.\n" +
        "Relance : python -m scripts.generer_scenarios"
    );
    process.exitCode = 1;
    return;
  }

  let circuit = null;
  let horloge = null;
  let boucle = null;
  let cle_courante = null;
  let compares = 0;
  let valeurs = 0;
  let images = 0;
  const echecs = [];

  for (const ligne of pas) {
    const cle = `${ligne.seance} / ${ligne.scenario}`;
    if (cle !== cle_courante) {
      horloge = { t: INSTANT_INITIAL };
      circuit = circuit_pour(seances[ligne.seance], horloge, catalogue);
      // Le compteur, l'etat et `derniere_rep` survivent d'une image a l'autre
      // et d'une serie a l'autre, comme dans la boucle camera : les recreer a
      // chaque pas masquerait la moitie de ce que le moteur doit gerer.
      const annonces = [];
      boucle = {
        compteur: new CompteurMouvement(),
        etat: creer_etat(),
        annonces,
        coach: (cle_son, valeur = null) => annonces.push([cle_son, valeur]),
        derniere_rep: 0,
      };
      cle_courante = cle;
    }

    const [resultat, erreur] = jouer(
      circuit, horloge, ligne.commande, ligne.arguments, boucle, banque
    );
    const obtenu = observer(circuit);
    const obtenu_etat = observer_etat(boucle.etat);
    const annonces = boucle.annonces.splice(0);
    if (ligne.commande === "image") images += 1;
    compares += 1;
    valeurs += Object.keys(obtenu).length + Object.keys(obtenu_etat).length + 1;

    const ecarts = [
      ...comparer(ligne.etat, obtenu),
      ...comparer(ligne.etat_seance, obtenu_etat),
    ];
    if (JSON.stringify(ligne.annonces) !== JSON.stringify(annonces)) {
      ecarts.push({
        champ: "(annonces du coach)",
        attendu: JSON.stringify(ligne.annonces),
        obtenu: JSON.stringify(annonces),
      });
    }
    if (JSON.stringify(ligne.resultat) !== JSON.stringify(resultat)) {
      ecarts.push({
        champ: "(valeur de retour)",
        attendu: JSON.stringify(ligne.resultat),
        obtenu: JSON.stringify(resultat),
      });
    }
    if (ligne.erreur !== erreur) {
      ecarts.push({
        champ: "(exception)",
        attendu: String(ligne.erreur),
        obtenu: String(erreur),
      });
    }

    if (ecarts.length) echecs.push({ ligne, ecarts });
  }

  console.log(`${compares} pas rejoues (dont ${images} images), ${valeurs} valeurs comparees`);

  if (!echecs.length) {
    console.log("\nAucun ecart : le portage du circuit et du moteur est fidele.");
    return;
  }

  console.log(`
${echecs.length} pas divergent. Les ${ECARTS_DETAILLES} premiers :
`);
  for (const { ligne, ecarts } of echecs.slice(0, ECARTS_DETAILLES)) {
    console.log(`  ${ligne.seance} / ${ligne.scenario} / pas ${ligne.pas}`);
    console.log(`    commande : ${ligne.commande}(${JSON.stringify(ligne.arguments)})`);
    for (const e of ecarts) {
      console.log(`    ${e.champ.padEnd(26)} python=${e.attendu}  js=${e.obtenu}`);
    }
    console.log();
  }
  process.exitCode = 1;
}

main();
