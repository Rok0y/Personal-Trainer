// Le lecteur du coach : la file des sons et la fonction `coach`.
//
// La premiere version jouait chaque son des qu'il etait demande, tous en meme
// temps : « le compte se marche un peu dessus », a dit le premier testeur.
// Cinq regles composent la file.
//
// (1) **Un son a la fois.** Le lecteur attend la fin du precedent avant de
//     demarrer le suivant.
// (2) **Une file a priorites.** Chaque cle en porte une — `compteur` vaut 1,
//     `bip` 2, `fin_serie` 10 — et la file sert le plus urgent d'abord.
// (3) **Un evenement important (>= 5) vide les petits sons en attente**
//     plutot que de faire la queue derriere eux : quand une serie se termine,
//     les bips de comptage n'ont plus rien a dire.
// (4) **Un blanc entre deux phrases.** Rien ne jouait jamais litteralement en
//     meme temps, et pourtant le coach « se chevauchait » a l'oreille : la
//     file enchainait l'entree suivante a la milliseconde ou la precedente se
//     taisait. *Deux phrases collees s'entendent comme une phrase coupee.*
// (5) **Un chiffre n'est pas une phrase.** Le blanc se prenait d'abord apres
//     *chaque* entree, chiffres compris, et le comptage prenait du retard a
//     chaque repetition sans jamais le rattraper. Un son de rythme (chiffre,
//     bip) part donc tout de suite, ne repousse aucune phrase, et remplace
//     celui de son espece qui attendait encore : un chiffre dit ou l'on en
//     est, pas ou l'on en etait.
//
// Les tables viennent de `donnees/sons.json` : ni les fichiers, ni les
// priorites, ni les delais, ni les silences ne sont reecrits ici.

//: Priorite a partir de laquelle un son vide les petits sons en attente, et
//: en dessous de laquelle il peut lui-meme etre vide.
const PRIORITE_IMPORTANTE = 5;

//: Priorite par defaut d'une cle absente de la table.
const PRIORITE_PAR_DEFAUT = 5;

//: Le comptage des repetitions est le son le moins prioritaire : c'est celui
//: qu'on sacrifie quand la serie se termine.
const PRIORITE_COMPTEUR = 1;

//: Duree maximale d'une tentative de relance du contexte audio, en secondes.
//: Au-dela on renonce et on attend un contact avec l'ecran.
const DELAI_REPRISE = 0.5;

//: Temps de calme apres un changement de peripherique avant de recreer le
//: contexte, en secondes.
const DELAI_CHANGEMENT_SORTIE = 0.3;

export class Lecteur {
  /**
   * @param {string} dossier  ou trouver les .wav
   * @param {object} tables   { fichiers, priorites, delais } de `sons.json`
   */
  constructor(dossier, tables) {
    this.dossier = dossier.replace(/\/$/, "");
    this.fichiers = tables.fichiers ?? {};
    this.priorites = tables.priorites ?? {};
    this.delais = tables.delais ?? {};
    // Les deux silences, de `sons.json` (`silences`). Les valeurs de repli
    // ne sont pas une seconde source : elles servent le seul cas ou
    // `sons.json` est trop ancien pour les porter, et valent alors zero —
    // c'est-a-dire le comportement d'avant, jamais un reglage invente ici.
    this.silence_entre = tables.silences?.entre_annonces ?? 0;
    this.silence_presentation = tables.silences?.presentation ?? 0;
    // Meme regle de repli : zero rend le comportement d'avant (toujours
    // « repose-toi » puis le blanc, et aucun son traite comme du rythme).
    this.repos_minimal = tables.silences?.repos_minimal ?? 0;
    this.priorite_rythme_max = tables.silences?.priorite_rythme_max ?? 0;

    this.contexte = null;
    this._tampons = new Map();
    this._file = [];
    this._joue = false;
    this._rang = 0;
    this._dernieres = new Map();
    // L'instant (en secondes) ou la derniere **phrase** s'est tue : le blanc
    // se compte depuis lui, pour qu'un chiffre glisse entre deux phrases ne
    // repousse pas la suivante.
    this._fin_phrase = -Infinity;
    // Survie du contexte (voir `_creer_contexte`).
    this._precharges = [];
    this._reprise_armee = false;
    this._sorties_surveillees = false;
    this._recreation_due = false;
    this._micros = null;
  }

  /** Un chiffre ou un bip : un son qui suit le geste. */
  est_rythme(priorite) {
    return priorite <= this.priorite_rythme_max;
  }

  /**
   * Cree le contexte audio. **A appeler depuis un geste de l'utilisateur** :
   * iOS refuse de jouer quoi que ce soit tant qu'un contexte n'a pas ete cree
   * pendant un evenement tactile.
   */
  async preparer() {
    if (!this.contexte) this._creer_contexte();
    this._surveiller_sorties();
    return this._reprendre();
  }

  /**
   * Le son peut-il sortir en ce moment ? Lu a chaque image par le voyant du
   * HUD, pour qu'un son coupe se voie au lieu de se taire.
   */
  son_actif() {
    return this.contexte?.state === "running";
  }

  // ------------------------------------------------------------------
  // Survie du contexte audio
  //
  // **Brancher ou retirer des ecouteurs coupait le son pour le reste de la
  // seance**, et rien ne le disait. Un changement de sortie fait passer le
  // contexte d'iOS a `interrupted` ou `suspended`, et `resume()` n'etait
  // appele qu'une fois, au clic sur la seance. Les sons suivants partaient
  // donc sur un contexte arrete — et le filet de `_jouer_tampon`, qui empeche
  // la file de se bloquer, rendait la panne parfaitement muette. Pire, apres
  // un passage aux ecouteurs Bluetooth la frequence d'echantillonnage change,
  // et WebKit garde parfois un contexte qui se dit `running` sans plus rien
  // sortir : aucun etat a surveiller ne le revele. D'ou trois parades.
  //
  // (1) Un contexte qui sort de `running` est relance aussitot.
  // (2) Un changement d'ecouteurs **recree** le contexte, seule reponse au cas
  //     « running mais muet » — reconnu au nombre de micros, pas au seul
  //     `devicechange`, que l'ouverture de la camera declenche aussi. Le
  //     neuf ne remplace l'ancien que s'il joue ; sinon la recreation attend
  //     un geste.
  // (3) Une relance refusee — iOS en exige parfois un geste — s'arme sur le
  //     prochain contact avec l'ecran, et `son_actif()` le fait savoir.
  // La file, elle, joue **toujours** : elle ne se tait jamais sur la foi de
  // l'etat rapporte par Safari.
  // ------------------------------------------------------------------

  _creer_contexte() {
    this._adopter(this._nouveau_contexte());
  }

  _nouveau_contexte() {
    const Classe = globalThis.AudioContext ?? globalThis.webkitAudioContext;
    return new Classe();
  }

  _adopter(contexte) {
    contexte.onstatechange = () => {
      // Un ancien contexte, ferme par `_recreer`, n'a plus rien a dire.
      if (contexte !== this.contexte) return;
      if (contexte.state === "suspended" || contexte.state === "interrupted") {
        this._reprendre();
      }
    };
    this.contexte = contexte;
  }

  /**
   * Relance le contexte, sans jamais attendre plus de `DELAI_REPRISE` : une
   * promesse de `resume()` qui ne se resout pas (contexte interrompu par un
   * appel) bloquerait sinon toute la file. Rend vrai si le son peut sortir.
   */
  async _reprendre() {
    const contexte = this.contexte;
    if (!contexte || contexte.state === "closed") return false;
    if (contexte.state !== "running") {
      await Promise.race([
        contexte.resume().catch(() => {}),
        this._attendre(DELAI_REPRISE),
      ]);
    }
    const actif = contexte === this.contexte && contexte.state === "running";
    if (!actif) this._reprendre_au_toucher();
    return actif;
  }

  /**
   * Arme une relance sur le prochain contact avec l'ecran.
   *
   * `resume()` est appele **dans le gestionnaire**, sans aucune attente
   * avant : c'est la seule fenetre ou iOS l'accepte a coup sur. En phase de
   * capture, pour passer avant un gestionnaire de page qui arreterait la
   * propagation.
   */
  _reprendre_au_toucher() {
    if (this._reprise_armee || !globalThis.document) return;
    this._reprise_armee = true;
    globalThis.document.addEventListener(
      "pointerdown",
      () => {
        this._reprise_armee = false;
        // Une sortie a change sans qu'on ait pu recreer le contexte : c'est
        // le moment, iOS acceptant un contexte neuf pendant un geste.
        if (this._recreation_due) {
          this._recreation_due = false;
          const neuf = this._nouveau_contexte();
          neuf.resume().catch(() => {});
          this._remplacer(neuf);
          return;
        }
        this.contexte?.resume().catch(() => {});
      },
      { once: true, capture: true },
    );
  }

  _surveiller_sorties() {
    const peripheriques = globalThis.navigator?.mediaDevices;
    if (this._sorties_surveillees || !peripheriques?.addEventListener) return;
    this._sorties_surveillees = true;
    // Un branchement declenche souvent plusieurs evenements d'affilee : on
    // attend que ca se calme pour ne juger qu'une fois.
    let attente = null;
    this._compter_micros().then((n) => { this._micros = n; });
    peripheriques.addEventListener("devicechange", () => {
      clearTimeout(attente);
      attente = setTimeout(() => this._sortie_peut_etre_changee(), DELAI_CHANGEMENT_SORTIE * 1000);
    });
  }

  /**
   * Le nombre de micros, ou null s'il ne se lit pas.
   *
   * C'est l'indice d'un changement d'ecouteurs : Safari n'enumere pas les
   * sorties audio, mais des AirPods apportent leur micro. **Un `devicechange`
   * seul ne suffit pas** — ouvrir la camera en declenche un sur iOS, et la
   * premiere version recreait alors le contexte hors de tout geste, donc
   * suspendu : la seance entiere est restee muette.
   */
  async _compter_micros() {
    try {
      const liste = await globalThis.navigator.mediaDevices.enumerateDevices();
      return liste.filter((p) => p.kind === "audioinput").length;
    } catch {
      return null;
    }
  }

  async _sortie_peut_etre_changee() {
    const avant = this._micros;
    const apres = await this._compter_micros();
    this._micros = apres;
    if (avant === null || apres === null || avant === apres) {
      // Rien ne dit qu'une sortie a change : une simple relance suffit.
      this._reprendre();
      return;
    }
    await this._recreer();
  }

  /**
   * Remplace le contexte par un neuf, sur la nouvelle sortie.
   *
   * Les tampons decodes sont oublies : ils l'ont ete a la frequence de
   * l'ancienne sortie. Les sons precharges le sont de nouveau, sans quoi la
   * premiere repetition apres le changement s'annoncerait en retard.
   */
  async _recreer() {
    if (!this.contexte) return;
    let neuf;
    try {
      neuf = this._nouveau_contexte();
    } catch {
      return;
    }
    await Promise.race([neuf.resume().catch(() => {}), this._attendre(DELAI_REPRISE)]);
    if (neuf.state !== "running") {
      // iOS refuse souvent un contexte neuf hors d'un geste. **On garde
      // l'ancien**, qui joue peut-etre encore, et la recreation attendra le
      // prochain contact avec l'ecran : remplacer un contexte qui marche par
      // un contexte suspendu, c'est ce qui rendait la seance muette.
      neuf.close?.().catch(() => {});
      this._recreation_due = true;
      this._reprise_armee = false;
      this._reprendre_au_toucher();
      this._reprendre();
      return;
    }
    this._remplacer(neuf);
  }

  /** Bascule sur `neuf` et ferme l'ancien, tampons redecodes. */
  _remplacer(neuf) {
    const ancien = this.contexte;
    this._adopter(neuf);
    this._tampons.clear();
    ancien?.close?.().catch(() => {});
    this.precharger(this._precharges);
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
    // Retenus pour `_recreer`, qui doit les recharger sur la nouvelle sortie.
    this._precharges = [...new Set([...(this._precharges ?? []), ...cles])];
    const fichiers = new Set();
    for (const cle of cles) {
      if (/^\d+$/.test(cle)) fichiers.add(`${cle}.wav`);
      else for (const f of this.fichiers[cle] ?? []) fichiers.add(f);
    }
    await Promise.all([...fichiers].map((f) => this._tampon(f)));
  }

  /**
   * Demande un son. Point d'entree unique.
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

    // Meme garde-fou que `coach()`, sur la meme table `delais` :
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
    // Un chiffre remplace le chiffre qui attendait encore : deux en file,
    // c'est deja un de retard. Celui qui joue n'est pas dans la file, donc
    // il n'est jamais coupe.
    if (this.est_rythme(priorite)) {
      this._file = this._file.filter((e) => !this.est_rythme(e.priorite));
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
        const { fichiers, priorite, silence_avant } = this._file.shift();
        // Relancer d'abord, puis jouer **quoi qu'il arrive**. La premiere
        // version jetait l'entree quand le contexte ne se disait pas
        // `running`, pour eviter une rafale a la relance : sur l'iPad, une
        // seance entiere est restee muette. L'etat rapporte par Safari n'est
        // pas assez fiable pour decider de se taire — une rafale tardive vaut
        // mieux qu'un coach qui ne dit plus rien.
        if (!this.son_actif()) await this._reprendre();
        const rythme = this.est_rythme(priorite);
        if (!rythme) {
          // La respiration se prend **avant une phrase**, comptee depuis la
          // fin de la precedente : une annonce demandee dans le silence part
          // tout de suite, et un chiffre ne doit jamais attendre.
          const attente = this._fin_phrase + this.silence_entre - this._maintenant();
          if (attente > 0) await this._attendre(attente);
        }
        if (silence_avant) await this._attendre(silence_avant);
        // Une entree est une sequence : ses morceaux s'enchainent sans que la
        // file puisse etre reordonnee entre deux.
        for (const fichier of fichiers) {
          const tampon = await this._tampon(fichier);
          if (!tampon) continue;
          await this._jouer_tampon(tampon);
        }
        if (!rythme) this._fin_phrase = this._maintenant();
      }
    } finally {
      this._joue = false;
    }
  }

  _maintenant() {
    return performance.now() / 1000;
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
