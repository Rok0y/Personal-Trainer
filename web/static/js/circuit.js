// La machine a etats d'une seance.
//
// Meme convention que landmarks.js, compteur.js et detections.js : les noms
// sont en snake_case, contrairement a l'usage JavaScript. Ne rien renommer :
// les reponses figees des tests designent les methodes par leur nom.
//
// `node scripts/comparer_seances.mjs` rejoue des suites de commandes
// horodatees sur les vraies seances, releve l'etat apres chaque pas et le
// compare a des reponses figees.

import { est_cible_manuelle } from "./cible_manuelle.js";

export const MODE_REPETITIONS = "repetitions";
export const MODE_MAINTIEN = "maintien";
export const MODE_CHRONO = "chrono";
export const MODE_AMRAP = "amrap";
export const MODE_ECHAUFFEMENT = "echauffement";

export const MODES_CONNUS = [
  MODE_REPETITIONS,
  MODE_MAINTIEN,
  MODE_CHRONO,
  MODE_AMRAP,
  MODE_ECHAUFFEMENT,
];

// Modes dont la cible se compte en secondes, et non en repetitions. C'est ce
// qui decide quel champ d'un bloc est *joue* : `duree` ici, `repetitions`
// ailleurs. Le `MODES_DUREE` des gabarits dit presque la meme chose mais sert
// a autre chose — quel champ le formulaire presente —, et il laisse l'AMRAP de
// cote ; celui-ci decide de ce qui fait avancer la serie, et l'AMRAP est bien
// borne par un temps.
export const MODES_CIBLE_TEMPORELLE = [
  MODE_MAINTIEN,
  MODE_CHRONO,
  MODE_AMRAP,
  MODE_ECHAUFFEMENT,
];

/**
 * La cible d'un bloc *dans l'unite que son mode joue*.
 *
 * Un bloc porte `repetitions` et `duree` en meme temps — volontairement, pour
 * qu'un changement de mode ne perde pas l'autre valeur —, donc seul le mode
 * dit lequel des deux est la cible. Un `repetitions || duree` prend le premier
 * non nul, c'est-a-dire parfois celui que le mode ne joue pas.
 *
 * Accepte aussi bien un bloc JSON qu'un `BlocExercice` : les deux formes
 * circulent, et la regle est la meme.
 */
export function cible_du_bloc(bloc) {
  if (MODES_CIBLE_TEMPORELLE.includes(bloc.mode)) return bloc.duree || 0;
  return (bloc.repetitions ?? bloc.repetitions_par_serie) || 0;
}

// Modes dont le deroulement depend d'une fonction de detection : pour eux,
// `Exercice.detection` ne peut pas etre nul. Le chrono et l'echauffement en
// sont absents parce qu'ils avancent au temps, sans analyser la pose.
export const MODES_AVEC_DETECTION_OBLIGATOIRE = [
  MODE_REPETITIONS,
  MODE_MAINTIEN,
  MODE_AMRAP,
];

/**
 * Un bloc d'echauffement guide un mouvement sans compter nulle part.
 *
 * Point d'entree unique de la regle « invisible dans les stats » : la
 * progression de la seance, les objectifs et l'export vers l'historique s'y
 * referent tous.
 */
export function est_echauffement(bloc) {
  return bloc.mode === MODE_ECHAUFFEMENT;
}

export class Exercice {
  constructor({
    nom,
    detection = null,
    description = "",
    instructions = null,
    erreurs = null,
    mise_en_place = null,
    erreurs_frequentes = null,
    variante_facile = null,
    variante_difficile = null,
    orientation = null,
    amplitude = null,
    changements = null,
    sensations = null,
    depart = null,
    delai_min_reps = null,
    voix_tous_les = null,
    instrument = null,
    autre_cote = null,
  }) {
    this.nom = nom;
    this.detection = detection;
    this.description = description;
    this.instructions = instructions ?? [];
    this.erreurs = erreurs ?? [];
    this.mise_en_place = mise_en_place ?? [];
    this.erreurs_frequentes = erreurs_frequentes ?? [];
    this.variante_facile = variante_facile;
    this.variante_difficile = variante_difficile;
    // Le seul champ que le coach **prononce**. Il manquait ici, donc
    // `bloc.exercice.orientation` valait `undefined` dans toute
    // l'application et `sequence_orientation` rendait une liste vide : la
    // voix n'a jamais dit de quel cote se placer, alors que la donnee etait
    // bien exportee dans `mouvements.json`. Un champ present dans les
    // donnees et absent du constructeur ne se signale nulle part.
    this.orientation = orientation;
    // Couple [fonction, cle de message] : la profondeur a atteindre pendant
    // une repetition. Voir `suivre_amplitude` dans `moteur.js`.
    this.amplitude = amplitude;
    // Ce que le coach annonce en cours de chrono : [[fraction, "sens"], ...].
    // Meme piege que l'orientation — un champ oublie ici rendrait les
    // echauffements muets sans que rien ne le signale.
    this.changements = (changements ?? []).map((c) => [...c]);
    this.sensations = sensations ?? [];
    // La position ou une serie commence ("debut", "fin"), ou null pour « la
    // premiere vue ». Lue par `CompteurMouvement.mettre_a_jour`. Meme piege
    // que les deux champs ci-dessus.
    this.depart = depart;
    // L'ecart minimal, en secondes, entre deux repetitions comptees, quand le
    // mouvement va plus vite que le compteur ne l'admet d'ordinaire (une
    // montee de genoux ou chaque pas compte). null : le delai par defaut de
    // `compteur.js`. Meme piege que l'orientation.
    this.delai_min_reps = delai_min_reps;
    // Tous les combien la voix dit le compte (`nombre_a_dire`, moteur.js),
    // quand chaque pas compte et qu'un nombre par pas couvrirait tout. null :
    // chaque repetition. Meme piege que l'orientation.
    this.voix_tous_les = voix_tous_les;
    // L'instrument de sa detection (`instruments.js`) : ce qui dit **pourquoi**
    // une repetition n'a pas compte (`expliquer_tentative`). Jamais ce qui
    // compte.
    this.instrument = instrument;
    // `{ detection, membre }` pour un mouvement unilateral : la detection du
    // meme mouvement de l'autre cote, et ce qui se dit (« c'est l'autre
    // bras »). Lu par `surveiller_autre_cote`. Meme piege que l'orientation.
    this.autre_cote = autre_cote;
  }

  fiche() {
    return {
      nom: this.nom,
      description: this.description,
      mise_en_place: [...this.mise_en_place],
      instructions: [...this.instructions],
      erreurs_frequentes: [...this.erreurs_frequentes],
      sensations: [...this.sensations],
      variante_facile: this.variante_facile,
      variante_difficile: this.variante_difficile,
      orientation: this.orientation,
      changements: this.changements.map((c) => [...c]),
      analyse_la_pose: this.detection !== null,
    };
  }
}

// Champs temporels poses par les modes au fil d'une serie, et effaces
// ensemble par `reinitialiser_etat_serie`. Un seul endroit connait cette
// liste — ne pas la redupliquer en ajoutant un mode.
const CHAMPS_TEMPORELS = [
  "dernier_maintien",
  "derniere_seconde_bip",
  "debut_chrono",
  "temps_chrono",
  "debut_amrap",
  "temps_amrap",
  "temps_echauffement",
  "dernier_tick_echauffement",
  "amplitude_atteinte",
  "avertissement_amplitude",
  "faute_en_cours",
  "faute_depuis",
  "faute_dite_a",
  "suivi_tentatives",
  "non_comptee",
  "verdict_en_attente",
  // Le maintien tenu au moins une fois dans la serie : sans lui, rien n'est
  // corrige. Oublie, il survivait a la serie et « reprends la position »
  // partait des la serie 2, avant meme qu'on soit en place.
  "position_maintien_validee",
  // L'autre cote (`surveiller_autre_cote`) : son compteur fantome et l'echec
  // qu'il attend de confirmer.
  "autre_cote_compteur",
  "autre_cote_attente",
  "autre_cote_depuis",
  "autre_cote_dit",
  // L'ouverture de la serie (`attendre_mise_en_place`) : une serie refaite,
  // remise a zero ou changee de variante se rouvre, « c'est parti » compris.
  "serie_ouverte",
  "mise_en_place_buste",
  "mise_en_place_jeton",
  "mise_en_place_depuis",
];

export class BlocExercice {
  constructor({
    exercice,
    poids,
    mode,
    nombre_series,
    repetitions_par_serie,
    duree,
    repos_entre_series,
    repos_apres,
    commentaire = "",
    entrelace_avec = null,
    cible_manuelle = false,
  }) {
    // Conservee **telle qu'elle a ete stockee** (une liste d'identifiants de
    // profils) et non reduite a un booleen : les seances etant partagees, une
    // marque appartient a un profil, et l'aplatir ici ferait perdre celles des
    // autres au premier reenregistrement.
    this.cible_manuelle = cible_manuelle;
    this.exercice = exercice;
    this.poids = poids;
    this.mode = mode;
    this.nombre_series = nombre_series;
    this.repetitions_par_serie = repetitions_par_serie;
    this.duree = duree;
    this.repos_entre_series = repos_entre_series;
    this.repos_apres = repos_apres;
    this.commentaire = commentaire || "";
    this.entrelace_avec = entrelace_avec;
    // Le mouvement ecrit dans la seance, quand ce bloc en joue un autre — une
    // variante plus facile retenue par le profil (`variantes.js`) ou choisie
    // en pleine seance. null sinon. Affichage seulement : l'historique
    // enregistre ce qui a ete **joue**.
    this.remplace = null;
    // Les mouvements quittes en cours de seance, du plus ancien au plus
    // recent, avec ce qu'ils demandaient : `{nom, poids, series, repetitions,
    // duree}`. Leurs series deja faites restent enregistrees sous leur nom.
    this.abandons = [];

    this.temps_maintien = 0;
    this.temps_restant_precedent = null;
  }
}

//: Phases ou l'on peut passer a la variante plus facile du bloc courant :
//: avant la premiere serie, pendant l'effort, et pendant la recuperation qui
//: suit une serie. Pas pendant le repos entre deux exercices : le bloc courant
//: y est deja fini.
export const PHASES_VARIANTE = ["preparation", "exercice", "recuperation_serie"];

/**
 * Les liens d'entrelacement d'une seance : index d'un bloc → index de son
 * partenaire.
 *
 * Le partenaire est le premier bloc qui porte le nom vise **apres** celui qui
 * le vise — jamais avant, sans quoi deux blocs se renverraient l'un a l'autre
 * sans fin. Prend les noms et les liens plutot que des blocs, pour servir aux
 * deux formes : les `BlocExercice` du `Circuit` et le JSON qu'on valide
 * (`problemes_des_blocs`).
 */
export function paires_entrelacees(noms, liens) {
  const paires = new Map();
  liens.forEach((lien, index) => {
    if (!lien) return;
    for (let autre = index + 1; autre < noms.length; autre++) {
      if (noms[autre] === lien) {
        paires.set(index, autre);
        return;
      }
    }
  });
  return paires;
}

/**
 * Les circuits que forment ces liens : index de chaque bloc → la chaine
 * entiere, dans l'ordre de jeu (la tete d'abord).
 *
 * **Une paire est une chaine de deux** : un superset et un circuit en tours ne
 * font qu'une regle. La tete est le bloc que personne ne vise ; on suit les
 * liens a partir d'elle. Un bloc deja range ne l'est pas deux fois (deux blocs
 * qui visent le meme partenaire : le premier le garde).
 */
export function chaines_entrelacees(paires) {
  const visees = new Set(paires.values());
  const chaines = new Map();
  for (const tete of [...paires.keys()].sort((a, b) => a - b)) {
    if (visees.has(tete) || chaines.has(tete)) continue;
    const chaine = [tete];
    let courant = tete;
    while (paires.has(courant) && !chaines.has(paires.get(courant))) {
      courant = paires.get(courant);
      if (chaine.includes(courant)) break;
      chaine.push(courant);
    }
    if (chaine.length < 2) continue;
    for (const index of chaine) chaines.set(index, chaine);
  }
  return chaines;
}

//: Comment annoncer un bloc selon sa place dans la seance. Ce sont des cles
//: du vocabulaire ferme d'`annonces.js`.
export const AMORCES_PAR_POSITION = {
  premier: "premier_exercice",
  dernier: "dernier_exercice",
  milieu: "prochain_exercice",
};

export class Circuit {
  constructor(exercices) {
    this.exercices = exercices;
    this.index_exercice = 0;
    this.serie_actuelle = 1;
    this.phase = "preparation";
    this.debut_repos = null;
    this.historique_enregistre = false;
    this.seance_id = null;
    this.utilisateur_id = null;

    // Horloge de la seance, portee par l'objet et non par le module : chaque
    // client a sa propre ligne de temps. **Toutes** les durees du circuit
    // passent par elle, y compris le decompte de repos et `duree_totale` — ne
    // pas y reintroduire de `Date.now()` direct, c'est la condition pour
    // qu'une seance de 45 minutes se rejoue en quelques millisecondes.
    //
    // Secondes et non millisecondes : les durees des blocs (`repos_apres`,
    // `duree`) sont en secondes.
    this.maintenant = () => performance.now() / 1000;
    this.debut = this.maintenant();

    this.resultats_series = [];
    this.paires_entrelacees = this._detecter_paires_entrelacees();
    // Le circuit de chaque bloc entrelace (une paire en est un de deux) : ce
    // qui dit ou aller apres chaque serie d'un tour.
    this._chaine_de = chaines_entrelacees(this.paires_entrelacees);
    this.serie_actuelle_locale = 1;
    this._exercice_precedent_entrelace = null;

    // Repere de la derniere serie terminee, pose par `terminer_serie` avant
    // qu'elle ne deplace quoi que ce soit. C'est le seul moyen fiable de
    // savoir quoi refaire : `terminer_serie` a cinq sorties, l'increment de
    // `serie_actuelle` n'a lieu que s'il reste des series, et l'index
    // d'exercice a parfois deja avance.
    this._derniere_serie_terminee = null;
  }

  _detecter_paires_entrelacees() {
    return paires_entrelacees(
      this.exercices.map((bloc) => bloc.exercice.nom),
      this.exercices.map((bloc) => bloc.entrelace_avec)
    );
  }

  /** Le circuit dont ce bloc fait partie, la tete d'abord, ou null. */
  _chaine(index) {
    return this._chaine_de.get(index) ?? null;
  }

  /**
   * Le tour en cours d'un circuit : celui que la tete a ouvert, ou la serie
   * courante quand aucun tour n'est ouvert (on est sur la tete, avant sa
   * serie).
   */
  get _tour() {
    return this._exercice_precedent_entrelace?.serie ?? this.serie_actuelle;
  }

  _est_entrelace(index) {
    return this.paires_entrelacees.has(index);
  }

  _obtenir_partenaire_entrelace(index) {
    return this.paires_entrelacees.has(index)
      ? this.paires_entrelacees.get(index)
      : null;
  }

  /**
   * Indice du vrai prochain exercice, en sautant tout le circuit du bloc
   * courant : ses membres se jouent dans ses tours, pas apres lui.
   */
  _obtenir_vrai_prochain_exercice_index() {
    let prochain_index = this.index_exercice + 1;
    const chaine = this._chaine(this.index_exercice);
    if (chaine !== null) {
      prochain_index = Math.max(prochain_index, Math.max(...chaine) + 1);
    }
    return prochain_index;
  }

  get bloc_actuel() {
    if (this.index_exercice >= this.exercices.length) return null;
    return this.exercices[this.index_exercice];
  }

  // Methode et non accesseur — la seule de cette famille de lectures a
  // l'etre, parce qu'elle prend le bloc en argument.
  /**
   * Comment annoncer ce bloc, selon sa place dans la seance.
   *
   * « Le premier exercice sera » a l'entree,
   * « pour finir » sur le dernier bloc, « prochain exercice » ailleurs. La
   * comparaison est d'**identite** et non d'index, deux blocs pouvant porter
   * le meme exercice.
   *
   * Un circuit revient sur ses blocs : le premier n'est « premier » que tant
   * que rien n'a ete fait, et le dernier n'est « pour finir » qu'au dernier
   * tour.
   */
  amorce_annonce(bloc) {
    if (!bloc || !this.exercices.length) return AMORCES_PAR_POSITION.milieu;
    if (bloc === this.exercices[0] && this.resultats_series.length === 0) {
      return AMORCES_PAR_POSITION.premier;
    }
    if (bloc === this.exercices[this.exercices.length - 1]) {
      const chaine = this._chaine(this.exercices.length - 1);
      if (chaine !== null && this._tour < this.exercices[chaine[0]].nombre_series) {
        return AMORCES_PAR_POSITION.milieu;
      }
      return AMORCES_PAR_POSITION.dernier;
    }
    return AMORCES_PAR_POSITION.milieu;
  }

  /**
   * La pause en cours mene-t-elle a un autre bloc que celui qu'on vient de
   * finir ? C'est le cas dans un circuit (et un superset) : la recuperation
   * entre deux series y est aussi un changement d'exercice, qu'il faut
   * annoncer.
   */
  change_de_bloc() {
    return (
      this.phase === "recuperation_serie" &&
      this._derniere_serie_terminee !== null &&
      this._derniere_serie_terminee.index_exercice !== this.index_exercice
    );
  }

  prochain_bloc() {
    const prochain_index = this._obtenir_vrai_prochain_exercice_index();
    if (prochain_index >= this.exercices.length) return null;
    return this.exercices[prochain_index];
  }

  get poids() {
    // Se protege de `bloc_actuel` nul comme ses voisines : `payload_etat` lit
    // ce champ a chaque image, et une exception y gele le flux video.
    if (this.bloc_actuel === null) return 0;
    return this.bloc_actuel.poids;
  }

  get exercice_actuel() {
    if (this.bloc_actuel === null) return null;
    return this.bloc_actuel.exercice;
  }

  get nombre_series() {
    if (this.bloc_actuel === null) return 0;
    return this.bloc_actuel.nombre_series;
  }

  get repetitions_cibles() {
    if (this.bloc_actuel === null) return 0;
    return this.bloc_actuel.repetitions_par_serie;
  }

  get temps_restant() {
    if (this.phase === "exercice") return 0;
    let duree;
    if (this.phase === "recuperation_serie") {
      duree = this.bloc_actuel.repos_entre_series;
    } else if (this.phase === "repos_exercice") {
      duree = this.bloc_actuel.repos_apres;
    } else {
      return 0;
    }
    const temps_ecoule = this.maintenant() - this.debut_repos;
    return Math.max(0, duree - temps_ecoule);
  }

  get duree_totale() {
    // Tronque vers zero : `Math.trunc` et **pas** `Math.floor`, les deux ne
    // differant que pour un negatif, qu'une horloge qui recule produirait.
    return Math.trunc(this.maintenant() - this.debut);
  }

  /** Blocs qui comptent dans la progression, les objectifs et l'historique. */
  get blocs_comptabilises() {
    return this.exercices.filter((bloc) => !est_echauffement(bloc));
  }

  _est_comptabilise(index) {
    return (
      index >= 0 &&
      index < this.exercices.length &&
      !est_echauffement(this.exercices[index])
    );
  }

  get nombre_series_total() {
    return this.blocs_comptabilises.reduce((somme, bloc) => somme + bloc.nombre_series, 0);
  }

  /**
   * Miroir exact de `blocs_comptabilises` : l'echauffement etant exclu de
   * partout ailleurs, il lui faut son propre compteur plutot qu'une exception
   * glissee dans celui des exercices.
   */
  get blocs_echauffement() {
    return this.exercices.filter((bloc) => est_echauffement(bloc));
  }

  get nombre_series_echauffement() {
    return this.blocs_echauffement.reduce((somme, bloc) => somme + bloc.nombre_series, 0);
  }

  /**
   * Vrai tant que le bloc courant est un echauffement.
   *
   * C'est ce drapeau, et non « reste-t-il des echauffements ? », qui decide de
   * la barre affichee : une seance peut n'en avoir aucun, et la barre des
   * exercices doit alors s'afficher des la premiere image.
   */
  get dans_echauffement() {
    return (
      this.index_exercice >= 0 &&
      this.index_exercice < this.exercices.length &&
      est_echauffement(this.exercices[this.index_exercice])
    );
  }

  /**
   * Meme comptage que `series_terminees`, avec le filtre inverse.
   *
   * L'entrelacement n'est pas traite ici : il n'a de sens qu'entre deux
   * exercices comptabilises, et un echauffement entrelace n'existe pas.
   */
  get series_echauffement_terminees() {
    const passes = this.exercices
      .slice(0, this.index_exercice)
      .filter((bloc) => est_echauffement(bloc))
      .reduce((somme, bloc) => somme + bloc.nombre_series, 0);
    return passes + (this.dans_echauffement ? Math.max(0, this.serie_actuelle - 1) : 0);
  }

  get series_terminees() {
    // Avec entrelacement, seuls les resultats enregistres comptent juste :
    // l'index d'exercice fait des aller-retours.
    if (this.paires_entrelacees.size > 0) {
      return this.resultats_series.filter((resultat) =>
        this._est_comptabilise(resultat.index_exercice)
      ).length;
    }

    // Cas normal. Le second terme est neutralise pendant un echauffement,
    // sinon la barre avancerait avant que le premier exercice comptabilise
    // ait commence.
    const passes = this.exercices
      .slice(0, this.index_exercice)
      .filter((bloc) => !est_echauffement(bloc))
      .reduce((somme, bloc) => somme + bloc.nombre_series, 0);
    return (
      passes +
      (this._est_comptabilise(this.index_exercice)
        ? Math.max(0, this.serie_actuelle - 1)
        : 0)
    );
  }

  /**
   * Les series de chaque bloc, telles qu'elles ont ete jouees.
   *
   * Pour chaque bloc de `blocs` (l'une des deux listes des barres de
   * progression) : `series`, une case par serie, null tant qu'elle n'est pas
   * faite, sinon `{repetitions, duree, completee}` ; et `en_cours`, le numero
   * de la serie courante si ce bloc est le bloc courant, null sinon.
   *
   * **Lu dans les resultats, pas deduit d'un compte.** La barre remplissait
   * ses segments a plat avec `series_terminees` : en superset, A1 puis B1
   * remplissaient A1 puis A2, et la barre n'avancait qu'un exercice sur deux.
   * Seules comptent les series du mouvement joue : apres une variante, celles
   * du mouvement quitte ne remplissent pas la barre de sa remplacante.
   */
  etat_des_series(blocs) {
    return blocs.map((bloc) => {
      const index = this.exercices.indexOf(bloc);
      const series = Array.from({ length: Number(bloc.nombre_series) || 0 }, () => null);
      for (const resultat of this.resultats_series) {
        if (resultat.index_exercice !== index || resultat.exercice !== bloc.exercice.nom) continue;
        if (resultat.serie < 1 || resultat.serie > series.length) continue;
        series[resultat.serie - 1] = {
          repetitions: resultat.repetitions,
          duree: resultat.duree,
          completee: resultat.completee,
        };
      }
      const courant = index === this.index_exercice && !["termine", "abandonne"].includes(this.phase);
      return { series, en_cours: courant ? this.serie_actuelle : null };
    });
  }

  passer_pause() {
    if (this.phase !== "recuperation_serie" && this.phase !== "repos_exercice") {
      return false;
    }
    this.debut_repos = null;
    if (this.phase === "recuperation_serie") {
      this.phase = "exercice";
    } else {
      this.passer_exercice_suivant();
    }
    return true;
  }

  /**
   * Un echauffement seul ne fait pas une seance : sans ce filtre, un abandon
   * pendant l'echauffement enregistrerait une seance sans aucun exercice.
   */
  a_des_resultats() {
    return this.resultats_series.some((resultat) =>
      this._est_comptabilise(resultat.index_exercice)
    );
  }

  /**
   * Enregistre une seule performance par exercice et par numero de serie.
   *
   * Une serie refaite apres navigation remplace son ancien resultat : elle ne
   * peut donc ni disparaitre ni etre comptee deux fois.
   */
  enregistrer_resultat_serie({ repetitions = 0, duree = 0, completee = true } = {}) {
    const resultat = {
      index_exercice: this.index_exercice,
      serie: this.serie_actuelle,
      // Le mouvement fait, et pas seulement le bloc : apres un passage a la
      // variante, la serie 1 de celle-ci ne doit ni ecraser la serie 1 du
      // mouvement quitte, ni s'exporter sous son nom.
      exercice: this.bloc_actuel.exercice.nom,
      repetitions,
      duree,
      completee,
      objectif_repetitions: this.bloc_actuel.repetitions_par_serie,
      objectif_duree: this.bloc_actuel.duree,
    };
    for (let index = 0; index < this.resultats_series.length; index++) {
      const precedent = this.resultats_series[index];
      if (
        precedent.index_exercice === this.index_exercice &&
        precedent.serie === this.serie_actuelle &&
        precedent.exercice === resultat.exercice
      ) {
        this.resultats_series[index] = resultat;
        return;
      }
    }
    this.resultats_series.push(resultat);
  }

  /**
   * Remet a zero les champs temporels d'un bloc (par defaut le bloc courant).
   *
   * Utilisee en interne et par le moteur a la fin de chaque mode, pour eviter
   * que les deux ne dupliquent la liste des attributs a reinitialiser.
   */
  reinitialiser_etat_serie(bloc = null) {
    const cible = bloc !== null ? bloc : this.bloc_actuel;
    if (cible === null) return;

    cible.temps_maintien = 0;
    cible.temps_restant_precedent = null;
    for (const nom of CHAMPS_TEMPORELS) {
      // L'attribut doit disparaitre, pas valoir undefined : l'operateur `in`
      // doit repondre faux.
      if (nom in cible) delete cible[nom];
    }
  }

  /** Efface la progression de la serie courante sans changer d'index. */
  remettre_serie_a_zero() {
    if (this.bloc_actuel === null) return;
    this.reinitialiser_etat_serie();
    if (this.phase !== "termine" && this.phase !== "preparation") {
      this.phase = "exercice";
      this.debut_repos = null;
    }
  }

  /** Relance entierement la serie courante depuis son etat initial. */
  recommencer_serie() {
    if (this.bloc_actuel === null) return;
    this.reinitialiser_etat_serie();
    this.phase = "exercice";
    this.debut_repos = null;
  }

  /** Revient a la serie precedente, si elle existe. */
  serie_precedente() {
    if (this.serie_actuelle <= 1 || this.bloc_actuel === null) return false;
    this.serie_actuelle -= 1;
    this.reinitialiser_etat_serie();
    this.phase = "exercice";
    this.debut_repos = null;
    return true;
  }

  /**
   * Retire la performance enregistree pour une serie donnee.
   *
   * Symetrique d'`enregistrer_resultat_serie`, qui deduplique a l'ecriture :
   * tant qu'on ne l'appelle pas, une serie qu'on s'apprete a refaire garde son
   * ancien resultat, et une seance abandonnee entre-temps l'exporterait comme
   * si elle avait compte.
   */
  oublier_resultat_serie(index_exercice, serie, exercice = null) {
    this.resultats_series = this.resultats_series.filter(
      (resultat) =>
        !(
          resultat.index_exercice === index_exercice &&
          resultat.serie === serie &&
          (exercice === null || resultat.exercice === exercice)
        )
    );
  }

  /**
   * Une serie a-t-elle deja ete terminee ?
   *
   * Volontairement muet sur la phase : c'est tout l'interet du repere, et
   * c'est ce qui manquait a l'ancienne condition (`serie_actuelle > 1`),
   * fausse des la derniere serie d'un exercice.
   */
  peut_refaire_derniere_serie() {
    return this._derniere_serie_terminee !== null;
  }

  /**
   * Decrit les blocs configures — tous par defaut.
   *
   * `blocs` sert aux **deux** barres de progression, qui indexent leurs
   * segments a plat avec un compteur : celle des exercices recoit
   * `blocs_comptabilises`, celle de l'echauffement `blocs_echauffement`.
   * Melanger les deux listes decalerait tous les segments de l'autre — c'est
   * pour cela que cette methode prend la liste et non un booleen
   * `inclure_echauffement`, qui ne saurait pas en decrire deux.
   *
   * `cible_manuelle` est **resolu** en booleen : cet export alimente
   * l'affichage, ou la question est « ce bloc est-il fige *pour moi* ? ».
   * La valeur brute, une liste d'identifiants de profils, ne quitte jamais
   * l'ecriture sur disque — l'aplatir la effacerait la marque des autres.
   */
  exporter_configuration(blocs = null, utilisateur_id = null) {
    return (blocs === null ? this.exercices : blocs).map((bloc) => ({
      nom: bloc.exercice.nom,
      series: bloc.nombre_series,
      repetitions: bloc.repetitions_par_serie,
      poids: bloc.poids,
      mode: bloc.mode,
      duree: bloc.duree,
      commentaire: bloc.commentaire,
      repos_entre_series: bloc.repos_entre_series,
      repos_apres: bloc.repos_apres,
      entrelace_avec: bloc.entrelace_avec,
      cible_manuelle: est_cible_manuelle(bloc, utilisateur_id),
    }));
  }

  /**
   * Rejoue la serie qui vient d'etre terminee, quelle que soit la phase.
   *
   * Le repos qui suit une serie est justement le moment ou l'on se rend compte
   * qu'elle ne comptait pas.
   */
  refaire_derniere_serie() {
    if (this._derniere_serie_terminee === null) return false;

    const repere = this._derniere_serie_terminee;

    // L'index d'exercice d'abord : `recommencer_serie` remet a zero l'etat
    // temporel de `bloc_actuel`, qui depend de lui. Le restaurer apres coup
    // nettoierait le mauvais bloc — celui de l'exercice suivant, quand
    // `repos_apres` vaut 0 et que la transition a deja eu lieu.
    this.index_exercice = repere.index_exercice;
    this.serie_actuelle = repere.serie;
    // Sans cette ligne, un superset croit etre au milieu d'un aller-retour qui
    // n'existe plus : la serie refaite renverrait vers le partenaire au lieu
    // d'enchainer, ou sauterait un cran de serie au retour.
    this._exercice_precedent_entrelace =
      repere.entrelace !== null ? { ...repere.entrelace } : null;

    // La performance precedente est effacee maintenant, pas quand la serie
    // refaite se termine : compter sur la deduplication laisserait une fenetre
    // pendant laquelle un abandon exporte la tentative qu'on vient de
    // desavouer — et c'est la le sens du bouton.
    this.oublier_resultat_serie(repere.index_exercice, repere.serie, repere.exercice);

    // Le repere est conserve : rappeler cette methode restaure le meme etat
    // plutot que de reculer encore d'un cran.
    this.recommencer_serie();
    return true;
  }

  /** Avance a la serie suivante, sans depasser le bloc actuel. */
  serie_suivante() {
    if (this.serie_actuelle >= this.nombre_series || this.bloc_actuel === null) {
      return false;
    }
    this.serie_actuelle += 1;
    this.reinitialiser_etat_serie();
    this.phase = "exercice";
    this.debut_repos = null;
    return true;
  }

  /**
   * La performance donnee atteint-elle la consigne du bloc courant ?
   *
   * Point d'entree unique de « cette serie compte-t-elle ». Le seuil depend du
   * mode : une duree pour un maintien ou un chrono, des repetitions sinon.
   */
  /**
   * Le mouvement plus facile proposable maintenant, ou null.
   *
   * Le nom seulement : le `Circuit` ne connait pas le catalogue, c'est
   * l'appelant qui resout l'`Exercice` et son objectif. Refuse sur un bloc
   * entrelace — faire repartir un seul des deux partenaires a la serie 1
   * casserait l'aller-retour.
   */
  variante_possible() {
    const bloc = this.bloc_actuel;
    if (bloc === null || !PHASES_VARIANTE.includes(this.phase)) return null;
    if (est_echauffement(bloc)) return null;
    if (
      this._est_entrelace(this.index_exercice) ||
      [...this.paires_entrelacees.values()].includes(this.index_exercice)
    ) {
      return null;
    }
    return bloc.exercice.variante_facile || null;
  }

  /**
   * Joue le bloc courant sur un mouvement plus facile, des maintenant.
   *
   * **Le bloc repart a la serie 1**, avec la cible de la variante. Les series
   * deja faites restent enregistrees sous le nom de l'original (`abandons`).
   * Leve si `exercice` n'est pas celui que `variante_possible` nomme.
   */
  passer_a_la_variante(exercice, { poids, series, repetitions, duree }) {
    const attendu = this.variante_possible();
    if (attendu === null || !exercice || exercice.nom !== attendu) {
      throw new Error("Pas de variante plus facile à jouer maintenant");
    }

    const bloc = this.bloc_actuel;
    bloc.abandons.push({
      nom: bloc.exercice.nom,
      poids: bloc.poids,
      series: bloc.nombre_series,
      repetitions: bloc.repetitions_par_serie,
      duree: bloc.duree,
    });
    if (bloc.remplace === null) bloc.remplace = bloc.exercice.nom;
    bloc.exercice = exercice;
    bloc.poids = poids;
    bloc.nombre_series = series;
    bloc.repetitions_par_serie = repetitions;
    bloc.duree = duree;
    // Une cible figee l'etait pour l'original, pas pour sa variante.
    bloc.cible_manuelle = null;

    this.serie_actuelle = 1;
    // On ne « refait » pas une serie d'un autre mouvement.
    this._derniere_serie_terminee = null;
    this.reinitialiser_etat_serie();
    if (this.phase !== "preparation") {
      this.phase = "exercice";
      this.debut_repos = null;
    }
    return true;
  }

  objectif_serie_atteint({ repetitions = 0, duree = 0 } = {}) {
    const bloc = this.bloc_actuel;
    if (bloc === null) return false;
    if (bloc.mode === MODE_MAINTIEN || bloc.mode === MODE_CHRONO) {
      return duree >= bloc.duree;
    }
    return repetitions >= bloc.repetitions_par_serie;
  }

  /**
   * Enregistre la performance courante puis lance la transition.
   *
   * La serie n'est marquee `completee` que si elle atteint sa consigne :
   * terminer a la main, c'est justement le cas ou l'objectif peut ne pas etre
   * atteint, et le forcer a vrai ferait passer un abandon pour une reussite.
   */
  terminer_serie_manuellement({ repetitions = 0, duree = 0 } = {}) {
    if (this.phase !== "exercice" || this.bloc_actuel === null) return false;

    this.enregistrer_resultat_serie({
      repetitions,
      duree,
      completee: this.objectif_serie_atteint({ repetitions, duree }),
    });
    this.reinitialiser_etat_serie();
    this.terminer_serie();
    return true;
  }

  /** Appelee lorsque la cible de la serie est atteinte. */
  terminer_serie() {
    // Meme garde que `commencer_exercice` : plus aucun bloc courant, donc plus
    // rien a terminer. Les lectures de `bloc_actuel.repos_apres` plus bas la
    // supposent deja.
    if (this.bloc_actuel === null) return;

    // Photographier la serie qui vient de s'achever *avant* de bouger quoi que
    // ce soit : a la sortie, l'information n'est plus reconstituable.
    this._derniere_serie_terminee = {
      index_exercice: this.index_exercice,
      serie: this.serie_actuelle,
      exercice: this.bloc_actuel.exercice.nom,
      entrelace:
        this._exercice_precedent_entrelace !== null
          ? { ...this._exercice_precedent_entrelace }
          : null,
    };

    // Cas 1 : le bloc courant est dans un circuit (une paire en est un de
    // deux), et le tour n'est pas fini : on passe au membre suivant.
    const chaine = this._chaine(this.index_exercice);
    if (chaine !== null) {
      const position = chaine.indexOf(this.index_exercice);
      const dernier = position === chaine.length - 1;

      if (!dernier && (position > 0 || this._exercice_precedent_entrelace === null)) {
        // Le tour s'ouvre sur la tete, ou se poursuit. On garde le meme
        // `serie_actuelle` d'un membre a l'autre : c'est le numero du tour, et
        // la serie que chaque membre enregistre. Le repere nomme toujours la
        // tete, ou l'on revient a la fin du tour.
        if (this._exercice_precedent_entrelace === null) {
          this._exercice_precedent_entrelace = {
            index: chaine[0],
            serie: this.serie_actuelle,
          };
        }
        this.index_exercice = chaine[position + 1];
        this.phase = "recuperation_serie";
        this.debut_repos = this.maintenant();
        return;
      }

      // Le tour est fini (dernier membre, ou tete qui porte deja un tour
      // ouvert) : retour a la tete, tour suivant. Sans tour ouvert, le dernier
      // membre se joue comme un bloc seul — c'est le cas ordinaire plus bas.
      if (this._exercice_precedent_entrelace !== null) {
        this.index_exercice = this._exercice_precedent_entrelace.index;
        this.serie_actuelle = this._exercice_precedent_entrelace.serie + 1;
        this._exercice_precedent_entrelace = null;

        if (this.serie_actuelle > this.nombre_series) {
          this._finir_bloc();
        } else {
          this.phase = "recuperation_serie";
          this.debut_repos = this.maintenant();
        }
        return;
      }
    }

    // Cas 2 : un tour ouvert alors que le bloc courant n'est dans aucun
    // circuit. Ne se produit pas en jeu ; garde pour qu'aucun etat ne reste
    // sans issue.
    if (this._exercice_precedent_entrelace !== null) {
      this.index_exercice = this._exercice_precedent_entrelace.index;
      this.serie_actuelle = this._exercice_precedent_entrelace.serie + 1;
      this._exercice_precedent_entrelace = null;

      if (this.serie_actuelle > this.nombre_series) {
        this._finir_bloc();
      } else {
        this.phase = "recuperation_serie";
        this.debut_repos = this.maintenant();
      }
      return;
    }

    // Il reste des series (cas normal, pas entrelace).
    if (this.serie_actuelle < this.nombre_series) {
      this.serie_actuelle += 1;
      this.phase = "recuperation_serie";
      this.debut_repos = this.maintenant();
      return;
    }

    // Toutes les series de cet exercice sont terminees.
    this._finir_bloc();
  }

  /**
   * Toutes les series du bloc courant sont faites : repos, ou bloc suivant.
   *
   * **Pas de repos apres le dernier bloc** : il ne prepare a rien, et l'on
   * attendait la fin d'un compte a rebours pour voir l'ecran de fin. Le bloc
   * suivant se lit par `prochain_bloc`, qui saute le partenaire d'un superset
   * — sans quoi la derniere paire de la seance garderait son repos.
   */
  _finir_bloc() {
    if (this.bloc_actuel.repos_apres > 0 && this.prochain_bloc() !== null) {
      this.phase = "repos_exercice";
      this.debut_repos = this.maintenant();
    } else {
      this.passer_exercice_suivant();
    }
  }

  commencer_exercice() {
    // Ne pas ouvrir un exercice qui n'existe pas : la seance terminee, l'index
    // depasse le dernier bloc, et poser « exercice » y laissait un etat
    // impossible — phase active, `bloc_actuel` nul — dans lequel
    // `terminer_serie` levait. La regle vit ici et non dans l'appelant.
    if (this.bloc_actuel === null) return;
    this.phase = "exercice";
  }

  passer_exercice_suivant() {
    this.index_exercice = this._obtenir_vrai_prochain_exercice_index();

    if (this.index_exercice >= this.exercices.length) {
      this.phase = "termine";
      return;
    }

    this.serie_actuelle = 1;
    this.phase = "exercice";
    this.debut_repos = null;
    this._exercice_precedent_entrelace = null;
  }

  update() {
    if (this.phase === "recuperation_serie") {
      if (this.temps_restant <= 0) {
        this.phase = "exercice";
        this.debut_repos = null;
      }
    } else if (this.phase === "repos_exercice") {
      if (this.temps_restant <= 0) {
        this.passer_exercice_suivant();
      }
    }
  }
}

/**
 * Construit un circuit depuis la definition JSON d'une seance.
 *
 * Ne connait le catalogue que par la table qu'on lui passe : le `Circuit` ne
 * resout pas lui-meme les noms d'exercice.
 */
export function construire_circuit(blocs, catalogue) {
  if (!blocs || !blocs.length) throw new Error("Au moins un exercice est requis");

  for (const bloc of blocs) {
    if (!(bloc.exercice in catalogue)) {
      throw new Error(`Exercice inconnu : ${bloc.exercice}`);
    }
    if (!MODES_CONNUS.includes(bloc.mode)) {
      throw new Error(`Mode inconnu : ${bloc.mode}`);
    }
    if (
      MODES_AVEC_DETECTION_OBLIGATOIRE.includes(bloc.mode) &&
      catalogue[bloc.exercice].detection === null
    ) {
      throw new Error(`${bloc.exercice} n'analyse pas la pose`);
    }
    // Une cible nulle dans l'unite que le mode joue produirait une serie qui
    // s'acheve a la premiere image : la seance entiere defile en une fraction
    // de seconde et s'annonce terminee sans que rien n'ait ete fait.
    if (cible_du_bloc(bloc) <= 0) {
      throw new Error(`${bloc.exercice} n'a pas de cible`);
    }
  }

  return new Circuit(
    blocs.map(
      (bloc) =>
        new BlocExercice({
          exercice: catalogue[bloc.exercice],
          poids: bloc.poids ?? 0,
          mode: bloc.mode ?? MODE_REPETITIONS,
          nombre_series: bloc.series ?? 1,
          repetitions_par_serie: bloc.repetitions ?? 0,
          duree: bloc.duree ?? 0,
          repos_entre_series: bloc.repos_entre_series ?? 0,
          repos_apres: bloc.repos_apres ?? 0,
          commentaire: bloc.commentaire ?? "",
          entrelace_avec: bloc.entrelace_avec ?? null,
          cible_manuelle: bloc.cible_manuelle ?? false,
        })
    )
  );
}
