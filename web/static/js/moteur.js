// Ce qui fait avancer une serie, image par image.
//
// `scripts/comparer_seances.mjs` rejoue des images horodatees et compare
// l'etat et les annonces, pas a pas, a des reponses figees.
//
// Les decisions d'annonce (`annoncer_progression`, `annoncer_temps_restant`…)
// sont **dans ce module** et non dans la couche audio, parce que ce sont des
// decisions et non du son : quand annoncer n'est pas la meme chose que comment
// jouer. Tout ce qui sort vers le haut-parleur passe par le `coach` injecte,
// ce qui rend le module pur et donc verifiable.
//
// `etat` est un objet libre (voir `etat.js`) : le moteur ne l'importe pas, il
// le recoit — c'est ce qui le rend agnostique le jour ou l'etat change de
// forme.

import {
  MODE_AMRAP,
  MODE_CHRONO,
  MODE_ECHAUFFEMENT,
  MODE_MAINTIEN,
  MODE_REPETITIONS,
} from "./circuit.js";
import { CompteurMouvement } from "./compteur.js";
import { SuiviTentatives } from "./instruments.js";
import { SEUIL_IMMOBILE, vitesse_du_buste } from "./immobilite.js";

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
 * Vit ici et non dans la couche audio : c'est une decision de coaching, pas
 * une affaire de son.
 */
export function annoncer_progression(coach, repetitions, cible) {
  const restantes = cible - repetitions;
  if (restantes === 0) return coach("fin_serie");
  if (restantes === 1) return coach("avant_derniere");
  if (restantes === 3) return coach("encore_3");
  if (restantes === 5) coach("encore_5");
  // **« A la moitie » a ete retire**, avec sa cle et sa
  // priorite : une cle qui ne sert plus laisse croire qu'un palier existe.
  // Elle tombait en plein milieu de la serie, entre deux chiffres, et
  // n'apprenait rien qu'on ne sache deja — le coach comptait par-dessus
  // lui-meme.
}

/**
 * « Change de sens », « change de jambe ». Un changement est annonce quand
 * son instant tombe dans ]avant, apres] : chaque instant tombe dans un seul
 * intervalle, donc s'annonce une seule fois. La cle se deduit du mot ; un mot
 * inconnu est ignore par le lecteur, qui ne trouve aucun fichier.
 */
export function annoncer_changements(coach, bloc, avant, apres) {
  for (const [fraction, quoi] of bloc.exercice.changements ?? []) {
    if (avant < fraction * bloc.duree && fraction * bloc.duree <= apres) {
      coach(`changement_${quoi}`);
    }
  }
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
  // Six seuils, du plus grand au plus petit : le decompte des trois dernieres
  // secondes en fait partie. `comparer_seances.mjs` compare les annonces pas a
  // pas, donc un seuil ajoute ou retire s'y voit.
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
 * Meme forme que `annoncer_temps_restant` ci-dessus, deux differences qui comptent : le
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

// Les modes qui comptent des repetitions : les seuls ou les gestes ±1 ont un
// compte a corriger, et les seuls qui attendent qu'on soit en place.
export const MODES_A_COMPTE = [MODE_REPETITIONS, MODE_AMRAP];

// Combien de temps il faut rester immobile en position pour ouvrir une serie
// comptee. Assez pour qu'un passage par la position en marchant ou en prenant
// l'haltere ne suffise pas, assez peu pour ne pas faire attendre.
export const DUREE_MISE_EN_PLACE = 1.5;

/**
 * Ouvre la serie : « c'est parti ». Une fois par serie — le drapeau vit sur
 * le bloc (`CHAMPS_TEMPORELS`), si bien qu'une serie refaite, remise a zero
 * ou changee de variante se rouvre.
 */
function ouvrir_serie(bloc, coach) {
  bloc.serie_ouverte = true;
  coach("debut_serie");
}

/**
 * Attend qu'on soit en place avant d'ouvrir une serie comptee ; rend vrai
 * quand elle est ouverte.
 *
 * **Rien ne compte avant** : se rendre a sa place, prendre l'haltere, faire
 * un essai a vide passaient par les positions du mouvement, et le coach
 * comptait ou expliquait des repetitions que personne ne faisait. Etre en
 * place, c'est deux conditions tenues `DUREE_MISE_EN_PLACE` sans interruption :
 *
 * - le jeton reste **le meme, a une extremite** du mouvement (`debut` ou
 *   `fin`, ou le seul `depart` declare) : bras tendu pour un curl, planche
 *   bras tendus pour une pompe, debout pour un squat. Une detection ne rend
 *   une extremite qu'en position, donc debout devant une pompe n'y est pas ;
 * - le buste est **immobile** (`vitesse_du_buste`, le seuil de la demo) :
 *   marcher bras ballant tient un curl en `debut`.
 *
 * Le compteur ne recoit ses jetons qu'a partir de la : sa position de depart
 * est donc la position tenue, et la mise en place ne peut plus devenir une
 * repetition.
 *
 * Une image manquee (corps hors champ, image lente) remet l'attente a zero :
 * sans elle, sortir du champ deux secondes puis revenir ouvrait la serie a
 * la premiere image.
 */
export function attendre_mise_en_place({ bloc, corps, jeton, maintenant, depart, coach }) {
  if (bloc.serie_ouverte) return true;

  const precedent = bloc.mise_en_place_buste ?? null;
  const continu = precedent !== null && maintenant - precedent.instant <= INTERVALLE_MAX;
  const [vitesse, repere] = vitesse_du_buste(continu ? precedent : null, corps, maintenant);
  bloc.mise_en_place_buste = repere;

  const en_position = depart ? jeton === depart : jeton === "debut" || jeton === "fin";
  const immobile = vitesse !== null && vitesse <= SEUIL_IMMOBILE;
  if (!en_position || !immobile) {
    delete bloc.mise_en_place_jeton;
    delete bloc.mise_en_place_depuis;
    return false;
  }
  if (bloc.mise_en_place_jeton !== jeton) {
    bloc.mise_en_place_jeton = jeton;
    bloc.mise_en_place_depuis = maintenant;
  }
  if (maintenant - bloc.mise_en_place_depuis < DUREE_MISE_EN_PLACE) return false;

  ouvrir_serie(bloc, coach);
  return true;
}

/**
 * Ce que montre une serie comptee qui attend : l'etape, et la consigne de se
 * mettre en place. Ni faute de forme (elle n'existe que pendant l'effort), ni
 * compte.
 */
function montrer_attente(etat, jeton, compteur, messages) {
  etat.erreur = null;
  etat.consigne = messages.texte("mise_en_place");
  poser_etape(etat, jeton, messages.libelle_etape);
  etat.repetitions = compteur.repetitions;
}

/**
 * Ajoute ou retire une repetition a la main ; rend le nouveau `derniere_rep`.
 *
 * Point d'entree unique des gestes ±1. N'agit qu'en phase `exercice`, sur un
 * mode a compte.
 *
 * **Un +1 ne se termine pas ici** : il ne touche que le compteur, et c'est
 * `executer_mode`, a l'image suivante, qui voit le compte depasser
 * `derniere_rep`, l'annonce et clot la serie si la cible est atteinte —
 * exactement comme une repetition detectee, donc sans seconde regle de fin.
 * **Un −1 doit faire reculer `derniere_rep`**, sans quoi la repetition reelle
 * suivante ne serait pas annoncee (`repetitions > derniere_rep` resterait
 * faux) ; et il annonce le nouveau compte, seul retour audible a trois metres.
 *
 * **Un geste ±1 ouvre la serie, en silence** : corriger son compte prouve
 * qu'on est la, et attendre encore l'immobilite laisserait le +1 sans suite.
 */
export function ajuster_repetitions({ seance, compteur, etat, coach, delta, derniere_rep }) {
  const bloc = seance.bloc_actuel;
  if (seance.phase !== "exercice" || !bloc || !MODES_A_COMPTE.includes(bloc.mode)) {
    return derniere_rep;
  }
  bloc.serie_ouverte = true;
  const repetitions = compteur.ajuster(delta);
  etat.repetitions = repetitions;
  if (delta < 0) {
    derniere_rep = Math.min(derniere_rep, repetitions);
    if (repetitions > 0) coach("compteur", repetitions);
  }
  return derniere_rep;
}

/**
 * Publie la premiere faute de forme detectee, ou efface le bandeau, et rend
 * sa cle (null sans faute) pour que la voix la reprenne (`annoncer_faute`).
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
  return cle;
}

// Une faute n'est dite qu'apres avoir dure : une image isolee (le modele qui
// hesite sur un coude) ferait parler le coach a tort, et une consigne qui se
// declenche a tort apprend a ne plus etre ecoutee. Six dixiemes, c'est une
// vingtaine d'images ; une vraie faute (genou trop avance en bas d'une fente,
// coude qui part pendant la montee d'un curl) dure davantage.
export const DUREE_AVANT_CORRECTION = 0.6;

// Une faute qui persiste est redite, mais pas plus souvent : le coach compte
// aussi les repetitions, et une correction en boucle couvrirait le compte.
export const RAPPEL_CORRECTION = 6;

/**
 * Dit la faute de forme qui dure. **Une cle, deux canaux** : la cle du
 * bandeau (`messages.js`) est aussi celle du son (`sons.json`), et une faute
 * sans voix enregistree se tait d'elle-meme dans le lecteur.
 *
 * Le repere vit sur le bloc (`faute_en_cours`, `faute_depuis`,
 * `faute_dite_a`, nettoyes par `reinitialiser_etat_serie`) et se lit a
 * l'horloge de la seance. Une autre faute, ou la fin de la faute, ouvre un
 * nouvel episode ; le delai du lecteur (`delais`) empeche un episode qui
 * vacille de se redire aussitot.
 */
export function annoncer_faute(coach, bloc, cle, maintenant) {
  if (cle !== bloc.faute_en_cours) {
    bloc.faute_en_cours = cle;
    bloc.faute_depuis = maintenant;
    delete bloc.faute_dite_a;
    return;
  }
  if (!cle || maintenant - bloc.faute_depuis < DUREE_AVANT_CORRECTION) return;
  if ("faute_dite_a" in bloc && maintenant - bloc.faute_dite_a < RAPPEL_CORRECTION) return;
  bloc.faute_dite_a = maintenant;
  coach(cle);
}

/**
 * Avertit d'une repetition comptee qui n'est pas allee assez loin. Le jeton
 * est retenu tant que le compteur est arme, oublie a chaque nouvel armement,
 * et l'avertissement reste affiche jusqu'a la repetition suivante — une faute
 * de forme du moment passe devant lui.
 *
 * Rend la cle de l'avertissement **a l'image ou la repetition compte**, null
 * sinon : la voix le dit une fois, au moment ou il nait, alors que l'ecran le
 * garde jusqu'a la repetition suivante.
 */
export function suivre_amplitude(exercice, corps, bloc, etat, stage_avant, stage, rep_comptee, texte) {
  if (!exercice.amplitude) return null;
  const [atteinte, cle] = exercice.amplitude;
  if (stage === "debut") {
    if (stage_avant !== "debut") bloc.amplitude_atteinte = false;
    if (atteinte(corps)) bloc.amplitude_atteinte = true;
  }
  if (rep_comptee) {
    bloc.avertissement_amplitude = bloc.amplitude_atteinte === true ? null : cle;
  }
  const avertissement = bloc.avertissement_amplitude ?? null;
  if (etat.erreur === null && avertissement) etat.erreur = texte(avertissement);
  return rep_comptee ? avertissement : null;
}

// Combien de temps l'extremite ou une tentative a echoue doit durer pour que
// l'echec soit dit. Une image isolee qui retombe a tort sur une extremite (un
// avant-bras pointe vers la camera en pleine montee de curl : le poignet se
// projette sur le coude, et l'angle 2D se lit « bras tendu ») ne dure pas ;
// un vrai echec — on redescend sans etre monte assez haut — se pose. Un quart
// de seconde, huit images : bien moins que le temps d'une repetition.
export const PERSISTANCE_VERDICT = 0.25;

/**
 * Decide si un echec de tentative se dit : rend `[attente, raison_dite]`.
 *
 * Un echec significatif qui porte une raison n'est pas dit sur-le-champ : il
 * est mis **en attente** avec le jeton de l'extremite ou il s'est clos. Il est
 * dit si ce jeton dure `PERSISTANCE_VERDICT` ; il est **abandonne** si le
 * jeton change avant, ou si une repetition compte. Le suivi des tentatives,
 * lui, ne change pas : son journal (le banc d'essai) dit ce qu'il voit, et
 * c'est la parole qui attend d'etre sure. Pur, pour servir a la demo comme a
 * la seance.
 */
export function confirmer_verdict(attente, entree, jeton, maintenant, rep_comptee) {
  if (rep_comptee) attente = null;
  if (entree && !entree.complet && entree.significatif && entree.raison) {
    attente = { raison: entree.raison, jeton, depuis: maintenant };
  }
  if (!attente) return [null, null];
  if (jeton !== attente.jeton) return [null, null];
  if (maintenant - attente.depuis < PERSISTANCE_VERDICT) return [attente, null];
  return [null, attente.raison];
}

/**
 * Dit pourquoi une repetition n'a pas compte.
 *
 * « Ca ne compte pas », sans plus, frustre : on recommence la meme erreur.
 * Le suivi des tentatives (`SuiviTentatives`, sur l'instrument de la
 * detection) voit l'aller interrompu (un crunch qui ne monte pas assez) et le
 * retour incomplet (une pompe pas assez descendue : le compteur ne se
 * rearme pas, la suivante ne comptera pas), et dit ce qui a manque. Une
 * hesitation sous `PROGRESSION_SIGNIFICATIVE` du chemin, ou un mouvement fait
 * hors position, se tait.
 *
 * La voix le dit une fois, quand l'echec est confirme (`confirmer_verdict`,
 * un quart de seconde plus tard) ; le bandeau le garde
 * jusqu'a la prochaine repetition comptee, **devant** l'avertissement
 * d'amplitude (plus ancien) et **derriere** une faute de forme du moment.
 * Le suivi et la raison vivent sur le bloc (`CHAMPS_TEMPORELS`). Rend la cle
 * de la raison a l'image ou elle est dite, null sinon.
 */
export function expliquer_tentative({
  exercice, corps, bloc, etat, coach, jeton, maintenant, rep_comptee, faute, texte,
  muet = false,
}) {
  const instrument = exercice.instrument;
  if (!instrument) return null;
  if (!bloc.suivi_tentatives) {
    bloc.suivi_tentatives = new SuiviTentatives(instrument, {
      intervalle_max: INTERVALLE_MAX,
      depart: exercice.depart ?? null,
    });
  }
  const valeurs = instrument.mesures.map((mesure) => mesure.valeur(corps));
  const entree = bloc.suivi_tentatives.observer(jeton, valeurs, maintenant);
  if (rep_comptee) delete bloc.non_comptee;

  let [attente, dite] = confirmer_verdict(
    bloc.verdict_en_attente ?? null, entree, jeton, maintenant, rep_comptee
  );
  // L'autre cote vient de bouger : cet echec-ci n'en est pas un, c'est le
  // mauvais cote (`surveiller_autre_cote` le dit).
  if (muet) [attente, dite] = [null, null];
  if (attente) bloc.verdict_en_attente = attente;
  else delete bloc.verdict_en_attente;
  if (dite) {
    bloc.non_comptee = dite;
    coach("repetition_non_comptee", dite);
  }
  if (!faute && bloc.non_comptee) {
    etat.erreur = texte("repetition_non_comptee", { raison: texte(bloc.non_comptee) ?? "" });
  }
  return dite;
}

// Un mouvement de l'autre cote compte pendant qu'on attend celui-ci. Les deux
// bras d'un curl partent souvent ensemble : on attend une demi-seconde que le
// bon cote compte aussi avant de dire l'erreur.
export const FENETRE_AUTRE_COTE = 0.5;
// Pendant combien de temps l'echec d'une tentative se tait apres un mouvement
// de l'autre cote. Dans une fente du mauvais pied, le genou mesure — l'arriere
// — descend lui aussi, puis echoue sur la condition du pied avant : sans ce
// silence, le coach dirait « tu ne descends pas assez bas » au lieu du pied.
export const SILENCE_APRES_AUTRE_COTE = 1;
// Un maintien de l'autre cote se dit apres une seconde : le temps de se mettre
// en place sans se faire reprendre en passant.
export const TENUE_AUTRE_COTE = 1;

/**
 * Le mauvais cote : un mouvement unilateral fait de l'autre bras, de l'autre
 * jambe. La detection de l'autre cote (`exercice.autre_cote`) alimente un
 * compteur fantome sur le bloc ; quand il compte et que le vrai ne compte pas
 * dans `FENETRE_AUTRE_COTE`, c'est le mauvais cote. Pour un maintien
 * (`maintien: true`), c'est le jeton `maintien` de l'autre cote, tenu
 * `TENUE_AUTRE_COTE` alors que le notre ne l'est pas, une fois par episode.
 *
 * Rend `{ raison, muet }` : la raison (`raison_autre_bras`…) a l'image ou
 * l'erreur se confirme, sinon null ; `muet` dit a `expliquer_tentative` de
 * taire un echec qui n'en est pas un. Ne parle pas : l'appelant dit la raison
 * comme une repetition qui ne compte pas. Pur ; l'etat vit sur le bloc
 * (`CHAMPS_TEMPORELS`).
 */
export function surveiller_autre_cote({
  exercice, corps, bloc, maintenant, rep_comptee = false, derniere_rep_a = null,
  jeton = null, maintien = false,
}) {
  const autre = exercice.autre_cote;
  if (!autre) return { raison: null, muet: false };
  const raison = raison_autre_cote(exercice);
  const jeton_autre = autre.detection(corps);

  if (maintien) {
    if (jeton_autre !== "maintien" || jeton === "maintien") {
      delete bloc.autre_cote_depuis;
      delete bloc.autre_cote_dit;
      return { raison: null, muet: false };
    }
    if (!("autre_cote_depuis" in bloc)) bloc.autre_cote_depuis = maintenant;
    if (bloc.autre_cote_dit || maintenant - bloc.autre_cote_depuis < TENUE_AUTRE_COTE) {
      return { raison: null, muet: false };
    }
    bloc.autre_cote_dit = true;
    return { raison, muet: false };
  }

  if (!bloc.autre_cote_compteur) bloc.autre_cote_compteur = new CompteurMouvement();
  const fantome = bloc.autre_cote_compteur;
  const avant = fantome.repetitions;
  fantome.mettre_a_jour(jeton_autre, maintenant);
  if (rep_comptee) delete bloc.autre_cote_attente;
  if (fantome.repetitions > avant) {
    bloc.autre_cote_depuis = maintenant;
    const bon_cote_aussi = rep_comptee ||
      (derniere_rep_a !== null && maintenant - derniere_rep_a < FENETRE_AUTRE_COTE);
    if (!bon_cote_aussi) bloc.autre_cote_attente = maintenant;
  }
  const muet = "autre_cote_depuis" in bloc &&
    maintenant - bloc.autre_cote_depuis < SILENCE_APRES_AUTRE_COTE;
  if ("autre_cote_attente" in bloc &&
      maintenant - bloc.autre_cote_attente >= FENETRE_AUTRE_COTE) {
    delete bloc.autre_cote_attente;
    return { raison, muet };
  }
  return { raison: null, muet };
}

/** La raison dite pour un mouvement fait de l'autre cote, ou null. */
export function raison_autre_cote(exercice) {
  return exercice.autre_cote ? `raison_autre_${exercice.autre_cote.membre}` : null;
}

/**
 * Publie le mauvais cote comme une repetition qui ne compte pas : la meme
 * voix composee (« Ca ne compte pas » + « c'est l'autre jambe ») et le meme
 * bandeau, garde jusqu'a la prochaine repetition comptee.
 */
function dire_autre_cote(coach, bloc, raison) {
  if (!raison) return;
  bloc.non_comptee = raison;
  coach("repetition_non_comptee", raison);
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
  const stage_detecte = exercice.detection(corps);
  if (!attendre_mise_en_place({
    bloc, corps, jeton: stage_detecte, maintenant: seance.maintenant(),
    depart: exercice.depart ?? null, coach,
  })) {
    montrer_attente(etat, stage_detecte, compteur, messages);
    return [derniere_rep, compteur.repetitions, false];
  }
  const faute = mettre_a_jour_erreur(exercice, corps, etat, messages.texte);

  const stage_avant = compteur.stage;
  const repetitions_avant = compteur.repetitions;
  const [stage, repetitions] = compteur.mettre_a_jour(
    stage_detecte, seance.maintenant(), exercice.depart ?? null, exercice.delai_min_reps ?? null
  );
  const amplitude_manquee = suivre_amplitude(
    exercice, corps, bloc, etat, stage_avant, stage, repetitions > repetitions_avant, messages.texte
  );
  const autre_cote = surveiller_autre_cote({
    exercice, corps, bloc, maintenant: seance.maintenant(),
    rep_comptee: repetitions > repetitions_avant, derniere_rep_a: compteur.derniere_rep_a,
  });
  dire_autre_cote(coach, bloc, autre_cote.raison);
  expliquer_tentative({
    exercice, corps, bloc, etat, coach, jeton: stage_detecte, maintenant: seance.maintenant(),
    rep_comptee: repetitions > repetitions_avant, faute, texte: messages.texte,
    muet: autre_cote.muet,
  });

  if (repetitions > derniere_rep) {
    coach("compteur", repetitions);
    // Avant les encouragements : un evenement important (fin de serie) vide
    // la file, et une correction dite apres « fin de serie » ne sert a rien.
    if (amplitude_manquee) coach(amplitude_manquee);
    annoncer_progression(coach, repetitions, bloc.repetitions_par_serie);
    derniere_rep = repetitions;
  }
  annoncer_faute(coach, bloc, faute, seance.maintenant());

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
  const position = bloc.exercice.detection(corps);
  if (position === "maintien") bloc.position_maintien_validee = true;
  // Rien n'est corrige avant d'avoir tenu la position une premiere fois : se
  // mettre en planche n'est pas une planche ratee.
  if (bloc.position_maintien_validee === true) {
    const faute = mettre_a_jour_erreur(bloc.exercice, corps, etat, messages.texte);
    annoncer_faute(coach, bloc, faute, seance.maintenant());
  } else {
    etat.erreur = null;
  }
  const autre_cote = surveiller_autre_cote({
    exercice: bloc.exercice, corps, bloc, maintenant: seance.maintenant(), jeton: position,
    maintien: true,
  });
  if (autre_cote.raison) coach("repetition_non_comptee", autre_cote.raison);
  // Le bandeau dure autant que le mauvais cote, sans attendre la seconde.
  if ("autre_cote_depuis" in bloc && !etat.erreur) {
    etat.erreur = messages.texte("repetition_non_comptee", {
      raison: messages.texte(raison_autre_cote(bloc.exercice)) ?? "",
    });
  }

  if (position !== "maintien" && bloc.position_maintien_validee === true) {
    coach("correction_gainage");
  }
  const maintenant = seance.maintenant();

  if (!("dernier_maintien" in bloc)) bloc.dernier_maintien = maintenant;

  const temps_ecoule = Math.min(maintenant - bloc.dernier_maintien, INTERVALLE_MAX);
  bloc.dernier_maintien = maintenant;

  if (position === "maintien") bloc.temps_maintien += temps_ecoule;

  // Bip chaque seconde. Le temps etant toujours positif ici, `Math.floor`
  // ferait pareil que `Math.trunc`.
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
  const maintenant = seance.maintenant();
  const stage_detecte = bloc.exercice.detection(corps);
  // Le chrono part avec la serie, a « c'est parti » : un AMRAP qui courait
  // pendant qu'on se met en place volerait ces secondes a la serie.
  if (!attendre_mise_en_place({
    bloc, corps, jeton: stage_detecte, maintenant,
    depart: bloc.exercice.depart ?? null, coach,
  })) {
    montrer_attente(etat, stage_detecte, compteur, messages);
    etat.temps_amrap_restant = bloc.duree;
    return [derniere_rep, compteur.repetitions, false];
  }
  const faute = mettre_a_jour_erreur(bloc.exercice, corps, etat, messages.texte);
  annoncer_faute(coach, bloc, faute, maintenant);

  if (!("debut_amrap" in bloc)) bloc.debut_amrap = maintenant;

  bloc.temps_amrap = maintenant - bloc.debut_amrap;
  annoncer_temps_restant(coach, bloc, bloc.duree - bloc.temps_amrap);

  const repetitions_avant = compteur.repetitions;
  const [stage, repetitions] = compteur.mettre_a_jour(
    stage_detecte, maintenant, bloc.exercice.depart ?? null, bloc.exercice.delai_min_reps ?? null
  );
  const autre_cote = surveiller_autre_cote({
    exercice: bloc.exercice, corps, bloc, maintenant,
    rep_comptee: repetitions > repetitions_avant, derniere_rep_a: compteur.derniere_rep_a,
  });
  dire_autre_cote(coach, bloc, autre_cote.raison);
  expliquer_tentative({
    exercice: bloc.exercice, corps, bloc, etat, coach, jeton: stage_detecte, maintenant,
    rep_comptee: repetitions > repetitions_avant, faute, texte: messages.texte,
    muet: autre_cote.muet,
  });

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
  const avant = bloc.temps_echauffement;
  bloc.temps_echauffement += Math.min(delta, INTERVALLE_MAX);

  if (bloc.exercice.detection !== null && bloc.exercice.detection !== undefined) {
    const faute = mettre_a_jour_erreur(bloc.exercice, corps, etat, messages.texte);
    annoncer_faute(coach, bloc, faute, maintenant);
    poser_etape(etat, bloc.exercice.detection(corps), messages.libelle_etape);
  } else {
    etat.erreur = null;
    poser_etape(etat, "echauffement", messages.libelle_etape);
  }

  annoncer_changements(coach, bloc, avant, bloc.temps_echauffement);
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

/**
 * Fait avancer la serie courante d'une image, selon son mode.
 *
 * `mise_en_place` : une serie comptee attend-elle qu'on soit en place
 * (`attendre_mise_en_place`) ? Vrai dans l'application. **Faux dans le rejeu
 * des scenarios figes** (`comparer_seances.mjs`) : leurs poses sont tirees au
 * hasard et ne restent jamais immobiles, si bien que plus rien n'y
 * compterait — et `--mettre-a-jour` remplacerait des comptes verifies par
 * zero. La regle se verifie a part (`verifier_mise_en_place.mjs`). Faux, la
 * serie s'ouvre a sa premiere image, comme celles qui ne comptent pas.
 */
export function executer_mode({
  seance, corps, compteur, etat, coach, derniere_rep, messages, mise_en_place = true,
}) {
  const bloc = seance.bloc_actuel;
  etat.mode = bloc.mode;
  // Un maintien, un chrono, un echauffement s'ouvrent a leur premiere image :
  // ils ne comptent rien qu'une mise en place pourrait fausser, et le
  // maintien attend deja la position pour faire avancer son temps.
  if (!bloc.serie_ouverte && (!mise_en_place || !MODES_A_COMPTE.includes(bloc.mode))) {
    ouvrir_serie(bloc, coach);
  }

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
