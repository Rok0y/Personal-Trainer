// Le simulateur de progression : des profils de materiel et des athletes
// virtuels, joues sur **le vrai moteur**.
//
// `dev/progression.html` l'affiche, `scripts/verifier_simulation.mjs` le
// rejoue. La question est « la progression est-elle bonne pour tout le
// monde ? » — un debutant sans halteres, quelqu'un qui n'a que des 10 kg —,
// et elle ne se juge pas sur les parametres du bareme, seulement sur ce qu'il
// propose seance apres seance.
//
// **Rien ici n'est une regle de l'application.** Le moteur est celui de
// `construire_progression`, les seances s'ecrivent et se relisent par
// `historique.js`, les resultats sortent de `resultats_par_exercice`, les
// montees et descentes de variante de `Variantes`. Le simulateur ne fait que
// jouer le role de la personne devant l'ecran.
//
// Ce qui lui est propre, c'est **le modele de l'athlete** (`HYPOTHESES`) : la
// part du poids du corps que deplace chaque mouvement, la fatigue d'une serie
// a l'autre, la formule d'Epley qui relie charge et repetitions. Ce sont des
// hypotheses de test, affichees et modifiables sur la page, et l'application
// n'en lit aucune. Elles servent a deux choses : faire reussir ou echouer
// l'athlete virtuel, et exprimer ce qu'une seance exige dans **une seule
// unite** (le 1RM estime, en kg) — la seule facon de comparer un squat a vide
// et un squat a 10 kg, ou des pompes contre le mur et des vraies pompes.
//
// Tout est deterministe : deux simulations des memes reglages rendent la meme
// chose, et une courbe qui change ne peut venir que du moteur ou des reglages.

import { construire_progression, variantes_en_cours } from "./progression.js";
import {
  base_vide,
  creer_utilisateur,
  definir_note_athlete,
  definir_variantes,
  enregistrer_ressentis,
  enregistrer_seance,
  recuperer_ancrages,
  recuperer_historique,
} from "./historique.js";
import { circuit_pour, exercice_pour, resultats_par_exercice } from "./seance.js";
import { catalogue_depuis, chaine, normaliser as normaliser_variantes } from "./variantes.js";
import { note_du_profil, note_valide } from "./calibration.js";
import { ECHELLE } from "./ressenti.js";
import { UNITE_SECONDES } from "./paliers.js";
import { MODE_MAINTIEN, MODE_REPETITIONS } from "./circuit.js";

//: Le modele de l'athlete virtuel, et lui seul.
//:
//: `parts_du_corps` : la part du poids du corps que deplace chaque mouvement.
//: L'ordre compte plus que les valeurs : il doit suivre celui des chaines de
//: variantes (le mur avant les inclinees, les inclinees avant les genoux),
//: sinon l'athlete virtuel trouverait une variante « facile » plus dure que
//: celle du dessus.
//:
//: `fatigue_par_serie` : ce que chaque serie retire a la suivante, repos
//: compris. `secondes_par_repetition` traduit un maintien en repetitions,
//: pour qu'un gainage passe par la meme formule.
//:
//: Les trois derniers decident du ressenti : une marge de 25 % au-dessus de
//: la cible sur la serie la plus dure fait dire « facile », 50 % « trop
//: facile » ; un echec sous 70 % de ce qui etait demande fait dire « trop
//: dur ».
export const HYPOTHESES = {
  parts_du_corps: {
    "Pompes contre le mur": 0.25,
    "Pompes inclinées": 0.45,
    "Pompes sur les genoux": 0.5,
    Pompes: 0.65,
    "Squat sur chaise": 0.55,
    Squat: 0.7,
    "Squat chargé": 0.7,
    "Fente droite": 0.8,
    "Fente droite chargée": 0.8,
    "Fente gauche": 0.8,
    "Fente gauche chargée": 0.8,
    "Gainage sur les genoux": 0.35,
    "Gainage planche": 0.6,
  },
  fatigue_par_serie: 0.08,
  secondes_par_repetition: 2,
  marge_facile: 1.25,
  marge_trop_facile: 1.5,
  part_trop_dur: 0.7,
};

//: Des athletes types. `capacites` donne, pour un mouvement de chaque
//: famille, ce qu'il tient **en une serie au poids du corps** (repetitions,
//: ou secondes pour un maintien) : c'est un nombre qu'on sait estimer pour
//: quelqu'un, contrairement a une force en kilos. La cle est un mouvement et
//: non une famille, pour survivre au renommage de la tete d'une chaine.
//:
//: `progression` est la part de l'ecart au plafond comblee a chaque seance :
//: des progres rapides au debut, qui ralentissent. `plafond` borne la force
//: atteignable, en multiple de la force de depart.
//:
//: Les deux derniers ont la force de l'un et la note de l'autre : c'est ce
//: qui arrive quand quelqu'un se juge mal a l'accueil.
export const ATHLETES = [
  {
    cle: "debutant",
    libelle: "Débutant",
    note: 1,
    poids_corps: 75,
    progression: 0.04,
    plafond: 2.5,
    accepte_descente: true,
    capacites: { Pompes: 1, Squat: 12, "Fente droite": 6, "Fente gauche": 6, "Gainage planche": 20 },
  },
  {
    cle: "intermediaire",
    libelle: "Intermédiaire",
    note: 4,
    poids_corps: 75,
    progression: 0.03,
    plafond: 1.8,
    accepte_descente: true,
    capacites: { Pompes: 12, Squat: 30, "Fente droite": 15, "Fente gauche": 15, "Gainage planche": 60 },
  },
  {
    cle: "confirme",
    libelle: "Confirmé",
    note: 7,
    poids_corps: 75,
    progression: 0.02,
    plafond: 1.4,
    accepte_descente: true,
    capacites: { Pompes: 35, Squat: 60, "Fente droite": 30, "Fente gauche": 30, "Gainage planche": 150 },
  },
  {
    cle: "sous_estime",
    libelle: "Intermédiaire qui se note 1",
    note: 1,
    poids_corps: 75,
    progression: 0.03,
    plafond: 1.8,
    accepte_descente: true,
    capacites: { Pompes: 12, Squat: 30, "Fente droite": 15, "Fente gauche": 15, "Gainage planche": 60 },
  },
  {
    cle: "surestime",
    libelle: "Débutant qui se note 6",
    note: 6,
    poids_corps: 75,
    progression: 0.04,
    plafond: 2.5,
    accepte_descente: true,
    capacites: { Pompes: 1, Squat: 12, "Fente droite": 6, "Fente gauche": 6, "Gainage planche": 20 },
  },
];

const OK = { reussi: true, ressenti: null };
const RATE = { reussi: false, ressenti: null };

//: Des suites de verdicts ecrites a la main, sans modele de force : elles
//: montrent la mecanique pure du moteur, cas par cas. `issue(n)` rend le
//: verdict de la seance n (a partir de 0).
export const SCENARIOS = [
  { cle: "reussi", libelle: "Toujours réussi, sans réponse", issue: () => OK },
  { cle: "facile", libelle: "Toujours réussi, « facile »", issue: () => ({ reussi: true, ressenti: "facile" }) },
  { cle: "trop_facile", libelle: "Toujours réussi, « trop facile »", issue: () => ({ reussi: true, ressenti: "trop_facile" }) },
  { cle: "plateau", libelle: "Réussi 8 fois, puis échoué", issue: (n) => (n < 8 ? OK : RATE) },
  { cle: "alternance", libelle: "Réussi et échoué en alternance", issue: (n) => (n % 2 === 0 ? OK : RATE) },
  {
    cle: "trop_dur",
    libelle: "Réussi 10 fois, puis « trop dur »",
    issue: (n) => (n < 10 ? OK : { reussi: false, ressenti: "trop_dur" }),
  },
];

//: Le comportement qui suit la force cachee de l'athlete, a cote des
//: scenarios ecrits.
export const COMPORTEMENT_CAPACITE = "capacite";

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
 * Les separateurs sont les espaces, « ; » et « + ». Rend null sur une saisie
 * vide, l'inventaire (eventuellement vide) sinon, et la liste des morceaux
 * illisibles a part pour que la page puisse les signaler.
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
    .map((tete) => ({ tete, mouvements: chaine(tete, catalogue).reverse() }));
}

/* ------------------------------------------------------- modele de l'athlete */

/** La force (1RM estime, kg) de qui fait `repetitions` sous `charge` kg (Epley). */
export function force_epley(charge, repetitions) {
  return charge * (1 + Math.max(0, repetitions) / 30);
}

/** Les repetitions qu'une force permet sous une charge, sans fatigue. */
function repetitions_max(force, charge) {
  return Math.max(0, 30 * (force / charge - 1));
}

function part_du_corps(nom, hyp) {
  const part = hyp.parts_du_corps[nom];
  if (!(part > 0)) throw new Error(`Hypothèse manquante : part du corps de « ${nom} »`);
  return part;
}

/** La charge reellement deplacee, en kg : la part du corps et les halteres. */
export function charge_deplacee(nom, poids, baremes, athlete, hyp) {
  const halteres = poids > 0 ? poids * Math.max(1, baremes.nombre_halteres(nom)) : 0;
  return part_du_corps(nom, hyp) * athlete.poids_corps + halteres;
}

/** Une cible dans l'unite de la formule : un maintien passe en repetitions. */
function en_repetitions(cible, unite, hyp) {
  return unite === UNITE_SECONDES ? cible / hyp.secondes_par_repetition : cible;
}

/**
 * Ce qu'un palier exige, en 1RM estime (kg) : la force qui tient toutes ses
 * series, la derniere etant la plus dure. C'est l'unite commune de toutes les
 * courbes du simulateur.
 */
export function exigence(nom, palier, baremes, athlete, hyp) {
  if (!palier) return null;
  const charge = charge_deplacee(nom, palier.poids ?? 0, baremes, athlete, hyp);
  const cible = en_repetitions(palier.cible, palier.unite, hyp);
  const sans_fatigue = cible / (1 - hyp.fatigue_par_serie) ** Math.max(0, palier.series - 1);
  return force_epley(charge, sans_fatigue);
}

/**
 * La force de depart de l'athlete dans une famille, depuis ce qu'il tient au
 * poids du corps sur l'un de ses mouvements. null si aucun ne figure dans
 * ses capacites.
 */
export function force_initiale(famille, athlete, baremes, hyp) {
  const nom = famille.mouvements.find((m) => athlete.capacites?.[m] !== undefined);
  if (nom === undefined) return null;
  const charge = charge_deplacee(nom, 0, baremes, athlete, hyp);
  return force_epley(charge, en_repetitions(athlete.capacites[nom], baremes.unite(nom), hyp));
}

/**
 * Les series qu'un athlete de cette force realise sur un bloc, et ce qu'il
 * en dit. Chaque serie va jusqu'a la cible si la force le permet, s'arrete
 * avant sinon ; la suivante part avec la fatigue en plus.
 */
function executer_par_la_force(bloc, force, baremes, athlete, hyp) {
  const nom = bloc.exercice.nom;
  const unite = baremes.unite(nom);
  const en_secondes = unite === UNITE_SECONDES;
  const cible = en_secondes ? bloc.duree : bloc.repetitions_par_serie;
  const charge = charge_deplacee(nom, bloc.poids, baremes, athlete, hyp);
  const possibles = repetitions_max(force, charge);
  const series = [];
  let derniere_marge = 0;
  for (let k = 0; k < bloc.nombre_series; k += 1) {
    const brut = possibles * (1 - hyp.fatigue_par_serie) ** k;
    const tenu = en_secondes ? brut * hyp.secondes_par_repetition : brut;
    const realise = Math.min(cible, Math.floor(tenu));
    series.push({ realise, completee: realise >= cible });
    derniere_marge = cible > 0 ? tenu / cible : 0;
  }
  const reussi = series.every((s) => s.completee);
  let ressenti = null;
  if (reussi && derniere_marge >= hyp.marge_trop_facile) ressenti = "trop_facile";
  else if (reussi && derniere_marge >= hyp.marge_facile) ressenti = "facile";
  else if (!reussi) {
    const fait = series.reduce((somme, s) => somme + s.realise, 0);
    if (fait < hyp.part_trop_dur * cible * bloc.nombre_series) ressenti = "trop_dur";
  }
  return { series, reussi, ressenti };
}

/**
 * Les series d'un verdict ecrit : tout a la cible, ou la derniere serie
 * manquee de peu. Un « facile » apres un echec n'existe pas a l'ecran : il
 * est ignore ici aussi.
 */
function executer_par_le_scenario(bloc, verdict, baremes) {
  const en_secondes = baremes.unite(bloc.exercice.nom) === UNITE_SECONDES;
  const cible = en_secondes ? bloc.duree : bloc.repetitions_par_serie;
  const manque = en_secondes ? 5 : 1;
  const series = Array.from({ length: bloc.nombre_series }, (_, k) => {
    const rate = !verdict.reussi && k === bloc.nombre_series - 1;
    const realise = rate ? Math.max(0, cible - manque) : cible;
    return { realise, completee: !rate };
  });
  const coherent = verdict.reussi
    ? ["facile", "trop_facile"].includes(verdict.ressenti)
    : verdict.ressenti === "trop_dur";
  return { series, reussi: verdict.reussi, ressenti: coherent ? verdict.ressenti : null };
}

/* ------------------------------------------------------------- simulations */

/** Le mode qui joue un mouvement dans l'unite de son bareme. */
function mode_de(nom, baremes) {
  return baremes.unite(nom) === UNITE_SECONDES ? MODE_MAINTIEN : MODE_REPETITIONS;
}

/** Une seance a un bloc par famille, nommant la tete : les seances ecrites nomment la forme la plus dure. */
function blocs_synthetiques(choisies, baremes) {
  return choisies.map((famille) => ({
    exercice: famille.tete,
    mode: mode_de(famille.tete, baremes),
    // Des valeurs de remplissage : le moteur les reecrit toutes, et un bloc
    // qu'il ne piloterait pas se verrait a sa cible de 1.
    series: 1,
    repetitions: 1,
    duree: 1,
    repos_entre_series: 0,
    repos_apres: 0,
  }));
}

/** Un palier sans ce qui ne s'affiche pas. */
function palier_lisible(palier) {
  return palier
    ? { niveau: palier.niveau, poids: palier.poids, series: palier.series, cible: palier.cible, unite: palier.unite }
    : null;
}

/**
 * Ce que propose une premiere seance, pour chaque note de 1 a 10.
 *
 * Lu par les fonctions memes de l'application sur un profil neuf — le
 * mouvement par `variantes_en_cours` puis `substitution`, son palier par
 * `objectifs_par_exercice` —, et non par `niveau_de_depart` seul : c'est ce
 * que la seance jouerait, pas un calcul voisin. Pour chaque famille : le
 * mouvement joue, son palier et son exigence, puis le depart qu'aurait chacun
 * des mouvements de la chaine.
 */
export function departs({ tables, mouvements, materiel, choisies, athlete, hyp = HYPOTHESES }) {
  const catalogue = catalogue_depuis(mouvements);
  const moteur = construire_progression(tables, materiel, catalogue);
  const par_note = [];
  for (let note = 1; note <= 10; note += 1) {
    const lecture = { seances: [], ancrages: {}, note: { declaree: note, relevee_apres: null } };
    const objectifs = moteur.objectifs.objectifs_par_exercice(lecture.seances, lecture.ancrages, lecture.note);
    const table = variantes_en_cours(moteur, {}, lecture, catalogue);
    par_note.push(
      choisies.map((famille) => {
        const joue = moteur.variantes.substitution(famille.tete, mode_de(famille.tete, moteur.baremes), table, catalogue)
          ?? famille.tete;
        return {
        tete: famille.tete,
        joue,
        palier: palier_lisible(objectifs[joue] ?? null),
        exige: exigence(joue, objectifs[joue] ?? null, moteur.baremes, athlete, hyp),
        chaine: famille.mouvements.map((nom) => ({
          nom,
          palier: palier_lisible(objectifs[nom] ?? null),
          exige: exigence(nom, objectifs[nom] ?? null, moteur.baremes, athlete, hyp),
        })),
        };
      }),
    );
  }
  return par_note;
}

/**
 * Ce qu'un parcours a de remarquable, pour la relecture : le plus gros saut
 * et le plus gros recul de l'exigence d'une seance a la suivante (en part de
 * la precedente), le nombre d'echecs, les changements de variante, et le
 * dernier point. Ne juge rien : c'est a la personne qui relit de dire si un
 * saut de 25 % est trop.
 */
export function bilan(points) {
  let saut = null;
  let recul = null;
  for (let i = 1; i < points.length; i += 1) {
    const avant = points[i - 1].exige;
    const apres = points[i].exige;
    if (!(avant > 0) || !(apres > 0)) continue;
    const part = apres / avant - 1;
    const ecart = { n: points[i].n, avant: points[i - 1], apres: points[i], part };
    if (part > 0 && (saut === null || part > saut.part)) saut = ecart;
    if (part < 0 && (recul === null || part < recul.part)) recul = ecart;
  }
  return {
    saut,
    recul,
    echecs: points.filter((p) => !p.reussi).length,
    montees: points.filter((p) => p.evenement?.sens === "montée").length,
    descentes: points.filter((p) => p.evenement?.sens === "descente").length,
    dernier: points.at(-1) ?? null,
  };
}

//: Le premier jour simule : la date n'entre dans aucun calcul de
//: progression, mais l'historique l'enregistre et une date fixe garde la
//: simulation deterministe.
const DEBUT = Date.UTC(2026, 0, 5, 18, 0);
const JOUR = 24 * 3600 * 1000;

/**
 * Fait vivre un athlete `seances` fois sur un profil de materiel.
 *
 * Chaque tour suit le chemin de l'application : objectifs relus sur tout
 * l'historique, variantes du profil appliquees au circuit, seance jouee par
 * le modele ou le scenario, ecrite dans une base en memoire, ressenti
 * enregistre, montees de variante, puis descente proposee — acceptee si
 * l'athlete le veut, comme un appui sur le bouton.
 *
 * Rend, par famille, un point par seance : le mouvement joue, le palier, ce
 * qu'il exige et la force de l'athlete a ce moment (null sous un scenario),
 * le verdict, et l'evenement de variante s'il y en a eu un.
 */
export function simuler({
  tables,
  mouvements,
  materiel,
  choisies,
  athlete,
  comportement = COMPORTEMENT_CAPACITE,
  seances = 40,
  hyp = HYPOTHESES,
}) {
  const catalogue = catalogue_depuis(mouvements);
  const moteur = construire_progression(tables, materiel, catalogue);
  const { baremes } = moteur;
  const scenario = SCENARIOS.find((s) => s.cle === comportement) ?? null;
  if (comportement !== COMPORTEMENT_CAPACITE && scenario === null) {
    throw new Error(`Comportement inconnu : ${comportement}`);
  }

  let jour = 0;
  const maintenant = () => new Date(DEBUT + jour * 2 * JOUR);
  const base = base_vide();
  const { id: uid } = creer_utilisateur(base, "Athlète simulé", maintenant);
  const profil = base.utilisateurs.find((u) => u.id === uid);
  profil.materiel = materiel ?? null;
  if (note_valide(athlete.note)) definir_note_athlete(base, uid, athlete.note);

  const depart = new Map();
  const force = new Map();
  for (const famille of choisies) {
    const initiale = scenario ? null : force_initiale(famille, athlete, baremes, hyp);
    depart.set(famille.tete, initiale);
    force.set(famille.tete, initiale);
  }
  const traces = choisies.map((famille) => ({
    ...famille,
    force_initiale: depart.get(famille.tete),
    sans_capacite: !scenario && depart.get(famille.tete) === null,
    points: [],
  }));
  // Une famille sans capacite declaree n'est pas jouee plutot que jouee avec
  // une force inventee : la page le dit, au lieu de tracer une courbe fausse.
  const jouees = traces.filter((t) => !t.sans_capacite);
  if (!jouees.length) return traces;

  for (let n = 0; n < seances; n += 1, jour += 1) {
    const histoire = recuperer_historique(base, uid);
    const ancrages = recuperer_ancrages(base, uid);
    const note = note_du_profil(profil);
    const objectifs = moteur.objectifs.objectifs_par_exercice(histoire, ancrages, note);

    // Comme `demarrer` : le mouvement de depart d'une famille jamais jouee
    // est ecrit sur le profil avant de jouer.
    const variantes = variantes_en_cours(moteur, profil.variantes, { seances: histoire, ancrages, note }, catalogue);
    if (JSON.stringify(variantes) !== JSON.stringify(normaliser_variantes(profil.variantes))) {
      definir_variantes(base, uid, variantes);
    }
    const circuit = circuit_pour(mouvements, blocs_synthetiques(jouees, baremes));
    moteur.variantes.appliquer_au_circuit(
      circuit, variantes, catalogue, (nom) => exercice_pour(mouvements, nom),
    );
    moteur.objectifs.appliquer_a_circuit(circuit, objectifs, uid);

    const ressentis = {};
    const issues = circuit.exercices.map((bloc, index) => {
      const tete = jouees[index].tete;
      const issue = scenario
        ? executer_par_le_scenario(bloc, scenario.issue(n), baremes)
        : executer_par_la_force(bloc, force.get(tete), baremes, athlete, hyp);
      const en_secondes = baremes.unite(bloc.exercice.nom) === UNITE_SECONDES;
      issue.series.forEach((serie, k) => {
        circuit.resultats_series.push({
          index_exercice: index,
          exercice: bloc.exercice.nom,
          serie: k + 1,
          repetitions: en_secondes ? 0 : serie.realise,
          duree: en_secondes ? serie.realise : 0,
          completee: serie.completee,
        });
      });
      if (issue.ressenti) ressentis[bloc.exercice.nom] = issue.ressenti;
      return issue;
    });

    const resultats = resultats_par_exercice(circuit);
    const seance_id = enregistrer_seance(base, {
      duree: 0,
      exercices: resultats,
      statut: "finished",
      nom_seance: "Simulation",
      utilisateur_id: uid,
      maintenant,
    });
    enregistrer_ressentis(base, seance_id, ressentis, ECHELLE);

    // Les montees se font d'elles-memes en fin de seance ; l'athlete
    // virtuel ne touche jamais « Rester sur… ».
    const evenements = {};
    const [montee, faites] = moteur.variantes.montees(
      profil.variantes, { statut: "finished", exercices: resultats }, catalogue,
    );
    if (faites.length) {
      definir_variantes(base, uid, montee);
      for (const fait of faites) evenements[fait.original] = { sens: "montée", depuis: fait.depuis, vers: fait.vers };
    }

    const apres = recuperer_historique(base, uid);
    if (athlete.accepte_descente) {
      const propositions = moteur.variantes.propositions(
        apres, moteur.ressenti.jugements_par_seance(apres), normaliser_variantes(profil.variantes), catalogue,
      )[seance_id] ?? {};
      for (const [depuis, proposition] of Object.entries(propositions)) {
        try {
          const table = moteur.variantes.definir(profil.variantes, proposition.original, proposition.vers, catalogue);
          definir_variantes(base, uid, table);
          evenements[proposition.original] = { sens: "descente", depuis, vers: proposition.vers };
        } catch {
          // Refusee par `definir` : l'ecran n'aurait pas propose le bouton.
        }
      }
    }

    const records = moteur.niveaux.niveaux_par_exercice(apres, recuperer_ancrages(base, uid));
    circuit.exercices.forEach((bloc, index) => {
      const trace = jouees[index];
      const joue = bloc.exercice.nom;
      const palier = objectifs[joue] ?? null;
      const ligne = resultats.find((r) => r.nom === joue) ?? null;
      trace.points.push({
        n: n + 1,
        joue,
        palier: palier_lisible(palier),
        exige: exigence(joue, palier, baremes, athlete, hyp),
        force: force.get(trace.tete),
        reussi: issues[index].reussi,
        ressenti: issues[index].ressenti,
        realise: issues[index].series.map((s) => s.realise),
        niveau_prouve: ligne ? moteur.niveaux.niveau_prouve_par(ligne) : null,
        record: records[joue]?.niveau ?? null,
        evenement: evenements[trace.tete] ?? null,
      });
    });

    if (!scenario) {
      for (const trace of jouees) {
        const actuelle = force.get(trace.tete);
        const plafond = trace.force_initiale * athlete.plafond;
        force.set(trace.tete, actuelle + (plafond - actuelle) * athlete.progression);
      }
    }
  }
  return traces;
}
