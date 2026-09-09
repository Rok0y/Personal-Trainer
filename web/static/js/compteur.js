// Jumeau de mouvements/compteur.py.
//
// La convention est celle du Python et ne doit pas etre inversee : le
// compteur s'arme sur "debut" et incremente sur "fin", ou "fin" designe la
// position qui *valide* une repetition, c'est-a-dire la fin de la phase
// concentrique — le haut d'un curl, mais aussi le retour debout d'un squat.

export class CompteurMouvement {
  constructor() {
    this.stage = null;
    this.repetitions = 0;
  }

  mettre_a_jour(nouveau_stage) {
    if (nouveau_stage !== "debut" && nouveau_stage !== "fin") {
      return [this.stage, this.repetitions];
    }

    if (this.stage === "debut" && nouveau_stage === "fin") {
      this.stage = "fin";
      this.repetitions += 1;
    } else if (this.stage === "fin" && nouveau_stage === "debut") {
      this.stage = "debut";
    } else if (this.stage === null) {
      this.stage = nouveau_stage;
    }

    return [this.stage, this.repetitions];
  }

  reset() {
    this.stage = null;
    this.repetitions = 0;
  }
}
