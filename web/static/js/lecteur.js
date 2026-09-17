// Jumeau d'`audio/lecteur.py` et de la fonction `coach` d'`audio/coach.py`.
//
// Ce module existe parce qu'il manquait : la premiere version du coach web
// jouait chaque son des qu'il etait demande, tous en meme temps. « Le compte
// se marche un peu dessus », a dit le premier testeur — ce n'etait pas un
// raffinement a venir mais une piece non portee, et le desktop, lui, ne l'a
// jamais eu ce defaut.
//
// Trois regles la composent, toutes venues du Python.
//
// (1) **Un son a la fois.** Le lecteur attend la fin du precedent avant de
//     demarrer le suivant, comme le thread Python attend `mixer.get_busy()`.
// (2) **Une file a priorites.** Chaque cle en porte une — `compteur` vaut 1,
//     `bip` 2, `fin_serie` 10 — et la file sert le plus urgent d'abord.
// (3) **Un evenement important (>= 5) vide les petits sons en attente**
//     plutot que de faire la queue derriere eux : quand une serie se termine,
//     les bips de comptage n'ont plus rien a dire.
// (4) **Un blanc entre deux entrees.** Rien ne jouait jamais litteralement en
//     meme temps, et pourtant le coach « se chevauchait » a l'oreille : la
//     file enchainait l'entree suivante a la milliseconde ou la precedente se
//     taisait. *Deux phrases collees s'entendent comme une phrase coupee.*
//
// Les tables viennent de `donnees/sons.json`, exporte du Python : ni les
// fichiers, ni les priorites, ni les delais, ni les silences ne sont reecrits
// ici.

//: Priorite a partir de laquelle un son vide les petits sons en attente, et
//: en dessous de laquelle il peut lui-meme etre vide. La meme valeur des deux
//: cotes, comme en Python.
const PRIORITE_IMPORTANTE = 5;

//: Priorite par defaut d'une cle absente de la table.
const PRIORITE_PAR_DEFAUT = 5;

//: Le comptage des repetitions est le son le moins prioritaire : c'est celui
//: qu'on sacrifie quand la serie se termine.
const PRIORITE_COMPTEUR = 1;

export class Lecteur {
  /**
   * @param {string} dossier  ou trouver les .wav
   * @param {object} tables   { fichiers, priorites, delais } exporte du Python
   */
  constructor(dossier, tables) {
    this.dossier = dossier.replace(/\/$/, "");
    this.fichiers = tables.fichiers ?? {};
    this.priorites = tables.priorites ?? {};
    this.delais = tables.delais ?? {};
    // Les deux silences, exportes de `audio/lecteur.py`. Les valeurs de repli
    // ne sont pas une seconde source : elles servent le seul cas ou
    // `sons.json` est trop ancien pour les porter, et valent alors zero —
    // c'est-a-dire le comportement d'avant, jamais un reglage invente ici.
    this.silence_entre = tables.silences?.entre_annonces ?? 0;
    this.silence_presentation = tables.silences?.presentation ?? 0;

    this.contexte = null;
    this._tampons = new Map();
    this._file = [];
    this._joue = false;
    this._rang = 0;
    this._dernieres = new Map();
  }

  /**
   * Cree le contexte audio. **A appeler depuis un geste de l'utilisateur** :
   * iOS refuse de jouer quoi que ce soit tant qu'un contexte n'a pas ete cree
   * pendant un evenement tactile.
   */
  async preparer() {
    this.contexte =
      this.contexte ?? new (window.AudioContext ?? window.webkitAudioContext)();
    await this.contexte.resume().catch(() => {});
    return this.contexte.state === "running";
  }

  async _tampon(fichier) {
    if (this._tampons.has(fichier)) return this._tampons.get(fichier);
    // La promesse est memorisee avant d'etre resolue : deux demandes du meme
    // son pendant le telechargement ne doivent pas le telecharger deux fois.
    const promesse = fetch(`${this.dossier}/${fichier}`)
      .then((r) => (r.ok ? r.arrayBuffer() : Promise.reject(new Error(r.status))))
      .then((donnees) => this.contexte.decodeAudioData(donnees))
      // Un son manquant est un silence, jamais une exception : on est dans la
      // boucle image, ou une erreur non rattrapee gele l'affichage.
      .catch(() => null);
    this._tampons.set(fichier, promesse);
    return promesse;
  }

  /**
   * Charge d'avance les sons les plus joues.
   *
   * Sans ca, la premiere repetition d'une seance arrive avant son fichier et
   * s'annonce en retard, ou pas du tout.
   */
  async precharger(cles) {
    if (!this.contexte) return;
    const fichiers = new Set();
    for (const cle of cles) {
      if (/^\d+$/.test(cle)) fichiers.add(`${cle}.wav`);
      else for (const f of this.fichiers[cle] ?? []) fichiers.add(f);
    }
    await Promise.all([...fichiers].map((f) => this._tampon(f)));
  }

  /**
   * Demande un son. Point d'entree unique, jumeau de `coach(event, valeur)`.
   *
   * Ne rend pas de promesse de lecture : l'appelant est la boucle image, qui
   * ne doit jamais attendre le son.
   */
  coach(cle, valeur = null) {
    if (!this.contexte) return;

    if (cle === "compteur") {
      // La bibliotheque s'arrete a vingt : au-dela on bipe plutot que
      // d'inventer un fichier qui n'existe pas.
      const fichier = valeur > 0 && valeur <= 20 ? `${valeur}.wav` : "bip.wav";
      this._empiler(fichier, PRIORITE_COMPTEUR);
      return;
    }

    const variantes = this.fichiers[cle];
    if (!variantes?.length) return;

    // Delai minimal entre deux annonces du meme type : sans lui, la
    // correction de gainage se repete a chaque image ou la position se perd.
    const delai = this.delais[cle] ?? 0;
    const maintenant = performance.now() / 1000;
    const derniere = this._dernieres.get(cle);
    if (derniere !== undefined && maintenant - derniere < delai) return;
    this._dernieres.set(cle, maintenant);

    const fichier = variantes[Math.floor(Math.random() * variantes.length)];
    this._empiler(fichier, this.priorites[cle] ?? PRIORITE_PAR_DEFAUT);
  }

  /**
   * Joue une phrase composee de plusieurs fichiers, **comme un seul son**.
   * Jumeau de `jouer_sequence` dans `audio/lecteur.py`.
   *
   * C'est l'indivisibilite qui compte. Empiler quatre `coach()` d'affilee
   * ordonnerait bien les morceaux — le rang departage les priorites egales —
   * mais rien n'empecherait un evenement urgent de se glisser au milieu : on
   * entendrait « prochain exercice… 12 repetitions ». Une sequence est donc
   * **une** entree de la file, que la purge garde ou jette en entier.
   *
   * Un fichier manquant est un silence et non une panne (`_tampon` rend null) :
   * c'est ce qui permet d'enregistrer les prises par lots, une phrase
   * s'abregeant au lieu de disparaitre.
   */
  sequence(fichiers, priorite = PRIORITE_PAR_DEFAUT, cle = null, silence_avant = 0) {
    if (!this.contexte) return;
    const propres = (fichiers ?? []).filter(Boolean);
    if (!propres.length) return;

    // Meme garde-fou que `coach()`, et sur la meme table exportee du Python :
    // sans lui, une consigne evaluee a chaque image se repete des que la
    // position vacille. C'est le defaut qu'avait la correction de gainage, et
    // il se reproduirait a l'identique sur le guidage de cadrage.
    if (cle) {
      const delai = this.delais[cle] ?? 0;
      const maintenant = performance.now() / 1000;
      const derniere = this._dernieres.get(cle);
      if (derniere !== undefined && maintenant - derniere < delai) return;
      this._dernieres.set(cle, maintenant);
    }

    this._empiler(propres, priorite, silence_avant);
  }

  _empiler(fichiers, priorite, silence_avant = 0) {
    if (priorite >= PRIORITE_IMPORTANTE) {
      this._file = this._file.filter((e) => e.priorite >= PRIORITE_IMPORTANTE);
    }
    // Le rang departage deux sons de meme priorite : le premier demande passe
    // en premier, ce qu'un tri sur la seule priorite ne garantirait pas.
    const propres = Array.isArray(fichiers) ? fichiers : [fichiers];
    this._file.push({
      fichiers: propres,
      priorite,
      rang: this._rang++,
      silence_avant,
    });
    this._file.sort((a, b) => b.priorite - a.priorite || a.rang - b.rang);
    this._servir();
  }

  async _servir() {
    if (this._joue) return;
    this._joue = true;
    try {
      while (this._file.length) {
        const { fichiers, silence_avant } = this._file.shift();
        if (silence_avant) await this._attendre(silence_avant);
        // Une entree est une sequence : ses morceaux s'enchainent sans que la
        // file puisse etre reordonnee entre deux.
        for (const fichier of fichiers) {
          const tampon = await this._tampon(fichier);
          if (!tampon) continue;
          await this._jouer_tampon(tampon);
        }
        // La respiration se prend **apres** la sequence et non avant : une
        // annonce demandee dans le silence doit partir tout de suite, c'est
        // l'enchainement qui a besoin d'air, pas le premier son.
        if (this.silence_entre) await this._attendre(this.silence_entre);
      }
    } finally {
      this._joue = false;
    }
  }

  _attendre(secondes) {
    return new Promise((resoudre) => setTimeout(resoudre, secondes * 1000));
  }

  _jouer_tampon(tampon) {
    return new Promise((resoudre) => {
      const source = this.contexte.createBufferSource();
      source.buffer = tampon;
      source.connect(this.contexte.destination);
      source.onended = resoudre;
      source.start();
      // Filet : `onended` ne se declenche pas si le contexte est suspendu
      // entre-temps (onglet mis en arriere-plan), et la file resterait bloquee
      // pour le reste de la seance.
      setTimeout(resoudre, (tampon.duration + 0.5) * 1000);
    });
  }

  /** Vide la file : une seance qui se termine n'a plus rien a annoncer. */
  taire() {
    this._file = [];
  }
}
