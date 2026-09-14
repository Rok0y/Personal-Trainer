// La camera et le detecteur de pose, partages par la demo et l'application.
//
// Ce module existe parce que les regles qu'il porte sont exactement celles
// que `CLAUDE.md` interdit de dupliquer : le suivi temporel du sujet, la
// serialisation de la fabrication du detecteur, et la camera ouverte une fois
// par session. Deux copies de ces trois regles divergeraient, et la divergence
// ne se verrait qu'a l'usage, sur l'appareil de quelqu'un d'autre.
//
// Ce qui reste hors d'ici : tout ce qui touche au DOM d'une page — l'affichage
// de la resolution, le selecteur de camera, le panneau de reglages. Chaque
// page a le sien, et les melanger rendrait le module inutilisable par l'autre.

import {
  PoseLandmarker,
  FilesetResolver,
  DrawingUtils,
} from "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";

export const VERSION_WASM =
  "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm";
export const MODELE =
  "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_full/float16/1/pose_landmarker_full.task";

// Chercher plusieurs personnes coute cher, et c'est mesure : sur le meme iPad
// et le meme modele, 36 images/s et un squelette stable a une pose, contre 24
// et un squelette qui saute a quatre. Une seule pose est donc l'ordinaire ;
// plusieurs garde son sens en salle de sport, ou le modele pourrait se fixer
// sur un passant.
export const POSES_SEUL = 1;
export const POSES_ENTOURE = 4;

// Deplacement maximal du centre d'un sujet entre deux images, en fraction de
// l'image. Au-dela, on considere le sujet perdu et on repart sur la plus
// grande silhouette.
export const SAUT_MAX = 0.25;

function repere(pose) {
  const xs = pose.map((p) => p.x);
  const ys = pose.map((p) => p.y);
  const [x0, x1] = [Math.min(...xs), Math.max(...xs)];
  const [y0, y1] = [Math.min(...ys), Math.max(...ys)];
  return { x: (x0 + x1) / 2, y: (y0 + y1) / 2, surface: (x1 - x0) * (y1 - y0) };
}

/**
 * Le detecteur, la camera et le sujet suivi.
 *
 * Une instance par page. L'etat est regroupe ici plutot qu'en variables de
 * module pour la meme raison que `EtatSeance` : deux pages ouvertes ne
 * doivent pas se partager un detecteur.
 */
export class Camera {
  constructor(poses = POSES_SEUL) {
    this.flux = null;
    this.video = null;
    this.miroir = true;
    this.poses_voulues = poses;

    this._detecteur = null;
    this._fileset = null;
    this._poses_du_detecteur = null;
    // Les appels s'enchainent au lieu de se chevaucher : le prechargement et
    // un clic rapide sur « Demarrer » fabriqueraient sinon deux detecteurs,
    // dont un jamais libere.
    this._preparation = Promise.resolve();

    this._sujet = null;
  }

  // ----- detecteur -----

  /**
   * Fabrique le detecteur, ou rend celui qui existe deja.
   *
   * Le modele pese une dizaine de mega-octets et met une quinzaine de
   * secondes a arriver sur une connexion moyenne. L'appeler des l'ouverture
   * d'une fiche recouvre cette attente par le temps de lecture des consignes ;
   * pas plus tot, car allouer un detecteur pour quelqu'un qui parcourt une
   * liste coute de la memoire sur les appareils qui en manquent le plus.
   */
  preparer() {
    this._preparation = this._preparation
      .catch(() => {})
      .then(async () => {
        if (!this._fileset) {
          this._fileset = await FilesetResolver.forVisionTasks(VERSION_WASM);
        }
        // Lu avant l'attente : le reglage peut basculer pendant la
        // fabrication, et c'est ce qui a ete construit qu'on enregistre.
        const voulues = this.poses_voulues;
        if (this._detecteur && this._poses_du_detecteur === voulues) {
          return this._detecteur;
        }
        const detecteur = await this._creer(voulues);
        this._detecteur?.close();
        this._detecteur = detecteur;
        this._poses_du_detecteur = voulues;
        return detecteur;
      });
    return this._preparation;
  }

  async _creer(poses) {
    const options = {
      baseOptions: { modelAssetPath: MODELE, delegate: "GPU" },
      runningMode: "VIDEO",
      numPoses: poses,
    };
    try {
      return await PoseLandmarker.createFromOptions(this._fileset, options);
    } catch {
      // Sans GPU accessible, le CPU tient encore la cadence sur un appareil
      // recent — plus lentement, mais c'est mieux que rien du tout.
      options.baseOptions.delegate = "CPU";
      return await PoseLandmarker.createFromOptions(this._fileset, options);
    }
  }

  /** Les poses detectees sur l'image courante, ou un tableau vide. */
  detecter(instant) {
    if (!this._detecteur || !this.video) return [];
    const resultat = this._detecteur.detectForVideo(this.video, instant);
    return resultat?.landmarks ?? [];
  }

  // ----- suivi du sujet -----

  /**
   * La pose de la personne suivie, parmi celles detectees.
   *
   * Suit **la meme personne d'une image a l'autre** — la plus proche du
   * dernier centre retenu — et ne reprend la plus grande qu'au premier choix,
   * ou apres un saut de plus de SAUT_MAX. Reprendre la plus grande a chaque
   * image semblait sur et ne l'etait pas : deux candidats de tailles voisines
   * echangent leur rang d'une image a l'autre — mesure a 22 changements de
   * sujet sur 200 images —, le squelette saute d'un corps a l'autre, et un
   * seul aller-retour suffit a compter une repetition qui n'a pas eu lieu.
   */
  choisir(poses) {
    if (!poses?.length) return null;
    const reperes = poses.map(repere);

    let choisi = 0;
    for (let i = 1; i < reperes.length; i++) {
      if (reperes[i].surface > reperes[choisi].surface) choisi = i;
    }

    if (this._sujet) {
      let plus_proche = null;
      let distance = Infinity;
      for (let i = 0; i < reperes.length; i++) {
        const d = Math.hypot(reperes[i].x - this._sujet.x, reperes[i].y - this._sujet.y);
        if (d < distance) {
          distance = d;
          plus_proche = i;
        }
      }
      if (distance <= SAUT_MAX) choisi = plus_proche;
    }

    this._sujet = reperes[choisi];
    return poses[choisi];
  }

  oublier_sujet() {
    this._sujet = null;
  }

  // ----- cycle de vie de la camera -----

  /**
   * Ouvre la camera. **Une fois par session, pas une fois par exercice** :
   * chaque `getUserMedia` est une demande d'autorisation potentielle, et
   * Safari a redemande l'acces trois fois a un testeur au cours d'une session
   * de 23 exercices.
   */
  async ouvrir(deviceId) {
    // Changer de camera est le seul cas ou l'on ferme vraiment la precedente.
    this.liberer();

    // Resolution demandee en 4:3 plutot qu'en 16:9 : sur un telephone pose
    // debout, c'est la hauteur qui manque pour cadrer un corps entier, et le
    // 16:9 rogne precisement le haut et le bas.
    const contrainte = deviceId
      ? { deviceId: { exact: deviceId } }
      : { facingMode: "user" };
    contrainte.width = { ideal: 1920 };
    contrainte.height = { ideal: 1440 };

    this.flux = await navigator.mediaDevices.getUserMedia({
      video: contrainte,
      audio: false,
    });

    if (!this.video) {
      this.video = document.createElement("video");
      this.video.playsInline = true;
      this.video.muted = true;
    }
    this.video.srcObject = this.flux;
    await this.video.play();

    const reglages = this.flux.getVideoTracks()[0].getSettings();
    // Le miroir est une convention d'affichage du selfie ; sur une camera
    // arriere il desoriente. Il ne touche que le dessin, jamais l'image
    // envoyee au modele — la detection y est donc insensible.
    this.miroir = reglages.facingMode !== "environment";
    return reglages;
  }

  vivante() {
    return this.flux?.getVideoTracks()[0]?.readyState === "live";
  }

  /**
   * Coupe les images sans rendre le peripherique.
   *
   * Les pistes sont **desactivees** et non arretees : plus rien ne circule,
   * donc rien n'est analyse ni affiche, mais l'autorisation reste acquise. Le
   * prix est que le voyant de la camera reste allume pendant les temps morts,
   * ce que l'ecran de fin doit annoncer plutot que de le laisser subir.
   */
  suspendre() {
    for (const piste of this.flux?.getTracks() ?? []) piste.enabled = false;
  }

  async reprendre() {
    for (const piste of this.flux?.getTracks() ?? []) piste.enabled = true;
    await this.video?.play().catch(() => {});
  }

  /** Rend vraiment le peripherique. Deux cas seulement : changer de camera, et quitter la page. */
  liberer() {
    for (const piste of this.flux?.getTracks() ?? []) piste.stop();
    this.flux = null;
  }

  // **La lutte contre la veille ne vit plus ici.** Cette classe en portait un
  // second exemplaire — un verrou demande une fois, jamais repris — et deux
  // verrous concurrents sur la meme page sont surtout deux facons de croire
  // qu'on tient l'ecran. Tout est dans `veille.js`, qui gere aussi le repli
  // video, et c'est la page qui le pilote : elle seule sait quand une seance
  // commence et se termine, la ou la camera ne fait que s'allumer et
  // s'eteindre entre deux exercices.
}

/**
 * Dessine le squelette d'une pose sur un contexte 2D.
 *
 * Ici et pas dans la page : MediaPipe est deja importe par ce module, et le
 * refaire ailleurs ajoutait une **attente reseau bloquante au demarrage
 * d'une seance** — un CDN lent, et plus personne ne pouvait s'entrainer.
 * Aucune page n'a besoin de connaitre MediaPipe.
 */
export function dessiner_squelette(ctx, pose) {
  const utils = new DrawingUtils(ctx);
  utils.drawConnectors(pose, PoseLandmarker.POSE_CONNECTIONS, {
    color: "#4b9bff",
    lineWidth: 4,
  });
  utils.drawLandmarks(pose, { color: "#e8eef6", radius: 3 });
}
