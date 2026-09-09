// Jumeau de mouvements/outils.py.

export function calculer_distance(point_a, point_b) {
  return Math.sqrt((point_a.x - point_b.x) ** 2 + (point_a.y - point_b.y) ** 2);
}

export function calculer_angle(a, b, c) {
  const radians =
    Math.atan2(c.y - b.y, c.x - b.x) - Math.atan2(a.y - b.y, a.x - b.x);
  let angle = Math.abs((radians * 180) / Math.PI);
  if (angle > 180) {
    angle = 360 - angle;
  }
  return angle;
}

export class HoldPosition {
  // L'horloge est injectable pour que la classe reste testable hors
  // navigateur : le harnais de comparaison ne peut pas attendre 1,5 s reelle.
  constructor(position, duree, horloge = () => performance.now() / 1000) {
    this.position = position;
    this.duree = duree;
    this.horloge = horloge;
    this.debut = null;
    this.termine = false;
  }

  update(corps) {
    if (!this.position(corps)) {
      this.debut = null;
      this.termine = false;
      return [0, false];
    }

    if (this.debut === null) {
      this.debut = this.horloge();
    }

    const temps_ecoule = this.horloge() - this.debut;
    const progression = Math.min((temps_ecoule / this.duree) * 100, 100);

    if (progression >= 100) {
      if (!this.termine) {
        this.termine = true;
        return [100, true];
      }
      return [100, false];
    }

    return [progression, false];
  }
}
