// Rejoue les scenarios figes sur le circuit et le moteur, et signale le
// moindre ecart.
//
// Pendant de `comparer_detections.mjs`, pour une classe qui a de la memoire :
// la ou les detections se comparent pose par pose, un circuit se compare
// **pas a pas sur une histoire**. Un ecart est donc date — il nomme la seance,
// le scenario, le numero de pas et le champ — parce qu'apres une divergence
// tous les pas suivants divergent aussi, et seul le premier renseigne.
//
// Les scenarios melangent une marche aleatoire et des scenarios ecrits
// (`superset_refaire`, `decompte_final`, `pompes_peu_profondes`…) : les etats
// profonds d'une machine a etats sont hors de portee du hasard. Les commandes
// sont des entrees figees ; seuls les etats releves sont reecrits par
// `--mettre-a-jour`.
//
// Usage : node scripts/comparer_seances.mjs [--mettre-a-jour]

import { Circuit, BlocExercice, Exercice, MODE_REPETITIONS } from "../web/static/js/circuit.js";
import { DETECTIONS } from "../web/static/js/detections.js";
import { amplitude_pour } from "../web/static/js/seance.js";
import { construire_corps } from "../web/static/js/landmarks.js";
import { CompteurMouvement } from "../web/static/js/compteur.js";
import { creer_etat } from "../web/static/js/etat.js";
import { ajuster_repetitions, executer_mode, oublier_durees } from "../web/static/js/moteur.js";
import { texte, libelle_etape } from "../web/static/js/messages.js";
import { Releve, lire_json, lire_lignes } from "./fixtures.mjs";

// Le catalogue fige (`catalogue_seances.json`) donne, pour chaque exercice, le
// *nom* de sa fonction de detection et celui de ses verifications de forme.
// Les fonctions elles-memes vivent dans `detections.js` et portent les memes
// noms — c'est ce qui evite une table de correspondance a maintenir. Il
// contient les echauffements, que les donnees de l'application listent aussi.

// Les instants sont releves en *ecart* depuis cette valeur, mais `debut` est
// pose dessus : la changer decalerait toutes les reponses figees.
const INSTANT_INITIAL = 1000.0;

/**
 * La surface verifiee du circuit. **Le levier principal de ce test est le
 * nombre de champs releves ici**, bien avant le nombre de pas : un champ
 * ajoute est signale au premier passage, puis fige par `--mettre-a-jour`.
 * On y releve aussi des etats internes (`_exercice_precedent_entrelace`,
 * `_derniere_serie_terminee`) : observer la cause vaut mieux qu'attendre que
 * son effet remonte a la surface.
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
            exercice: circuit._derniere_serie_terminee.exercice,
            entrelace: circuit._derniere_serie_terminee.entrelace,
          },
    resultats: circuit.resultats_series.length,
    a_des_resultats: circuit.a_des_resultats(),
    // Sans le nom par serie, la serie 1 de la variante ecraserait en silence
    // celle de l'original.
    variante_possible: circuit.variante_possible(),
    remplace: bloc === null ? null : bloc.remplace,
    abandons: bloc === null ? null : bloc.abandons.map((a) => ({ ...a })),
    resultats_detail: circuit.resultats_series.map((r) => [
      r.index_exercice, r.serie, r.exercice ?? null, r.completee,
    ]),
  };
}

/**
 * Construit le circuit sans validation : le test porte sur la machine a
 * etats, pas sur la validation des noms d'exercices (`problemes_des_blocs`).
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
      sensations: fiche.sensations ?? [],
      erreurs: (fiche.erreurs ?? []).map((nom) => DETECTIONS[nom]),
      variante_facile: fiche.variante_facile,
      variante_difficile: fiche.variante_difficile,
      orientation: fiche.orientation ?? null,
      amplitude: amplitude_pour(fiche.amplitude),
      changements: fiche.changements ?? [],
    });
  }
  return table;
}

/** Joue une commande. Une exception est une donnee relevee, pas un incident. */
function jouer(circuit, horloge, nom, arguments_, boucle, banque) {
  if (nom === "avancer") {
    horloge.t += arguments_.secondes;
    return [null, null];
  }
  if (nom === "image") {
    // Meme garde que la boucle de l'application : les modes ne tournent que
    // pendant la phase « exercice » et sur un bloc existant.
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

  if (nom === "ajuster") {
    // Le garde est dans la fonction : elle n'agit qu'en exercice.
    boucle.derniere_rep = ajuster_repetitions({
      seance: circuit,
      compteur: boucle.compteur,
      etat: boucle.etat,
      coach: boucle.coach,
      delta: arguments_.delta,
      derniere_rep: boucle.derniere_rep,
    });
    return [boucle.derniere_rep, null];
  }

  if (nom === "aller_a_l_amplitude") {
    // Commande du test : premier bloc qui verifie une amplitude.
    for (let i = 0; i < circuit.exercices.length; i++) {
      const bloc = circuit.bloc_actuel;
      if (bloc === null || bloc.exercice.amplitude !== null) break;
      circuit.passer_exercice_suivant();
    }
    return [null, null];
  }
  if (nom === "variante") {
    // Un refus est releve sous un nom fixe plutot que par sa classe
    // d'exception.
    const attendu = circuit.variante_possible();
    const exercice = attendu ? boucle.catalogue[attendu] ?? null : null;
    try {
      circuit.passer_a_la_variante(exercice, arguments_);
    } catch {
      return ["refus", null];
    }
    boucle.compteur.reset();
    boucle.derniere_rep = 0;
    oublier_durees(boucle.etat);
    return [attendu, null];
  }
  if (nom === "aller_a_un_changement") {
    // Commande du test : va au bloc qui annonce le plus de changements.
    let meilleur = 0;
    let plus = 0;
    circuit.exercices.forEach((bloc, index) => {
      if ((bloc.exercice.changements ?? []).length > plus) {
        meilleur = index;
        plus = bloc.exercice.changements.length;
      }
    });
    for (let i = 0; i < meilleur; i++) circuit.passer_exercice_suivant();
    return [null, null];
  }
  if (nom === "aller_a_une_variante") {
    for (let i = 0; i < circuit.exercices.length; i++) {
      const bloc = circuit.bloc_actuel;
      if (bloc === null || bloc.exercice.variante_facile) break;
      circuit.passer_exercice_suivant();
    }
    return [null, null];
  }
  if (nom === "aller_au_superset") {
    // Commande du test, pas du circuit : pilotee par les donnees, pour qu'un
    // superset deplace ne rende pas le scenario muet sans prevenir.
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
    // `undefined` n'existe pas en JSON : une methode sans retour est relevee
    // comme null.
    return [resultat === undefined ? null : resultat, null];
  }
  return [resultat.constructor.name, null];
}

// La surface verifiee de `moteur.js`.
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
    // Arrondi au millionieme : un flottant accumule image par image ne doit
    // pas faire changer une reponse figee pour son dernier bit.
    releve[champ] =
      typeof valeur === "number" && !Number.isInteger(valeur)
        ? Math.round(valeur * 1e6) / 1e6
        : valeur;
  }
  return releve;
}

function main() {
  const seances = lire_json("donnees/seances_personnalisees.json");
  const catalogue = catalogue_pour(lire_json("catalogue_seances.json"));
  const banque = lire_lignes("poses_seances").map((pose) => construire_corps(pose));
  const pas = lire_lignes("seances");

  let circuit = null;
  let horloge = null;
  let boucle = null;
  let cle_courante = null;
  let compares = 0;
  let images = 0;
  const releve = new Releve();

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
        catalogue,
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

    const ou = `${ligne.seance} / ${ligne.scenario} / pas ${ligne.pas} ` +
      `${ligne.commande}(${JSON.stringify(ligne.arguments)})`;
    for (const champ of Object.keys(obtenu)) {
      releve.verifier(`${ou} / ${champ}`, ligne.etat, champ, obtenu[champ]);
    }
    for (const champ of Object.keys(obtenu_etat)) {
      releve.verifier(`${ou} / etat.${champ}`, ligne.etat_seance, champ, obtenu_etat[champ]);
    }
    releve.verifier(`${ou} / annonces du coach`, ligne, "annonces", annonces);
    releve.verifier(`${ou} / valeur de retour`, ligne, "resultat", resultat);
    releve.verifier(`${ou} / exception`, ligne, "erreur", erreur);
  }

  console.log(
    `${compares} pas rejoues (dont ${images} images), ${releve.comparaisons} valeurs comparees`
  );
  releve.conclure({
    fichier: "seances",
    lignes: pas,
    succes: "Aucun ecart : le circuit et le moteur rendent les reponses figees.",
    detail: 5,
  });
}

main();
