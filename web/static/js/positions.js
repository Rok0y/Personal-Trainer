// Les gestes de controle de la seance.

import { calculer_angle } from "./outils.js";

export function bras_droit_leve(corps) {
  const angle_coude_droit = calculer_angle(
    corps.poignet_droit,
    corps.coude_droit,
    corps.epaule_droite
  );
  return corps.poignet_droit.y < corps.epaule_droite.y && angle_coude_droit > 160;
}

export function bras_gauche_leve(corps) {
  const angle_coude_gauche = calculer_angle(
    corps.poignet_gauche,
    corps.coude_gauche,
    corps.epaule_gauche
  );
  return (
    corps.poignet_gauche.y < corps.epaule_gauche.y && angle_coude_gauche > 160
  );
}

export function bras_en_x(corps) {
  if (!de_face(corps)) return false;
  const x_min_epaules = Math.min(corps.epaule_gauche.x, corps.epaule_droite.x);
  const x_max_epaules = Math.max(corps.epaule_gauche.x, corps.epaule_droite.x);

  return (
    corps.poignet_gauche.x < corps.poignet_droit.x &&
    x_min_epaules <= corps.poignet_gauche.x &&
    corps.poignet_gauche.x <= x_max_epaules &&
    x_min_epaules <= corps.poignet_droit.x &&
    corps.poignet_droit.x <= x_max_epaules
  );
}

// Le buste debout : les epaules nettement au-dessus des hanches. On compare
// l'ecart vertical entre le milieu des epaules et celui des hanches a leur
// ecart horizontal : debout, le premier domine ; allonge, le second. Aucun
// seuil a regler, et l'orientation de la camera n'y change rien. Pourquoi
// l'exiger : allonge, bras tendus est la position haute du developpe couche,
// et le geste de remise a zero y effacait la serie.
export function _torse_vertical(corps) {
  const epaules_x = (corps.epaule_gauche.x + corps.epaule_droite.x) / 2;
  const epaules_y = (corps.epaule_gauche.y + corps.epaule_droite.y) / 2;
  const hanches_x = (corps.hanche_gauche.x + corps.hanche_droite.x) / 2;
  const hanches_y = (corps.hanche_gauche.y + corps.hanche_droite.y) / 2;
  return hanches_y - epaules_y > Math.abs(hanches_x - epaules_x);
}

// Un nez que le modele voit vraiment : de face, sa `visibility` frole 1 ; de
// dos, le modele devine un visage qu'il ne voit pas et la baisse.
const VISIBILITE_NEZ_DE_FACE = 0.5;

// Face a la camera, debout. Un geste de controle se fait face a l'ecran : de
// dos, deux mains ramenees entre les epaules passaient pour des bras croises,
// et une pause sautait pendant qu'on se retournait. La video arrive brute au
// modele, l'etiquetage est donc vrai : de face, l'epaule gauche est a droite
// de l'image. Le nez couvre le cas ou le modele, de dos, inverserait les
// cotes ; le buste debout ecarte tout ce qui se fait allonge.
export function de_face(corps) {
  return (
    corps.epaule_gauche.x > corps.epaule_droite.x &&
    corps.nez.visibility >= VISIBILITE_NEZ_DE_FACE &&
    _torse_vertical(corps)
  );
}

export function deux_bras_leves(corps) {
  return bras_droit_leve(corps) && bras_gauche_leve(corps) && de_face(corps);
}

// Un seul bras leve, debout : +1 a droite, -1 a gauche. L'autre poignet doit
// etre **sous son epaule** et non simplement « pas leve » : on passe par un
// seul bras en levant les deux, et la tenue doit se couper des que le second
// commence a monter. C'est aussi ce qui ecarte le developpe epaule et
// l'extension triceps, ou les deux poignets sont en haut ; le buste debout
// ecarte ce qui se fait allonge (planche laterale bras leve, developpe couche).
export function seul_bras_droit_leve(corps) {
  return (
    bras_droit_leve(corps) &&
    corps.poignet_gauche.y > corps.epaule_gauche.y &&
    de_face(corps)
  );
}

export function seul_bras_gauche_leve(corps) {
  return (
    bras_gauche_leve(corps) &&
    corps.poignet_droit.y > corps.epaule_droite.y &&
    de_face(corps)
  );
}
