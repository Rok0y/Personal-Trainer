// **c'est ici que le moteur pilote les
// seances**.
//
// Le principe directeur de tout `progression/` est la distinction niveau /
// objectif, et rien ne doit la brouiller. Le *niveau* est le plus haut palier
// **jamais** valide : un record, une preuve stricte, qui ne recule jamais.
// L'*objectif* est ce que la prochaine seance demande : un plan, qui monte ou
// descend selon la reussite et le ressenti. Un objectif peut donc
// legitimement passer **sous** le niveau — c'est un delestage, pas une
// regression, et l'ecran des records continue d'afficher le niveau acquis.

import { UNITE_SECONDES } from "./paliers.js";
import { UNITE_PAR_MODE } from "./niveaux.js";
import { definir_cible_manuelle, est_cible_manuelle } from "./cible_manuelle.js";
import { chaine } from "./variantes.js";

export {
  profils_cible_manuelle,
  est_cible_manuelle,
  definir_cible_manuelle,
  fusionner_cible_manuelle,
  enteriner_cibles_manuelles,
} from "./cible_manuelle.js";

/** Les blocs JSON nomment l'exercice `exercice`, les blocs exportes `nom`. */
function _nom_exercice(bloc) {
  return bloc.exercice ?? bloc.nom;
}

export class Objectifs {
  /**
   * `catalogue_variantes` est celui de `variantes.js` (`catalogue_depuis`) :
   * il dit quel exercice vient d'une variante plus facile. Vide, la regle du
   * palier 1 ne s'applique a rien.
   */
  constructor(baremes, niveaux, ressenti, calibration, catalogue_variantes = {}) {
    this.baremes = baremes;
    this.niveaux = niveaux;
    this.ressenti = ressenti;
    this.calibration = calibration;
    this.catalogue_variantes = catalogue_variantes ?? {};
  }

  /** Une variante plus facile de `nom` a-t-elle deja un niveau ? */
  _monte_d_une_variante(nom, etats) {
    return chaine(nom, this.catalogue_variantes)
      .slice(1)
      .some((facile) => (etats[facile]?.niveau ?? null) !== null);
  }

  /**
   * Palier a viser pour chaque exercice suivi.
   *
   * Trois regles, dans cet ordre.
   *
   * 1. **Le repere de la derniere seance** : le palier alors demande, plus ou
   *    moins ce que la reussite et le ressenti lui valent.
   * 2. **Un exercice jamais fait** — aucun repere, aucun niveau prouve — part
   *    du palier de la note d'athlete effective, sauf s'il vient d'une
   *    variante plus facile qui a deja un niveau : il part alors du palier 1.
   * 3. A defaut, `suivant` : le premier palier non valide, et si le bareme est
   *    epuise, le dernier palier atteint plutot que rien.
   *
   * Par-dessus 1 et 3, une **note relevee a la main** pose un plancher sur la
   * prochaine seance, une fois, sans rien valider.
   *
   * `note` vaut `{declaree, relevee_apres}` (`calibration.note_du_profil`) :
   * passee en argument, comme les ancrages : le module ne lit pas le profil.
   */
  objectifs_par_exercice(seances, ancrages = {}, note = { declaree: null, relevee_apres: null }) {
    const reperes = this.ressenti.evaluation(seances, ancrages);
    const etats = this.niveaux.etats_niveaux(seances, ancrages);
    const depart = this.calibration.note_effective(
      note.declaree ?? null,
      this.calibration.note_mesuree(seances, ancrages),
    );

    const objectifs = {};
    for (const [nom, etat] of Object.entries(etats)) {
      const repere = reperes[nom];
      const vise = repere ? this.baremes.palier(nom, repere.vise) : null;
      if (vise === null && etat.niveau === null) {
        // Venu d'une variante plus facile deja maitrisee : le bas du bareme,
        // et non le depart de la note, pose pour le mouvement complet.
        objectifs[nom] = this._monte_d_une_variante(nom, etats)
          ? this.baremes.palier(nom, 1)
          : this.baremes.palier(nom, this.calibration.niveau_de_depart(nom, depart));
        continue;
      }
      let objectif = vise ?? etat.suivant ?? etat.actuel;
      const plancher = this.calibration.niveau_plancher(nom, note, repere);
      if (objectif && plancher && objectif.niveau < plancher) {
        objectif = this.baremes.palier(nom, plancher);
      }
      objectifs[nom] = objectif;
    }
    return objectifs;
  }

  /**
   * Exercices dont rien ne prouve le niveau : ni historique, ni ancrage.
   *
   * Ne sert plus qu'a l'affichage : le badge « 1re fois » des exercices dont
   * la cible vient de la note d'athlete et non de l'historique.
   */
  exercices_sans_donnees(seances, ancrages = {}) {
    const sans = new Set();
    for (const [nom, etat] of Object.entries(
      this.niveaux.etats_niveaux(seances, ancrages)
    )) {
      if (etat.niveau === null) sans.add(nom);
    }
    return sans;
  }

  /**
   * Ce couple exercice/mode releve-t-il du moteur ? Un bloc qui n'en releve
   * pas garde la cible de son fichier.
   */
  _pilote_par_le_moteur(nom, mode) {
    if (!this.baremes.est_suivi_par_le_moteur(nom)) return false;
    return UNITE_PAR_MODE[mode] === this.baremes.unite(nom);
  }

  /** Palier a viser pour un bloc, ou null si le moteur ne le pilote pas. */
  objectif_pour(nom, mode, objectifs) {
    if (!this._pilote_par_le_moteur(nom, mode)) return null;
    return objectifs[nom] ?? null;
  }

  /**
   * Reecrit les cibles des blocs (dictionnaires) pilotes par le moteur.
   *
   * Modifie les objets sur place et les rend, pour servir aussi bien a la
   * construction d'une seance qu'a son affichage — les deux doivent montrer
   * la meme chose, sinon l'accueil annonce une cible que la seance ne joue
   * pas.
   */
  appliquer_a_blocs(blocs, objectifs, utilisateur_id) {
    for (const bloc of blocs) {
      if (est_cible_manuelle(bloc, utilisateur_id)) continue;
      const palier_vise = this.objectif_pour(_nom_exercice(bloc), bloc.mode, objectifs);
      if (palier_vise === null) continue;
      bloc.poids = palier_vise.poids;
      bloc.series = palier_vise.series;
      if (palier_vise.unite === UNITE_SECONDES) bloc.duree = palier_vise.cible;
      else bloc.repetitions = palier_vise.cible;
    }
    return blocs;
  }

  /**
   * Repere les cibles saisies a la main, en les comparant au moteur.
   *
   * **L'utilisateur n'a pas a declarer qu'il fait une exception** : editer une
   * cible, c'est s'ecarter de ce que le moteur propose, et c'est cet ecart qui
   * est detecte. Remettre la valeur sur le palier propose efface la marque et
   * rebranche le bloc sur le moteur, sans rien a cocher.
   *
   * A n'appeler que depuis une edition d'utilisateur. L'appeler a la fin d'une
   * seance comparerait des valeurs posees par le moteur a un objectif qui a pu
   * changer entre-temps, et marquerait manuel tout ce qui a progresse.
   *
   * Un exercice jamais fait n'a plus de cas a part : il recoit le palier de la
   * note d'athlete, qui est un vrai palier, donc la comparaison est juste.
   */
  marquer_cibles_manuelles(blocs, objectifs, utilisateur_id) {
    for (const bloc of blocs) {
      const palier_vise = this.objectif_pour(_nom_exercice(bloc), bloc.mode, objectifs);

      let manuelle = false;
      if (palier_vise !== null) {
        const cible =
          palier_vise.unite === UNITE_SECONDES ? bloc.duree || 0 : bloc.repetitions || 0;
        manuelle = !(
          (bloc.poids || 0) === palier_vise.poids &&
          (bloc.series || 0) === palier_vise.series &&
          cible === palier_vise.cible
        );
      }

      const valeur = definir_cible_manuelle(
        bloc.cible_manuelle ?? null, manuelle, utilisateur_id
      );
      if (valeur === null) delete bloc.cible_manuelle;
      else bloc.cible_manuelle = valeur;
    }
    return blocs;
  }

  /** Meme chose sur un `Circuit` deja construit. */
  appliquer_a_circuit(circuit, objectifs, utilisateur_id) {
    for (const bloc of circuit.exercices) {
      if (est_cible_manuelle(bloc, utilisateur_id)) continue;
      const palier_vise = this.objectif_pour(bloc.exercice.nom, bloc.mode, objectifs);
      if (palier_vise === null) continue;
      bloc.poids = palier_vise.poids;
      bloc.nombre_series = palier_vise.series;
      if (palier_vise.unite === UNITE_SECONDES) bloc.duree = palier_vise.cible;
      else bloc.repetitions_par_serie = palier_vise.cible;
    }
    return circuit;
  }
}
