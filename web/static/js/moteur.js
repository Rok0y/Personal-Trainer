// Jumeau de session/moteur.py — ce qui fait avancer une serie, image par image.
//
// Meme convention que les autres jumeaux : les noms sont ceux du Python, en
// snake_case. Le Python fait autorite ; `scripts/comparer_seances.mjs` rejoue
// les memes images des deux cotes et diffe.
//
// Une difference d'architecture, et une seule : cote Python, `moteur.py`
// importe `annoncer_progression` et `annoncer_temps_restant` d'`audio.coach`.
// Ici elles sont **dans ce module**, parce que ce sont des decisions et non du
// son : quand annoncer n'est pas la meme chose que comment jouer. Tout ce qui
// sort vers le haut-parleur passe par le `coach` injecte, ce qui rend le
// module pur et donc verifiable.
//
// `etat` est un objet libre (le jumeau d'`EtatSeance`) : le moteur ne
// l'importe pas, il le recoit — exactement comme en Python, ou c'est ce qui a
// rendu le module agnostique le jour ou l'etat a change de forme.

import {
  MODE_AMRAP,
  MODE_CHRONO,
  MODE_ECHAUFFEMENT,
  MODE_MAINTIEN,
  MODE_REPETITIONS,
} from "./circuit.js";

// Un ecart plus long que ca entre deux images vient forcement d'une
// interruption du flux (utilisateur hors champ, onglet suspendu par iOS,
// image lente) : on ne le comptabilise pas d'un bloc au retour. S'applique a
// tous les modes qui cumulent des deltas image par image — maintien et
// echauffement — et non au seul echauffement, d'ou le nom.
export const INTERVALLE_MAX = 0.5;

// Quel compteur de l'etat porte la duree realisee, selon le mode. Un mode
// absent d'ici ne mesure pas de temps.
export const COMPTEUR_DUREE_PAR_MODE = {
  [MODE_MAINTIEN]: "temps_maintien",
  [MODE_CHRONO]: "temps_chrono",
  [MODE_ECHAUFFEMENT]: "temps_echauffement",
};

/**
 * Les paliers d'encouragement d'une serie comptee.
 *
 * Vit ici et non dans la couche audio : c'est une decision de coaching, qui
 * doit rester identique des deux cotes, alors que jouer le son ne l'est pas.
 */
export function annoncer_progression(coach, repetitions, cible) {
  const restantes = cible - repetitions;
  if (restantes === 0) return coach("fin_serie");
  if (restantes === 1) return coach("avant_derniere");
  if (restantes === 3) return coach("encore_3");
  if (restantes === 5) coach("encore_5");
  // **« A la moitie » a ete retire** des deux cotes, avec sa cle et sa
  // priorite : une cle qui ne sert plus laisse croire qu'un palier existe.
  // Elle tombait en plein milieu de la serie, entre deux chiffres, et
  // n'apprenait rien qu'on ne sache deja — le coach comptait par-dessus
  // lui-meme.
}

/**
 * Annonce le temps restant au franchissement d'un seuil, jamais en continu.
 *
 * Le repere est `bloc.temps_restant_precedent` : c'est la *traversee* du seuil
 * qui declenche, donc la premiere image d'une serie ne dit rien — elle ne fait
 * que poser le repere.
 */
export function annoncer_temps_restant(coach, bloc, secondes_restantes) {
  if (bloc.temps_restant_precedent === null || bloc.temps_restant_precedent === undefined) {
    bloc.temps_restant_precedent = secondes_restantes;
    return;
  }
  // Les six memes seuils qu'en Python, dans le meme ordre : le decompte des
  // trois dernieres secondes en fait partie. `comparer_seances.mjs` compare
  // les annonces pas a pas, donc un seuil ajoute d'un seul cote s'y voit.
  const seuils = [
    [20, "temps_20"],
    [10, "temps_10"],
    [5, "temps_5"],
    [3, "temps_3"],
    [2, "temps_2"],
    [1, "temps_1"],
  ];
  for (const [seuil, message] of seuils) {
    if (bloc.temps_restant_precedent > seuil && secondes_restantes <= seuil) {
      coach(message);
      break;
    }
  }
  bloc.temps_restant_precedent = secondes_restantes;
}

/**
 * Annonce le decompte d'un repos au franchissement d'un seuil.
 *
 * Jumeau d'`audio.coach.annoncer_temps_repos`. Meme forme que
 * `annoncer_temps_restant` ci-dessus, deux differences qui comptent : le
 * repere vit sur la **seance** et non sur le bloc (un repos n'appartient a
 * aucun bloc — il est entre deux), et les cles sont `repos_20` / `repos_10` /
 * `repos_5`.
 *
 * Le repere est remis a `null` au retour en phase `exercice`, cote appelant :
 * sans ca, le repos suivant hériterait du compte du precedent et annoncerait
 * un seuil deja franchi.
 *
 * @param {(cle: string) => void} coach — le coach injecte, jamais un global.
 * @param {object} seance — le Circuit, qui porte `repos_restant_precedent`.
 * @param {number} secondes_restantes — deja arrondi a l'entier par l'appelant.
 */
export function annoncer_temps_repos(coach, seance, secondes_restantes) {
  // Premier appel apres l'armement : poser le repere et sortir. Sans ca,
  // entrer en repos avec 9 secondes restantes annoncerait aussitot « 10
  // secondes », un seuil qu'on n'a jamais traverse.
  if (seance.repos_restant_precedent === null || seance.repos_restant_precedent === undefined) {
    seance.repos_restant_precedent = secondes_restantes;
    return;
  }
  const seuils = [
    [20, "repos_20"],
    [10, "repos_10"],
    [5, "repos_5"],
  ];
  for (const [seuil, message] of seuils) {
    // C'est la **traversee** qui declenche, pas le fait d'etre sous le seuil :
    // autrement l'annonce se repeterait a chaque image.
    if (seance.repos_restant_precedent > seuil && secondes_restantes <= seuil) {
      coach(message);
      // Une image lente peut faire passer de 21 a 4 secondes d'un coup : sans
      // ce `break`, les trois seuils partiraient en rafale.
      break;
    }
  }
  seance.repos_restant_precedent = secondes_restantes;
}

/**
 * Duree courante du bloc, lue dans le compteur de **son** mode.
 *
 * Ne jamais remplacer par une chaine `temps_maintien || temps_chrono ||
 * temps_echauffement` : les trois compteurs sont partages, et un gainage
 * abandonne avant la premiere seconde laisse `temps_maintien` a 0 — donc
 * falsy. La chaine retombait alors sur la duree du dernier echauffement, et
 * enregistrait 30 s pour une serie jamais tenue.
 */
export function duree_realisee(bloc, etat) {
  if (bloc === null || bloc === undefined) return 0;
  const champ = COMPTEUR_DUREE_PAR_MODE[bloc.mode];
  if (champ === undefined) return 0;
  return etat[champ] || 0;
}

/** Remet a zero les compteurs de duree partages entre les series. */
export function oublier_durees(etat) {
  for (const attribut of Object.values(COMPTEUR_DUREE_PAR_MODE)) {
    etat[attribut] = 0;
  }
  etat.chrono_termine = false;
}

/**
 * Termine la serie en cours et reinitialise les champs temporels du bloc.
 *
 * Factorise ce que les quatre `gerer_mode_*` repetaient, en deleguant le reset
 * a `Circuit.reinitialiser_etat_serie` pour qu'un seul endroit connaisse la
 * liste de ces attributs.
 */
function _finaliser_serie(seance, etat, bloc) {
  seance.terminer_serie();
  mettre_a_jour_prochain_exercice(seance, etat);
  seance.reinitialiser_etat_serie(bloc);
  oublier_durees(etat);
}

/**
 * Publie la premiere faute de forme detectee, ou efface le bandeau.
 *
 * Les fonctions de verification retournent une **cle**, pas une phrase : c'est
 * ici qu'elle est resolue. Une cle inconnue rend null, donc n'affiche rien.
 */
export function mettre_a_jour_erreur(exercice, corps, etat, texte) {
  let cle = null;
  for (const verifier of exercice.erreurs) {
    const trouvee = verifier(corps);
    if (trouvee) {
      cle = trouvee;
      break;
    }
  }
  etat.erreur = cle ? texte(cle) : null;
}

/**
 * Publie l'etape du mouvement, sous sa forme brute et sous sa forme lisible.
 *
 * Les deux, parce qu'elles ne servent pas au meme public : le jeton reste la
 * donnee du detecteur (et les modes s'en servent), le libelle est ce que lit
 * l'utilisateur.
 */
export function poser_etape(etat, jeton, libelle_etape) {
  etat.stage = jeton;
  etat.etape_libelle = libelle_etape(jeton);
}

// Les quatre fonctions de mode retournent toutes un triplet
// [derniere_rep, repetitions, serie_terminee]. Un mode qui en rendrait moins
// planterait a chaque image cote appelant — c'est un contrat, pas une
// convention.

export function gerer_mode_repetitions({
  corps, exercice, bloc, seance, compteur, etat, coach, derniere_rep, messages,
}) {
  let serie_terminee = false;
  mettre_a_jour_erreur(exercice, corps, etat, messages.texte);
  const stage_detecte = exercice.detection(corps);

  const [stage, repetitions] = compteur.mettre_a_jour(stage_detecte);

  if (repetitions > derniere_rep) {
    coach("compteur", repetitions);
    annoncer_progression(coach, repetitions, bloc.repetitions_par_serie);
    derniere_rep = repetitions;
  }

  poser_etape(etat, stage, messages.libelle_etape);
  etat.repetitions = repetitions;

  if (repetitions >= bloc.repetitions_par_serie) {
    seance.enregistrer_resultat_serie({ repetitions, completee: true });
    _finaliser_serie(seance, etat, bloc);
    compteur.reset();
    etat.repetitions = 0;
    derniere_rep = 0;
    serie_terminee = true;
  }

  return [derniere_rep, repetitions, serie_terminee];
}

export function gerer_mode_maintien({ corps, bloc, seance, etat, coach, messages }) {
  mettre_a_jour_erreur(bloc.exercice, corps, etat, messages.texte);
  const position = bloc.exercice.detection(corps);
  if (position === "maintien") bloc.position_maintien_validee = true;

  if (position !== "maintien" && bloc.position_maintien_validee === true) {
    coach("correction_gainage");
  }
  const maintenant = seance.maintenant();

  if (!("dernier_maintien" in bloc)) bloc.dernier_maintien = maintenant;

  const temps_ecoule = Math.min(maintenant - bloc.dernier_maintien, INTERVALLE_MAX);
  bloc.dernier_maintien = maintenant;

  if (position === "maintien") bloc.temps_maintien += temps_ecoule;

  // Bip chaque seconde. `int()` en Python tronque vers zero, comme
  // `Math.trunc` — le temps etant toujours positif ici, `Math.floor` ferait
  // pareil, mais on garde la traduction litterale.
  const seconde = Math.trunc(bloc.temps_maintien);
  const precedente = "derniere_seconde_bip" in bloc ? bloc.derniere_seconde_bip : -1;
  if (precedente !== seconde) {
    bloc.derniere_seconde_bip = seconde;
    coach("bip");
  }

  annoncer_temps_restant(coach, bloc, bloc.duree - bloc.temps_maintien);
  etat.repetitions = 0;
  poser_etape(etat, position, messages.libelle_etape);
  etat.temps_maintien = bloc.temps_maintien;
  etat.duree_maintien = bloc.duree;

  if (bloc.temps_maintien >= bloc.duree) {
    seance.enregistrer_resultat_serie({ duree: bloc.temps_maintien, completee: true });
    _finaliser_serie(seance, etat, bloc);
    return [0, 0, true];
  }

  return [0, 0, false];
}

export function gerer_mode_chrono({ bloc, seance, etat, coach }) {
  // Un chrono ne juge pas la forme : il n'a aucune faute a signaler, mais il
  // doit effacer celle du bloc precedent, sinon le bandeau reste affiche
  // pendant toute la duree du mouvement.
  etat.erreur = null;
  const maintenant = seance.maintenant();

  if (!("debut_chrono" in bloc)) bloc.debut_chrono = maintenant;

  bloc.temps_chrono = maintenant - bloc.debut_chrono;
  annoncer_temps_restant(coach, bloc, bloc.duree - bloc.temps_chrono);

  if (bloc.temps_chrono >= bloc.duree) {
    bloc.temps_chrono = bloc.duree;
    etat.temps_chrono = bloc.temps_chrono;
    etat.chrono_termine = true;

    seance.enregistrer_resultat_serie({ duree: bloc.temps_chrono, completee: true });
    _finaliser_serie(seance, etat, bloc);
    return [0, 0, true];
  }

  etat.temps_chrono = bloc.temps_chrono;
  etat.chrono_termine = false;

  return [0, 0, false];
}

export function gerer_mode_amrap({
  corps, bloc, compteur, seance, etat, coach, derniere_rep, messages,
}) {
  mettre_a_jour_erreur(bloc.exercice, corps, etat, messages.texte);
  const maintenant = seance.maintenant();

  if (!("debut_amrap" in bloc)) bloc.debut_amrap = maintenant;

  bloc.temps_amrap = maintenant - bloc.debut_amrap;
  annoncer_temps_restant(coach, bloc, bloc.duree - bloc.temps_amrap);

  const stage_detecte = bloc.exercice.detection(corps);
  const [stage, repetitions] = compteur.mettre_a_jour(stage_detecte);

  if (repetitions > derniere_rep) {
    coach("compteur", repetitions);
    derniere_rep = repetitions;
  }

  poser_etape(etat, stage, messages.libelle_etape);
  etat.repetitions = repetitions;
  etat.temps_amrap_restant = Math.max(0, bloc.duree - bloc.temps_amrap);

  if (bloc.temps_amrap >= bloc.duree) {
    seance.enregistrer_resultat_serie({ repetitions, completee: true });
    _finaliser_serie(seance, etat, bloc);
    compteur.reset();
    derniere_rep = 0;
    return [derniere_rep, repetitions, true];
  }

  return [derniere_rep, repetitions, false];
}

/**
 * Mouvement d'echauffement : un chrono guide, la detection est un bonus.
 *
 * Deux differences volontaires avec `gerer_mode_chrono` :
 *
 * - le temps est accumule image par image (comme le maintien) plutot que
 *   mesure depuis un `debut_chrono` mural. L'appelant n'appelant les modes que
 *   lorsqu'un corps est visible et hors pause, le chrono se met ainsi de
 *   lui-meme en pause quand l'utilisateur sort du champ ;
 * - `bloc.exercice.detection` peut etre nulle. Quand elle existe, elle
 *   n'alimente que l'affichage : elle ne conditionne jamais l'avancement du
 *   chrono, un echauffement ne doit pas pouvoir se bloquer.
 */
export function gerer_mode_echauffement({ corps, bloc, seance, etat, coach, messages }) {
  const maintenant = seance.maintenant();

  if (!("temps_echauffement" in bloc)) {
    bloc.temps_echauffement = 0;
    bloc.dernier_tick_echauffement = maintenant;
  }

  const delta = maintenant - bloc.dernier_tick_echauffement;
  bloc.dernier_tick_echauffement = maintenant;
  bloc.temps_echauffement += Math.min(delta, INTERVALLE_MAX);

  if (bloc.exercice.detection !== null && bloc.exercice.detection !== undefined) {
    mettre_a_jour_erreur(bloc.exercice, corps, etat, messages.texte);
    poser_etape(etat, bloc.exercice.detection(corps), messages.libelle_etape);
  } else {
    etat.erreur = null;
    poser_etape(etat, "echauffement", messages.libelle_etape);
  }

  annoncer_temps_restant(coach, bloc, bloc.duree - bloc.temps_echauffement);

  etat.repetitions = 0;
  etat.temps_echauffement = bloc.temps_echauffement;
  etat.duree_echauffement = bloc.duree;

  if (bloc.temps_echauffement >= bloc.duree) {
    bloc.temps_echauffement = bloc.duree;
    etat.temps_echauffement = bloc.duree;

    seance.enregistrer_resultat_serie({ duree: bloc.temps_echauffement, completee: true });
    _finaliser_serie(seance, etat, bloc);
    return [0, 0, true];
  }

  return [0, 0, false];
}

export function executer_mode({ seance, corps, compteur, etat, coach, derniere_rep, messages }) {
  const bloc = seance.bloc_actuel;
  etat.mode = bloc.mode;

  if (bloc.mode === MODE_REPETITIONS) {
    return gerer_mode_repetitions({
      corps, exercice: bloc.exercice, bloc, seance, compteur, etat, coach,
      derniere_rep, messages,
    });
  }
  if (bloc.mode === MODE_MAINTIEN) {
    return gerer_mode_maintien({ corps, bloc, seance, etat, coach, messages });
  }
  if (bloc.mode === MODE_CHRONO) {
    return gerer_mode_chrono({ bloc, seance, etat, coach });
  }
  if (bloc.mode === MODE_AMRAP) {
    return gerer_mode_amrap({
      corps, bloc, compteur, seance, etat, coach, derniere_rep, messages,
    });
  }
  if (bloc.mode === MODE_ECHAUFFEMENT) {
    return gerer_mode_echauffement({ corps, bloc, seance, etat, coach, messages });
  }

  throw new Error(`Mode inconnu : ${bloc.mode}`);
}

export function decrire_prochaine_etape(bloc, serie_actuelle, nombre_total_series = null) {
  if (bloc === null || bloc === undefined) return null;
  if (nombre_total_series === null) nombre_total_series = serie_actuelle;

  return {
    exercice: bloc.exercice.nom,
    poids: bloc.poids,
    serie_actuelle,
    nombre_total_series,
    series: serie_actuelle,
    repetitions: bloc.repetitions_par_serie,
    mode: bloc.mode,
    duree: bloc.duree,
    commentaire: bloc.commentaire,
  };
}

export function mettre_a_jour_prochain_exercice(circuit, etat) {
  // La fiche du prochain exercice suit le meme calcul que son libelle : elle
  // n'a de sens qu'entre deux exercices, et se recalcule ici plutot que dans
  // un second parcours du circuit.
  etat.fiche_suivante = null;

  if (circuit.phase === "preparation" || circuit.phase === "exercice") {
    const bloc = circuit.bloc_actuel;
    etat.prochaine_etape = decrire_prochaine_etape(
      bloc,
      circuit.serie_actuelle,
      bloc ? bloc.nombre_series : 0
    );
    return;
  }

  // Repos entre deux series : on reprend le meme exercice.
  if (circuit.phase === "recuperation_serie") {
    const bloc = circuit.bloc_actuel;
    if (bloc) {
      etat.prochaine_etape = decrire_prochaine_etape(
        bloc,
        circuit.serie_actuelle,
        bloc.nombre_series
      );
      return;
    }
  }

  // Repos entre deux exercices : on prepare le suivant.
  if (circuit.phase === "repos_exercice") {
    const prochain = circuit.prochain_bloc();
    if (prochain) {
      etat.prochaine_etape = decrire_prochaine_etape(prochain, 1, prochain.nombre_series);
      etat.fiche_suivante = prochain.exercice.fiche();
      return;
    }
  }

  etat.prochaine_etape = null;
}
