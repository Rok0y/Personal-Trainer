// Jumeau de session/circuit.py — la machine a etats d'une seance.
//
// Meme convention que landmarks.js, compteur.js et detections.js : les noms
// sont ceux du Python, en snake_case, contrairement a l'usage JavaScript.
// C'est ce qui permet de lire les deux implementations cote a cote et au
// harnais d'apparier les methodes par leur nom, sans table de correspondance
// qui pourrait deriver.
//
// Le Python fait autorite : un ecart est un bug d'ici jusqu'a preuve du
// contraire. `python -m scripts.generer_scenarios` joue des suites de
// commandes horodatees sur les vraies seances et releve l'etat apres chaque
// pas ; `node scripts/comparer_seances.mjs` rejoue les memes pas ici et diffe.
//
// Ce qui n'est PAS porte, volontairement : `exporter_configuration`,
// `exporter_resultats`, `objectifs_reussis`, `appliquer_progression` et la
// cloture des tests de calibration. Toutes appellent `progression/`, qui
// reste en Python jusqu'a l'etape 4 du portage. Les methodes correspondantes
// sont absentes plutot que vides — une methode qui ment est pire qu'une
// methode qui manque.

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
  }

  fiche() {
    return {
      nom: this.nom,
      description: this.description,
      mise_en_place: [...this.mise_en_place],
      instructions: [...this.instructions],
      erreurs_frequentes: [...this.erreurs_frequentes],
      variante_facile: this.variante_facile,
      variante_difficile: this.variante_difficile,
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

    // Serie de calibration : cet exercice n'a encore aucune donnee, donc la
    // seance demande un maximum au lieu d'une cible.
    this.test_max = false;

    this.temps_maintien = 0;
    this.temps_restant_precedent = null;
  }
}

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
    // Secondes et non millisecondes, comme `time.monotonic()` : les durees des
    // blocs (`repos_apres`, `duree`) sont en secondes des deux cotes.
    this.maintenant = () => performance.now() / 1000;
    this.debut = this.maintenant();

    this.resultats_series = [];
    this.paires_entrelacees = this._detecter_paires_entrelacees();
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
    const paires = new Map();
    this.exercices.forEach((bloc, index) => {
      if (bloc.entrelace_avec) {
        const partenaire = this._trouver_exercice_par_nom(bloc.entrelace_avec, index);
        if (partenaire !== null) paires.set(index, partenaire);
      }
    });
    return paires;
  }

  /**
   * Indice du premier exercice portant ce nom apres `depuis`.
   *
   * La recherche est strictement vers l'avant : un partenaire situe plus haut
   * dans la seance (ou l'exercice lui-meme) creerait une boucle infinie.
   */
  _trouver_exercice_par_nom(nom_exercice, depuis = -1) {
    for (let index = depuis + 1; index < this.exercices.length; index++) {
      if (this.exercices[index].exercice.nom === nom_exercice) return index;
    }
    return null;
  }

  _est_entrelace(index) {
    return this.paires_entrelacees.has(index);
  }

  _obtenir_partenaire_entrelace(index) {
    return this.paires_entrelacees.has(index)
      ? this.paires_entrelacees.get(index)
      : null;
  }

  /** Indice du vrai prochain exercice, en sautant le partenaire entrelace. */
  _obtenir_vrai_prochain_exercice_index() {
    let prochain_index = this.index_exercice + 1;
    const partenaire_direct = this._obtenir_partenaire_entrelace(this.index_exercice);
    if (partenaire_direct !== null) {
      prochain_index = Math.max(prochain_index, partenaire_direct + 1);
    }
    return prochain_index;
  }

  get bloc_actuel() {
    if (this.index_exercice >= this.exercices.length) return null;
    return this.exercices[this.index_exercice];
  }

  // Methode et non accesseur, comme en Python — la seule de cette famille de
  // lectures a l'etre.
  prochain_bloc() {
    const prochain_index = this._obtenir_vrai_prochain_exercice_index();
    if (prochain_index >= this.exercices.length) return null;
    return this.exercices[prochain_index];
  }

  get poids() {
    // Se protege de `bloc_actuel` nul comme ses voisines : `main.py` lit ce
    // champ a chaque image, et une exception y gele le flux video.
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
    // `int()` en Python tronque vers zero, ce que fait `Math.trunc` et **pas**
    // `Math.floor` : les deux ne different que pour un negatif, qu'une horloge
    // qui recule produirait.
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
        precedent.serie === this.serie_actuelle
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
      // `delattr` cote Python : l'attribut doit disparaitre, pas valoir
      // undefined — `hasattr` et l'operateur `in` doivent repondre faux.
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
  oublier_resultat_serie(index_exercice, serie) {
    this.resultats_series = this.resultats_series.filter(
      (resultat) =>
        !(resultat.index_exercice === index_exercice && resultat.serie === serie)
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
    this.oublier_resultat_serie(repere.index_exercice, repere.serie);

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
      entrelace:
        this._exercice_precedent_entrelace !== null
          ? { ...this._exercice_precedent_entrelace }
          : null,
    };

    // Cas 1 : l'exercice courant a un partenaire entrelace.
    if (this._est_entrelace(this.index_exercice)) {
      const partenaire_index = this._obtenir_partenaire_entrelace(this.index_exercice);

      if (this._exercice_precedent_entrelace === null) {
        // Le partenaire n'a pas encore ete visite pour cette serie : on y va
        // en gardant le meme `serie_actuelle`, pour que l'affichage reste
        // coherent pendant l'aller-retour.
        this._exercice_precedent_entrelace = {
          index: this.index_exercice,
          serie: this.serie_actuelle,
        };
        this.index_exercice = partenaire_index;
        this.phase = "recuperation_serie";
        this.debut_repos = this.maintenant();
        return;
      }

      // On revient du partenaire : retour a l'exercice d'origine, serie
      // suivante.
      this.index_exercice = this._exercice_precedent_entrelace.index;
      this.serie_actuelle = this._exercice_precedent_entrelace.serie + 1;
      this._exercice_precedent_entrelace = null;

      if (this.serie_actuelle > this.nombre_series) {
        if (this.bloc_actuel.repos_apres > 0) {
          this.phase = "repos_exercice";
          this.debut_repos = this.maintenant();
        } else {
          this.passer_exercice_suivant();
        }
      } else {
        this.phase = "recuperation_serie";
        this.debut_repos = this.maintenant();
      }
      return;
    }

    // Cas 2 : on revient du partenaire alors que c'est lui l'exercice courant.
    if (this._exercice_precedent_entrelace !== null) {
      this.index_exercice = this._exercice_precedent_entrelace.index;
      this.serie_actuelle = this._exercice_precedent_entrelace.serie + 1;
      this._exercice_precedent_entrelace = null;

      if (this.serie_actuelle > this.nombre_series) {
        if (this.bloc_actuel.repos_apres > 0) {
          this.phase = "repos_exercice";
          this.debut_repos = this.maintenant();
        } else {
          this.passer_exercice_suivant();
        }
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
    if (this.bloc_actuel.repos_apres > 0) {
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
 * Construit un circuit depuis la meme definition JSON que le Python.
 *
 * Jumeau partiel de `session.seances.construire_circuit` : il valide les
 * memes choses, mais ne connait le catalogue que par la table qu'on lui
 * passe — c'est `preparer_demo` qui l'exporte, et la demo qui le charge.
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
