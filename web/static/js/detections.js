// Uniquement les fonctions de detection et d'erreur de forme.
//
// Les objets `Exercice` (fiches, consignes, variantes), le catalogue et la
// machine a etats vivent ailleurs. Ici il n'y a que des fonctions pures
// `corps -> jeton`.
//
// Les fonctions d'erreur retournent une **cle** de message ou null, jamais
// une phrase : c'est la convention de `messages.js`, qui resout la cle en
// francais.

import { calculer_angle, calculer_distance } from "./outils.js";

// Seuil de fin resserre de 30 a 20 degres : « la validation arrive trop
// tot ».
const CURL_FIN = 20;

export function curl_biceps_droit_detection(corps) {
  const angle = calculer_angle(
    corps.epaule_droite,
    corps.coude_droit,
    corps.poignet_droit
  );
  if (angle < CURL_FIN) return "fin";
  else if (angle > 160) return "debut";
  return "milieu";
}

function _coude_qui_part_en_avant(hanche, epaule, coude) {
  // 45 -> 23 degres, valeur donnee par le testeur en lisant la jauge.
  if (calculer_angle(hanche, epaule, coude) > 23) {
    return "forme_coude_qui_part_en_avant";
  }
  return null;
}

export function coude_avance_curl_droit(corps) {
  return _coude_qui_part_en_avant(
    corps.hanche_droite,
    corps.epaule_droite,
    corps.coude_droit
  );
}

export function coude_avance_curl_gauche(corps) {
  return _coude_qui_part_en_avant(
    corps.hanche_gauche,
    corps.epaule_gauche,
    corps.coude_gauche
  );
}

export function curl_biceps_gauche_detection(corps) {
  const angle = calculer_angle(
    corps.epaule_gauche,
    corps.coude_gauche,
    corps.poignet_gauche
  );
  if (angle < CURL_FIN) return "fin";
  else if (angle > 160) return "debut";
  return "milieu";
}

// Poignet sous l'epaule, rapporte au buste : ~1 bras le long du corps, 0 a
// hauteur d'epaule. null si le buste n'a pas de longueur lisible.
function hauteur_sous_epaule(poignet, epaule, hanche) {
  const buste = calculer_distance(epaule, hanche);
  if (buste <= 0) return null;
  return (poignet.y - epaule.y) / buste;
}

// De combien le poignet est sorti vers l'exterieur de son epaule (le cote
// oppose a l'autre epaule), rapporte au buste. C'est ce qui distingue une
// elevation laterale d'une elevation frontale.
function ecart_lateral(poignet, epaule, autre_epaule, hanche) {
  const buste = calculer_distance(epaule, hanche);
  if (buste <= 0) return null;
  const sortie = epaule.x >= autre_epaule.x ? poignet.x - epaule.x : epaule.x - poignet.x;
  return sortie / buste;
}

export function elevation_laterale_detection(corps) {
  // La fin exige la hauteur, des bras tendus et chaque poignet sorti de son
  // cote ; le depart, des mains nettement basses. Lever les bras devant soi
  // comptait avant, et sans zone intermediaire un tremblement faisait un
  // aller-retour.
  const hauteur_droite = hauteur_sous_epaule(
    corps.poignet_droit, corps.epaule_droite, corps.hanche_droite
  );
  const hauteur_gauche = hauteur_sous_epaule(
    corps.poignet_gauche, corps.epaule_gauche, corps.hanche_gauche
  );
  if (hauteur_droite === null || hauteur_gauche === null) return "milieu";
  if (hauteur_droite > 0.6 && hauteur_gauche > 0.6) return "debut";

  const angle_coude_droit = calculer_angle(
    corps.epaule_droite, corps.coude_droit, corps.poignet_droit
  );
  const angle_coude_gauche = calculer_angle(
    corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche
  );
  const ecart_droit = ecart_lateral(
    corps.poignet_droit, corps.epaule_droite, corps.epaule_gauche, corps.hanche_droite
  );
  const ecart_gauche = ecart_lateral(
    corps.poignet_gauche, corps.epaule_gauche, corps.epaule_droite, corps.hanche_gauche
  );
  if (
    hauteur_droite < 0.15 &&
    hauteur_gauche < 0.15 &&
    angle_coude_droit > 140 &&
    angle_coude_gauche > 140 &&
    ecart_droit > 0.3 &&
    ecart_gauche > 0.3
  ) {
    return "fin";
  }
  return "milieu";
}

// En deca de cet ecart de visibilite, les deux bras sont aussi bien vus l'un
// que l'autre (de face, typiquement) : c'est alors la profondeur qui tranche.
const MARGE_VISIBILITE = 0.1;

// `visibility` est le nom du champ du point MediaPipe brut.
function visibilite_bras(coude, poignet) {
  return (coude.visibility + poignet.visibility) / 2;
}

// Epaule, coude et poignet du bras que la camera voit vraiment. De profil, le
// coude eloigne est estime par le modele et restait tendu pendant que l'autre
// pliait ; ni la conjonction ni la moyenne n'y resistent. Le choix se faisait
// sur `z`, la coordonnee la moins fiable du modele, et un bras cache designe
// a tort ne comptait plus aucune pompe : il se fait desormais sur la
// visibilite, `z` ne departageant que deux bras aussi bien vus.
function bras_proche(corps) {
  const gauche = visibilite_bras(corps.coude_gauche, corps.poignet_gauche);
  const droite = visibilite_bras(corps.coude_droit, corps.poignet_droit);
  const bras_gauche = Math.abs(gauche - droite) >= MARGE_VISIBILITE
    ? gauche > droite
    : corps.epaule_gauche.z <= corps.epaule_droite.z;
  if (bras_gauche) {
    return [corps.epaule_gauche, corps.coude_gauche, corps.poignet_gauche];
  }
  return [corps.epaule_droite, corps.coude_droit, corps.poignet_droit];
}

function angle_coude_proche(corps) {
  const [epaule, coude, poignet] = bras_proche(corps);
  return calculer_angle(epaule, coude, poignet);
}

// Deux seuils en bas : le premier decide si la pompe compte, le second si
// elle etait assez profonde. Profondeur ouverte de 100 a 108 degres : l'angle
// se lit en deux dimensions et sur le bras le mieux vu, et une pompe
// franchement descendue se faisait encore dire de descendre plus bas. Pas
// 110 : la pose figee qui joue la pompe peu profonde du scenario ecrit
// (`pompes_peu_profondes`) est construite a 110 pile, et elle ne serait plus
// peu profonde — le scenario ne testerait plus rien. Aller au-dela demande
// d'abord un nouveau cas construit.
export const SEUIL_COMPTAGE_POMPE = 120;
export const SEUIL_PROFONDEUR_POMPE = 108;

export function pompe_detection(corps) {
  // Corps a l'horizontale, ou rien ne compte : debout, plier le bras
  // comptait une pompe. Meme condition que le developpe couche.
  if (buste_vertical(corps) >= 0) return "milieu";
  const angle_coude = angle_coude_proche(corps);
  if (angle_coude < SEUIL_COMPTAGE_POMPE) return "debut";
  else if (angle_coude > 160) return "fin";
  return "milieu";
}

// Les bornes de la position « mains au mur », rapportees au buste. Le poignet
// ne descend pas plus d'une demi-longueur de buste sous l'epaule (les mains se
// posent a hauteur de poitrine), ne monte pas plus d'un tiers au-dessus — au-
// dela, tenues trois secondes, deux mains en l'air ressembleraient au geste qui
// remet le compteur a zero —, et s'avance d'au moins un cinquieme de buste
// devant l'epaule : c'est ce qui ecarte un bras qu'on plie debout le long du
// corps. L'avancee reste basse parce qu'en bas du mouvement, poitrine pres du
// mur, l'epaule rejoint presque les mains.
export const HAUTEUR_MUR_MAX = 0.5;
export const HAUTEUR_MUR_MIN = -0.35;
export const AVANCEE_MUR_MIN = 0.2;

// Hauteur et avancee du poignet du bras visible, rapportees au buste.
function poignet_devant_epaule(corps) {
  const [epaule, , poignet] = bras_proche(corps);
  const hanche = epaule === corps.epaule_gauche ? corps.hanche_gauche : corps.hanche_droite;
  const hauteur = hauteur_sous_epaule(poignet, epaule, hanche);
  if (hauteur === null) return [null, null];
  return [hauteur, Math.abs(poignet.x - epaule.x) / calculer_distance(epaule, hanche)];
}

// Pompe debout, mains au mur, de profil. `pompe_detection` exige un buste
// couche : ici on est debout, donc la position se dit par les mains — devant
// soi, a hauteur de poitrine. Hors de cette position, tout est "milieu".
export function pompe_mur_detection(corps) {
  if (buste_vertical(corps) <= 0) return "milieu";
  const [hauteur, avancee] = poignet_devant_epaule(corps);
  if (hauteur === null) return "milieu";
  if (!(HAUTEUR_MUR_MIN < hauteur && hauteur < HAUTEUR_MUR_MAX) || avancee <= AVANCEE_MUR_MIN) {
    return "milieu";
  }
  const angle_coude = angle_coude_proche(corps);
  if (angle_coude < SEUIL_COMPTAGE_POMPE) return "debut";
  else if (angle_coude > 160) return "fin";
  return "milieu";
}

// Un jeton, pas une faute — le moteur retient
// s'il a ete vu pendant la descente.
export function pompe_profondeur(corps) {
  if (angle_coude_proche(corps) < SEUIL_PROFONDEUR_POMPE) return "profond";
  return null;
}

// Ecart vertical moins ecart horizontal entre le milieu des epaules et celui
// des hanches : negatif quand le buste est plus couche que debout. Meme
// comparaison que `_torse_vertical` des gestes (`positions.js`).
function buste_vertical(corps) {
  const epaules_x = (corps.epaule_gauche.x + corps.epaule_droite.x) / 2;
  const epaules_y = (corps.epaule_gauche.y + corps.epaule_droite.y) / 2;
  const hanches_x = (corps.hanche_gauche.x + corps.hanche_droite.x) / 2;
  const hanches_y = (corps.hanche_gauche.y + corps.hanche_droite.y) / 2;
  return Math.abs(epaules_y - hanches_y) - Math.abs(epaules_x - hanches_x);
}

export function developpe_couche_sol_detection(corps) {
  // Debout, plier et tendre les coudes comptait : hors de la position
  // allongee, rien n'est ni debut ni fin.
  if (buste_vertical(corps) >= 0) return "milieu";
  const angle_coude = angle_coude_proche(corps);
  if (angle_coude < 100) return "debut";
  else if (angle_coude > 160) return "fin";
  return "milieu";
}

function coudes_leves(corps) {
  return (
    corps.coude_gauche.y < corps.epaule_gauche.y &&
    corps.coude_droit.y < corps.epaule_droite.y
  );
}

// Distance entre deux points rapportee a la largeur des epaules (de face
// seulement). null si elle est nulle.
function ecart_rapporte_aux_epaules(point_gauche, point_droit, corps) {
  const largeur = calculer_distance(corps.epaule_gauche, corps.epaule_droite);
  if (largeur <= 0) return null;
  return calculer_distance(point_gauche, point_droit) / largeur;
}

// Deux seuils sur l'ecart des coudes, comme les pompes en ont deux sur la
// profondeur : au-dela du premier, le coach avertit ; au-dela du second, la
// repetition ne compte plus. A 18 kg, des coudes grands ouverts faisaient
// passer pour des extensions ce que les epaules soulevaient. Le refus est une
// **condition de position** partagee par `debut` et `fin` — une repetition
// coudes ouverts ne s'arme ni ne se valide —, jamais une repetition retiree.
// En largeurs d'epaules, coudes leves.
export const ECART_COUDES_AVERTISSEMENT = 1.3;
export const ECART_COUDES_MAX = 1.6;

export function extension_triceps_au_dessus_de_la_tete_detection(corps) {
  const angle_coude_droit = calculer_angle(
    corps.epaule_gauche,
    corps.coude_gauche,
    corps.poignet_gauche
  );
  const angle_coude_gauche = calculer_angle(
    corps.epaule_droite,
    corps.coude_droit,
    corps.poignet_droit
  );
  // Coudes en l'air et poignets presque joints sur l'haltere, sinon ni debut
  // ni fin : n'importe quelle flexion des bras comptait.
  const ecart_poignets = ecart_rapporte_aux_epaules(
    corps.poignet_gauche, corps.poignet_droit, corps
  );
  const ecart_coudes = ecart_rapporte_aux_epaules(corps.coude_gauche, corps.coude_droit, corps);
  if (!coudes_leves(corps) || ecart_poignets === null || ecart_poignets >= 0.6) {
    return "milieu";
  }
  if (ecart_coudes === null || ecart_coudes >= ECART_COUDES_MAX) return "milieu";
  if (angle_coude_droit < 90 && angle_coude_gauche < 90) return "debut";
  else if (angle_coude_droit > 140 && angle_coude_gauche > 140) return "fin";
  return "milieu";
}

// Coudes ecartes au-dela de la largeur des epaules, coudes leves seulement
// (bras le long du corps, ils y sont naturellement). Avertit avant que le
// comptage ne refuse (`ECART_COUDES_MAX`).
export function extension_triceps_erreur_coudes(corps) {
  if (!coudes_leves(corps)) return null;
  const ecart = ecart_rapporte_aux_epaules(corps.coude_gauche, corps.coude_droit, corps);
  if (ecart !== null && ecart > ECART_COUDES_AVERTISSEMENT) return "forme_coudes_trop_ecartes";
  return null;
}

export function developpe_epaule_detection(corps) {
  const angle_coude_droit = calculer_angle(
    corps.epaule_gauche,
    corps.coude_gauche,
    corps.poignet_gauche
  );
  const angle_coude_gauche = calculer_angle(
    corps.epaule_droite,
    corps.coude_droit,
    corps.poignet_droit
  );
  // Un developpe epaule se termine *au-dessus de la tete*, et l'angle du
  // coude seul ne le dit pas : bras baisses et tendus le long du corps, il
  // depasse aussi 150 degres.
  const mains_en_haut =
    corps.poignet_gauche.y < corps.epaule_gauche.y &&
    corps.poignet_droit.y < corps.epaule_droite.y;
  // Seuil bas ouvert de 40 a 60 degres : il fallait descendre trop bas.
  if (angle_coude_droit < 60 && angle_coude_gauche < 60) return "debut";
  else if (angle_coude_droit > 150 && angle_coude_gauche > 150 && mains_en_haut)
    return "fin";
  return "milieu";
}

// Angle du buste au-dessus de l'horizontale, en degres : la droite qui va du
// milieu des hanches au milieu des epaules. Positif quand les epaules sont
// plus hautes que les hanches. Les deux cotes sont moyennes par construction,
// ce qui convient a une vue de profil, ou le cote eloigne est estime.
function inclinaison_buste(corps) {
  const epaules_x = (corps.epaule_gauche.x + corps.epaule_droite.x) / 2;
  const epaules_y = (corps.epaule_gauche.y + corps.epaule_droite.y) / 2;
  const hanches_x = (corps.hanche_gauche.x + corps.hanche_droite.x) / 2;
  const hanches_y = (corps.hanche_gauche.y + corps.hanche_droite.y) / 2;
  return (Math.atan2(hanches_y - epaules_y, Math.abs(epaules_x - hanches_x)) * 180) / Math.PI;
}

// Un crunch se lit a ce que la fiche demande : **decoller les epaules**,
// c'est-a-dire incliner le buste. L'angle epaule-hanche-genou qui le mesurait
// dependait des genoux — allonge pieds a plat, il valait deja 110 a 135
// degres —, et son seuil de 85 degres demandait presque un releve de buste.
// Il exigeait en plus les deux cotes ensemble, vus de profil.
//
// Dix degres d'ecart entre les deux bornes : l'hysteresis qui empeche un
// tremblement de compter. Le plafond de `fin` est une condition de position :
// au-dela, on est assis ou debout, ce n'est plus un crunch.
export const CRUNCH_DEBUT_MAX = 10;
export const CRUNCH_FIN_MIN = 20;
export const CRUNCH_FIN_MAX = 60;

export function crunches_detection(corps) {
  const inclinaison = inclinaison_buste(corps);
  if (inclinaison < CRUNCH_DEBUT_MAX) return "debut";
  if (inclinaison > CRUNCH_FIN_MIN && inclinaison < CRUNCH_FIN_MAX) return "fin";
  return "milieu";
}

export function detection_gainage(corps) {
  const angle_hanche_droite = calculer_angle(
    corps.epaule_gauche,
    corps.hanche_gauche,
    corps.genou_gauche
  );
  const angle_hanche_gauche = calculer_angle(
    corps.epaule_droite,
    corps.hanche_droite,
    corps.genou_droit
  );
  // Seuil ouvert de 145 a 135 degres : un bassin legerement bas reste un
  // gainage, et a 145 le maintien se coupait par a-coups.
  //
  // Moyenne des deux cotes, et non conjonction. La fiche demande une vue de
  // profil : la jambe eloignee est donc *toujours* masquee et son genou
  // estime. Exiger que les deux angles depassent le seuil revient a exiger
  // que cette estimation soit exacte — un testeur voyait le chrono s'arreter
  // par intermittence et l'attribuait a ses genoux. Ce qu'on abandonne, c'est
  // le reperage d'un bassin affaisse d'un seul cote, qu'une vue de profil ne
  // montre de toute facon pas.
  const hanches_droites = (angle_hanche_droite + angle_hanche_gauche) / 2 > 135;

  const hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y;

  // Tombe a plat ventre, le chrono continuait. Ce qui fait le gainage, c'est
  // l'effort : epaules soulevees au-dessus des coudes (moyenne des deux
  // cotes, le bras eloigne etant estime) et hanches decollees du sol.
  const appui =
    (appui_sur_le_bras(corps.epaule_gauche, corps.coude_gauche, corps.hanche_gauche) +
      appui_sur_le_bras(corps.epaule_droite, corps.coude_droit, corps.hanche_droite)) / 2;
  const decollee = hanche_decollee(
    (corps.epaule_gauche.y + corps.epaule_droite.y) / 2,
    (corps.hanche_gauche.y + corps.hanche_droite.y) / 2,
    (corps.cheville_gauche.y + corps.cheville_droite.y) / 2
  );
  const en_appui = appui > 0.25 && decollee !== null && decollee > 0.3;

  if (hanches_droites && hanche_au_dessus_coude && en_appui) return "maintien";

  return "repos";
}

export function squat_detection(corps) {
  const distance_gauche = calculer_distance(corps.coude_gauche, corps.genou_gauche);
  const distance_droite = calculer_distance(corps.coude_droit, corps.genou_droit);
  const distance_moyenne = (distance_gauche + distance_droite) / 2;

  if (distance_moyenne < 0.05) return "debut";
  else if (distance_moyenne > 0.15) return "fin";
  return "milieu";
}

// De combien le genou du cote mesure est plus haut que l'autre, rapporte a
// son tibia. En bas d'une fente, le genou arriere descend vers le sol et le
// genou avant reste a hauteur de tibia : c'est ce qui dit quelle jambe est
// devant. Lisible de face comme de profil, et rien n'est suppose du sens du
// regard. null quand le tibia est illisible.
function genou_au_dessus_de_l_autre(genou, cheville, autre_genou) {
  const tibia = calculer_distance(genou, cheville);
  if (tibia <= 0) return null;
  return (autre_genou.y - genou.y) / tibia;
}

// Le bas d'une fente exige que la jambe mesuree soit **devant** : le genou
// arriere se plie aussi a 90 degres, et une fente faite de l'autre pied
// comptait. Condition du bas seulement : debout, pieds rapproches, les deux
// genoux sont a la meme hauteur et la position de depart doit rester lisible.
export const FENTE_GENOU_AVANT_MIN = 0.3;

function fente(hanche, genou, cheville, autre_genou) {
  const angle_genou = calculer_angle(hanche, genou, cheville);
  const avance = genou_au_dessus_de_l_autre(genou, cheville, autre_genou);
  if (angle_genou < 100 && avance !== null && avance > FENTE_GENOU_AVANT_MIN) return "debut";
  else if (angle_genou > 150) return "fin";
  return "milieu";
}

export function fente_droite_detection(corps) {
  return fente(corps.hanche_droite, corps.genou_droit, corps.cheville_droite, corps.genou_gauche);
}

export function fente_gauche_detection(corps) {
  return fente(corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche, corps.genou_droit);
}

// De combien le genou avant passe devant la pointe du pied, rapporte au
// tibia. Le sens du regard se lit sur le pied (talon vers pointe), donc rien
// n'est suppose du cote de la camera. null quand le pied est vu de bout ou le
// tibia illisible.
function genou_depasse_pied(genou, cheville, talon, pointe) {
  const longueur_pied = pointe.x - talon.x;
  const tibia = calculer_distance(genou, cheville);
  if (Math.abs(longueur_pied) < 0.01 || tibia <= 0) return null;
  const sens = longueur_pied > 0 ? 1 : -1;
  return ((genou.x - pointe.x) * sens) / tibia;
}

// Faute affichee seulement : elle ne retire rien au comptage de la fente.
function faute_genou_avant(genou, cheville, talon, pointe) {
  const depassement = genou_depasse_pied(genou, cheville, talon, pointe);
  if (depassement !== null && depassement > 0.05) return "forme_genou_avant_trop_avance";
  return null;
}

export function fente_droite_erreur_genou(corps) {
  return faute_genou_avant(
    corps.genou_droit, corps.cheville_droite, corps.talon_droit, corps.pointe_pied_droite
  );
}

export function fente_gauche_erreur_genou(corps) {
  return faute_genou_avant(
    corps.genou_gauche, corps.cheville_gauche, corps.talon_gauche, corps.pointe_pied_gauche
  );
}

// La hauteur des poignets au-dessus des chevilles, en tibias (moyenne des deux
// cotes). Une distance brute dans l'image dependait de la distance a la
// camera : a trois metres, debout, on restait sous le seuil du haut et il
// fallait plier les coudes pour que la repetition compte. Le tibia est le
// segment qui bouge le moins : les genoux ne plient presque pas, et la hanche,
// elle, part en arriere. Verticale, parce que les halteres glissent le long
// des jambes. null quand aucun tibia n'est lisible.
function hauteur_poignets(corps) {
  const cotes = [
    [corps.poignet_gauche, corps.genou_gauche, corps.cheville_gauche],
    [corps.poignet_droit, corps.genou_droit, corps.cheville_droite],
  ].map(([poignet, genou, cheville]) => {
    const tibia = calculer_distance(genou, cheville);
    return tibia > 0 ? (cheville.y - poignet.y) / tibia : null;
  }).filter((hauteur) => hauteur !== null);
  if (!cotes.length) return null;
  return cotes.reduce((a, b) => a + b, 0) / cotes.length;
}

// Debout, les poignets sont a environ 1,8 tibia au-dessus des chevilles ;
// buste a l'horizontale, vers 0,6. Le haut compte vers 40 degres d'inclinaison :
// « presque debout » sans exiger de verrouiller. Le bas reprend ce
// qu'exigeait l'ancienne mesure a la distance d'une seance.
export const SOULEVE_BAS_MAX = 0.9;
export const SOULEVE_HAUT_MIN = 1.55;

export function souleve_de_terre_roumain_detection(corps) {
  const hauteur = hauteur_poignets(corps);
  if (hauteur === null) return "milieu";
  if (hauteur < SOULEVE_BAS_MAX) return "debut";
  else if (hauteur > SOULEVE_HAUT_MIN) return "fin";
  return "milieu";
}

// De combien le buste est souleve par l'appui sur le bras, rapporte a la
// longueur du buste — donc sans unite, independant de la taille et du cadrage.
// Vaut environ 0 quand on est simplement allonge sur le cote (epaule et coude
// tous deux au sol) et grimpe vers 0,5 des qu'on se redresse sur l'avant-bras.
function appui_sur_le_bras(epaule, coude, hanche) {
  const buste = calculer_distance(epaule, hanche);
  if (buste <= 0) return 0;
  return (coude.y - epaule.y) / buste;
}

// Hauteur de la hanche au-dessus des pieds, rapportee a celle de l'epaule :
// vers 0,5 en planche (la hanche est sur la ligne pieds-epaule), vers 0
// hanches posees au sol. null quand l'epaule n'est pas plus haut que les pieds.
function hanche_decollee(y_epaule, y_hanche, y_cheville) {
  const hauteur = y_cheville - y_epaule;
  if (hauteur <= 0) return null;
  return (y_cheville - y_hanche) / hauteur;
}

function gainage_lateral_decolle(epaule, hanche, cheville) {
  const decollee = hanche_decollee(epaule.y, hanche.y, cheville.y);
  return decollee !== null && decollee > 0.3;
}

export function detection_gainage_laterale_gauche(corps) {
  const angle_hanche_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.hanche_gauche,
    corps.cheville_gauche
  );
  // Seuil resserre de 150 a 155 degres : a 150 le corps pouvait casser de 30
  // degres et passer pour aligne, fesses posees au sol comprises. Resserre
  // modestement : sans hysteresis, un seuil trop pres de la position parfaite
  // ferait clignoter le maintien.
  const corps_aligne = angle_hanche_gauche > 155;

  const cote_gauche_au_sol = corps.epaule_gauche.y > corps.epaule_droite.y;

  const hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y;

  // Allonge sur le cote sans rien faire, les trois conditions precedentes sont
  // reunies : le corps est aligne, le bon cote est en bas, et la hanche passe
  // de justesse au-dessus du coude puisque tous deux touchent le sol. Un
  // testeur voyait donc le chrono tourner « alors que je ne suis pas en
  // position ». Ce qui distingue vraiment une planche laterale, c'est que le
  // buste est *souleve* par l'appui sur l'avant-bras.
  const souleve = appui_sur_le_bras(corps.epaule_gauche, corps.coude_gauche, corps.hanche_gauche) > 0.25;

  // Buste souleve ne suffisait pas : il ne descendait jamais sous 0,43,
  // allonge sur le cote on reste appuye sur le coude. Il manquait la hanche
  // decollee du sol.
  const decollee = gainage_lateral_decolle(corps.epaule_gauche, corps.hanche_gauche, corps.cheville_gauche);

  if (corps_aligne && cote_gauche_au_sol && hanche_au_dessus_coude && souleve && decollee) {
    return "maintien";
  }

  return "repos";
}

export function detection_gainage_laterale_droite(corps) {
  const angle_hanche_droite = calculer_angle(
    corps.epaule_droite,
    corps.hanche_droite,
    corps.cheville_droite
  );
  // Meme resserrement que du cote gauche, et pour la meme raison.
  const corps_aligne = angle_hanche_droite > 155;

  const cote_droit_au_sol = corps.epaule_droite.y > corps.epaule_gauche.y;

  const hanche_au_dessus_coude = corps.hanche_droite.y < corps.coude_droit.y;

  // Allonge sur le cote sans rien faire, les trois conditions precedentes sont
  // reunies : le corps est aligne, le bon cote est en bas, et la hanche passe
  // de justesse au-dessus du coude puisque tous deux touchent le sol. Un
  // testeur voyait donc le chrono tourner « alors que je ne suis pas en
  // position ». Ce qui distingue vraiment une planche laterale, c'est que le
  // buste est *souleve* par l'appui sur l'avant-bras.
  const souleve = appui_sur_le_bras(corps.epaule_droite, corps.coude_droit, corps.hanche_droite) > 0.25;

  // Buste souleve ne suffisait pas : il ne descendait jamais sous 0,43,
  // allonge sur le cote on reste appuye sur le coude. Il manquait la hanche
  // decollee du sol.
  const decollee = gainage_lateral_decolle(corps.epaule_droite, corps.hanche_droite, corps.cheville_droite);

  if (corps_aligne && cote_droit_au_sol && hanche_au_dessus_coude && souleve && decollee) {
    return "maintien";
  }

  return "repos";
}

export function rowing_unilateral_gauche_detection(corps) {
  const angle_coude_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.coude_gauche,
    corps.poignet_gauche
  );
  const angle_buste_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.hanche_gauche,
    corps.genou_gauche
  );

  const poignet_au_dessus_hanche = corps.poignet_gauche.y < corps.hanche_gauche.y;
  const buste_penche = angle_buste_gauche < 160;

  // Seuil du haut ouvert de 70 a 90 degres, trop severe.
  if (angle_coude_gauche < 90 && poignet_au_dessus_hanche && buste_penche) {
    return "fin";
  } else if (angle_coude_gauche > 150) {
    return "debut";
  }
  return "milieu";
}

export function rowing_unilateral_gauche_erreur_buste(corps) {
  const angle_buste_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.hanche_gauche,
    corps.genou_gauche
  );
  if (angle_buste_gauche >= 160) return "forme_buste_pas_assez_penche";
  return null;
}

export function rowing_unilateral_droit_detection(corps) {
  const angle_coude_droit = calculer_angle(
    corps.epaule_droite,
    corps.coude_droit,
    corps.poignet_droit
  );
  const angle_buste_droit = calculer_angle(
    corps.epaule_droite,
    corps.hanche_droite,
    corps.genou_droit
  );

  const poignet_au_dessus_hanche = corps.poignet_droit.y < corps.hanche_droite.y;
  const buste_penche = angle_buste_droit < 160;

  // Seuil du haut ouvert de 70 a 90 degres, trop severe.
  if (angle_coude_droit < 90 && poignet_au_dessus_hanche && buste_penche) {
    return "fin";
  } else if (angle_coude_droit > 150) {
    return "debut";
  }
  return "milieu";
}

export function rowing_unilateral_droit_erreur_buste(corps) {
  const angle_buste_droit = calculer_angle(
    corps.epaule_droite,
    corps.hanche_droite,
    corps.genou_droit
  );
  if (angle_buste_droit >= 160) return "forme_buste_pas_assez_penche";
  return null;
}

export function rowing_penche_detection(corps) {
  const angle_coude_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.coude_gauche,
    corps.poignet_gauche
  );
  const angle_buste_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.hanche_gauche,
    corps.genou_gauche
  );

  const poignet_au_dessus_hanche = corps.poignet_gauche.y < corps.hanche_gauche.y;
  const buste_penche = angle_buste_gauche < 165;

  if (angle_coude_gauche < 70 && poignet_au_dessus_hanche && buste_penche) {
    return "fin";
  } else if (angle_coude_gauche > 150) {
    return "debut";
  }
  return "milieu";
}

export function rowing_penche_erreur_buste(corps) {
  const angle_buste_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.hanche_gauche,
    corps.genou_gauche
  );
  if (angle_buste_gauche >= 165) return "forme_buste_pas_assez_penche";
  return null;
}

export function rowing_penche_erreur_genoux(corps) {
  const angle_genou_gauche = calculer_angle(
    corps.hanche_gauche,
    corps.genou_gauche,
    corps.cheville_gauche
  );
  if (angle_genou_gauche < 155) return "forme_genoux_trop_plies";
  return null;
}

export function oiseau_detection(corps) {
  const angle_bras_gauche = calculer_angle(
    corps.hanche_gauche,
    corps.epaule_gauche,
    corps.coude_gauche
  );
  const angle_bras_droit = calculer_angle(
    corps.hanche_droite,
    corps.epaule_droite,
    corps.coude_droit
  );
  const angle_bras_moyen = (angle_bras_gauche + angle_bras_droit) / 2;

  if (angle_bras_moyen > 65) return "fin";
  else if (angle_bras_moyen < 30) return "debut";
  return "milieu";
}

export function oiseau_erreur_coudes(corps) {
  const angle_coude_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.coude_gauche,
    corps.poignet_gauche
  );
  const angle_coude_droit = calculer_angle(
    corps.epaule_droite,
    corps.coude_droit,
    corps.poignet_droit
  );
  const angle_coude_moyen = (angle_coude_gauche + angle_coude_droit) / 2;

  if (angle_coude_moyen > 170) return "forme_coudes_trop_tendus";
  if (angle_coude_moyen < 120) return "forme_coudes_trop_plies";
  return null;
}

// Hauteur de la hanche au-dessus du genou, rapportee a celle du tibia. Sans
// unite, donc independante de la taille de la personne et de sa distance a la
// camera : environ 1 debout, tend vers 0 quand la hanche arrive a hauteur de
// genou. Une mesure et non une detection : elle reste hors de `DETECTIONS`.
function descente_hanche(hanche, genou, cheville) {
  const tibia = cheville.y - genou.y;
  if (tibia <= 0) return null;
  return (genou.y - hanche.y) / tibia;
}

// Le squat sur chaise a quitte le catalogue : plus aucun mouvement ne nomme
// cette detection. Elle reste pour les entrees figees des tests
// (`tests/fixtures/donnees/`), qui le contiennent encore et dont les reponses
// ont ete verifiees avec elle.
export function squat_sur_chaise_detection(corps) {
  // Profondeur lue sur la descente de la hanche, et non sur un angle. Deux
  // reperes ont ete essayes avant celui-ci, et chacun supposait un point de
  // vue. La distance coude-genou de squat_detection suppose des halteres qui
  // pendent le long du corps. L'angle du genou, lui, ne se lit que de profil :
  // la flexion se fait dans le plan sagittal, donc *vers* la camera quand on
  // lui fait face, et une projection en deux dimensions garde alors la jambe
  // presque droite au plus bas du mouvement — la detection ne quittait jamais
  // "fin" et ne comptait rien.
  //
  // Les deux jambes sont moyennees et non exigees ensemble : de face elles
  // sont egalement visibles, de profil la plus eloignee est estimee, et une
  // moyenne encaisse cette estimation la ou une conjonction s'y casse.
  const mesures = [
    descente_hanche(corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche),
    descente_hanche(corps.hanche_droite, corps.genou_droit, corps.cheville_droite),
  ].filter((mesure) => mesure !== null);
  if (!mesures.length) return "milieu";

  const descente = mesures.reduce((a, b) => a + b, 0) / mesures.length;
  if (descente < 0.45) return "debut";
  if (descente > 0.75) return "fin";
  return "milieu";
}

// ---------------------------------------------------------------- sauts
//
// Les sauts de la seance cardio, comptes en AMRAP et vus de face. Toutes les
// mesures sont rapportees au corps (largeur d'epaules, buste, tibia) : a trois
// metres comme a deux, un saut fait les memes nombres.

// L'ecart des chevilles, en largeurs d'epaules : vers 0,3 a 0,6 pieds joints,
// au-dela de 1,5 jambes ecartees d'un saut. null si les epaules sont
// illisibles.
function ecart_chevilles(corps) {
  return ecart_rapporte_aux_epaules(corps.cheville_gauche, corps.cheville_droite, corps);
}

// La hauteur sous son epaule du poignet **le plus bas** des deux, en bustes
// (`hauteur_sous_epaule`). Negative : les deux mains sont au-dessus des
// epaules. null si un cote est illisible — « les deux bras » ne se devine pas.
function bras_le_plus_bas(corps) {
  const gauche = hauteur_sous_epaule(corps.poignet_gauche, corps.epaule_gauche, corps.hanche_gauche);
  const droite = hauteur_sous_epaule(corps.poignet_droit, corps.epaule_droite, corps.hanche_droite);
  if (gauche === null || droite === null) return null;
  return Math.max(gauche, droite);
}

// La meme hauteur pour le poignet **le plus haut** : au-dela de 0,6, les deux
// bras sont le long du corps.
function bras_le_plus_haut(corps) {
  const gauche = hauteur_sous_epaule(corps.poignet_gauche, corps.epaule_gauche, corps.hanche_gauche);
  const droite = hauteur_sous_epaule(corps.poignet_droit, corps.epaule_droite, corps.hanche_droite);
  if (gauche === null || droite === null) return null;
  return Math.min(gauche, droite);
}

// La descente des hanches, moyenne des deux jambes (`descente_hanche`) :
// environ 1 debout, vers 0 hanches a hauteur de genoux. Verticale, donc
// lisible de face, la ou l'angle du genou ne l'est pas.
function descente_hanches(corps) {
  const mesures = [
    descente_hanche(corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche),
    descente_hanche(corps.hanche_droite, corps.genou_droit, corps.cheville_droite),
  ].filter((mesure) => mesure !== null);
  if (!mesures.length) return null;
  return mesures.reduce((a, b) => a + b, 0) / mesures.length;
}

// Le toucher croise d'un stance jack : la main qui descend (le poignet le
// plus bas) et le pied **oppose**. Le poignet droit va au pied gauche.
function main_qui_touche(corps) {
  const droite = corps.poignet_droit.y >= corps.poignet_gauche.y;
  return droite
    ? { poignet: corps.poignet_droit, genou: corps.genou_gauche, cheville: corps.cheville_gauche,
        hanche_opposee: corps.hanche_gauche, hanche: corps.hanche_droite }
    : { poignet: corps.poignet_gauche, genou: corps.genou_droit, cheville: corps.cheville_droite,
        hanche_opposee: corps.hanche_droite, hanche: corps.hanche_gauche };
}

// La hauteur de cette main au-dessus du pied oppose, en tibias : vers 1,8
// debout bras le long du corps, sous 0,6 la main au pied. null si le tibia
// est illisible.
function toucher_hauteur(corps) {
  const { poignet, genou, cheville } = main_qui_touche(corps);
  const tibia = calculer_distance(genou, cheville);
  if (tibia <= 0) return null;
  return (cheville.y - poignet.y) / tibia;
}

// De combien cette main a passe l'axe du corps (le milieu des hanches) vers le
// cote oppose, en largeurs d'epaules : positif quand elle va bien au pied
// d'en face. Pieds joints, le pied oppose est juste de l'autre cote de l'axe,
// et c'est ce passage qui distingue le toucher croise d'une main au pied du
// meme cote. Rien n'est suppose du sens de l'image : le cote oppose se lit sur
// les hanches. null si les epaules sont illisibles.
function toucher_croisement(corps) {
  const { poignet, hanche_opposee, hanche } = main_qui_touche(corps);
  const largeur = calculer_distance(corps.epaule_gauche, corps.epaule_droite);
  if (largeur <= 0) return null;
  const milieu = (hanche_opposee.x + hanche.x) / 2;
  const sens = hanche_opposee.x >= hanche.x ? 1 : -1;
  return ((poignet.x - milieu) * sens) / largeur;
}

// L'ecart des poignets, en largeurs d'epaules : vers 0,3 mains jointes, 2 a 3
// bras en V. null si les epaules sont illisibles.
function ecart_poignets(corps) {
  return ecart_rapporte_aux_epaules(corps.poignet_gauche, corps.poignet_droit, corps);
}

// Jumping jack : pieds rapproches et bras le long du corps, puis jambes
// ecartees et les deux mains au-dessus des epaules, **presque jointes** (a
// moins de 0,8 epaule l'une de l'autre) : des bras en V ne comptent pas
// (demande du 2026-10-29). Les deux seuils de chaque
// mesure laissent une zone morte entre eux (hysteresis), et un jumping jack a
// moitie fait — bras a l'horizontale, pieds a peine ecartes — reste en
// `milieu`. Le buste debout est une condition de position commune.
export const JACK_ECART_JOINT = 0.9;
export const JACK_ECART_ECARTE = 1.3;
export const JACK_BRAS_BAS = 0.6;
export const JACK_BRAS_HAUT = 0;
export const JACK_MAINS_JOINTES = 0.8;

export function jumping_jacks_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const ecart = ecart_chevilles(corps);
  const bas = bras_le_plus_bas(corps);
  const haut = bras_le_plus_haut(corps);
  const mains = ecart_poignets(corps);
  if (ecart !== null && ecart > JACK_ECART_ECARTE && bas !== null && bas < JACK_BRAS_HAUT
      && mains !== null && mains < JACK_MAINS_JOINTES) return "fin";
  if (ecart !== null && ecart < JACK_ECART_JOINT && haut !== null && haut > JACK_BRAS_BAS) return "debut";
  return "milieu";
}

// Power jack : on retombe jambes ecartees en squat (`debut`), on remonte en
// sautant bras au-dessus de la tete (`fin`, la fin de la phase concentrique).
// L'ecart des pieds n'est demande qu'en bas, les bras qu'en haut.
// Debout, la descente vaut 1,26 a 1,41 ; un squat de power jack, 0,5 a 0,85
// selon la fatigue (premier banc du 2026-10-29 : aucun ne passait sous 0,6 ;
// second banc : dix squats arretes entre 0,75 et 0,82, « il me demande de
// descendre trop bas »).
export const POWER_JACK_HANCHES_BAS = 0.85;
export const POWER_JACK_HANCHES_HAUT = 1.05;

export function power_jacks_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const hanches = descente_hanches(corps);
  const ecart = ecart_chevilles(corps);
  const bas = bras_le_plus_bas(corps);
  if (hanches !== null && hanches > POWER_JACK_HANCHES_HAUT && bas !== null && bas < JACK_BRAS_HAUT) return "fin";
  if (hanches !== null && hanches < POWER_JACK_HANCHES_BAS && ecart !== null && ecart > JACK_ECART_ECARTE) return "debut";
  return "milieu";
}

// Stance jack : debout pieds joints (`debut`), puis une main touche le pied
// oppose (`fin`) ; chaque toucher compte, et l'on remonte pieds joints entre
// deux. Pas de condition sur le buste : il se penche pour toucher. Les pieds
// joints tiennent le neutre : sans eux, le poignet qui touche, cache derriere
// la jambe, sautait d'une image vers le haut et le toucher comptait deux fois
// (banc du 2026-10-29, main droite sur pied gauche). Et le toucher se fait
// pieds ecartes : pieds joints, se pencher vers ses pieds comptait (second banc).
export const STANCE_JACK_TOUCHER = 0.6;
export const STANCE_JACK_ECARTE = 1.1;
export const STANCE_JACK_DEBOUT = 1.4;
export const STANCE_JACK_CROISEMENT = 0.05;

export function stance_jacks_detection(corps) {
  const hauteur = toucher_hauteur(corps);
  const croisement = toucher_croisement(corps);
  const ecart = ecart_chevilles(corps);
  if (hauteur !== null && hauteur < STANCE_JACK_TOUCHER && croisement !== null && croisement > STANCE_JACK_CROISEMENT
      && ecart !== null && ecart > STANCE_JACK_ECARTE) {
    return "fin";
  }
  if (hauteur !== null && hauteur > STANCE_JACK_DEBOUT && ecart !== null && ecart < JACK_ECART_JOINT) return "debut";
  return "milieu";
}

// ------------------------------------------------------ jambes alternees
//
// Course, montees de genoux, talons-fesses, Heisman, mountain climber debout,
// switch kicks, scissor runs : **chaque cote compte**. `debut` est la position
// neutre (pieds au sol, genoux au meme niveau), `fin` l'un **ou** l'autre cote
// a son extremite — une mesure qui garde le plus avance des deux cotes. Chaque
// pas repasse par le neutre, et debout immobile on y est : la mise en place
// marche telle quelle (`depart: "debut"`). Ces mouvements vont vite : chacun
// declare son `delai_min_reps`.

// Le tibia d'une jambe, null s'il est illisible.
function tibia(genou, cheville) {
  const longueur = calculer_distance(genou, cheville);
  return longueur > 0 ? longueur : null;
}

// De combien le pied le plus leve est au-dessus de l'autre, en tibias (de sa
// jambe) : 0 pieds au sol, au-dela de 1 le talon monte vers la fesse. Lisible
// de face comme de profil. null si un tibia est illisible.
function pied_le_plus_leve(corps) {
  const t_gauche = tibia(corps.genou_gauche, corps.cheville_gauche);
  const t_droite = tibia(corps.genou_droit, corps.cheville_droite);
  if (t_gauche === null || t_droite === null) return null;
  return Math.max(
    (corps.cheville_droite.y - corps.cheville_gauche.y) / t_gauche,
    (corps.cheville_gauche.y - corps.cheville_droite.y) / t_droite
  );
}

// De combien le genou le plus haut depasse l'autre, en tibias
// (`genou_au_dessus_de_l_autre`, des deux cotes). null si un cote est
// illisible.
function genou_le_plus_leve(corps) {
  const gauche = genou_au_dessus_de_l_autre(corps.genou_gauche, corps.cheville_gauche, corps.genou_droit);
  const droite = genou_au_dessus_de_l_autre(corps.genou_droit, corps.cheville_droite, corps.genou_gauche);
  if (gauche === null || droite === null) return null;
  return Math.max(gauche, droite);
}

// Le genou le plus haut, sous sa hanche, en tibias : vers 1 debout, 0 genou a
// hauteur de hanche, negatif au-dessus. Verticale : lisible de profil, ou la
// cuisse se leve devant soi. null si un tibia est illisible.
function genou_le_plus_haut_sous_hanche(corps) {
  const t_gauche = tibia(corps.genou_gauche, corps.cheville_gauche);
  const t_droite = tibia(corps.genou_droit, corps.cheville_droite);
  if (t_gauche === null || t_droite === null) return null;
  return Math.min(
    (corps.genou_gauche.y - corps.hanche_gauche.y) / t_gauche,
    (corps.genou_droit.y - corps.hanche_droite.y) / t_droite
  );
}

// La jambe levee (genou le plus haut) et la jambe d'appui, l'autre.
function jambes_levee_et_appui(corps) {
  const gauche_levee = corps.genou_gauche.y <= corps.genou_droit.y;
  const gauche = { genou: corps.genou_gauche, cheville: corps.cheville_gauche, hanche: corps.hanche_gauche,
    poignet: corps.poignet_gauche };
  const droite = { genou: corps.genou_droit, cheville: corps.cheville_droite, hanche: corps.hanche_droite,
    poignet: corps.poignet_droit };
  return gauche_levee ? { levee: gauche, appui: droite } : { levee: droite, appui: gauche };
}

// Heisman : de combien le pied d'appui est sorti a l'exterieur de sa hanche,
// en largeurs d'epaules. On retombe sur un pied, de cote : le pied d'appui est
// alors hors de la ligne des hanches, la ou une montee de genou sur place le
// garde dessous. L'exterieur se lit sur les hanches, rien n'est suppose du
// sens de l'image. null si les epaules sont illisibles.
function appui_exterieur(corps) {
  const { levee, appui } = jambes_levee_et_appui(corps);
  const largeur = calculer_distance(corps.epaule_gauche, corps.epaule_droite);
  if (largeur <= 0) return null;
  const sens = appui.hanche.x >= levee.hanche.x ? 1 : -1;
  return ((appui.cheville.x - appui.hanche.x) * sens) / largeur;
}

// Mountain climber debout : la main opposee au genou leve, au-dessus de la
// tete (du nez), en bustes. Positive : la main est plus haute que la tete.
// null si le buste est illisible.
function main_opposee_au_dessus_de_la_tete(corps) {
  const { appui } = jambes_levee_et_appui(corps);
  const epaules_y = (corps.epaule_gauche.y + corps.epaule_droite.y) / 2;
  const hanches_y = (corps.hanche_gauche.y + corps.hanche_droite.y) / 2;
  const buste = hanches_y - epaules_y;
  if (buste <= 0) return null;
  return (corps.nez.y - appui.poignet.y) / buste;
}

// Le pied le plus haut (switch kick) : sa hauteur sous sa hanche, en tibias
// (vers 2 debout, 0 cheville a hauteur de hanche), et sa portee horizontale
// depuis la hanche, en tibias. La portee distingue le coup de pied, jambe
// lancee devant, du talon-fesse, ou la cheville monte sous la hanche.
function pied_haut(corps) {
  const gauche_haut = corps.cheville_gauche.y <= corps.cheville_droite.y;
  return gauche_haut
    ? { cheville: corps.cheville_gauche, genou: corps.genou_gauche, hanche: corps.hanche_gauche }
    : { cheville: corps.cheville_droite, genou: corps.genou_droit, hanche: corps.hanche_droite };
}

function pied_haut_sous_hanche(corps) {
  const { cheville, genou, hanche } = pied_haut(corps);
  const longueur = tibia(genou, cheville);
  if (longueur === null) return null;
  return (cheville.y - hanche.y) / longueur;
}

function pied_haut_portee(corps) {
  const { cheville, genou, hanche } = pied_haut(corps);
  const longueur = tibia(genou, cheville);
  if (longueur === null) return null;
  return Math.abs(cheville.x - hanche.x) / longueur;
}

// Scissor runs : l'ecart avant-arriere des chevilles, de profil, en tibias
// (moyenne des deux). null si un tibia est illisible.
function ecart_avant_arriere(corps) {
  const t_gauche = tibia(corps.genou_gauche, corps.cheville_gauche);
  const t_droite = tibia(corps.genou_droit, corps.cheville_droite);
  if (t_gauche === null || t_droite === null) return null;
  return Math.abs(corps.cheville_gauche.x - corps.cheville_droite.x) / ((t_gauche + t_droite) / 2);
}

// Course sur place, de face : un pied quitte le sol (> 0,25 tibia), puis les
// deux y reviennent (< 0,08).
export const COURSE_PIED_LEVE = 0.25;
export const COURSE_PIEDS_AU_SOL = 0.08;

export function course_sur_place_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const pied = pied_le_plus_leve(corps);
  if (pied !== null && pied > COURSE_PIED_LEVE) return "fin";
  if (pied !== null && pied < COURSE_PIEDS_AU_SOL) return "debut";
  return "milieu";
}

// Montees de genoux, de profil : un genou **au niveau de sa hanche**
// (< 0,05 tibia dessous) ; en dessous, c'est de la course. Les deux genoux
// bas (> 0,7) font le neutre.
export const MONTEE_GENOU_HAUT = 0.05;
export const MONTEE_GENOUX_BAS = 0.7;

export function montees_de_genou_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const genou = genou_le_plus_haut_sous_hanche(corps);
  if (genou !== null && genou < MONTEE_GENOU_HAUT) return "fin";
  if (genou !== null && genou > MONTEE_GENOUX_BAS) return "debut";
  return "milieu";
}

// Talons-fesses, de profil : le talon monte haut (pied > 0,7 tibia au-dessus
// de l'autre) **et** les genoux restent au meme niveau (< 0,3) — le genou
// pointe le sol. Sans cette seconde condition, une montee de genou comptait.
// Le neutre est large (< 0,3) : en courant, le pied qui redescend croise
// l'autre en l'air, et la difference ne repasse pas sous 0,15 entre deux
// images (premier banc du 2026-10-29 : 17 pas sur 20 sans retour au neutre).
// A 0,4, il comptait en trop (second banc : 20 pour 15) ; resserre a 0,3, avec
// un delai de 0,25 s (mouvements.json).
export const TALON_HAUT = 0.7;
export const TALON_GENOUX_ALIGNES = 0.3;
export const TALON_PIEDS_AU_SOL = 0.3;

export function talons_fesses_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const pied = pied_le_plus_leve(corps);
  const genou = genou_le_plus_leve(corps);
  if (pied !== null && pied > TALON_HAUT && genou !== null && genou < TALON_GENOUX_ALIGNES) return "fin";
  if (pied !== null && pied < TALON_PIEDS_AU_SOL) return "debut";
  return "milieu";
}

// Heisman, de face : un genou leve (> 0,5 tibia au-dessus de l'autre) **et**
// le pied d'appui hors de la ligne des hanches (> 0,1 epaule). Genoux au meme
// niveau (< 0,15) : le neutre, entre deux appuis.
export const HEISMAN_GENOU_LEVE = 0.5;
export const HEISMAN_APPUI_EXTERIEUR = 0.1;
export const GENOUX_ALIGNES = 0.15;

export function heisman_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const genou = genou_le_plus_leve(corps);
  const appui = appui_exterieur(corps);
  if (genou !== null && genou > HEISMAN_GENOU_LEVE && appui !== null && appui > HEISMAN_APPUI_EXTERIEUR) return "fin";
  if (genou !== null && genou < GENOUX_ALIGNES) return "debut";
  return "milieu";
}

// Mountain climber debout, de profil : un genou leve (> 0,5 tibia au-dessus de
// l'autre) **et** la main opposee au-dessus de la tete. Genoux au meme niveau :
// le neutre.
export const CLIMBER_GENOU_LEVE = 0.5;
export const CLIMBER_MAIN_HAUTE = 0;

export function mountain_climber_debout_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const genou = genou_le_plus_leve(corps);
  const main = main_opposee_au_dessus_de_la_tete(corps);
  if (genou !== null && genou > CLIMBER_GENOU_LEVE && main !== null && main > CLIMBER_MAIN_HAUTE) return "fin";
  if (genou !== null && genou < GENOUX_ALIGNES) return "debut";
  return "milieu";
}

// Switch kicks, de profil : le pied le plus haut pres de la hanche (< 0,75
// tibia dessous) **et** lance loin d'elle (portee > 1 tibia). Debout, pieds
// au sol, il est a ~2 tibias sous la hanche (> 1,6).
export const KICK_PIED_HAUT = 0.75;
export const KICK_PORTEE = 1;
export const KICK_PIEDS_AU_SOL = 1.6;

export function switch_kicks_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const hauteur = pied_haut_sous_hanche(corps);
  const portee = pied_haut_portee(corps);
  if (hauteur !== null && hauteur < KICK_PIED_HAUT && portee !== null && portee > KICK_PORTEE) return "fin";
  if (hauteur !== null && hauteur > KICK_PIEDS_AU_SOL) return "debut";
  return "milieu";
}

// Scissor runs, de profil : pieds ecartes d'avant en arriere (> 0,7 tibia),
// puis ramenes l'un pres de l'autre (< 0,35) a chaque echange. A 1 tibia, un
// echange sur trois n'arrivait pas (banc du 2026-10-29 : 0,7 a 0,98).
export const CISEAUX_ECARTES = 0.7;
export const CISEAUX_JOINTS = 0.35;

export function scissor_runs_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const ecart = ecart_avant_arriere(corps);
  if (ecart !== null && ecart > CISEAUX_ECARTES) return "fin";
  if (ecart !== null && ecart < CISEAUX_JOINTS) return "debut";
  return "milieu";
}

// ---------------------------------------------------------------- au sol
//
// Burpee et suicide jumps, de profil : on descend au sol, on revient debout et
// l'on saute. **Le saut n'est pas verifie** : en l'air ou debout, le corps a la
// meme forme, et c'est le retour debout qui compte (`fin`). Depart `fin` :
// on se met en place debout.
//
// Debout se lit a l'angle du buste et aux hanches **rapportees a la longueur
// du tibia**, jamais a sa hauteur (`descente_hanches`) : accroupi ou en
// planche, le tibia se couche, sa hauteur tend vers zero et la mesure
// explosait (30 et plus). Le burpee comptait des qu'on ramenait les pieds aux
// mains, et le suicide jump comptait aussi en planche, ou le buste oscille
// autour de 45 degres.

// Les hanches au-dessus des genoux, en tibias (longueur, pas hauteur) :
// vers 1 debout, vers 0 accroupi ou en planche. Moyenne des deux jambes : de
// profil, la plus eloignee est estimee. null si aucun tibia n'est lisible.
function hanches_au_dessus_des_genoux(corps) {
  const mesures = [
    [corps.hanche_gauche, corps.genou_gauche, corps.cheville_gauche],
    [corps.hanche_droite, corps.genou_droit, corps.cheville_droite],
  ].map(([hanche, genou, cheville]) => {
    const longueur = calculer_distance(genou, cheville);
    return longueur > 0 ? (genou.y - hanche.y) / longueur : null;
  }).filter((mesure) => mesure !== null);
  if (!mesures.length) return null;
  return mesures.reduce((a, b) => a + b, 0) / mesures.length;
}

// Debout : buste redresse au-dela de 60 degres et hanches hautes. Couche :
// buste sous 45 degres. L'ecart entre les deux est l'hysteresis du buste.
export const SOL_BUSTE_DEBOUT = 60;
export const SOL_BUSTE_COUCHE = 45;
export const SOL_DEBOUT_HANCHES = 0.7;

function debout_apres_le_sol(corps) {
  const hanches = hanches_au_dessus_des_genoux(corps);
  return inclinaison_buste(corps) > SOL_BUSTE_DEBOUT && hanches !== null && hanches > SOL_DEBOUT_HANCHES;
}

// Burpee : **la pompe est verifiee**. `debut` est le bas d'une pompe — buste
// couche, coude plie sous le seuil qui arme une pompe
// (`SEUIL_COMPTAGE_POMPE`, la meme regle que les pompes). Une planche bras
// tendus ne l'arme pas : un burpee sans pompe ne compte pas.
export function burpee_detection(corps) {
  if (debout_apres_le_sol(corps)) return "fin";
  if (inclinaison_buste(corps) < SOL_BUSTE_COUCHE && angle_coude_proche(corps) < SEUIL_COMPTAGE_POMPE) return "debut";
  return "milieu";
}

// Suicide jumps : la planche **bras tendus** arme (coude au-dela de 150
// degres), sans pompe.
export const SUICIDE_BRAS_TENDUS = 150;

export function suicide_jumps_detection(corps) {
  if (debout_apres_le_sol(corps)) return "fin";
  if (inclinaison_buste(corps) < SOL_BUSTE_COUCHE && angle_coude_proche(corps) > SUICIDE_BRAS_TENDUS) return "debut";
  return "milieu";
}

// ----------------------------------------------------------- power knees
//
// Un cote par serie : « Power knees droit » et « Power knees gauche », relies
// par `autre_cote` (le genou de l'autre jambe se dit « c'est l'autre jambe »).
// De face. `debut` : les mains au-dessus de la tete (les deux poignets
// au-dessus des epaules) et les genoux au meme niveau. `fin` : le genou
// mesure leve (> 0,5 tibia au-dessus de l'autre) **et** les deux mains
// descendues le toucher (a moins de 0,8 tibia de lui).
export const POWER_KNEE_GENOU_LEVE = 0.5;
export const POWER_KNEE_MAINS = 0.8;

// La main la plus loin du genou, en tibias de cette jambe : les deux mains
// le touchent quand elle est proche. null si le tibia est illisible.
function mains_au_genou(genou, cheville, corps) {
  const longueur = tibia(genou, cheville);
  if (longueur === null) return null;
  return Math.max(
    calculer_distance(corps.poignet_gauche, genou),
    calculer_distance(corps.poignet_droit, genou)
  ) / longueur;
}

function power_knee(genou, cheville, autre_genou, corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const leve = genou_au_dessus_de_l_autre(genou, cheville, autre_genou);
  const mains = mains_au_genou(genou, cheville, corps);
  const bras = bras_le_plus_bas(corps);
  if (leve !== null && leve > POWER_KNEE_GENOU_LEVE && mains !== null && mains < POWER_KNEE_MAINS) return "fin";
  if (leve !== null && leve < GENOUX_ALIGNES && bras !== null && bras < JACK_BRAS_HAUT) return "debut";
  return "milieu";
}

export function power_knees_droit_detection(corps) {
  return power_knee(corps.genou_droit, corps.cheville_droite, corps.genou_gauche, corps);
}

export function power_knees_gauche_detection(corps) {
  return power_knee(corps.genou_gauche, corps.cheville_gauche, corps.genou_droit, corps);
}

// -------------------------------------------------------------- crochets
//
// Des crochets par paquets (quelques-uns d'un cote, puis de l'autre), de face :
// chaque crochet compte, quel que soit le bras. `debut` : la garde, les deux
// poings au-dessus de la taille (0,75 buste sous l'epaule) et chacun de son
// cote. A mi-buste, le poing qui revient d'un crochet n'etait pas encore
// remonte quand partait le suivant (banc du 2026-10-29). `fin` : un
// poing passe la ligne du milieu des epaules vers l'autre cote, **a hauteur
// d'epaule**.

// Le poing le plus avance vers l'autre cote : de combien il a passe le milieu
// des epaules, en largeurs d'epaules (positif : de l'autre cote), et sa hauteur
// sous son epaule, en bustes (`hauteur_sous_epaule`). L'autre cote se lit sur
// les epaules, rien n'est suppose du sens de l'image.
function poing_qui_croise(corps) {
  const largeur = calculer_distance(corps.epaule_gauche, corps.epaule_droite);
  if (largeur <= 0) return null;
  const milieu = (corps.epaule_gauche.x + corps.epaule_droite.x) / 2;
  const vers_la_gauche = corps.epaule_gauche.x >= corps.epaule_droite.x ? 1 : -1;
  const droit = ((corps.poignet_droit.x - milieu) * vers_la_gauche) / largeur;
  const gauche = ((milieu - corps.poignet_gauche.x) * vers_la_gauche) / largeur;
  return droit >= gauche
    ? { croisement: droit, poignet: corps.poignet_droit, epaule: corps.epaule_droite, hanche: corps.hanche_droite }
    : { croisement: gauche, poignet: corps.poignet_gauche, epaule: corps.epaule_gauche, hanche: corps.hanche_gauche };
}

function crochet_croisement(corps) {
  return poing_qui_croise(corps)?.croisement ?? null;
}

// L'ecart de ce poing a la hauteur de son epaule, en bustes, sans signe : 0 a
// hauteur d'epaule exactement.
function crochet_hauteur(corps) {
  const poing = poing_qui_croise(corps);
  if (poing === null) return null;
  const hauteur = hauteur_sous_epaule(poing.poignet, poing.epaule, poing.hanche);
  return hauteur === null ? null : Math.abs(hauteur);
}

export const CROCHET_CROISE = 0.3;
export const CROCHET_HAUTEUR = 0.35;
export const GARDE_DE_SON_COTE = 0.1;
export const GARDE_HAUTE = 0.75;

export function crochets_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const croisement = crochet_croisement(corps);
  const hauteur = crochet_hauteur(corps);
  const garde = bras_le_plus_bas(corps);
  if (croisement !== null && croisement > CROCHET_CROISE && hauteur !== null && hauteur < CROCHET_HAUTEUR) return "fin";
  if (croisement !== null && croisement < GARDE_DE_SON_COTE && garde !== null && garde < GARDE_HAUTE) return "debut";
  return "milieu";
}

// ------------------------------------------------------------------- ski
//
// Sauts lateraux pieds joints, d'un cote a l'autre, de face : chaque reception
// compte, **cuisses flechies** (`fin`), et l'on se rearme jambes tendues, a
// l'impulsion (`debut`). Le passage par le milieu n'est plus demande : il se
// fait en l'air, sur peu d'images, et decale d'un cote on ne voyait qu'une
// reception sur deux (banc du 2026-10-29). **Seul mouvement qui lit un repere
// exterieur au corps** : le centre de l'image (les coordonnees du modele vont
// de 0 a 1), pour qu'un squat saute sur place, au milieu, ne compte pas. Le
// seuil est bas (0,15 epaule) : decale d'une demi-epaule, on retombait d'un cote
// a 0,2-0,4 du centre et ces receptions ne comptaient pas (second banc du
// 2026-10-29, 6 sur 20). La fiche demande de se placer au milieu de l'image.

// De combien le milieu des chevilles s'ecarte du centre de l'image, sans signe,
// en largeurs d'epaules. null si les epaules sont illisibles.
function ecart_au_centre(corps) {
  const largeur = calculer_distance(corps.epaule_gauche, corps.epaule_droite);
  if (largeur <= 0) return null;
  const milieu = (corps.cheville_gauche.x + corps.cheville_droite.x) / 2;
  return Math.abs(milieu - 0.5) / largeur;
}

// La flexion se lit a la descente des hanches (`descente_hanches`, verticale,
// lisible de face) : 1,26 a 1,41 debout, sous 1,1 cuisses flechies (au second
// banc, des receptions flechies s'arretaient entre 1 et 1,1).
export const SKI_DE_COTE = 0.15;
export const SKI_FLECHI = 1.1;
export const SKI_TENDU = 1.25;

export function ski_detection(corps) {
  if (!(buste_vertical(corps) > 0)) return "milieu";
  const ecart = ecart_au_centre(corps);
  const hanches = descente_hanches(corps);
  if (hanches !== null && hanches < SKI_FLECHI && ecart !== null && ecart > SKI_DE_COTE) return "fin";
  if (hanches !== null && hanches > SKI_TENDU) return "debut";
  return "milieu";
}

// Les mesures privees sont exportees sous un nom prefixe pour que
// instruments.js les reprenne au lieu de les recopier. Elles restent hors de
// DETECTIONS, que les tests rejouent en entier : une mesure ne rend pas de
// jeton.
export {
  appui_sur_le_bras as _appui_sur_le_bras,
  descente_hanche as _descente_hanche,
  hauteur_sous_epaule as _hauteur_sous_epaule,
  ecart_lateral as _ecart_lateral,
  angle_coude_proche as _angle_coude_proche,
  bras_proche as _bras_proche,
  visibilite_bras as _visibilite_bras,
  genou_depasse_pied as _genou_depasse_pied,
  buste_vertical as _buste_vertical,
  inclinaison_buste as _inclinaison_buste,
  ecart_rapporte_aux_epaules as _ecart_rapporte_aux_epaules,
  hanche_decollee as _hanche_decollee,
  poignet_devant_epaule as _poignet_devant_epaule,
  genou_au_dessus_de_l_autre as _genou_au_dessus_de_l_autre,
  hauteur_poignets as _hauteur_poignets,
  ecart_chevilles as _ecart_chevilles,
  bras_le_plus_bas as _bras_le_plus_bas,
  bras_le_plus_haut as _bras_le_plus_haut,
  descente_hanches as _descente_hanches,
  toucher_hauteur as _toucher_hauteur,
  toucher_croisement as _toucher_croisement,
  pied_le_plus_leve as _pied_le_plus_leve,
  genou_le_plus_leve as _genou_le_plus_leve,
  genou_le_plus_haut_sous_hanche as _genou_le_plus_haut_sous_hanche,
  appui_exterieur as _appui_exterieur,
  main_opposee_au_dessus_de_la_tete as _main_opposee_au_dessus_de_la_tete,
  pied_haut_sous_hanche as _pied_haut_sous_hanche,
  pied_haut_portee as _pied_haut_portee,
  ecart_avant_arriere as _ecart_avant_arriere,
  mains_au_genou as _mains_au_genou,
  crochet_croisement as _crochet_croisement,
  crochet_hauteur as _crochet_hauteur,
  ecart_au_centre as _ecart_au_centre,
  ecart_poignets as _ecart_poignets,
  hanches_au_dessus_des_genoux as _hanches_au_dessus_des_genoux,
};

// Appariement nom -> fonction, consomme par le harnais de comparaison et par
// la couche de seance. Les cles sont les noms que `mouvements.json` designe
// (`detection`, `erreurs`, `amplitude`) : renommer une fonction casse ce lien.
export const DETECTIONS = {
  curl_biceps_droit_detection,
  coude_avance_curl_droit,
  coude_avance_curl_gauche,
  curl_biceps_gauche_detection,
  elevation_laterale_detection,
  pompe_detection,
  pompe_profondeur,
  pompe_mur_detection,
  developpe_couche_sol_detection,
  extension_triceps_au_dessus_de_la_tete_detection,
  developpe_epaule_detection,
  crunches_detection,
  detection_gainage,
  squat_detection,
  fente_droite_detection,
  fente_gauche_detection,
  fente_droite_erreur_genou,
  fente_gauche_erreur_genou,
  souleve_de_terre_roumain_detection,
  detection_gainage_laterale_gauche,
  detection_gainage_laterale_droite,
  rowing_unilateral_gauche_detection,
  rowing_unilateral_gauche_erreur_buste,
  rowing_unilateral_droit_detection,
  rowing_unilateral_droit_erreur_buste,
  rowing_penche_detection,
  rowing_penche_erreur_buste,
  rowing_penche_erreur_genoux,
  oiseau_detection,
  oiseau_erreur_coudes,
  squat_sur_chaise_detection,
  extension_triceps_erreur_coudes,
  jumping_jacks_detection,
  power_jacks_detection,
  stance_jacks_detection,
  course_sur_place_detection,
  montees_de_genou_detection,
  talons_fesses_detection,
  heisman_detection,
  mountain_climber_debout_detection,
  switch_kicks_detection,
  scissor_runs_detection,
  burpee_detection,
  suicide_jumps_detection,
  power_knees_droit_detection,
  power_knees_gauche_detection,
  crochets_detection,
  ski_detection,
};
