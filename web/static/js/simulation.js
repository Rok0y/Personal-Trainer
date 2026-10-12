// Le simulateur de progression : ou chaque exercice demarre, et ce qu'il
// demande seance apres seance a quelqu'un qui reussit toujours.
//
// `dev/progression.html` l'affiche, `scripts/verifier_simulation.mjs` le
// rejoue. Pas de modele d'athlete : l'athlete virtuel **reussit toujours, sans
// rien repondre**. Chaque seance le fait donc monter d'un palier, et son
// parcours est le bareme lu palier apres palier depuis le depart de sa note —
// avec les changements de variante (mur -> inclinees -> genoux -> pompes,
// squat a vide -> squat charge) la ou le moteur les fait. Ce qu'on y cherche,
// c'est un palier qui demande **moins** que le precedent.
//
// **Rien ici n'est une regle de l'application.** Le moteur est celui de
// `construire_progression`, le mouvement de depart vient de
// `variantes_en_cours`, les seances s'ecrivent et se relisent par
// `historique.js`, les resultats sortent de `resultats_par_exercice`, les
// montees de `Variantes.montees`. Le simulateur ne fait que jouer le role de
// la personne devant l'ecran.
//
// Tout est deterministe : deux simulations des memes reglages rendent la meme
// chose, et une courbe qui change ne peut venir que du moteur ou des reglages.

import { construire_progression, variantes_en_cours } from "./progression.js";
import {
  base_vide,
  creer_utilisateur,
  definir_note_athlete,
  definir_variantes,
  enregistrer_seance,
  recuperer_ancrages,
  recuperer_historique,
} from "./historique.js";
import { circuit_pour, exercice_pour, resultats_par_exercice } from "./seance.js";
import { catalogue_depuis, chaine, normaliser as normaliser_variantes } from "./variantes.js";
import { note_du_profil, note_valide } from "./calibration.js";
import { UNITE_SECONDES } from "./paliers.js";
import { MODE_MAINTIEN, MODE_REPETITIONS } from "./circuit.js";

/**
 * Les profils de materiel a comparer. Les accessoires sont tous coches : ils
 * ne changent aucun bareme, seulement les avertissements d'une fiche.
 */
export function profils_materiel(tables) {
  const accessoires = Object.keys(tables.accessoires ?? {});
  const complet = {};
  for (const poids of tables.echelles.reference) complet[poids] = 2;
  return [
    { cle: "aucun", libelle: "Aucun haltère", materiel: { halteres: {}, accessoires } },
    { cle: "paire_5", libelle: "Une paire de 5 kg", materiel: { halteres: { 5: 2 }, accessoires } },
    {
      cle: "lourds",
      libelle: "Paires de 10, 12 et 13 kg",
      materiel: { halteres: { 10: 2, 12: 2, 13: 2 }, accessoires },
    },
    { cle: "un_seul", libelle: "Un seul haltère de 10 kg", materiel: { halteres: { 10: 1 }, accessoires } },
    { cle: "complet", libelle: "Set complet", materiel: { halteres: complet, accessoires } },
    // `null` et non un inventaire : c'est ce que porte un profil qui n'a
    // jamais repondu au questionnaire, et `Baremes` le traduit lui-meme.
    { cle: "muet", libelle: "Profil muet (matériel supposé)", materiel: null },
  ];
}

/**
 * Un inventaire depuis une saisie libre : « 5x2 8x2 10x1 ». Un poids sans
 * quantite vaut une paire ; la virgule decimale est acceptee (« 2,5x2 »).
 * Les separateurs sont les espaces, « ; » et « + ». Rend `{materiel,
 * illisibles}` : `materiel` null sur une saisie vide, et la liste des
 * morceaux illisibles a part pour que la page puisse les signaler.
 */
export function inventaire_depuis_texte(texte, tables) {
  const morceaux = String(texte ?? "").trim().split(/[\s;+]+/).filter(Boolean);
  if (!morceaux.length) return { materiel: null, illisibles: [] };
  const halteres = {};
  const illisibles = [];
  for (const morceau of morceaux) {
    const trouve = /^(\d+(?:[.,]\d+)?)(?:\s*[x×*]\s*(\d+))?$/i.exec(morceau);
    if (!trouve) {
      illisibles.push(morceau);
      continue;
    }
    const poids = Number(trouve[1].replace(",", "."));
    halteres[poids] = (halteres[poids] ?? 0) + (trouve[2] ? Number(trouve[2]) : 2);
  }
  return {
    materiel: { halteres, accessoires: Object.keys(tables.accessoires ?? {}) },
    illisibles,
  };
}

/**
 * Les familles du catalogue : chaque mouvement suivi par le moteur qui n'a
 * pas de variante plus dure, avec sa chaine **du plus facile au plus dur**.
 * Un exercice sans variante est une famille d'un seul mouvement.
 *
 * Derivees des variantes et non listees : une chaine ajoutee a
 * `mouvements.json` apparait d'elle-meme.
 */
export function familles(catalogue, baremes) {
  return Object.keys(catalogue)
    .filter((nom) => {
      const dur = catalogue[nom].variante_difficile;
      return baremes.est_suivi_par_le_moteur(nom) && !(dur && dur in catalogue);
    })
    .sort((a, b) => a.localeCompare(b, "fr"))
    .map((tete) => ({
      tete,
      mouvements: chaine(tete, catalogue).reverse().filter((nom) => baremes.est_suivi_par_le_moteur(nom)),
    }));
}

/**
 * Le volume d'un palier, **dans l'unite de la tete de sa famille**, pour que
 * toute la chaine tienne sur une meme courbe.
 *
 * Une forme a vide d'un mouvement charge (le squat a vide sous le squat
 * charge) se traduit par la part du corps (`equivalence_a_vide`), la meme
 * traduction que le moteur fait pour le seuil et l'entree. Les variantes sans
 * charge (les pompes) sont toutes en repetitions : rien a traduire.
 */
export function volume_comparable(baremes, famille, nom, palier) {
  if (!palier) return null;
  const part = nom === famille.tete ? null : baremes.equivalence_a_vide(nom, famille.tete);
  if (part !== null) return baremes.volume(palier.series, palier.cible, 0, part);
  return baremes.volume_exercice(nom, palier.series, palier.cible, palier.poids);
}

/** Un palier sans ce qui ne s'affiche pas. */
function palier_lisible(palier) {
  return palier
    ? { niveau: palier.niveau, poids: palier.poids, series: palier.series, cible: palier.cible, unite: palier.unite }
    : null;
}

/** Le mode qui joue un mouvement dans l'unite de son bareme. */
function mode_de(nom, baremes) {
  return baremes.unite(nom) === UNITE_SECONDES ? MODE_MAINTIEN : MODE_REPETITIONS;
}

/**
 * Ce que propose une premiere seance, pour chaque note de 1 a 10.
 *
 * Lu par les fonctions memes de l'application sur un profil neuf — le
 * mouvement par `variantes_en_cours` puis `substitution`, son palier par
 * `objectifs_par_exercice` —, et non par un calcul voisin. Rend, note par
 * note, une entree par famille : `{tete, joue, palier, volume}`.
 */
export function departs({ tables, mouvements, materiel, choisies }) {
  const catalogue = catalogue_depuis(mouvements);
  const moteur = construire_progression(tables, materiel, catalogue);
  const par_note = [];
  for (let note = 1; note <= 10; note += 1) {
    const lecture = { seances: [], ancrages: {}, note: { declaree: note, relevee_apres: null } };
    const objectifs = moteur.objectifs.objectifs_par_exercice(lecture.seances, lecture.ancrages, lecture.note);
    const table = variantes_en_cours(moteur, {}, lecture, catalogue);
    par_note.push(choisies.map((famille) => {
      const joue = moteur.variantes.substitution(famille.tete, mode_de(famille.tete, moteur.baremes), table, catalogue)
        ?? famille.tete;
      const palier = objectifs[joue] ?? null;
      return {
        tete: famille.tete,
        joue,
        palier: palier_lisible(palier),
        volume: volume_comparable(moteur.baremes, famille, joue, palier),
      };
    }));
  }
  return par_note;
}

//: Le premier jour simule : la date n'entre dans aucun calcul de
//: progression, mais l'historique l'enregistre et une date fixe garde la
//: simulation deterministe.
const DEBUT = Date.UTC(2026, 0, 5, 18, 0);
const JOUR = 24 * 3600 * 1000;

/**
 * Le parcours d'une famille sur `seances` seances, pour quelqu'un de cette
 * note qui reussit toujours sans rien repondre.
 *
 * Chaque tour suit le chemin de l'application : objectifs relus sur tout
 * l'historique, mouvement de depart ecrit au premier demarrage, variantes du
 * profil appliquees au circuit, toutes les series menees a la cible, seance
 * ecrite dans une base en memoire, montees de variante. Une famille par
 * simulation : un athlete qui reussit tout ne fait dependre un exercice
 * d'aucun autre, et l'historique reste court.
 *
 * Rend un point par seance : `{n, joue, palier, volume, niveau, evenement}`.
 */
export function parcours({ tables, mouvements, materiel, famille, note, seances = 60 }) {
  const catalogue = catalogue_depuis(mouvements);
  const moteur = construire_progression(tables, materiel, catalogue);
  const { baremes } = moteur;

  let jour = 0;
  const maintenant = () => new Date(DEBUT + jour * 2 * JOUR);
  const base = base_vide();
  const { id: uid } = creer_utilisateur(base, "Athlète simulé", maintenant);
  const profil = base.utilisateurs.find((u) => u.id === uid);
  profil.materiel = materiel ?? null;
  if (note_valide(note)) definir_note_athlete(base, uid, note);

  const points = [];
  for (let n = 0; n < seances; n += 1, jour += 1) {
    const histoire = recuperer_historique(base, uid);
    const ancrages = recuperer_ancrages(base, uid);
    const lecture = { seances: histoire, ancrages, note: note_du_profil(profil) };
    const objectifs = moteur.objectifs.objectifs_par_exercice(histoire, ancrages, lecture.note);

    // Comme `demarrer` : le mouvement de depart d'une famille jamais jouee
    // est ecrit sur le profil avant de jouer.
    const variantes = variantes_en_cours(moteur, profil.variantes, lecture, catalogue);
    if (JSON.stringify(variantes) !== JSON.stringify(normaliser_variantes(profil.variantes))) {
      definir_variantes(base, uid, variantes);
    }
    // Une seance d'un bloc nommant la tete : les seances ecrites nomment la
    // forme la plus dure. Les valeurs de remplissage sont reecrites par le
    // moteur.
    const circuit = circuit_pour(mouvements, [{
      exercice: famille.tete, mode: mode_de(famille.tete, baremes),
      series: 1, repetitions: 1, duree: 1, repos_entre_series: 0, repos_apres: 0,
    }]);
    moteur.variantes.appliquer_au_circuit(circuit, variantes, catalogue, (nom) => exercice_pour(mouvements, nom));
    moteur.objectifs.appliquer_a_circuit(circuit, objectifs, uid);

    const bloc = circuit.exercices[0];
    const joue = bloc.exercice.nom;
    const en_secondes = baremes.unite(joue) === UNITE_SECONDES;
    for (let k = 0; k < bloc.nombre_series; k += 1) {
      circuit.resultats_series.push({
        index_exercice: 0,
        exercice: joue,
        serie: k + 1,
        repetitions: en_secondes ? 0 : bloc.repetitions_par_serie,
        duree: en_secondes ? bloc.duree : 0,
        completee: true,
      });
    }
    const resultats = resultats_par_exercice(circuit);
    enregistrer_seance(base, {
      duree: 0, exercices: resultats, statut: "finished", nom_seance: "Simulation", utilisateur_id: uid, maintenant,
    });

    // Les montees se font d'elles-memes en fin de seance ; l'athlete
    // virtuel ne touche jamais « Rester sur… ».
    let evenement = null;
    const [montee, faites] = moteur.variantes.montees(
      profil.variantes, { statut: "finished", exercices: resultats }, catalogue,
    );
    if (faites.length) {
      definir_variantes(base, uid, montee);
      evenement = { sens: "montée", depuis: faites[0].depuis, vers: faites[0].vers };
    }

    const palier = objectifs[joue] ?? null;
    points.push({
      n: n + 1,
      joue,
      palier: palier_lisible(palier),
      volume: volume_comparable(baremes, famille, joue, palier),
      // Ce que la seance a prouve. L'athlete reussissant tout, c'est aussi
      // son record : relire tout l'historique pour l'afficher doublait le
      // temps de calcul.
      niveau: moteur.niveaux.niveau_prouve_par(resultats[0]),
      evenement,
    });
  }
  return points;
}

/**
 * Les baisses de volume d'une suite de points (`{volume}`), dans l'ordre :
 * `[{index, avant, apres, part}]`, `part` etant la baisse en part du volume
 * precedent. C'est ce que la page signale et ce qu'on corrige a la main.
 */
export function baisses(points) {
  const trouvees = [];
  for (let i = 1; i < points.length; i += 1) {
    const avant = points[i - 1].volume;
    const apres = points[i].volume;
    if (avant > 0 && apres !== null && apres < avant) {
      trouvees.push({ index: i, avant: points[i - 1], apres: points[i], part: apres / avant - 1 });
    }
  }
  return trouvees;
}
