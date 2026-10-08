// Verification du cadrage, jouee pendant la preparation d'un exercice.
//
// Elle repond a un defaut observe en conditions reelles : une testeuse a pose
// la camera a 40 cm du sol, fait dix squats, et l'application n'a rien compte
// ni rien dit. La consigne de cadrage existait pourtant — sur la fiche, lue
// avant de commencer, puis jamais rappelee. Un cadrage faux ne se voit pas de
// l'interieur : on se voit a l'ecran, donc on se croit vu.
//
// Le module est volontairement separe de la detection : il ne juge pas le
// mouvement, il juge si les points dont le mouvement a besoin sont reellement
// dans l'image. Il est pur, comme les detections, pour la meme raison : il se
// verifie dans Node, sans camera.

// Les points dont une detection a besoin ne sont pas declares : ils sont
// *observes*, en rejouant la fonction sur un corps espion qui note chaque
// landmark qu'on lui demande. Meme principe que le mode d'exercice deduit du
// jeton renvoye — rien a maintenir a cote du code, donc rien qui puisse
// mentir. Une detection ajoutee est couverte le jour ou elle est ecrite.
const memo = new Map();

export function points_utilises(detection) {
  if (memo.has(detection)) return memo.get(detection);

  const vus = new Set();
  const espion = new Proxy({}, {
    get(_, nom) {
      vus.add(nom);
      // Une pose neutre suffit : on ne lit pas le resultat, seulement les
      // acces. Les detections calculent leurs angles avant de brancher, donc
      // un seul passage les touche tous.
      return { x: 0.5, y: 0.5, z: 0, visibility: 1 };
    },
  });
  try {
    detection(espion);
  } catch {
    // Une detection qui refuse une pose degeneree n'a pas fini d'annoncer ses
    // points ; on garde ce qu'elle a demande avant d'echouer plutot que rien.
  }

  // Le buste est exige quoi qu'il arrive : « elevation laterale » ne regarde
  // qu'une epaule et un poignet, et se contenter de ca laisserait passer un
  // cadrage ou il ne reste que le haut du corps.
  for (const point of ["epaule_gauche", "epaule_droite", "hanche_gauche", "hanche_droite"]) {
    vus.add(point);
  }

  const points = [...vus];
  memo.set(detection, points);
  return points;
}

// Les parties du corps telles qu'on en parle a quelqu'un. Une partie n'est
// signalee que si *tous* ses points sont sortis : de profil, le membre
// eloigne est masque mais reste dans l'image, et les detections concernees
// moyennent deja les deux cotes.
const PARTIES = [
  ["tete", ["nez"]],
  ["epaules", ["epaule_gauche", "epaule_droite"]],
  ["coudes", ["coude_gauche", "coude_droit"]],
  ["mains", ["poignet_gauche", "poignet_droit"]],
  ["hanches", ["hanche_gauche", "hanche_droite"]],
  ["genoux", ["genou_gauche", "genou_droit"]],
  ["pieds", ["cheville_gauche", "cheville_droite"]],
];

/**
 * Tous les points que `PARTIES` sait nommer, pour un controle « corps entier ».
 *
 * L'accueil verifie un cadrage **sans exercice** : personne n'a encore choisi
 * de mouvement, donc `points_utilises` n'a aucune detection a espionner. Cette
 * liste est **derivee de `PARTIES`** et non ecrite a cote : une partie ajoutee
 * la-haut est couverte ici le jour ou elle est ecrite, et les deux ne peuvent
 * pas se desaccorder.
 */
export const POINTS_DU_CORPS_ENTIER = PARTIES.flatMap(([, points]) => points);

// Marge au-dela du bord avant de declarer un point sorti. MediaPipe extrapole
// les landmarks hors champ au lieu de les omettre : un pied a y = 1.01 est en
// pratique sur le bord, pas dehors. Sans cette marge, la consigne clignote
// des qu'on effleure le cadre.
const MARGE = 0.04;

// La visibilite n'entre volontairement pas dans le calcul. Elle s'effondre sur
// le membre eloigne de toute vue de profil, ou le cadrage est pourtant parfait
// — s'en servir ici rouvrirait exactement le defaut que les detections de
// gainage viennent de corriger en moyennant les deux cotes.
function bord_franchi(point) {
  if (point.y < -MARGE) return "haut";
  if (point.y > 1 + MARGE) return "bas";
  if (point.x < -MARGE) return "gauche";
  if (point.x > 1 + MARGE) return "droite";
  return null;
}

// Il n'y a volontairement aucun controle de distance. Il y en a eu un, et il
// se trompait a peu pres tout le temps : il mesurait l'etendue *verticale*
// des points, ce qui n'est un indice de distance que pour quelqu'un debout.
// Une planche parfaitement cadree, qui remplit l'image en largeur, mesure
// 0,13 de hauteur — et s'entendait dire « approche-toi ».
//
// La regle qui en sort vaut bien au-dela de ce reglage : **ne parler que
// lorsque la detection ne peut pas travailler**. Etre loin ne l'empeche pas,
// MediaPipe suit tres bien un corps petit dans l'image ; etre hors champ
// l'empeche, parce que le landmark est alors une invention du modele. Une
// consigne qui se declenche a tort est pire qu'absente : elle apprend a ne
// plus la lire.

/**
 * Mesure, sans rien decider : rend la liste des problemes constates.
 * Chaque entree vaut { partie, bord }, ou bord est le cote de l'image par
 * lequel cette partie est sortie.
 */
export function problemes_de_cadrage(corps, points_requis) {
  const requis = new Set(points_requis);
  const problemes = [];

  for (const [partie, points] of PARTIES) {
    const concernes = points.filter((p) => requis.has(p));
    if (!concernes.length) continue;

    const bords = concernes.map((p) => bord_franchi(corps[p]));
    if (bords.some((b) => b === null)) continue;
    problemes.push({ partie, bord: bords[0] });
  }

  return problemes;
}
// Comme ailleurs dans le projet, ce qui decide rend une cle et non une phrase.
//
// **Il n'y a plus qu'une consigne, et c'est une decision d'usage.** Le module a
// longtemps compose vingt-huit phrases — sept parties du corps croisees avec
// quatre actions — qui disaient precisement ce qui depassait et de quel cote :
// « Je ne vois pas tes genoux — baisse la camera », « place-toi au centre de
// l'image ». Mesure a l'usage, cette precision ne servait personne : elle
// arrive quand on est deja debout a trois metres, ou la seule chose qu'on
// puisse faire est reculer, et elle changeait de phrase a mesure qu'on
// bougeait, si bien qu'on ne savait plus quoi corriger. *Une consigne qui dit
// une chose differente a chaque image n'est pas plus precise, elle est
// illisible.*
//
// Ce qui a disparu est l'**arbitrage**, pas la **mesure** : `problemes_de_cadrage`
// est inchangee, et c'est toujours elle qui decide si le corps tient dans
// l'image. Seule la phrase se reduit.
//
// Prix assume : quelqu'un dont la camera est posee au sol s'entendra dire
// « recule », ce qui ne reglera rien. La hauteur de l'appareil est desormais
// portee par le tunnel d'accueil et par la fiche de l'exercice — a l'ecrit, la
// ou on peut la lire avant de s'eloigner.
export const QUOI_FAIRE = {
  recule: "recule, tu ne tiens pas dans l’image",
};

/**
 * Choisit la consigne a annoncer. Rend null si le cadrage convient, sinon
 * `{ partie, action }` — deux cles, jamais du texte.
 *
 * `partie` vaut toujours null depuis la reduction a une consigne unique. Le
 * couple est conserve parce que c'est le contrat d'`annonces.sequence_cadrage`,
 * qui sait encore composer les vingt-huit phrases : rebrancher
 * une consigne fine ne couterait que cette fonction, et aucune prise de son.
 */
export function message_de_cadrage(problemes) {
  if (!problemes.length) return null;
  return { partie: null, action: "recule" };
}

/**
 * La phrase que porte un `{partie, action}` deja choisi.
 *
 * Separee de `consigne_de_cadrage` parce que l'appelant a parfois besoin des
 * **deux cles en plus du texte** : le bandeau affiche la phrase, et le coach
 * prononce les briques correspondantes (`annonces.sequence_cadrage`).
 * Recalculer le choix pour l'un puis pour l'autre ferait tourner la detection
 * deux fois par image, et surtout laisserait les deux diverger le jour ou
 * l'arbitrage change.
 */
export function texte_de_cadrage(choix) {
  if (!choix) return null;
  const action = QUOI_FAIRE[choix.action];
  return action.charAt(0).toUpperCase() + action.slice(1);
}

export function consigne_de_cadrage(corps, points_requis) {
  return texte_de_cadrage(
    message_de_cadrage(problemes_de_cadrage(corps, points_requis))
  );
}
