// Les programmes sportifs, en lecture.
//
// Un programme ne stocke aucune donnee de progression : il declare, pour
// chaque exercice, la performance a atteindre. Le niveau requis en est deduit,
// le niveau acquis vient de l'historique, et l'ecart se recalcule a chaque
// affichage. Rien a migrer, rien a tenir a jour.
//
// **Il n'y a pas d'editeur de programme, et c'est une decision.**
// `donnees/programmes.json` fait autorite : il s'edite a la main et un
// deploiement le propage (`verifier_donnees.mjs` le valide). Un editeur dans
// l'application creerait une seconde source de verite que rien ne
// reconcilierait, sur des donnees qu'un appareil hors ligne ne peut pas
// renvoyer. Chaque fonction recoit donc le programme en argument.

import { UNITE_SECONDES } from "./paliers.js";
import { arrondi_python } from "./calibration.js";
import { via_variante } from "./variantes.js";

// Deux arrondis vivent dans ce module — l'avancement d'une exigence et la
// moyenne du programme — et tous deux passent par `arrondi_python`, qui
// arrondit au pair : 12,5 donne 12, la ou `Math.round` donne 13. Un avancement
// tombe sur un demi exact des que le rapport est simple, et les reponses
// figees des tests suivent l'arrondi au pair.

/** Volume que la prescription represente, dans l'unite du bareme. */
export function volume_exige(baremes, exigence) {
  return baremes.volume_exercice(
    exigence.exercice,
    exigence.series,
    exigence.cible,
    exigence.poids,
  );
}

/** La ligne telle qu'elle est ecrite dans le programme, pour l'affichage. */
export function prescription(baremes, exigence) {
  const suffixe = baremes.unite(exigence.exercice) === UNITE_SECONDES ? " s" : "";
  const charge = exigence.poids ? ` à ${exigence.poids} kg` : "";
  return `${exigence.series}x${exigence.cible}${suffixe}${charge}`;
}

/**
 * Un palier sous sa forme lisible.
 *
 * Les paliers sont des objets simples, d'ou une fonction. Elle vit ici plutot
 * que recopiee dans chaque ecran qui affiche un palier.
 */
export function resume_palier(palier) {
  if (!palier) return null;
  const suffixe = palier.unite === UNITE_SECONDES ? " s" : "";
  const charge = palier.poids ? ` à ${palier.poids} kg` : "";
  return `${palier.series}x${palier.cible}${suffixe}${charge}`;
}

/**
 * Confronte une exigence au niveau acquis.
 *
 * **La traduction passe par le volume** : un programme est ecrit avec le
 * materiel de son auteur, et « 4x12 a 28 kg » n'a pas de palier correspondant
 * si les halteres s'arretent a 10 kg. Son volume, lui, se retrouve ailleurs
 * sur le bareme.
 *
 * `prescription` et `palier_requis` sont **tous les deux** rendus, et les deux
 * doivent etre affiches : n'afficher que la traduction rendait la page
 * incomprehensible — on saisissait « 6x15 » dans l'editeur et on relisait
 * « 4x23 » sur la fiche, sans que rien ne relie les deux.
 */
export function etat_exigence(baremes, exigence, niveaux, variantes = {}) {
  const nom = exigence.exercice;
  const etat = niveaux[nom];
  const acquis = etat ? etat.niveau : null;
  const requis = baremes.niveau_pour_volume(nom, volume_exige(baremes, exigence));

  return {
    exercice: nom,
    seance: exigence.seance || "Séance",
    series: exigence.series,
    cible: exigence.cible,
    poids: exigence.poids,
    prescription: prescription(baremes, exigence),
    volume: volume_exige(baremes, exigence),
    niveau_requis: requis,
    palier_requis: requis ? baremes.palier(nom, requis) : null,
    niveau_actuel: acquis,
    actuel_resume: etat && etat.actuel ? resume_palier(etat.actuel) : null,
    // Hors d'atteinte : meme le sommet du bareme n'atteint pas ce volume.
    // Depuis que le bareme se termine par une tranche ouverte, ca ne peut plus
    // arriver qu'a un exercice sans bareme — qu'`etat_programme` ecarte deja.
    hors_atteinte: requis === null,
    atteint: Boolean(requis && acquis && acquis >= requis),
    // Borne a 100 % : depasser le niveau requis remplit l'exigence, ca ne fait
    // pas deborder la barre. Arrondi au pair (voir en tete du module).
    avancement: requis ? Math.min(100, arrondi_python((100 * (acquis || 0)) / requis)) : 0,
    restant: requis ? Math.max(0, requis - (acquis || 0)) : null,
    // Joue sous une variante : dit, sans toucher a l'avancement.
    via_variante: via_variante(nom, variantes ?? {}, niveaux),
  };
}

/** Libelles de seance du programme, dans leur ordre d'apparition. */
export function libelles_seances(programme) {
  const ordre = [];
  for (const exigence of programme.exigences ?? []) {
    const libelle = exigence.seance || "Séance";
    if (!ordre.includes(libelle)) ordre.push(libelle);
  }
  return ordre;
}

/**
 * Avancement d'un programme, entierement recalcule a la lecture.
 *
 * Les exigences forment une **liste plate**, chacune portant le libelle de sa
 * seance ; le regroupement se fait ici, a l'affichage, dans l'ordre
 * d'apparition — donc celui de l'editeur.
 */
export function etat_programme(baremes, cle, programme, niveaux, variantes = {}) {
  if (!programme) return null;

  const par_seance = {};
  const exigences = [];

  for (const ligne of programme.exigences ?? []) {
    if (!baremes.est_suivi_par_le_moteur(ligne.exercice)) continue;
    const etat = etat_exigence(baremes, ligne, niveaux, variantes);
    (par_seance[etat.seance] ??= []).push(etat);
    exigences.push(etat);
  }

  const atteintes = exigences.filter((e) => e.atteint);
  return {
    cle,
    nom: programme.nom,
    description: programme.description ?? "",
    exigences_brutes: programme.exigences ?? [],
    seances: par_seance,
    total: exigences.length,
    atteintes: atteintes.length,
    hors_atteinte: exigences.filter((e) => e.hors_atteinte).length,
    // **Moyenne des avancements**, et non part des exigences remplies : la
    // seconde reste a zero tant qu'aucune n'est *entierement* atteinte, ce qui
    // affiche une barre vide alors que tout a progresse. Les deux chiffres
    // coexistent a l'ecran, ils ne disent pas la meme chose.
    pourcentage: exigences.length
      ? arrondi_python(
          exigences.reduce((total, e) => total + e.avancement, 0) / exigences.length
        )
      : 0,
    battu: Boolean(exigences.length) && atteintes.length === exigences.length,
  };
}

/**
 * Associe chaque libelle de seance du programme a une seance jouable.
 *
 * Simple lecture du lien que le programme declare (`seances`, une donnee de
 * `programmes.json`). C'etait auparavant une heuristique par recouvrement
 * d'exercices, rejouee a chaque affichage : elle pouvait changer d'avis en
 * silence, et rendait null des que le recouvrement etait nul.
 */
export function liaison_seances(programme, catalogue_seances) {
  if (!programme) return {};
  const liens = programme.seances ?? {};
  const resultat = {};
  for (const libelle of libelles_seances(programme)) {
    const nom = liens[libelle];
    resultat[libelle] = nom && nom in catalogue_seances ? nom : null;
  }
  return resultat;
}

//: Sept jours **depuis la premiere seance du cycle**, et non une semaine du
//: calendrier — voir `semaine_du_programme`. En minutes : les
//: instants sont comptes en minutes d'horloge murale (voir `_lire_date`).
const DUREE_CYCLE = 7 * 24 * 60;
const TOURS_MAX = 3;
const JOURS_PAR_CYCLE = 7;
const CYCLES_RECENTS = 6;

/** Les rythmes proposables : 1, 2 ou 3 tours, tant qu'ils tiennent en sept jours. */
export function tours_possibles(nombre_seances) {
  const possibles = [];
  for (let tours = 1; tours <= TOURS_MAX; tours += 1) {
    if (tours * nombre_seances <= JOURS_PAR_CYCLE) possibles.push(tours);
  }
  return possibles.length ? possibles : [1];
}

const MOTIF_DATE = /^(\d{1,2})\/(\d{1,2})\/(\d{4}) (\d{1,2}):(\d{1,2})$/;

/**
 * Un instant depuis une date de seance « JJ/MM/AAAA HH:MM », en minutes, ou
 * null si elle est illisible.
 *
 * **En `Date.UTC` et jamais en heure locale** : la base stocke l'heure murale
 * sans fuseau, et c'est en heure murale que se comptent les sept jours. En
 * heure locale, une semaine qui traverse le changement d'heure durerait 167 ou
 * 169 heures, et le seuil des sept jours se decalerait d'une heure.
 */
function _lire_date(texte) {
  const m = MOTIF_DATE.exec(texte ?? "");
  if (!m) return null;
  const [annee, mois, jour, heure, minute] = [m[3], m[2], m[1], m[4], m[5]].map(Number);
  const ms = Date.UTC(annee, mois - 1, jour, heure, minute);
  const d = new Date(ms);
  // `Date.UTC` reporte un 31/02 au 3 mars sans rien dire : on relit pour
  // refuser une date impossible.
  if (
    d.getUTCFullYear() !== annee || d.getUTCMonth() !== mois - 1 ||
    d.getUTCDate() !== jour || d.getUTCHours() !== heure || d.getUTCMinutes() !== minute
  ) {
    return null;
  }
  return ms / 60000;
}

function _ecrire_date(minutes) {
  const d = new Date(minutes * 60000);
  const deux = (n) => String(n).padStart(2, "0");
  return (
    `${deux(d.getUTCDate())}/${deux(d.getUTCMonth() + 1)}/${d.getUTCFullYear()} ` +
    `${deux(d.getUTCHours())}:${deux(d.getUTCMinutes())}`
  );
}

/**
 * Ou en est la semaine du programme : ses cases, la suivante, la serie.
 *
 * **Les cases** sont les libelles du programme dans leur ordre, repetes
 * `tours` fois (Push, Pull, Jambes, Push, Pull, Jambes). On les remplit en
 * rejouant l'historique **dans l'ordre chronologique** — par identifiant, les
 * dates en `JJ/MM/AAAA` ne se triant pas :
 *
 * - une seance abandonnee ne compte pas, une seance hors programme non plus ;
 * - la premiere seance ouvre un cycle de sept jours ; une seance qui tombe
 *   **a sept jours pile ou apres** le clot comme rate et en ouvre un autre ;
 * - une seance coche **la premiere case vide de son libelle**, pas la case
 *   attendue : faire Jambes avant Pull ne doit rien couter, l'ordre ne sert
 *   qu'a ranger les cases et a proposer la suivante. Une seance de plus que
 *   ce que le cycle demande pour son libelle est ignoree — elle n'ouvre rien ;
 * - un cycle complet se clot comme reussi, et la seance d'apres en ouvre un.
 *
 * **Le cycle montre** est le dernier, tant que ses sept jours courent —
 * complet ou non. Passe ce delai, la semaine « demarre a ta prochaine
 * seance » : cases vides, `debut` a null.
 *
 * **La serie** compte les cycles reussis d'affilee. Le cycle en cours, s'il
 * est incomplet, ne compte pas et ne casse rien ; un cycle rate la casse, et
 * une semaine entiere sans aucune seance aussi — un cycle doit commencer
 * moins de sept jours apres la fin du precedent pour s'y enchainer.
 *
 * Rien n'est stocke : tout se relit dans l'historique, ce qui rend le calcul
 * **retroactif** — passer de 3 a 6 seances relit les cycles passes avec six
 * cases. Le programme arrive en argument, et `maintenant` est
 * **obligatoire** — une date au format de la base, que l'appelant fabrique
 * avec `horodatage()` —, pour que deux appels rendent le meme verdict.
 *
 * Remplace `prochaine_seance` : avec des cases a l'ecran, « la seance apres la
 * derniere faite » aurait contredit la premiere case vide.
 */
export function semaine_du_programme(programme, historique, catalogue_seances, tours, maintenant) {
  if (!programme) return null;
  const ordre = libelles_seances(programme);
  if (!ordre.length) return null;

  const possibles = tours_possibles(ordre.length);
  const tours_retenus = Math.min(
    Math.max(Math.trunc(Number(tours) || 1), 1),
    possibles[possibles.length - 1]
  );
  const instant = _lire_date(maintenant);

  const liaison = liaison_seances(programme, catalogue_seances);
  const par_nom = {};
  for (const [libelle, nom] of Object.entries(liaison)) {
    if (nom) par_nom[nom] = libelle;
  }
  const modele = [];
  for (let tour = 0; tour < tours_retenus; tour += 1) {
    for (const libelle of ordre) {
      modele.push({
        libelle,
        seance: liaison[libelle],
        position: modele.length + 1,
        faite: false,
        seance_id: null,
        date: null,
      });
    }
  }
  const nouveau_cycle = (debut) => ({
    debut,
    fin: debut + DUREE_CYCLE,
    cases: modele.map((c) => ({ ...c })),
    complet: false,
  });

  const cycles = [];
  let courant = null;
  // Par identifiant, dans l'ordre chronologique : les dates en JJ/MM/AAAA ne
  // se trient pas, et l'historique arrive du plus recent au plus ancien.
  const chronologique = [...historique].sort((a, b) => (a.id || 0) - (b.id || 0));
  for (const seance of chronologique) {
    if (seance.statut === "abandoned") continue;
    const libelle = par_nom[seance.nom];
    const quand = _lire_date(seance.date);
    if (libelle === undefined || quand === null) continue;
    if (courant !== null && quand >= courant.fin) courant = null;
    if (courant === null) {
      courant = nouveau_cycle(quand);
      cycles.push(courant);
    }
    const c = courant.cases.find((x) => x.libelle === libelle && !x.faite);
    if (!c) continue;
    c.faite = true;
    c.seance_id = seance.id ?? null;
    c.date = seance.date ?? null;
    if (courant.cases.every((x) => x.faite)) {
      courant.complet = true;
      courant = null;
    }
  }

  const dernier = cycles.length ? cycles[cycles.length - 1] : null;
  const montre = dernier !== null && instant < dernier.fin ? dernier : null;
  const en_cours = montre !== null && !montre.complet;
  const clos = en_cours ? cycles.slice(0, -1) : cycles;

  let serie = 0;
  let reference = en_cours ? montre.debut : instant;
  for (let i = clos.length - 1; i >= 0; i -= 1) {
    const cycle = clos[i];
    if (!cycle.complet || reference - cycle.fin >= DUREE_CYCLE) break;
    serie += 1;
    reference = cycle.debut;
  }

  const cases = montre !== null ? montre.cases : modele.map((c) => ({ ...c }));
  const a_faire = montre !== null && montre.complet ? null : cases.find((c) => !c.faite) ?? null;
  const proposee = a_faire ?? cases[0];
  return {
    tours: tours_retenus,
    tours_possibles: possibles,
    debut: montre ? _ecrire_date(montre.debut) : null,
    fin: montre ? _ecrire_date(montre.fin) : null,
    cases,
    faites: cases.filter((c) => c.faite).length,
    total: cases.length,
    reussie: Boolean(montre && montre.complet),
    prochaine: {
      libelle: proposee.libelle,
      seance: proposee.seance,
      position: proposee.position,
      total: cases.length,
    },
    serie,
    recents: clos.slice(-CYCLES_RECENTS).map((cycle) => ({
      debut: _ecrire_date(cycle.debut),
      reussi: cycle.complet,
    })),
  };
}

/** Tous les programmes, a partir d'une seule lecture des niveaux. */
export function etats_programmes(baremes, programmes, niveaux, variantes = {}) {
  const etats = {};
  for (const [cle, programme] of Object.entries(programmes ?? {})) {
    etats[cle] = etat_programme(baremes, cle, programme, niveaux, variantes);
  }
  return etats;
}
