// Jumeau de progression/objectifs.py — **c'est ici que le moteur pilote les
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
import { CIBLE_TEST } from "./calibration.js";
import { est_cible_manuelle } from "./cible_manuelle.js";

export {
  profils_cible_manuelle,
  est_cible_manuelle,
  definir_cible_manuelle,
  fusionner_cible_manuelle,
} from "./cible_manuelle.js";

/** Les blocs JSON nomment l'exercice `exercice`, les blocs exportes `nom`. */
function _nom_exercice(bloc) {
  return bloc.exercice ?? bloc.nom;
}

export class Objectifs {
  constructor(baremes, niveaux, ressenti, calibration) {
    this.baremes = baremes;
    this.niveaux = niveaux;
    this.ressenti = ressenti;
    this.calibration = calibration;
  }

  /**
   * Palier a viser pour chaque exercice suivi.
   *
   * Deux regles, dans cet ordre.
   *
   * 1. **Le repere de la derniere seance** : le palier alors demande, plus ou
   *    moins ce que la reussite et le ressenti lui valent. C'est ce qui permet
   *    de sauter plusieurs crans quand c'etait trop facile, et de reculer
   *    quand c'etait trop dur.
   * 2. A defaut de repere — premier passage, cible d'epoque indechiffrable, ou
   *    ancrage plus recent que la derniere seance —, `suivant` : le premier
   *    palier non valide. Et si le bareme est epuise, le dernier palier
   *    atteint plutot que rien.
   */
  objectifs_par_exercice(seances, ancrages = {}) {
    const reperes = this.ressenti.evaluation(seances, ancrages);
    const etats = this.niveaux.etats_niveaux(seances, ancrages);

    const objectifs = {};
    for (const [nom, etat] of Object.entries(etats)) {
      const repere = reperes[nom];
      const vise = repere ? this.baremes.palier(nom, repere.vise) : null;
      objectifs[nom] = vise ?? etat.suivant ?? etat.actuel;
    }
    return objectifs;
  }

  /**
   * Exercices dont rien ne prouve le niveau : ni historique, ni ancrage.
   *
   * **Ne pas confondre avec « absent d'`objectifs_par_exercice` »**, qui ne se
   * produit jamais : `etat_niveau` propose toujours `suivant`, c'est-a-dire le
   * palier 1, pour quelqu'un qui n'a rien fait. C'est un objectif par defaut,
   * pas un objectif mesure — et le prendre pour tel a exactement l'effet qu'on
   * veut eviter, programmer un debutant au hasard. Le signal fiable est
   * `niveau === null`, que `niveaux.js` documente comme « hors bareme » et non
   * « niveau 0 ».
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
   * Ce couple exercice/mode releve-t-il du moteur, objectif ou pas ?
   *
   * Separe d'`objectif_pour` parce que « le moteur ne pilote pas ce bloc » et
   * « le moteur le pilote mais n'a encore rien a proposer » demandent deux
   * reponses **opposees** : la premiere laisse la cible du fichier, la seconde
   * declenche un test de calibration.
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
   * Cet exercice doit-il etre teste au maximum avant d'etre programme ?
   *
   * Rien n'est stocke : le test pose un ancrage, cet ancrage donne un niveau,
   * et la question ne se repose plus — meme principe que le reste du moteur,
   * ou tout se derive au lieu de se marquer.
   */
  a_calibrer(nom, mode, sans_donnees) {
    if (!this._pilote_par_le_moteur(nom, mode)) return false;
    return sans_donnees.has(nom);
  }

  /**
   * Reecrit les cibles des blocs (dictionnaires) pilotes par le moteur.
   *
   * Modifie les objets sur place et les rend, pour servir aussi bien a la
   * construction d'une seance qu'a son affichage — les deux doivent montrer
   * la meme chose, sinon l'accueil annonce une cible que la seance ne joue
   * pas.
   */
  appliquer_a_blocs(blocs, objectifs, sans_donnees, utilisateur_id) {
    for (const bloc of blocs) {
      if (est_cible_manuelle(bloc, utilisateur_id)) continue;
      const nom = _nom_exercice(bloc);

      // **Marque, jamais reecrit** : ces dictionnaires servent a l'affichage,
      // mais repartent en ecriture depuis le formulaire d'objectifs. Y poser
      // la cible du test graverait `1 x 999` dans le fichier de seances. La
      // cible reelle du test est posee sur le `Circuit`, qui lui ne repart
      // jamais sur le disque tel quel.
      if (this.a_calibrer(nom, bloc.mode, sans_donnees)) {
        bloc.test_max = true;
        bloc.poids_test = this.calibration.charge_de_test(nom);
        continue;
      }
      delete bloc.test_max;
      delete bloc.poids_test;

      const palier_vise = this.objectif_pour(nom, bloc.mode, objectifs);
      if (palier_vise === null) continue;
      bloc.poids = palier_vise.poids;
      bloc.series = palier_vise.series;
      if (palier_vise.unite === UNITE_SECONDES) bloc.duree = palier_vise.cible;
      else bloc.repetitions = palier_vise.cible;
    }
    return blocs;
  }

  /** Meme chose sur un `Circuit` deja construit. */
  appliquer_a_circuit(circuit, objectifs, sans_donnees, utilisateur_id) {
    for (const bloc of circuit.exercices) {
      if (est_cible_manuelle(bloc, utilisateur_id)) continue;

      const nom = bloc.exercice.nom;
      // Un exercice sans le moindre repere n'est pas programme, il est
      // **mesure** : une serie unique au maximum, a charge moyenne, terminee a
      // la main. L'ancrage se pose des la serie finie, et la seance d'apres le
      // trouvera dans `objectifs`.
      bloc.test_max = this.a_calibrer(nom, bloc.mode, sans_donnees);
      if (bloc.test_max) {
        // La definition d'origine est mise de cote : la seance finie est
        // reecrite depuis ce meme bloc, et y graver `1 x 999` remplacerait
        // definitivement l'exercice par son test.
        bloc.avant_test = {
          nombre_series: bloc.nombre_series,
          poids: bloc.poids,
          repetitions_par_serie: bloc.repetitions_par_serie,
          duree: bloc.duree,
        };
        bloc.nombre_series = 1;
        bloc.poids = this.calibration.charge_de_test(nom);
        if (this.baremes.unite(nom) === UNITE_SECONDES) bloc.duree = CIBLE_TEST;
        else bloc.repetitions_par_serie = CIBLE_TEST;
        continue;
      }
      bloc.avant_test = null;

      const palier_vise = this.objectif_pour(nom, bloc.mode, objectifs);
      if (palier_vise === null) continue;
      bloc.poids = palier_vise.poids;
      bloc.nombre_series = palier_vise.series;
      if (palier_vise.unite === UNITE_SECONDES) bloc.duree = palier_vise.cible;
      else bloc.repetitions_par_serie = palier_vise.cible;
    }
    return circuit;
  }
}
