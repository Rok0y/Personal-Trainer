// Le moteur de progression d'un profil, assemble en un seul endroit.
//
// L'application le construisait dans sa page, et le simulateur
// (`dev/progression.html`) a besoin du meme : deux assemblages, c'est deux
// moteurs qui finissent par differer d'une dependance, et un simulateur qui
// decrit un autre moteur que celui qui joue. **Toute page qui veut le moteur
// d'un profil passe par `construire_progression`.**
//
// Le module ne lit rien : ni profil, ni historique, ni fichier. Il recoit les
// tables composees (`composer_baremes`), le materiel du profil et le catalogue
// des variantes (`catalogue_depuis`).

import { Baremes } from "./paliers.js";
import { Niveaux } from "./niveaux.js";
import { Ressenti } from "./ressenti.js";
import { Ligues } from "./ligues.js";
import { Calibration } from "./calibration.js";
import { Objectifs } from "./objectifs.js";
import { Variantes } from "./variantes.js";

/**
 * Le moteur d'un profil : `{baremes, niveaux, ressenti, ligues, calibration,
 * objectifs, variantes}`.
 *
 * A reconstruire quand le materiel change : `Baremes` normalise l'inventaire
 * une fois pour toutes, et tout le reste en derive.
 */
export function construire_progression(tables_baremes, materiel, catalogue_variantes) {
  const baremes = new Baremes(tables_baremes, materiel ?? null);
  const niveaux = new Niveaux(baremes);
  // Les ecrans s'en servent aussi pour *juger* une seance passee (« reussi »
  // ou « non atteint », et quelles reponses proposer), pas seulement le
  // moteur pour calculer un objectif.
  const ressenti = new Ressenti(baremes, niveaux);
  // Les ligues derivent du bareme, donc elles se refont avec lui quand le
  // materiel change. La calibration en depend — la note se traduit par
  // leurs bornes.
  const ligues = new Ligues(baremes, tables_baremes.ligues);
  const calibration = new Calibration(
    baremes, ligues, niveaux, ressenti, tables_baremes.note_athlete,
  );
  return {
    baremes,
    niveaux,
    calibration,
    ressenti,
    ligues,
    // Le catalogue des variantes y entre pour la regle du palier 1 : un
    // exercice atteint en remontant la chaine part du bas de son bareme.
    objectifs: new Objectifs(baremes, niveaux, ressenti, calibration, catalogue_variantes),
    // Les variantes plus faciles jouees a la place d'un mouvement. Le bareme
    // y entre pour l'unite, le materiel et la performance de retour, les
    // niveaux pour lire ce qu'une seance a prouve (`montees`), la table de
    // depart pour le premier mouvement de chaque famille (`selon_la_note`).
    variantes: new Variantes(
      baremes, tables_baremes.variantes?.retour ?? {}, niveaux, tables_baremes.variantes?.depart ?? {},
    ),
  };
}

/**
 * La table des variantes qu'un profil joue **en ce moment** : sa preference,
 * completee du mouvement de depart de chaque famille jamais jouee.
 *
 * Le depart suit la note **effective** (la mesuree quand elle a assez monte),
 * la meme que celle qui fixe le palier de depart dans `objectifs.js` : le
 * mouvement et son palier viennent ainsi de la meme note. L'application et
 * le simulateur lisent la table par ici ; a l'appelant de l'enregistrer au
 * demarrage d'une seance (`Variantes.selon_la_note` dit pourquoi).
 *
 * `lecture` vaut `{seances, ancrages, note}`, comme ce que recoit
 * `objectifs_par_exercice`.
 */
export function variantes_en_cours(moteur, preference, lecture, catalogue_variantes) {
  const { seances, ancrages, note } = lecture;
  const effective = moteur.calibration.note_effective(
    note?.declaree ?? null,
    moteur.calibration.note_mesuree(seances, ancrages),
  );
  return moteur.variantes.selon_la_note(preference, effective, seances, ancrages, catalogue_variantes);
}
