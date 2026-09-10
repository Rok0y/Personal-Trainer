// Jumeau de mouvements/exercices.py — uniquement les fonctions de detection
// et d'erreur de forme, dans le meme ordre que le Python et sous les memes
// noms, pour qu'un diff cote a cote reste lisible.
//
// Ce qui reste cote Python et n'a pas a etre porte : les objets `Exercice`
// (fiches, consignes, variantes), le catalogue et toute la machine a etats.
// Ici il n'y a que des fonctions pures `corps -> jeton`.
//
// Les fonctions d'erreur retournent une **cle** de message ou null, jamais
// une phrase : c'est la convention de core/messages.py, et c'est le serveur
// qui resout la cle en francais.

import { calculer_angle, calculer_distance } from "./outils.js";

export function curl_biceps_droit_detection(corps) {
  const angle = calculer_angle(
    corps.epaule_droite,
    corps.coude_droit,
    corps.poignet_droit
  );
  if (angle < 30) return "fin";
  else if (angle > 160) return "debut";
  return "milieu";
}

function _coude_qui_part_en_avant(hanche, epaule, coude) {
  if (calculer_angle(hanche, epaule, coude) > 45) {
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
  if (angle < 30) return "fin";
  else if (angle > 160) return "debut";
  return "milieu";
}

export function elevation_laterale_detection(corps) {
  // Le Python calcule ici deux angles de coude qu'il n'utilise jamais ; ils
  // ne sont pas repris, la detection ne portant que sur la hauteur des
  // poignets. Seule fonction du fichier sans jeton "milieu".
  if (
    corps.poignet_droit.y > corps.epaule_droite.y &&
    corps.poignet_gauche.y > corps.epaule_gauche.y
  ) {
    return "debut";
  } else {
    return "fin";
  }
}

export function pompe_detection(corps) {
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
  if (angle_coude_droit < 100 && angle_coude_gauche < 100) return "debut";
  else if (angle_coude_droit > 160 && angle_coude_gauche > 160) return "fin";
  return "milieu";
}

export function developpe_couche_sol_detection(corps) {
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
  if (angle_coude_droit < 100 && angle_coude_gauche < 100) return "debut";
  else if (angle_coude_droit > 160 && angle_coude_gauche > 160) return "fin";
  return "milieu";
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
  if (angle_coude_droit < 90 && angle_coude_gauche < 90) return "debut";
  else if (angle_coude_droit > 150 && angle_coude_gauche > 150) return "fin";
  return "milieu";
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
  if (angle_coude_droit < 40 && angle_coude_gauche < 40) return "debut";
  else if (angle_coude_droit > 150 && angle_coude_gauche > 150) return "fin";
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
  if (angle_hanche_droite < 70 && angle_hanche_gauche < 70) return "fin";
  else if (angle_hanche_droite > 95 && angle_hanche_gauche > 95) return "debut";
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
  const hanches_droites =
    angle_hanche_droite > 145 && angle_hanche_gauche > 145;

  const hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y;
  if (hanches_droites && hanche_au_dessus_coude) return "maintien";

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

export function detection_gainage_laterale_gauche(corps) {
  const angle_hanche_gauche = calculer_angle(
    corps.epaule_gauche,
    corps.hanche_gauche,
    corps.cheville_gauche
  );
  const corps_aligne = angle_hanche_gauche > 150;

  const cote_gauche_au_sol = corps.epaule_gauche.y > corps.epaule_droite.y;

  const hanche_au_dessus_coude = corps.hanche_gauche.y < corps.coude_gauche.y;

  if (corps_aligne && cote_gauche_au_sol && hanche_au_dessus_coude) {
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
  const corps_aligne = angle_hanche_droite > 150;

  const cote_droit_au_sol = corps.epaule_droite.y > corps.epaule_gauche.y;

  const hanche_au_dessus_coude = corps.hanche_droite.y < corps.coude_droit.y;

  if (corps_aligne && cote_droit_au_sol && hanche_au_dessus_coude) {
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

  if (angle_coude_gauche < 70 && poignet_au_dessus_hanche && buste_penche) {
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

  if (angle_coude_droit < 70 && poignet_au_dessus_hanche && buste_penche) {
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

  if (angle_bras_moyen > 80) return "fin";
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
// genou. Fonction privee, non exportee : le harnais n'apparie que les
// detections, et sa jumelle Python est `_descente_hanche`.
function descente_hanche(hanche, genou, cheville) {
  const tibia = cheville.y - genou.y;
  if (tibia <= 0) return null;
  return (genou.y - hanche.y) / tibia;
}

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

// Appariement nom -> fonction, consomme par le harnais de comparaison et par
// la couche de seance. Les cles reprennent exactement les noms Python.
export const DETECTIONS = {
  curl_biceps_droit_detection,
  coude_avance_curl_droit,
  coude_avance_curl_gauche,
  curl_biceps_gauche_detection,
  elevation_laterale_detection,
  pompe_detection,
  developpe_couche_sol_detection,
  extension_triceps_au_dessus_de_la_tete_detection,
  developpe_epaule_detection,
  crunches_detection,
  detection_gainage,
  squat_detection,
  fente_droite_detection,
  fente_gauche_detection,
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
};
