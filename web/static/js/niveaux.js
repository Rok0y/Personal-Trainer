// Jumeau de progression/niveaux.py — le niveau deduit de l'historique.
//
// **Le niveau est le plus haut palier jamais valide**, et il ne se stocke
// nulle part : il est recalcule a chaque lecture depuis l'historique. La
// regle est donc idempotente, insensible a l'ordre des seances comme a leur
// suppression, et elle applique d'elle-meme le « pas de recul ».
//
// A ne pas confondre avec l'**objectif** (`objectifs.js`), qui est ce que la
// prochaine seance demande : un plan, qui monte ou descend. Un objectif peut
// legitimement passer *sous* le niveau — c'est un delestage, pas une
// regression, et l'ecran des records continue d'afficher le niveau acquis.

import {
  MODE_AMRAP,
  MODE_CHRONO,
  MODE_MAINTIEN,
  MODE_REPETITIONS,
} from "./circuit.js";
import { UNITE_REPETITIONS, UNITE_SECONDES } from "./paliers.js";

//: Ce qu'un mode mesure. Un exercice enregistre en `maintien` ne peut pas
//: valider un bareme en repetitions : les deux ne parlent pas de la meme
//: chose.
export const UNITE_PAR_MODE = {
  [MODE_REPETITIONS]: UNITE_REPETITIONS,
  [MODE_AMRAP]: UNITE_REPETITIONS,
  [MODE_MAINTIEN]: UNITE_SECONDES,
  [MODE_CHRONO]: UNITE_SECONDES,
};

/**
 * Reduit un exercice de l'historique a ce qu'il *prouve* : [poids, series, cible].
 *
 * Deux regles gouvernent la lecture :
 *
 * - seules les series menees au bout comptent (`completee`) — une serie
 *   interrompue par un abandon ou par la navigation ne prouve rien ;
 * - c'est le **maillon faible** qui commande, pas la moyenne ni le maximum.
 *   « Objectif atteint sur TOUTES les series » se traduit par un minimum sur
 *   les series retenues, pour la cible comme pour le poids : 12, 12, 10, 12
 *   repetitions prouve 10, pas 12.
 *
 * Une ligne sans serie detaillee rend null plutot que de se rabattre sur les
 * colonnes agregees : `repetitions` y est une *somme* sur toutes les series,
 * dont la performance de la plus faible ne se deduit pas.
 */
export function performance_realisee(exercice, unite_attendue) {
  const champ = unite_attendue === UNITE_SECONDES ? "duree" : "repetitions";

  const series = (exercice.series_detaillees ?? []).filter((s) => s.completee);
  if (!series.length) return null;

  const poids = Math.min(...series.map((s) => s.poids || 0));
  const cible = Math.min(...series.map((s) => s[champ] || 0));
  return [poids, series.length, cible];
}

export class Niveaux {
  constructor(baremes) {
    this.baremes = baremes;
  }

  /** Le plus haut niveau qu'un exercice de l'historique valide, ou null. */
  niveau_prouve_par(exercice) {
    const nom = exercice.nom;
    if (!this.baremes.est_suivi_par_le_moteur(nom)) return null;

    const unite_attendue = this.baremes.unite(nom);
    if (UNITE_PAR_MODE[exercice.mode] !== unite_attendue) return null;

    const performance = performance_realisee(exercice, unite_attendue);
    if (performance === null) return null;

    const [poids, series, cible] = performance;
    return this.baremes.niveau_pour(nom, poids, series, cible);
  }

  /**
   * Niveau actuel de chaque exercice suivi, avec ce qui l'a etabli.
   *
   * Un meme exercice peut apparaitre deux fois dans une seance : chaque ligne
   * est jugee pour elle-meme et c'est la meilleure qui l'emporte, jamais leur
   * somme.
   *
   * Un **ancrage** recale le niveau d'un exercice que l'historique ne peut pas
   * prouver. Il agit de deux facons a la fois : il fait table rase de
   * l'historique anterieur, et il sert de plancher. C'est cette table rase qui
   * lui permet de corriger un niveau vers le bas — un simple plancher ne
   * saurait que le relever.
   */
  niveaux_par_exercice(seances, ancrages = {}) {
    const niveaux = {};

    for (const seance of seances) {
      for (const exercice of seance.exercices ?? []) {
        const nom = exercice.nom;
        const ancrage = ancrages[nom];
        // Anterieur a l'ancrage : ne compte plus.
        if (ancrage && (seance.id || 0) <= ancrage.apres_seance_id) continue;
        const niveau = this.niveau_prouve_par(exercice);
        if (niveau === null) continue;
        const meilleur = niveaux[nom];
        if (meilleur === undefined || niveau > meilleur.niveau) {
          niveaux[nom] = {
            niveau,
            palier: this.baremes.palier(nom, niveau),
            seance_id: seance.id ?? null,
            date: seance.date ?? null,
            ancre: false,
          };
        }
      }
    }

    for (const [nom, ancrage] of Object.entries(ancrages)) {
      if (!this.baremes.est_suivi_par_le_moteur(nom)) continue;
      const meilleur = niveaux[nom];
      if (meilleur === undefined || ancrage.niveau > meilleur.niveau) {
        niveaux[nom] = {
          niveau: ancrage.niveau,
          palier: this.baremes.palier(nom, ancrage.niveau),
          seance_id: null,
          date: ancrage.date,
          ancre: true,
        };
      }
    }

    return niveaux;
  }

  niveau_actuel(nom, seances, ancrages = {}) {
    const entree = this.niveaux_par_exercice(seances, ancrages)[nom];
    return entree ? entree.niveau : null;
  }

  /**
   * Tout ce qu'un ecran a besoin de savoir sur le niveau d'un exercice.
   *
   * **Trois situations distinctes, qu'un affichage ne doit pas confondre** :
   * `niveau` a null = hors bareme (aucune performance n'atteint le premier
   * palier, ce qui n'est pas « niveau 0 ») ; `maximum_atteint` = le bareme est
   * epuise ; sinon `suivant` decrit le palier suivant.
   *
   * Volontairement sans « pourcentage d'avancement » : un niveau dit ou l'on
   * en est, pas ce qu'il reste a faire. La part de bareme parcourue n'aurait
   * de sens que face a un objectif, ce qui releve de la couche programme.
   */
  etat_niveau(nom, niveaux) {
    if (!this.baremes.est_suivi_par_le_moteur(nom)) return null;

    const entree = niveaux[nom];
    const niveau = entree ? entree.niveau : null;
    const suivant = this.baremes.palier(nom, (niveau || 0) + 1);

    return {
      niveau,
      actuel: niveau ? this.baremes.palier(nom, niveau) : null,
      suivant,
      premier: this.baremes.palier(nom, 1),
      maximum_atteint: niveau !== null && suivant === null,
      date: entree ? entree.date : null,
      seance_id: entree ? entree.seance_id : null,
      ancre: Boolean(entree && entree.ancre),
    };
  }

  /**
   * Pour chaque seance, les exercices dont le niveau vient de monter grace a elle.
   *
   * Rejoue l'historique dans l'ordre **chronologique** (`recuperer_historique`
   * le rend le plus recent en tete) pour reperer l'instant precis ou chaque
   * niveau apparait. Meme regle de non-recul que `niveaux_par_exercice` et
   * meme traitement des ancrages ; la boucle est volontairement dupliquee
   * plutot que factorisee, l'une accumulant un maximum, l'autre un evenement
   * par franchissement.
   */
  montees_de_niveau(seances, ancrages = {}) {
    const chronologique = [...seances].sort((a, b) => (a.id || 0) - (b.id || 0));

    const niveaux = {};
    const montees = {};
    for (const seance of chronologique) {
      for (const exercice of seance.exercices ?? []) {
        const nom = exercice.nom;
        const ancrage = ancrages[nom];
        if (ancrage && (seance.id || 0) <= ancrage.apres_seance_id) continue;
        const niveau = this.niveau_prouve_par(exercice);
        if (niveau === null) continue;
        const avant = niveaux[nom];
        if (avant === undefined || niveau > avant) {
          montees[seance.id] = montees[seance.id] ?? {};
          montees[seance.id][nom] = {
            depuis: avant ?? null,
            vers: niveau,
            palier: this.baremes.palier(nom, niveau),
          };
          niveaux[nom] = niveau;
        }
      }
    }

    return montees;
  }

  /** Etat de niveau de tous les exercices suivis, en une seule lecture. */
  etats_niveaux(seances, ancrages = {}) {
    const niveaux = this.niveaux_par_exercice(seances, ancrages);
    const etats = {};
    for (const nom of this.baremes.exercices_suivis()) {
      etats[nom] = this.etat_niveau(nom, niveaux);
    }
    return etats;
  }
}
