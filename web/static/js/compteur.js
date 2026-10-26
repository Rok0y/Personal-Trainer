// Le comptage des repetitions, a partir des positions detectees.
//
// La convention ne doit pas etre inversee : le compteur s'arme sur "debut" et incremente sur "fin", ou "fin" designe la
// position qui *valide* une repetition, c'est-a-dire la fin de la phase
// concentrique — le haut d'un curl, mais aussi le retour debout d'un squat.

// Delai minimal, en secondes, entre deux repetitions comptees : un saut d'une
// ou deux images juste apres une vraie repetition la faisait compter deux
// fois. Aucune repetition d'un exercice de force ne tient en 0,3 s ; un
// mouvement plus rapide, ou chaque pas compte, declare le sien
// (`delai_min_reps` dans `mouvements.json`). L'hysteresis de sa detection
// empeche deja l'echo d'un aller-retour `fin → debut → fin` d'une image.
export const DELAI_MIN_ENTRE_REPS = 0.3;

export class CompteurMouvement {
  constructor() {
    this.stage = null;
    this.repetitions = 0;
    this.derniere_rep_a = null;
  }

  // `instant` est l'horloge de la seance, en secondes ; null le desactive.
  //
  // `depart` est la position ou une serie commence (`Exercice.depart`), ou
  // null. **Tant que rien n'est arme, seule elle est retenue.** Sans elle, le
  // premier jeton vu fixait la position de depart : en s'allongeant coudes
  // plies pour un developpe couche, on etait vu en `debut`, et pousser les
  // halteres en place comptait une repetition a chaque serie.
  //
  // `delai` est l'ecart minimal entre deux repetitions comptees
  // (`Exercice.delai_min_reps`), ou null pour le delai par defaut.
  mettre_a_jour(nouveau_stage, instant = null, depart = null, delai = null) {
    if (nouveau_stage !== "debut" && nouveau_stage !== "fin") {
      return [this.stage, this.repetitions];
    }
    if (this.stage === null && depart !== null && nouveau_stage !== depart) {
      return [this.stage, this.repetitions];
    }

    if (this.stage === "debut" && nouveau_stage === "fin") {
      this.stage = "fin";
      // Trop tot apres la precedente : la meme repetition, vue deux fois.
      if (
        instant === null ||
        this.derniere_rep_a === null ||
        instant - this.derniere_rep_a >= (delai ?? DELAI_MIN_ENTRE_REPS)
      ) {
        this.repetitions += 1;
        this.derniere_rep_a = instant;
      }
    } else if (this.stage === "fin" && nouveau_stage === "debut") {
      this.stage = "debut";
    } else if (this.stage === null) {
      this.stage = nouveau_stage;
    }

    return [this.stage, this.repetitions];
  }

  // Corrige le compte a la main (geste bras leve), jamais sous zero. Le stage
  // ne bouge pas : seule la valeur est corrigee.
  ajuster(delta) {
    this.repetitions = Math.max(0, this.repetitions + delta);
    return this.repetitions;
  }

  reset() {
    this.stage = null;
    this.repetitions = 0;
    this.derniere_rep_a = null;
  }
}
