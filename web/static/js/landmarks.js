// Jumeau de vision/landmarks.py — les 33 points MediaPipe et leur nom francais.
//
// Les noms de ce module et ceux des fonctions de detections.js reprennent
// exactement ceux du Python, en snake_case, contrairement a l'usage
// JavaScript : c'est ce qui permet de lire les deux implementations cote a
// cote et au harnais de comparaison d'apparier les fonctions par leur nom,
// sans table de correspondance qui pourrait deriver.

export const LANDMARKS = {
  // Visage
  nez: 0,
  oeil_gauche_interieur: 1,
  oeil_gauche: 2,
  oeil_gauche_exterieur: 3,
  oeil_droit_interieur: 4,
  oeil_droit: 5,
  oeil_droit_exterieur: 6,
  oreille_gauche: 7,
  oreille_droite: 8,
  // Bouche
  coin_bouche_gauche: 9,
  coin_bouche_droit: 10,
  // Epaules et bras
  epaule_gauche: 11,
  epaule_droite: 12,
  coude_gauche: 13,
  coude_droit: 14,
  poignet_gauche: 15,
  poignet_droit: 16,
  // Doigts (approximations MediaPipe)
  petit_doigt_gauche: 17,
  petit_doigt_droit: 18,
  index_gauche: 19,
  index_droit: 20,
  pouce_gauche: 21,
  pouce_droit: 22,
  // Hanches
  hanche_gauche: 23,
  hanche_droite: 24,
  // Genoux
  genou_gauche: 25,
  genou_droit: 26,
  // Chevilles
  cheville_gauche: 27,
  cheville_droite: 28,
  // Pieds
  talon_gauche: 29,
  talon_droit: 30,
  pointe_pied_gauche: 31,
  pointe_pied_droite: 32,
};

export function construire_corps(landmarks) {
  const corps = {};
  for (const [nom, index] of Object.entries(LANDMARKS)) {
    corps[nom] = landmarks[index];
  }
  return corps;
}
