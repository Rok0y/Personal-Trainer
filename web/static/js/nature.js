// Ce qu'est un mouvement du catalogue : un echauffement, un exercice, ou les
// deux.
//
// **Le mode du bloc decide de ce qui compte**, pas le mouvement : un bloc en
// `echauffement` est invisible dans les statistiques (`est_echauffement(bloc)`,
// `circuit.js`), quel que soit le mouvement qu'il joue. Le drapeau
// `est_echauffement` d'un mouvement ne dit donc que **ou le proposer** — dans
// le groupe des echauffements. Un echauffement qui a une detection de
// comptage peut etre aussi un exercice (`aussi_exercice`) : les Jumping jacks
// se jouent en echauffement au chrono, ou comptes en AMRAP, sous le meme nom.
//
// `aussi_exercice` est un drapeau a part, et non « un echauffement qui a une
// detection » : des echauffements ont deja une detection d'affichage seule
// (le Squat lent emprunte celle du squat) sans etre des exercices.
//
// Module feuille, sans import : les pages, les verificateurs et les modules
// le lisent sans risquer de cycle.

/** Le mouvement est-il propose dans le groupe des echauffements ? */
export function propose_en_echauffement(mouvement) {
  return Boolean(mouvement?.est_echauffement);
}

/** Le mouvement est-il un exercice (niveau, ligue, historique quand il compte) ? */
export function est_exercice(mouvement) {
  if (!mouvement) return false;
  return !mouvement.est_echauffement || mouvement.aussi_exercice === true;
}

/**
 * Le mouvement est-il en cours d'ajout, pas encore valide au banc d'essai ni en
 * seance ? Le banc d'essai le range a part. Le drapeau s'ecrit a l'ajout et se
 * retire a la cloture (protocole `ajouter-exercice`).
 */
export function est_en_developpement(mouvement) {
  return mouvement?.en_developpement === true;
}

/**
 * Un exercice compte par la camera : il lui faut un bareme, un tempo et un
 * instrument, et le banc d'essai le propose. Un exercice sans detection se
 * joue au chrono.
 */
export function est_compte(mouvement) {
  return est_exercice(mouvement) && Boolean(mouvement.detection);
}
