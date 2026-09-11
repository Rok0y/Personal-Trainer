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
// dans l'image. Il est pur, comme les detections, pour la meme raison — il
// devra un jour avoir un jumeau Python.

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
// La consigne se compose de deux moities qui ne se melangent pas : ce qui
// manque, et quoi faire. Les separer evite les 28 combinaisons qu'une table
// unique demanderait, et laisse corriger une formulation sans toucher a
// l'arbitrage.
export const CE_QUI_MANQUE = {
  tete: "Je ne vois pas ta tête",
  epaules: "Je ne vois pas tes épaules",
  coudes: "Je ne vois pas tes coudes",
  mains: "Je ne vois pas tes mains",
  hanches: "Je ne vois pas tes hanches",
  genoux: "Je ne vois pas tes genoux",
  pieds: "Je ne vois pas tes pieds",
};

export const QUOI_FAIRE = {
  recule: "recule, tu ne tiens pas dans l’image",
  baisse_camera: "baisse la caméra ou incline-la vers le bas",
  monte_camera: "monte la caméra ou incline-la vers le haut",
  // Volontairement sans gauche ni droite : l'image de la demo est affichee en
  // miroir, donc « decale-toi vers la droite » designerait un cote a l'ecran
  // et l'autre dans la piece. Le centre, lui, est le meme des deux cotes.
  centre: "place-toi au centre de l’image",
};

// Un bord franchi appelle une action, et une seule.
const ACTION_DU_BORD = {
  bas: "baisse_camera",
  haut: "monte_camera",
  gauche: "centre",
  droite: "centre",
};

// Rang vertical approximatif, de la tete aux pieds. Il sert a nommer, parmi
// les parties sorties par un meme bord, celle qui est la *plus eloignee* de ce
// bord : si les genoux et les pieds sont sortis par le bas, annoncer les
// genoux dit tout, alors qu'annoncer les pieds laisse croire qu'il ne manque
// qu'un centimetre.
const RANG = Object.fromEntries(PARTIES.map(([partie], i) => [partie, i]));

/**
 * Choisit le seul probleme a annoncer. Rend null si le cadrage convient, sinon
 * { partie, action } — deux cles, jamais du texte. `partie` vaut null dans le
 * seul cas ou aucune ne suffit a l'expliquer : coupe en haut *et* en bas.
 */
export function message_de_cadrage(problemes) {
  if (!problemes.length) return null;

  // Coupe en haut *et* en bas : ni monter ni baisser la camera n'y change
  // quoi que ce soit, il n'y a pas assez de champ. C'est le seul cas ou
  // nommer une partie tromperait, puisqu'il en manque des deux cotes.
  const haut = problemes.filter((p) => p.bord === "haut");
  const bas = problemes.filter((p) => p.bord === "bas");
  if (haut.length && bas.length) return { partie: null, action: "recule" };

  // Un corps coupe passe avant un corps decentre : c'est lui qui rend les
  // angles faux, la ou un decalage lateral les laisse mesurables.
  const verticaux = haut.length ? haut : bas;
  if (verticaux.length) {
    const extreme = verticaux.reduce((a, b) =>
      (haut.length ? RANG[b.partie] > RANG[a.partie] : RANG[b.partie] < RANG[a.partie]) ? b : a);
    return { partie: extreme.partie, action: ACTION_DU_BORD[extreme.bord] };
  }

  return { partie: problemes[0].partie, action: "centre" };
}

export function consigne_de_cadrage(corps, points_requis) {
  const choix = message_de_cadrage(problemes_de_cadrage(corps, points_requis));
  if (!choix) return null;
  const action = QUOI_FAIRE[choix.action];
  return choix.partie
    ? `${CE_QUI_MANQUE[choix.partie]} — ${action}`
    : action.charAt(0).toUpperCase() + action.slice(1);
}
