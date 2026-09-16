// Le guidage d'installation, joue camera ouverte pendant la preparation.
//
// Il repond au meme grief que `cadrage.js`, un cran plus tot. Le cadrage sait
// dire « je ne vois pas tes genoux » une fois que quelqu'un est devant
// l'objectif ; il ne sait pas dire ou poser la tablette, a quelle hauteur, ni
// qu'il faut verifier qu'on tient dans l'image **en bougeant**. Ces
// consignes-la existaient — sur la fiche, lues avant de commencer, puis jamais
// rappelees — et une testeuse a pose la camera a 40 cm du sol malgre elles.
//
// **Il se joue camera ouverte, et c'est tout son interet.** « Recule d'un
// pas » n'a de sens que si l'on se voit reculer, et l'etape de cadrage ne
// passe qu'une fois le corps reellement entier dans l'image — la consigne est
// donc *verifiee*, pas seulement prononcee.
//
// Trois decisions de forme.
//
// (1) **Le module est pur** : ni horloge, ni DOM, ni acces camera. L'instant
//     et l'etat du cadrage lui sont passes a chaque image, comme `Circuit`
//     recoit son horloge. C'est ce qui le rend verifiable sans navigateur, et
//     c'est la lecon d'`app/index.html` — une page qui garde sa logique pour
//     elle n'est pas seulement mal rangee, elle est inverifiable.
//
// (2) **Il rend des cles, jamais des phrases.** Les textes vivent dans
//     `audio/annonces.py` et arrivent par `donnees/sons.json`, qui porte a la
//     fois le `.wav` et le libelle. Le bandeau affiche donc **exactement** ce
//     que la voix prononce, sans qu'aucune phrase soit ecrite deux fois.
//
// (3) **Il ne connait pas `cadrage.js`.** L'appelant lui passe un booleen
//     `cadre`. Les deux modules restent ainsi independants, et le tutoriel se
//     joue dans un test sans qu'il faille fabriquer une pose valide.

//: Duree pendant laquelle le cadrage doit rester bon avant de passer a la
//: suite. Deux secondes, pas plus : les landmarks tremblent, et exiger une
//: perfection prolongee bloquerait quelqu'un de correctement place.
const CADRAGE_STABLE = 2;

/**
 * Les etapes d'un tutoriel de seance.
 *
 * Le contenu vit ici et non dans la page, pour la meme raison que la
 * mecanique : ce qui est dans un `<script>` de gabarit n'est verifie par rien.
 *
 * @param {object} options
 * @param {string|null} options.orientation  celle du premier exercice
 * @param {boolean} options.avec_tapis       la seance en demande-t-elle un
 */
export function etapes_de_seance({ orientation = null, avec_tapis = false } = {}) {
  const etapes = [
    {
      cle: "placement",
      annonces: ["installation_hauteur", "installation_distance"],
      duree: 7,
    },
    {
      // La seule etape que le temps ne suffit pas a franchir : on attend que
      // le corps soit reellement entier dans l'image. Sans borne de duree,
      // donc — le bouton « passer » est la sortie, pas un minuteur.
      cle: "cadrage",
      annonces: [],
      cadrage_stable: CADRAGE_STABLE,
    },
    {
      cle: "pas_de_cote",
      annonces: ["installation_pas_de_cote", "installation_toujours_visible"],
      duree: 9,
    },
    {
      cle: "pas_arriere",
      annonces: ["installation_pas_arriere"],
      duree: 7,
    },
  ];

  if (avec_tapis) {
    etapes.push({ cle: "tapis", annonces: ["installation_tapis"], duree: 5 });
  }

  if (orientation) {
    etapes.push({
      cle: "orientation",
      annonces: [`orientation_${orientation}`],
      duree: 5,
    });
  }

  etapes.push({
    cle: "pret",
    annonces: ["installation_bien_cadre", "geste_bras_en_x"],
    duree: 4,
  });

  return etapes;
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
    this.cadre_depuis = null;
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
   * @param {boolean} vue.cadre   le corps tient-il entierement dans l'image
   */
  update({ instant, cadre = false }) {
    if (this.termine) return { etape: null, annonces: [], termine: true };

    const etape = this.etape;
    const annonces = this._annoncee === this.index ? [] : etape.annonces;
    this._annoncee = this.index;

    if (etape.cadrage_stable !== undefined) {
      // Le compteur ne se remet a zero que lorsque le cadrage se perd : un
      // clignotement d'une image ne doit pas tout recommencer, mais une sortie
      // franche du champ, si.
      if (!cadre) {
        this.cadre_depuis = null;
      } else if (this.cadre_depuis === null) {
        this.cadre_depuis = instant;
      } else if (instant - this.cadre_depuis >= etape.cadrage_stable) {
        this._avancer(instant);
      }
      return { etape, annonces, termine: false };
    }

    if (instant - this.debut_etape >= etape.duree) {
      this._avancer(instant);
    }

    return { etape, annonces, termine: this.termine };
  }

  _avancer(instant) {
    this.index += 1;
    this.debut_etape = instant;
    this.cadre_depuis = null;
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
