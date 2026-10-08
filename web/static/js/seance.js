// Monter une seance depuis les donnees de `donnees/`, et en ressortir des
// resultats enregistrables.
//
// Ces fonctions vivaient dans la page, ou elles etaient invisibles a toute
// verification. Elles portent pourtant des regles, dont une que `CLAUDE.md`
// designe comme un point d'entree unique : **les echauffements sont exclus a
// la source** (`resultats_par_exercice`). Aucune ligne d'echauffement ne doit
// atteindre l'historique, et le filtre vit ici plutot que dans chaque ecran
// qui relit.

import {
  BlocExercice,
  Circuit,
  Exercice,
  MODES_AVEC_DETECTION_OBLIGATOIRE,
  MODES_CIBLE_TEMPORELLE,
  MODES_CONNUS,
  MODE_REPETITIONS,
  cible_du_bloc,
  est_echauffement,
} from "./circuit.js";
import { DETECTIONS } from "./detections.js";

/**
 * Les mouvements avec leurs textes de fiche.
 *
 * `donnees/mouvements.json` porte ce qui est couple au code (detection,
 * erreurs, amplitude, orientation, changements, variantes, materiel) ;
 * `donnees/fiches.json` porte le texte, edite sur `dev/fiches.html`. Les
 * assembler au chargement plutot que de recopier le texte dans les mouvements
 * est ce qui fait qu'une fiche modifiee change vraiment l'application.
 *
 * Ne leve jamais : un mouvement sans fiche garde simplement des textes vides,
 * et `verifier_donnees.mjs` le signale a froid.
 */
export function avec_fiches(mouvements, fiches) {
  const complets = {};
  for (const [nom, mouvement] of Object.entries(mouvements)) {
    complets[nom] = { ...mouvement, ...(fiches[nom] ?? {}) };
  }
  return complets;
}

/**
 * Un `Exercice` depuis son entree de `mouvements.json` (fiche comprise).
 *
 * Les fonctions sont retrouvees par leur **nom** dans `DETECTIONS`, ce qui
 * dispense d'une table de correspondance qui deriverait. `detection` peut
 * valoir null — un echauffement guide sans
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
    sensations: fiche.sensations ?? [],
    erreurs: (fiche.erreurs ?? []).map((n) => DETECTIONS[n]).filter(Boolean),
    variante_facile: fiche.variante_facile,
    variante_difficile: fiche.variante_difficile,
    // `?? null` et non `?? undefined` : `sequence_orientation` refuse tout ce
    // qui n'est pas au vocabulaire, donc les deux se taisent — mais `null` est
    // la valeur qui dit « rien de sur a dire », et c'est celle que les
    // reponses figees attendent.
    orientation: fiche.orientation ?? null,
    amplitude: amplitude_pour(fiche.amplitude),
    changements: fiche.changements ?? [],
  });
}

/**
 * `[nom de fonction, cle]` de `mouvements.json`, vers `[fonction, cle]`.
 * Une fonction inconnue de `detections.js` rend null plutot qu'un couple
 * dont l'appel leverait a chaque image.
 */
export function amplitude_pour(exporte) {
  if (!Array.isArray(exporte)) return null;
  const fonction = DETECTIONS[exporte[0]];
  return fonction ? [fonction, exporte[1]] : null;
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
          // Comme `construire_circuit` : sans elle, une cible figee a l'ecran
          // etait reecrite par le moteur au moment de jouer, la marque n'etant
          // jamais arrivee jusqu'au circuit.
          cible_manuelle: bloc.cible_manuelle ?? false,
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
  // La cle est le bloc **et** le mouvement : un bloc passe a sa variante en
  // cours de seance donne deux lignes, celle du mouvement quitte (incomplete,
  // donc jugee en echec, ce qui est la verite) puis celle de la variante.
  // L'ordre d'arrivee des resultats les range d'eux-memes dans cet ordre.
  const par_ligne = new Map();
  for (const resultat of seance.resultats_series) {
    const bloc = seance.exercices[resultat.index_exercice];
    if (!bloc || est_echauffement(bloc)) continue;
    const nom = resultat.exercice ?? bloc.exercice.nom;
    const cle = `${resultat.index_exercice}|${nom}`;
    if (!par_ligne.has(cle)) {
      // Un mouvement quitte **sans aucune serie** a quand meme sa ligne, juste
      // avant celle-ci : on bascule le plus souvent des la premiere tentative,
      // et sans elle l'historique ne saurait pas qu'il y a eu bascule — la fin
      // de seance ne proposerait jamais de garder la variante. Meme regle que
      // `Circuit.exporter_resultats`.
      for (const abandon of bloc.abandons ?? []) {
        const vide = `${resultat.index_exercice}|${abandon.nom}`;
        if (abandon.nom !== nom && !par_ligne.has(vide)) {
          par_ligne.set(vide, { bloc, nom: abandon.nom, series: [] });
        }
      }
      par_ligne.set(cle, { bloc, nom, series: [] });
    }
    par_ligne.get(cle).series.push(resultat);
  }

  return [...par_ligne.values()].map(({ bloc, nom, series }) => {
    // Un mouvement quitte garde ce qu'il demandait au moment ou on l'a quitte :
    // le bloc, lui, porte deja la cible de la variante.
    const abandon =
      nom === bloc.exercice.nom
        ? null
        : [...(bloc.abandons ?? [])].reverse().find((a) => a.nom === nom) ?? null;
    const poids = abandon ? abandon.poids : bloc.poids;
    return {
      nom,
      series: series.length,
      repetitions: series.reduce((s, r) => s + (r.repetitions ?? 0), 0),
      poids,
      mode: bloc.mode,
      duree: series.reduce((s, r) => s + (r.duree ?? 0), 0),
      commentaire: bloc.commentaire,
      // Les cibles sont celles du bloc, pas du realise : c'est ce qui permet
      // de relire plus tard « demande 4x12, fait 4x10 ».
      series_cibles: abandon ? abandon.series : bloc.nombre_series,
      repetitions_cibles: abandon ? abandon.repetitions : bloc.repetitions_par_serie,
      duree_cible: abandon ? abandon.duree : bloc.duree,
      entrelace_avec: bloc.entrelace_avec,
      repos_entre_series: bloc.repos_entre_series,
      repos_apres: bloc.repos_apres,
      series_detaillees: series.map((r) => ({
        serie: r.serie,
        repetitions: r.repetitions,
        poids,
        duree: r.duree,
        completee: r.completee,
      })),
    };
  });
}

//: Les phases pendant lesquelles le nom affiche n'est pas celui d'un
//: exercice.
const LIBELLES_DE_PHASE = {
  recuperation_serie: "Récupération",
  repos_exercice: "Repos",
  termine: "Séance terminée",
  abandonne: "Séance terminée",
};

/**
 * L'etat de seance tel que l'ecran le lit.
 *
 * **C'est le contrat de l'ecran** : `hud.js` ne lit que cet objet, fabrique
 * depuis le `Circuit` local et l'`etat` de la boucle.
 *
 * Les champs derives du circuit sont **relus ici** plutot que recopies dans
 * `etat` au fil de la boucle. Deux raisons : le circuit fait autorite, donc
 * une copie ne peut que se perimer ; et la boucle n'a alors rien a tenir a
 * jour pour l'affichage, ce qui retire une occasion d'oublier un champ.
 *
 * `commandes_autorisees` est le seul morceau de cet objet qui n'ait pas de
 * source cote circuit : il depend aussi du `statut` du pilote (en marche, en
 * pause).
 */
export function payload_etat(seance, etat, statut = "running", utilisateur_id = null) {
  const bloc = seance.bloc_actuel;
  const active = !["termine", "abandonne"].includes(seance.phase);
  const en_marche = ["running", "paused"].includes(statut);

  return {
    ...etat,

    // --- Ce que le circuit sait mieux que l'etat ---
    // La pause n'est pas une phase du circuit mais un etat du *pilote* : le
    // circuit continue d'exister tel quel, on cesse seulement de l'avancer,
    // et l'affichage n'a pas a connaitre la difference.
    phase: statut === "paused" ? "pause" : seance.phase,
    serie_actuelle: active ? seance.serie_actuelle : 0,
    nombre_series: active ? seance.nombre_series : 0,
    repetitions_cibles: active ? seance.repetitions_cibles : 0,
    temps_repos_restant: active ? seance.temps_restant : 0,
    poids: active ? seance.poids : 0,
    duree_session: seance.duree_totale,
    commentaire_exercice: bloc ? bloc.commentaire : "",
    exercice_actuel:
      LIBELLES_DE_PHASE[seance.phase] ??
      (seance.exercice_actuel ? seance.exercice_actuel.nom : etat.exercice_actuel),

    // --- Ce qui depend aussi du pilote ---
    statut_session: statut,
    series_terminees: active ? seance.series_terminees : 0,
    nombre_series_total: active ? seance.nombre_series_total : 0,
    exercices: active
      ? seance.exporter_configuration(seance.blocs_comptabilises, utilisateur_id)
      : [],
    echauffements: active
      ? seance.exporter_configuration(seance.blocs_echauffement, utilisateur_id)
      : [],
    echauffements_termines: active ? seance.series_echauffement_terminees : 0,
    dans_echauffement: active ? seance.dans_echauffement : false,
    // Le nom que le bouton « Plus facile » annonce, ou null : il se cache.
    variante_facile: active ? seance.variante_possible() : null,
    commandes_autorisees: {
      reset: en_marche,
      recommencer: en_marche,
      precedente: en_marche && active && seance.serie_actuelle > 1,
      suivante: en_marche && active && seance.serie_actuelle < seance.nombre_series,
      // Independant de la phase et de l'index courant : seule compte
      // l'existence d'une serie deja terminee.
      refaire: en_marche && active && seance.peut_refaire_derniere_serie(),
      terminer: en_marche,
      passer_pause:
        en_marche &&
        active &&
        ["recuperation_serie", "repos_exercice"].includes(seance.phase),
      terminer_seance: en_marche,
      abandonner: en_marche,
      variante_facile: en_marche && active && seance.variante_possible() !== null,
    },
  };
}


/**
 * Le catalogue reellement joue : le fichier, puis ce que l'appareil a modifie.
 *
 * **L'appareil gagne**, et c'est un arbitrage. Le fichier deploye reste la
 * source de depart, mais une seance modifiee ici ne doit pas etre reecrite au
 * prochain deploiement : l'edition a ete faite en connaissance de cause,
 * souvent loin de l'ordinateur, et la perdre sans prevenir serait le pire des
 * deux mondes.
 *
 * Corollaire a rendre visible a l'ecran : une correction faite sur
 * l'ordinateur n'atteindra plus cette seance tant qu'elle est locale. D'ou
 * `oublier_seance_locale`, qui la rend au fichier.
 */
export function catalogue_effectif(du_fichier, locales) {
  return { ...du_fichier, ...(locales ?? {}) };
}

/**
 * Refuse une liste de blocs que la seance ne saurait pas jouer.
 *
 * Mieux vaut un refus a l'enregistrement qu'une erreur en pleine seance,
 * quand on est a deux metres de l'ecran et deja echauffe. Les refus : un
 * exercice inconnu, un mode inconnu, un mode qui exige une detection sur un
 * mouvement qui n'en a pas, et une cible nulle dans l'unite jouee.
 *
 * Rend la liste des problemes plutot que de lever au premier : un formulaire
 * doit pouvoir tout signaler d'un coup.
 */
export function problemes_des_blocs(mouvements, blocs) {
  const problemes = [];
  if (!blocs.length) problemes.push("Au moins un exercice est requis.");

  for (const bloc of blocs) {
    const nom = bloc.exercice;
    const fiche = mouvements[nom];
    if (!fiche) {
      problemes.push(`Exercice inconnu : ${nom}`);
      continue;
    }
    const mode = bloc.mode ?? MODE_REPETITIONS;
    if (!MODES_CONNUS.includes(mode)) {
      problemes.push(`Mode inconnu : ${mode}`);
      continue;
    }
    if (MODES_AVEC_DETECTION_OBLIGATOIRE.includes(mode) && !fiche.detection) {
      problemes.push(
        `${nom} n'a pas de detection de pose : le mode « ${mode} » ne peut pas ` +
          "l'utiliser. Passe-le en chrono ou en echauffement."
      );
    }
    // Un bloc porte les deux unites a la fois ; seul le mode dit laquelle est
    // jouee. Une cible nulle **dans cette unite-la** termine la serie a la
    // premiere image, et la seance entiere s'annonce finie avant d'avoir
    // commence — c'est un refus a l'enregistrement, pas une surprise en seance.
    if (cible_du_bloc({ ...bloc, mode }) <= 0) {
      problemes.push(
        MODES_CIBLE_TEMPORELLE.includes(mode)
          ? `${nom} : le mode « ${mode} » se joue au temps. Mets une duree ` +
            "superieure a zero (les repetitions ne sont pas jouees)."
          : `${nom} : mets un nombre de repetitions superieur a zero.`
      );
    }
  }
  return problemes;
}
