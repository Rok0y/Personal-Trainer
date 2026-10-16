// La duree estimee d'une seance, pour la carte de l'accueil.
//
// **Le `Circuit` joue la seance lui-meme, sur une horloge a nous.** Les repos
// ne s'additionnent pas a la main : en superset, la pause qui suit A est le
// `repos_entre_series` de B, le `repos_apres` du partenaire n'est jamais joue,
// et le dernier bloc n'a pas de repos (`_finir_bloc`). Une formule tenue ici
// serait un jumeau de ces regles, et divergerait a la premiere retouche du
// circuit sans que rien ne le signale. C'est l'horloge de la seance
// (`maintenant`) qui le permet, comme elle permet aux tests de rejouer 45
// minutes en quelques millisecondes.
//
// Une estimation d'affichage, jamais une regle de jeu : ni transitions, ni
// mise en place, ni guide — l'effort et les repos ecrits.

import { MODES_CIBLE_TEMPORELLE, cible_du_bloc } from "./circuit.js";

/**
 * L'effort d'une serie de ce bloc, en secondes, ou null si son mouvement n'a
 * pas de tempo.
 *
 * Une cible en secondes est sa propre duree (maintien, chrono, AMRAP,
 * echauffement) ; une cible en repetitions se multiplie par le temps d'une
 * repetition **de ce mouvement**.
 */
function effort(bloc, secondes_par_repetition) {
  const cible = cible_du_bloc(bloc);
  if (MODES_CIBLE_TEMPORELLE.includes(bloc.mode)) return cible;
  const tempo = secondes_par_repetition?.[bloc.exercice.nom];
  return typeof tempo === "number" && tempo > 0 ? cible * tempo : null;
}

/**
 * La duree de la seance en secondes, ou null si elle ne s'estime pas.
 *
 * **Consomme le circuit** : on lui passe un circuit neuf, construit comme
 * celui qui sera joue (variantes et objectifs appliques), jamais la seance en
 * cours. Un mouvement sans tempo rend null — pas de valeur par defaut, qui
 * masquerait l'oubli (`verifier_donnees` exige un tempo par mouvement compte) :
 * la carte n'affiche alors rien, comme une video absente. Ne leve jamais : elle
 * tourne dans le dessin de l'accueil.
 */
export function duree_estimee(circuit, secondes_par_repetition) {
  if (!circuit?.exercices?.length) return null;
  let t = 0;
  circuit.maintenant = () => t;
  circuit.debut = 0;

  // Une serie passe au plus par l'effort et un repos ; chaque bloc ajoute
  // au plus une preparation et un repos entre exercices. Au-dela, le circuit
  // tourne en rond : mieux vaut ne rien afficher que geler l'ecran.
  const series = circuit.exercices.reduce((s, bloc) => s + (Number(bloc.nombre_series) || 0), 0);
  const pas_max = 4 * series + 2 * circuit.exercices.length + 10;

  for (let pas = 0; pas < pas_max; pas += 1) {
    switch (circuit.phase) {
      case "termine":
        return t;
      case "preparation":
        circuit.commencer_exercice();
        break;
      case "exercice": {
        const secondes = effort(circuit.bloc_actuel, secondes_par_repetition);
        if (secondes === null) return null;
        t += secondes;
        circuit.terminer_serie();
        break;
      }
      case "recuperation_serie":
      case "repos_exercice":
        t += circuit.temps_restant;
        circuit.update();
        break;
      default:
        return null;
    }
  }
  return null;
}

/**
 * « ≈ 40 min », ou null.
 *
 * A la minute pres sous un quart d'heure, aux cinq minutes au-dela : une
 * estimation qui affiche « 37 min » promet une precision qu'elle n'a pas.
 */
export function libelle_duree(secondes) {
  if (typeof secondes !== "number" || !(secondes > 0)) return null;
  const minutes = secondes / 60;
  const arrondi = minutes < 15
    ? Math.max(1, Math.round(minutes))
    : Math.round(minutes / 5) * 5;
  if (arrondi < 60) return `≈ ${arrondi} min`;
  const reste = arrondi % 60;
  return `≈ ${Math.floor(arrondi / 60)} h` + (reste ? ` ${String(reste).padStart(2, "0")}` : "");
}
