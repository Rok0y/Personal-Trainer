// Monter une seance depuis les donnees exportees, et en ressortir des
// resultats enregistrables.
//
// Ces trois fonctions vivaient dans la page, ou elles etaient invisibles a
// toute verification. Elles portent pourtant des regles, dont une que
// `CLAUDE.md` designe comme un point d'entree unique : **les echauffements
// sont exclus a la source**, comme le fait `Circuit.exporter_resultats` cote
// Python. Aucune ligne d'echauffement ne doit atteindre l'historique, et le
// filtre vit ici plutot que dans chaque ecran qui relit.

import {
  BlocExercice,
  Circuit,
  Exercice,
  MODE_REPETITIONS,
  est_echauffement,
} from "./circuit.js";
import { DETECTIONS } from "./detections.js";

/**
 * Un `Exercice` depuis sa fiche exportee.
 *
 * Les fonctions sont retrouvees par leur **nom** : `detections.js` porte les
 * memes que le Python, c'est ce qui dispense d'une table de correspondance qui
 * deriverait. `detection` peut valoir null — un echauffement guide sans
 * analyse de pose, et `circuit.js` le sait.
 */
export function exercice_pour(mouvements, nom) {
  const fiche = mouvements[nom];
  if (!fiche) throw new Error(`Mouvement inconnu : ${nom}`);
  return new Exercice({
    nom: fiche.nom,
    detection: fiche.detection ? DETECTIONS[fiche.detection] ?? null : null,
    description: fiche.description,
    instructions: fiche.instructions,
    mise_en_place: fiche.mise_en_place,
    erreurs_frequentes: fiche.erreurs_frequentes,
    erreurs: (fiche.erreurs ?? []).map((n) => DETECTIONS[n]).filter(Boolean),
    variante_facile: fiche.variante_facile,
    variante_difficile: fiche.variante_difficile,
  });
}

/** Un `Circuit` depuis la definition JSON d'une seance. */
export function circuit_pour(mouvements, blocs) {
  return new Circuit(
    blocs.map(
      (bloc) =>
        new BlocExercice({
          exercice: exercice_pour(mouvements, bloc.exercice),
          poids: bloc.poids ?? 0,
          mode: bloc.mode ?? MODE_REPETITIONS,
          nombre_series: bloc.series ?? 1,
          repetitions_par_serie: bloc.repetitions ?? 0,
          duree: bloc.duree ?? 0,
          repos_entre_series: bloc.repos_entre_series ?? 0,
          repos_apres: bloc.repos_apres ?? 0,
          commentaire: bloc.commentaire ?? "",
          entrelace_avec: bloc.entrelace_avec ?? null,
        })
    )
  );
}

/**
 * Les resultats d'une seance, regroupes par exercice et prets pour
 * `historique.enregistrer_seance`.
 *
 * Les echauffements sont filtres **ici et nulle part ailleurs** : c'est la
 * frontiere entre « ce qui a ete joue » et « ce qui compte ». Un exercice
 * entrelace apparait une seule fois, ses series venant de plusieurs
 * aller-retours — d'ou le regroupement par index de bloc et non par ordre
 * d'arrivee.
 */
export function resultats_par_exercice(seance) {
  const par_index = new Map();
  for (const resultat of seance.resultats_series) {
    const bloc = seance.exercices[resultat.index_exercice];
    if (!bloc || est_echauffement(bloc)) continue;
    if (!par_index.has(resultat.index_exercice)) {
      par_index.set(resultat.index_exercice, { bloc, series: [] });
    }
    par_index.get(resultat.index_exercice).series.push(resultat);
  }

  return [...par_index.values()].map(({ bloc, series }) => ({
    nom: bloc.exercice.nom,
    series: series.length,
    repetitions: series.reduce((s, r) => s + (r.repetitions ?? 0), 0),
    poids: bloc.poids,
    mode: bloc.mode,
    duree: series.reduce((s, r) => s + (r.duree ?? 0), 0),
    commentaire: bloc.commentaire,
    // Les cibles sont celles du bloc, pas du realise : c'est ce qui permet de
    // relire plus tard « demande 4x12, fait 4x10 ».
    series_cibles: bloc.nombre_series,
    repetitions_cibles: bloc.repetitions_par_serie,
    duree_cible: bloc.duree,
    entrelace_avec: bloc.entrelace_avec,
    repos_entre_series: bloc.repos_entre_series,
    repos_apres: bloc.repos_apres,
    series_detaillees: series.map((r) => ({
      serie: r.serie,
      repetitions: r.repetitions,
      poids: bloc.poids,
      duree: r.duree,
      completee: r.completee,
    })),
  }));
}
