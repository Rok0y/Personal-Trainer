// Jumeau de progression/calibration.py — de la note d'athlete d'un profil au
// palier de depart de ses exercices.
//
// **Une seule note, de 1 a 10, que la personne se donne a l'accueil.** Elle
// remplace le test au maximum qu'une seance jouait autrefois sur chaque
// exercice inconnu. Elle se traduit par les **bornes de ligue** et non par un
// numero de niveau : le niveau 20 des pompes et celui du curl ne demandent pas
// le meme effort, alors que les bornes ont ete posees exercice par exercice
// pour vouloir dire la meme chose partout.
//
// **Rien n'est ancre** : la note fixe un objectif, jamais un niveau. Trois
// regles, qui ne s'appliquent pas aux memes exercices — un exercice jamais fait
// part de la note effective ; la note monte toute seule quand l'historique
// recent la depasse nettement ; une note relevee a la main pose un plancher
// sur la prochaine seance des exercices deja faits. Le detail est dans la
// docstring du Python.
//
// Les tables (`rangs`, `part_exercices`, `marge`, `exercices_min`, `reperes`)
// sont exportees du Python dans `baremes.json`, cle `note_athlete` : aucune
// valeur n'est ecrite ici.

//: Cible des anciennes series de test : un plafond inatteignable. Plus aucune
//: seance n'en produit ; la constante ne sert qu'a relire l'historique, ou
//: `ressenti.est_serie_de_test` doit continuer de reconnaitre ces lignes.
export const CIBLE_TEST = 999;

export const NOTE_MIN = 1;
export const NOTE_MAX = 10;

/** La note est-elle un entier de 1 a 10 ? */
export function note_valide(note) {
  return Number.isInteger(note) && note >= NOTE_MIN && note <= NOTE_MAX;
}

/**
 * `{declaree, relevee_apres}` d'un profil de `historique.js`.
 *
 * Un profil d'avant la note n'a pas ces champs (il n'existe aucune migration
 * cote JavaScript) : absent vaut null, c'est-a-dire « pas encore demandee ».
 */
export function note_du_profil(profil) {
  return {
    declaree: profil?.note_athlete ?? null,
    relevee_apres: profil?.note_relevee_apres ?? null,
  };
}

export class Calibration {
  constructor(baremes, ligues, niveaux, ressenti, tables) {
    this.baremes = baremes;
    this.ligues = ligues;
    this.niveaux = niveaux;
    this.ressenti = ressenti;
    this.RANGS_PAR_NOTE = tables.rangs;
    this.PART_EXERCICES = tables.part_exercices;
    this.MARGE = tables.marge;
    this.EXERCICES_MIN = tables.exercices_min;
    this.REPERES_NOTE = tables.reperes ?? {};
  }

  /**
   * Niveau du palier sur lequel un exercice jamais fait demarre, pour cette note.
   *
   * null pour un exercice sans bareme. Une note absente ou invalide rend le
   * palier 1 : faute de savoir, on part du bas, qui appartient au debutant.
   */
  niveau_de_depart(nom, note) {
    if (!this.baremes.est_suivi_par_le_moteur(nom)) return null;
    if (!note_valide(note)) return 1;
    const rang = this.RANGS_PAR_NOTE[note - 1];
    if (rang <= 0) return 1;
    const seuils = this.ligues.seuils_exercice(nom);
    if (!seuils || !seuils.length) return 1;
    const borne = seuils[Math.min(rang, seuils.length) - 1];
    return this.baremes.niveau_pour_volume(nom, borne) || 1;
  }

  /**
   * Ce que la derniere seance de chaque exercice a prouve, `{nom: niveau|null}`.
   *
   * Memes lignes que le repere du ressenti : une seance abandonnee ne dit
   * rien, une seance anterieure a un ancrage est perimee — c'est alors
   * l'ancrage qui fait foi. Present avec null : joue sans rien prouver, donc
   * compte dans le total sans atteindre aucune note.
   */
  niveaux_recents(seances, ancrages = {}) {
    const recents = {};
    const tranches = new Set();
    for (const seance of seances) {
      const vus_ici = new Set();
      for (const exercice of this.ressenti._lignes_retenues(seance, ancrages)) {
        const nom = exercice.nom;
        if (!this.baremes.est_suivi_par_le_moteur(nom) || tranches.has(nom)) continue;
        vus_ici.add(nom);
        const niveau = this.niveaux.niveau_prouve_par(exercice);
        if (niveau !== null && (recents[nom] || 0) < niveau) {
          recents[nom] = niveau;
        } else if (!(nom in recents)) {
          recents[nom] = null;
        }
      }
      for (const nom of vus_ici) tranches.add(nom);
    }
    for (const [nom, ancrage] of Object.entries(ancrages)) {
      if (this.baremes.est_suivi_par_le_moteur(nom) && !(nom in recents)) {
        recents[nom] = ancrage.niveau;
      }
    }
    return recents;
  }

  /** La plus haute note que l'historique recent atteint, ou null. */
  note_mesuree(seances, ancrages = {}) {
    const recents = Object.entries(this.niveaux_recents(seances, ancrages));
    if (recents.length < this.EXERCICES_MIN) return null;

    let mesuree = null;
    for (let note = NOTE_MIN; note <= NOTE_MAX; note += 1) {
      const atteints = recents.filter(
        ([nom, niveau]) => niveau !== null && niveau >= this.niveau_de_depart(nom, note),
      ).length;
      if (atteints >= this.PART_EXERCICES * recents.length) mesuree = note;
    }
    return mesuree;
  }

  /**
   * La note qui fixe le depart des exercices jamais faits : la mesuree a partir
   * de `MARGE` crans au-dessus de la declaree, la declaree sinon.
   */
  note_effective(declaree, mesuree) {
    if (!note_valide(declaree)) return mesuree;
    if (mesuree !== null && mesuree >= declaree + this.MARGE) return mesuree;
    return declaree;
  }

  /**
   * Niveau en dessous duquel la prochaine seance de cet exercice ne descend pas,
   * ou null quand aucune hausse n'est en attente.
   */
  niveau_plancher(nom, note, repere) {
    const relevee_apres = note.relevee_apres ?? null;
    if (relevee_apres === null || !note_valide(note.declaree)) return null;
    if (repere && (repere.seance_id || 0) > relevee_apres) return null;
    return this.niveau_de_depart(nom, note.declaree);
  }

  /** Ce qu'un ecran de profil affiche de la note : declaree, mesuree, effective. */
  etat_note(note, seances, ancrages = {}) {
    const mesuree = this.note_mesuree(seances, ancrages);
    return {
      declaree: note.declaree ?? null,
      mesuree,
      effective: this.note_effective(note.declaree ?? null, mesuree),
    };
  }
}

/**
 * L'arrondi de Python : au pair le plus proche sur un demi exact.
 *
 * `Math.round(2.5)` vaut 3, `round(2.5)` en Python vaut 2. La difference ne
 * se voit que sur un demi exact, ce qui arrive des que le produit tombe
 * juste — et alors le resultat diverge. Il servait au test au maximum, et
 * sert toujours a `programmes.js`.
 */
export function arrondi_python(valeur) {
  const bas = Math.floor(valeur);
  const reste = valeur - bas;
  if (reste > 0.5) return bas + 1;
  if (reste < 0.5) return bas;
  return bas % 2 === 0 ? bas : bas + 1;
}
