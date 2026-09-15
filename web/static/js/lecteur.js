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
//
// Les trois tables viennent de `donnees/sons.json`, exporte du Python : ni les
// fichiers, ni les priorites, ni les delais ne sont reecrits ici.

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

  _empiler(fichier, priorite) {
    if (priorite >= PRIORITE_IMPORTANTE) {
      this._file = this._file.filter((e) => e.priorite >= PRIORITE_IMPORTANTE);
    }
    // Le rang departage deux sons de meme priorite : le premier demande passe
    // en premier, ce qu'un tri sur la seule priorite ne garantirait pas.
    this._file.push({ fichier, priorite, rang: this._rang++ });
    this._file.sort((a, b) => b.priorite - a.priorite || a.rang - b.rang);
    this._servir();
  }

  async _servir() {
    if (this._joue) return;
    this._joue = true;
    try {
      while (this._file.length) {
        const { fichier } = this._file.shift();
        const tampon = await this._tampon(fichier);
        if (!tampon) continue;
        await this._jouer_tampon(tampon);
      }
    } finally {
      this._joue = false;
    }
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
