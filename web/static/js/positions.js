// Jumeau de mouvements/positions.py — les gestes de controle de la seance.

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

// Le buste debout : les epaules nettement au-dessus des hanches. Voir la
// docstring Python pour le pourquoi — allonge, bras tendus est la position
// haute du developpe couche, et le geste de remise a zero y effacait la serie.
export function _torse_vertical(corps) {
  const epaules_x = (corps.epaule_gauche.x + corps.epaule_droite.x) / 2;
  const epaules_y = (corps.epaule_gauche.y + corps.epaule_droite.y) / 2;
  const hanches_x = (corps.hanche_gauche.x + corps.hanche_droite.x) / 2;
  const hanches_y = (corps.hanche_gauche.y + corps.hanche_droite.y) / 2;
  return hanches_y - epaules_y > Math.abs(hanches_x - epaules_x);
}

export function deux_bras_leves(corps) {
  return bras_droit_leve(corps) && bras_gauche_leve(corps) && _torse_vertical(corps);
}
