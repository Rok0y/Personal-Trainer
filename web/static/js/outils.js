// Distances, angles et tenue d'une position dans le temps.

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

// Combien de temps un geste doit etre tenu avant que son anneau apparaisse.
// Un poignet qui passe un instant devant l'autre est reconnu une image sur
// deux : l'anneau clignotait a chaque mouvement de bras. Un geste voulu, lui,
// se tient ; trois quarts de seconde l'en distinguent sans rallonger le geste.
export const DELAI_AFFICHAGE_GESTE = 0.75;

export class HoldPosition {
  // L'horloge est injectable pour que la classe reste testable hors
  // navigateur : un test ne peut pas attendre 1,5 s reelle.
  constructor(position, duree, horloge = () => performance.now() / 1000) {
    this.position = position;
    this.duree = duree;
    this.horloge = horloge;
    this.debut = null;
    this.termine = false;
  }

  /**
   * L'avancement **affiche** (0 a 100), en lecture seule : rien pendant
   * `DELAI_AFFICHAGE_GESTE`, puis de zero a plein jusqu'a l'instant ou le geste
   * est pris. Le delai retarde l'anneau, pas le geste : sa duree ne change pas.
   */
  progression_visible() {
    if (this.termine) return 100;
    if (this.debut === null) return 0;
    const delai = Math.min(DELAI_AFFICHAGE_GESTE, this.duree / 2);
    const visible = (this.horloge() - this.debut - delai) / (this.duree - delai);
    return Math.min(100, Math.max(0, visible * 100));
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

    if (this.horloge() - this.debut >= this.duree) {
      if (!this.termine) {
        this.termine = true;
        return [100, true];
      }
      return [100, false];
    }

    return [this.progression_visible(), false];
  }
}
