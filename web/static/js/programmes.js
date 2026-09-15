// Jumeau de la **lecture** de progression/programmes.py.
//
// Un programme ne stocke aucune donnee de progression : il declare, pour
// chaque exercice, la performance a atteindre. Le niveau requis en est deduit,
// le niveau acquis vient de l'historique, et l'ecart se recalcule a chaque
// affichage. Rien a migrer, rien a tenir a jour.
//
// **Seule la lecture est portee, et c'est une decision.** L'ecriture —
// `valider_programme`, `enregistrer_programme`, `synchroniser_seances`,
// `seance_correspondante` — est l'editeur, qui ecrit dans
// `programmes_personnalises.json`. Le meme arbitrage que pour les seances
// s'applique : **le fichier fait autorite**, il s'edite sur le poste fixe et
// un deploiement le propage. Porter l'editeur creerait une seconde source de
// verite que rien ne reconcilierait, sur des donnees qu'un appareil hors ligne
// ne peut pas renvoyer.
//
// Une divergence d'API assumee, la meme que pour les ancrages : le Python lit
// le fichier dans chaque fonction (`tous_les_programmes()`), le JavaScript
// recoit le programme en argument — il n'a pas de disque a relire, les
// programmes lui arrivent par `donnees/programmes.json`.

import { UNITE_SECONDES } from "./paliers.js";
import { arrondi_python } from "./calibration.js";

// Deux `round()` de Python vivent dans ce module — l'avancement d'une exigence
// et la moyenne du programme — et tous deux passent par `arrondi_python` :
// Python arrondit 12,5 a 12 (au pair le plus proche), JavaScript a 13, et un
// avancement tombe sur un demi exact des que le rapport est simple. Sabote,
// `Math.round` sort huit divergences sur le harnais.
//
// Le `:g` de `prescription`, en revanche, **n'a pas de contrepartie a ecrire**,
// et c'est mesure : une interpolation directe suffit. JSON ne distingue pas un
// entier d'un flottant et les nombres JavaScript non plus, si bien que le
// « 12.0 » du fichier arrive deja comme 12 et s'ecrit « 12 » de lui-meme. Une
// fonction defensive vivait ici pour ce piege ; le sabotage qui l'a retiree
// n'a produit aucune divergence, donc elle ne protegeait de rien.

/** Volume que la prescription represente, dans l'unite du bareme. */
export function volume_exige(baremes, exigence) {
  return baremes.volume(exigence.series, exigence.cible, exigence.poids);
}

/** La ligne telle qu'elle est ecrite dans le programme, pour l'affichage. */
export function prescription(baremes, exigence) {
  const suffixe = baremes.unite(exigence.exercice) === UNITE_SECONDES ? " s" : "";
  const charge = exigence.poids ? ` à ${exigence.poids} kg` : "";
  return `${exigence.series}x${exigence.cible}${suffixe}${charge}`;
}

/**
 * Un palier sous sa forme lisible — jumeau de `Palier.resume()`.
 *
 * Cote Python c'est une methode de la dataclass ; les paliers JavaScript sont
 * des objets simples, d'ou une fonction. Elle vit ici plutot que recopiee dans
 * chaque ecran qui affiche un palier.
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
export function etat_exigence(baremes, exigence, niveaux) {
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
    // pas deborder la barre. `arrondi_python` et non `Math.round` — Python
    // arrondit 12,5 a 12, JavaScript a 13, et un avancement tombe exactement
    // sur un demi des que le rapport est simple.
    avancement: requis ? Math.min(100, arrondi_python((100 * (acquis || 0)) / requis)) : 0,
    restant: requis ? Math.max(0, requis - (acquis || 0)) : null,
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
export function etat_programme(baremes, cle, programme, niveaux) {
  if (!programme) return null;

  const par_seance = {};
  const exigences = [];

  for (const ligne of programme.exigences ?? []) {
    if (!baremes.est_suivi_par_le_moteur(ligne.exercice)) continue;
    const etat = etat_exigence(baremes, ligne, niveaux);
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
 * Simple lecture du lien que `synchroniser_seances` a ecrit dans le programme,
 * cote poste fixe. C'etait auparavant une heuristique par recouvrement
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

/**
 * Seance du programme a enchainer maintenant.
 *
 * Le programme se parcourt **en boucle** : la prochaine est celle qui suit la
 * derniere effectivement realisee. Une seance abandonnee ne compte pas — on la
 * repropose plutot que de la considerer faite.
 */
export function prochaine_seance(programme, historique, catalogue_seances) {
  if (!programme) return null;
  const ordre = libelles_seances(programme);
  if (!ordre.length) return null;

  const liaison = liaison_seances(programme, catalogue_seances);
  const par_seance = {};
  for (const [libelle, nom] of Object.entries(liaison)) {
    if (nom) par_seance[nom] = libelle;
  }

  // L'historique rend les seances de la plus recente a la plus ancienne : la
  // premiere qui appartient au programme est donc la derniere faite.
  let index = 0;
  for (const seance of historique) {
    if (seance.statut === "abandoned") continue;
    const libelle = par_seance[seance.nom];
    if (ordre.includes(libelle)) {
      index = (ordre.indexOf(libelle) + 1) % ordre.length;
      break;
    }
  }

  const libelle = ordre[index];
  return {
    libelle,
    seance: liaison[libelle],
    position: index + 1,
    total: ordre.length,
  };
}

/** Tous les programmes, a partir d'une seule lecture des niveaux. */
export function etats_programmes(baremes, programmes, niveaux) {
  const etats = {};
  for (const [cle, programme] of Object.entries(programmes ?? {})) {
    etats[cle] = etat_programme(baremes, cle, programme, niveaux);
  }
  return etats;
}
