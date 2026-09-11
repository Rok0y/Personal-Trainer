// Jumeau de progression/ressenti.py — **de combien l'objectif bouge**.
//
// Toute la regle de progression tient dans la table `AJUSTEMENT`, indexee par
// le couple (reussi, ressenti). La changer, c'est changer cette table, et
// rien d'autre.
//
// `null` y est l'absence de reponse, et c'est elle qui reproduit exactement le
// comportement d'avant cette fonctionnalite : +1 apres une reussite, rien
// apres un echec. **Le ressenti ne fait qu'accelerer ou freiner un moteur qui
// tourne deja seul, jamais le remplacer.**

import { UNITE_SECONDES } from "./paliers.js";
import { UNITE_PAR_MODE } from "./niveaux.js";

//: Les cinq valeurs stockables. L'interface n'en propose que celles qui
//: *changent* quelque chose — « facile » et « trop facile » apres une
//: reussite, « trop dur » apres un echec. Pas de bouton neutre,
//: volontairement : ne rien selectionner est deja la reponse neutre.
export const ECHELLE = ["trop_dur", "dur", "ok", "facile", "trop_facile"];

//: Combien de paliers l'objectif gagne, selon ce qui s'est passe ET ce qui a
//: ete ressenti. La cle `null` vaut « pas de reponse ».
export const AJUSTEMENT = {
  "true|trop_facile": 3,
  "true|facile": 2,
  "true|null": 1,
  "false|trop_dur": -1,
  "false|null": 0,
};

const cle = (reussi, ressenti) => `${Boolean(reussi)}|${ressenti ?? "null"}`;

export function est_valide(valeur) {
  return ECHELLE.includes(valeur);
}

/**
 * Nombre de paliers a ajouter a l'objectif.
 *
 * Les combinaisons absentes de la table retombent sur l'absence de reponse :
 * dire « c'etait facile » apres un echec ne fait rien plutot que de produire
 * une regle que personne n'a ecrite. L'interface ne propose pas ces
 * combinaisons, mais l'historique peut en contenir — une reponse saisie a
 * posteriori depuis la page d'historique n'est pas contrainte par l'ecran de
 * fin de seance.
 */
export function ajustement(reussi, ressenti = null) {
  const exacte = AJUSTEMENT[cle(reussi, ressenti)];
  if (exacte !== undefined) return exacte;
  return AJUSTEMENT[cle(reussi, null)];
}

/**
 * D'ou repartir quand l'objectif de la derniere seance n'a pas ete atteint.
 *
 * On redemande exactement la meme chose. **Un echec ne fait pas reculer
 * l'objectif** : il le fige, et seul un « trop dur » explicite le fait
 * redescendre.
 *
 * La tentation serait de plafonner a `niveau_acquis + 1`, ce que faisait
 * l'application avant ce module. C'est une erreur, et l'historique le montre :
 * un developpe epaule a 3x12 a 8 kg manque de trois repetitions renvoyait a
 * 3x15 a **5 kg**, parce que c'etait le dernier palier *pleinement* valide.
 * Une serie ratee faisait perdre deux crans d'haltere.
 *
 * `niveau_acquis` reste dans la signature parce que c'est lui, et lui seul,
 * que voudrait consulter la regle concurrente : le garder visible evite de
 * devoir rebrancher un calcul de niveaux jusqu'ici si l'arbitrage change.
 */
export function base_apres_echec(base_demandee, niveau_acquis) {
  return base_demandee;
}

export class Ressenti {
  constructor(baremes, niveaux) {
    this.baremes = baremes;
    this.niveaux = niveaux;
  }

  /**
   * Ce que la seance demandait : [poids, series, cible], ou null.
   *
   * Lit les colonnes de **cible** de l'historique, pas les realisees. `poids`
   * fait exception : c'est la charge configuree du bloc, donc deja une
   * consigne — il n'existe pas de colonne `poids_cible`.
   */
  _cible_visee(exercice) {
    const nom = exercice.nom;
    if (!this.baremes.est_suivi_par_le_moteur(nom)) return null;

    const unite_attendue = this.baremes.unite(nom);
    if (UNITE_PAR_MODE[exercice.mode] !== unite_attendue) return null;

    const series = exercice.series_cibles || 0;
    const cible =
      unite_attendue === UNITE_SECONDES
        ? exercice.duree_cible || 0
        : exercice.repetitions_cibles || 0;
    if (!series || !cible) return null;

    return [exercice.poids || 0, series, cible];
  }

  /**
   * Ce qu'une ligne d'historique dit du couple (objectif, reussite).
   *
   * Rend `{base, reussi, ressenti}` ou null si la ligne ne permet pas de
   * situer un objectif — exercice hors bareme, mode incompatible avec son
   * unite, ou cible absente (seance jouee avant le moteur de progression).
   *
   * « Reussi » signifie que le palier demande a bien ete valide **au sens du
   * bareme** : `niveau_prouve_par` applique deja le maillon faible et ne
   * compte que les series menees au bout. Une seule serie manquee fait donc
   * basculer l'exercice en echec, ce qui est exactement la lecture voulue.
   */
  juger(exercice) {
    const visee = this._cible_visee(exercice);
    if (visee === null) return null;

    const base = this.baremes.niveau_pour(exercice.nom, ...visee);
    if (base === null) return null;

    return {
      base,
      reussi: (this.niveaux.niveau_prouve_par(exercice) || 0) >= base,
      ressenti: exercice.ressenti || null,
    };
  }

  /**
   * Les exercices d'une seance qui peuvent servir de repere, ou rien.
   *
   * Une seance **abandonnee** ne dit rien de l'objectif suivant, et une
   * seance anterieure a un ancrage a ete explicitement declaree perimee par
   * l'utilisateur : la reprendre ecraserait le recalage qu'elle a motive.
   */
  _lignes_retenues(seance, ancrages) {
    if (seance.statut === "abandoned") return [];
    const identifiant = seance.id || 0;
    return (seance.exercices ?? []).filter((exercice) => {
      const ancrage = ancrages[exercice.nom];
      return !(ancrage && identifiant <= ancrage.apres_seance_id);
    });
  }

  /**
   * Objectif a viser pour chaque exercice, d'apres sa derniere seance.
   *
   * Un exercice absent du resultat n'a pas de repere exploitable : c'est a
   * l'appelant de retomber sur la regle par defaut (`objectifs.js`).
   *
   * L'historique rend la seance la plus recente en tete, donc la premiere
   * ligne rencontree pour un exercice est la bonne. Un meme exercice peut
   * apparaitre deux fois dans une seance ; c'est alors l'objectif **le plus
   * haut** qui fait foi, et a objectif egal la ligne reussie l'emporte —
   * jamais une somme.
   */
  evaluation(seances, ancrages = {}, niveaux = null) {
    if (niveaux === null) {
      niveaux = this.niveaux.niveaux_par_exercice(seances, ancrages);
    }

    const resultat = {};
    for (const seance of seances) {
      for (const exercice of this._lignes_retenues(seance, ancrages)) {
        const nom = exercice.nom;
        // Deja tranche par une seance plus recente.
        if (nom in resultat && resultat[nom].seance_id !== (seance.id ?? null)) {
          continue;
        }

        const jugement = this.juger(exercice);
        if (jugement === null) continue;

        const precedent = resultat[nom];
        if (
          precedent &&
          (precedent.base > jugement.base ||
            (precedent.base === jugement.base && precedent.reussi))
        ) {
          continue;
        }

        let base = jugement.base;
        if (!jugement.reussi) {
          const acquis = niveaux[nom]?.niveau ?? null;
          base = base_apres_echec(base, acquis);
        }

        const gain = ajustement(jugement.reussi, jugement.ressenti);
        resultat[nom] = {
          ...jugement,
          base,
          ajustement: gain,
          vise: Math.max(1, base + gain),
          seance_id: seance.id ?? null,
        };
      }
    }

    return resultat;
  }

  /**
   * Jugement de chaque exercice, seance par seance, pour l'affichage.
   *
   * C'est ce qui permet aux ecrans de ne proposer que les reponses ayant un
   * sens : apres une reussite on demande si c'etait facile, apres un echec si
   * c'etait trop dur — jamais les cinq d'un coup, qui laisseraient croire a
   * un effet la ou il n'y en a pas.
   *
   * Contrairement a `evaluation`, **aucune seance n'est ecartee** : on decrit
   * ici ce qui s'est passe, pas ce qu'il faut viser ensuite. Une seance
   * abandonnee merite tout autant d'etre annotee.
   */
  jugements_par_seance(seances) {
    const parSeance = {};
    for (const seance of seances) {
      const jugements = {};
      for (const exercice of seance.exercices ?? []) {
        jugements[exercice.nom] =
          this.juger(exercice) ?? {
            // Hors bareme : pas d'objectif chiffre, mais un ressenti reste
            // utile — il pilote la vieille progression « +1 repetition ».
            base: null,
            reussi: this._reussite_brute(exercice),
            ressenti: exercice.ressenti || null,
          };
      }
      parSeance[seance.id ?? null] = jugements;
    }
    return parSeance;
  }

  evaluation_seance(seance_id, seances) {
    return this.jugements_par_seance(seances)[seance_id] ?? {};
  }

  /**
   * Reussite d'un exercice sans bareme : toutes les series, toute la cible.
   *
   * Le bareme est le juge normal, mais il ne couvre que les exercices qu'il
   * connait. Pour les autres, la seule lecture disponible est la comparaison
   * directe des series realisees a la consigne.
   */
  _reussite_brute(exercice) {
    const series = (exercice.series_detaillees ?? []).filter((s) => s.completee);
    if (!series.length || series.length < (exercice.series_cibles || 0)) {
      return false;
    }

    if (UNITE_PAR_MODE[exercice.mode] === UNITE_SECONDES) {
      const cible = exercice.duree_cible || 0;
      return series.every((s) => (s.duree || 0) >= cible);
    }
    const cible = exercice.repetitions_cibles || 0;
    return series.every((s) => (s.repetitions || 0) >= cible);
  }
}
