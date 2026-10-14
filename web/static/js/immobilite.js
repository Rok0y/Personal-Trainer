// Est-on immobile ? La vitesse du buste, d'une image a l'autre.
//
// Deux pages s'en servent pour la meme question — « la personne est-elle en
// place ? » : la demo avant de lancer le comptage, la seance avant d'ouvrir
// une serie (`attendre_mise_en_place`, moteur.js). Une seule mesure, donc un
// seul seuil a regler.

// Deplacement moyen du buste, en unites d'image par seconde, sous lequel on
// considere la personne installee. Regle sur la demo.
export const SEUIL_IMMOBILE = 0.25;

/**
 * Vitesse moyenne des epaules et des hanches depuis le repere precedent.
 *
 * Le buste seulement : poignets et chevilles bougent encore quand quelqu'un
 * est pret, et feraient echouer la detection d'immobilite.
 *
 * Pur : rend `[vitesse, repere]`, ou `repere` est a repasser a l'appel
 * suivant. La vitesse vaut null a la premiere image (ou a un instant deja
 * vu) : il faut deux images pour mesurer un deplacement.
 */
export function vitesse_du_buste(precedent, corps, instant) {
  const points = [
    corps.epaule_gauche, corps.epaule_droite,
    corps.hanche_gauche, corps.hanche_droite,
  ].map((p) => ({ x: p.x, y: p.y }));
  const repere = { points, instant };

  if (!precedent || precedent.instant === instant) return [null, repere];

  const ecoule = instant - precedent.instant;
  const total = points.reduce((somme, p, i) => {
    const avant = precedent.points[i];
    return somme + Math.hypot(p.x - avant.x, p.y - avant.y);
  }, 0);
  return [total / points.length / ecoule, repere];
}
