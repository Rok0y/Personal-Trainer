// Le guidage d'installation, joue camera ouverte pendant la preparation.
//
// Il repond au meme grief que `cadrage.js`, un cran plus tot. Le cadrage sait
// dire « je ne vois pas tes genoux » une fois que quelqu'un est devant
// l'objectif ; il ne sait pas dire ou poser la tablette, a quelle hauteur, ni
// qu'il faut verifier qu'on tient dans l'image **en bougeant**. Ces
// consignes-la existaient — sur la fiche, lues avant de commencer, puis jamais
// rappelees — et une testeuse a pose la camera a 40 cm du sol malgre elles.
//
// **Il se joue camera ouverte, mais il ne verifie plus rien.** Le cadrage
// est controle juste avant par l'installation de la page, qui ne le laisse
// demarrer qu'une fois le corps entier dans l'image : c'est elle qui dit
// « recule ». Le tutoriel ne dit que ce qu'elle ne dit pas.
//
// Deux decisions de forme.
//
// (1) **Le module est pur** : ni horloge, ni DOM, ni acces camera. L'instant
//     lui est passe a chaque image, comme `Circuit` recoit son horloge. C'est
//     ce qui le rend verifiable sans navigateur, et c'est la lecon
//     d'`app/index.html` — une page qui garde sa logique pour elle n'est pas
//     seulement mal rangee, elle est inverifiable.
//
// (2) **Il rend des cles, jamais des phrases.** Les textes vivent dans
//     `audio/annonces.py` et arrivent par `donnees/sons.json`, qui porte a la
//     fois le `.wav` et le libelle. Le bandeau affiche donc **exactement** ce
//     que la voix prononce, sans qu'aucune phrase soit ecrite deux fois.

/**
 * Les etapes d'un tutoriel de seance.
 *
 * Le contenu vit ici et non dans la page, pour la meme raison que la
 * mecanique : ce qui est dans un `<script>` de gabarit n'est verifie par rien.
 *
 * **Une seule phrase, et c'est le retour d'une seance reelle.** Il y en avait
 * six — hauteur de l'appareil, distance, cadrage, espace, tapis, orientation,
 * « tu es bien cadre, croise les bras » — soit une trentaine de secondes avant
 * le premier exercice, dont la moitie redisait autre chose : le cadrage est
 * deja verifie par l'installation, qui ne laisse passer qu'un corps entier dans
 * l'image (c'est elle qui dit « recule ») ; l'orientation et le geste sont
 * annonces par la presentation du premier exercice, qui suit. Ne reste que ce
 * que personne d'autre ne dit : garder de la place autour de soi.
 */
export function etapes_de_seance() {
  return [
    {
      // **Une information, pas un exercice.** On a fait executer ici des pas
      // — a droite, a gauche, en arriere — sans rien verifier pendant ces
      // pas : une consigne deguisee en controle. Il ne reste que la phrase
      // qui dit la place a garder ; rien n'attend qu'on l'execute.
      cle: "espace",
      annonces: ["installation_pas_de_cote"],
      duree: 5,
    },
  ];
}

export class Tutoriel {
  /**
   * @param {Array} etapes   celles de `etapes_de_seance`, ou les tiennes
   * @param {number} instant horodatage de depart, en secondes
   */
  constructor(etapes, instant) {
    this.etapes = etapes ?? [];
    this.index = 0;
    this.debut_etape = instant;
    this.termine = this.etapes.length === 0;
    //: L'etape dont les annonces ont deja ete jouees. Un tutoriel tourne a
    //: trente images par seconde : sans ce repere, chaque etape se
    //: reannoncerait a chaque image.
    this._annoncee = null;
  }

  get etape() {
    return this.etapes[this.index] ?? null;
  }

  /**
   * Fait avancer le tutoriel d'une image.
   *
   * Rend `{ etape, annonces, termine }`. `annonces` n'est non vide **qu'a
   * l'image ou l'on entre dans une etape** : c'est ce qui evite de rejouer la
   * phrase trente fois par seconde, et ca vaut mieux qu'un delai minimal, qui
   * la rejouerait quand meme, seulement moins souvent.
   *
   * @param {object} vue
   * @param {number} vue.instant  secondes, la meme horloge que la boucle
   */
  update({ instant }) {
    if (this.termine) return { etape: null, annonces: [], termine: true };

    const etape = this.etape;
    const annonces = this._annoncee === this.index ? [] : etape.annonces;
    this._annoncee = this.index;

    if (instant - this.debut_etape >= etape.duree) {
      this._avancer(instant);
    }

    return { etape, annonces, termine: this.termine };
  }

  _avancer(instant) {
    this.index += 1;
    this.debut_etape = instant;
    if (this.index >= this.etapes.length) {
      this.termine = true;
    }
  }

  /** Sortie immediate : le bouton « passer », ou « je commence ». */
  passer() {
    this.index = this.etapes.length;
    this.termine = true;
  }
}
