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
// elle etait assez profonde.
export const SEUIL_COMPTAGE_POMPE = 120;
export const SEUIL_PROFONDEUR_POMPE = 100;

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
  if (!coudes_leves(corps) || ecart_poignets === null || ecart_poignets >= 0.6) {
    return "milieu";
  }
  if (angle_coude_droit < 90 && angle_coude_gauche < 90) return "debut";
  else if (angle_coude_droit > 140 && angle_coude_gauche > 140) return "fin";
  return "milieu";
}

// Coudes ecartes au-dela de la largeur des epaules, coudes leves seulement
// (bras le long du corps, ils y sont naturellement).
export function extension_triceps_erreur_coudes(corps) {
  if (!coudes_leves(corps)) return null;
  const ecart = ecart_rapporte_aux_epaules(corps.coude_gauche, corps.coude_droit, corps);
  if (ecart !== null && ecart > 1.5) return "forme_coudes_trop_ecartes";
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

export function crunches_detection(corps) {
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
  // Seuils ouverts de 70/95 a 85/100 : a 70 degres il fallait decoller tout le
  // dos, c'est-a-dire faire un releve de buste et non un crunch. L'ecart de 15
  // degres entre les deux bornes est conserve — c'est lui qui empeche un
  // tremblement de landmark de compter une repetition.
  if (angle_hanche_droite < 85 && angle_hanche_gauche < 85) return "fin";
  else if (angle_hanche_droite > 100 && angle_hanche_gauche > 100) return "debut";
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

export function fente_droite_detection(corps) {
  const angle_genou_droit = calculer_angle(
    corps.hanche_droite,
    corps.genou_droit,
    corps.cheville_droite
  );

  if (angle_genou_droit < 100) return "debut";
  else if (angle_genou_droit > 150) return "fin";
  return "milieu";
}

export function fente_gauche_detection(corps) {
  const angle_genou_gauche = calculer_angle(
    corps.hanche_gauche,
    corps.genou_gauche,
    corps.cheville_gauche
  );

  if (angle_genou_gauche < 100) return "debut";
  else if (angle_genou_gauche > 150) return "fin";
  return "milieu";
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

export function souleve_de_terre_roumain_detection(corps) {
  const distance_gauche = calculer_distance(
    corps.poignet_gauche,
    corps.cheville_gauche
  );
  const distance_droite = calculer_distance(
    corps.poignet_droit,
    corps.cheville_droite
  );
  const distance_moyenne = (distance_gauche + distance_droite) / 2;

  if (distance_moyenne < 0.1) return "debut";
  else if (distance_moyenne > 0.2) return "fin";
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
// ont ete verifiees avec elle — comme `charge_facultative`.
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
  ecart_rapporte_aux_epaules as _ecart_rapporte_aux_epaules,
  hanche_decollee as _hanche_decollee,
  poignet_devant_epaule as _poignet_devant_epaule,
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
};
