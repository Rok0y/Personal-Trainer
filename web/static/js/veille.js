// Empecher l'appareil de s'endormir pendant une seance.
//
// Une seance, c'est plusieurs minutes sans toucher l'ecran : l'iPad l'eteint,
// la camera s'arrete, le comptage aussi. Deux mecanismes sont necessaires, et
// le second n'est pas une precaution theorique — il a fallu une seance reelle
// pour s'apercevoir que le premier ne suffisait pas.
//
// **1. Le `Screen Wake Lock`**, quand il existe. Trois choses le font echouer
// la ou on l'attendrait :
//
// - il est **libere des que la page devient invisible** — onglet en arriere
//   plan, notification qui prend le dessus — et **ne revient pas tout seul**.
//   D'ou la reprise sur `visibilitychange` ;
// - Safari ne l'a que depuis iOS 16.4, et le **mode economie d'energie** le
//   refuse meme sur les versions qui le connaissent ;
// - il se demande pendant que la page est visible, et le demander **au plus
//   pres du geste de l'utilisateur** evite tout refus lie a l'activation. Une
//   chaine d'`await` — preparer l'audio, ouvrir la camera, charger le modele —
//   peut prendre plusieurs secondes, et c'est exactement ce qui separait le
//   clic de la demande.
//
// **2. Une video qui joue**, en repli. iOS garde l'ecran allume tant qu'une
// video est lue, et c'est la methode qui marchait bien avant l'existence de
// l'API. On reutilise **le flux de la camera**, qui tourne deja : aucun
// fichier a embarquer, aucune seconde image a decoder. Le point qui compte est
// que l'element doit etre **attache au document et rendu** — une video
// detachee, ou masquee par `display:none`, ne compte pas comme lue. D'ou un
// carre d'un pixel, quasi transparent, plutot qu'un element cache.
//
// **L'etat est lisible** (`raison`), parce qu'un echec silencieux se paie en
// seance : l'ecran s'eteint, on ne sait pas pourquoi, et on ne peut rien
// corriger. L'application en fait un avertissement discret.

export class VerrouEcran {
  constructor() {
    this.voulu = false;
    this.verrou = null;
    this.video = null;
    //: Pourquoi l'ecran n'est peut-etre pas tenu. Null quand tout va bien.
    this.raison = null;

    document.addEventListener("visibilitychange", () => {
      if (this.voulu && document.visibilityState === "visible") this._demander();
    });
  }

  get disponible() {
    return typeof navigator !== "undefined" && "wakeLock" in navigator;
  }

  /** L'ecran est-il tenu par au moins un des deux mecanismes ? */
  get tenu() {
    return Boolean(this.verrou) || Boolean(this.video && !this.video.paused);
  }

  async _demander() {
    if (!this.disponible) {
      this.raison = "Ce navigateur ne sait pas empêcher la mise en veille.";
      return;
    }
    if (this.verrou) return;
    try {
      this.verrou = await navigator.wakeLock.request("screen");
      this.raison = null;
      this.verrou.addEventListener("release", () => {
        this.verrou = null;
      });
    } catch (erreur) {
      this.verrou = null;
      // **Le navigateur ne dit pas pourquoi**, et il y a plusieurs causes
      // possibles : page non visible, activation de l'utilisateur expiree,
      // mode economie d'energie. Mesure : un appel hors geste utilisateur
      // rend `NotAllowedError`, exactement comme un refus systeme. On nomme
      // donc le fait, pas une cause qu'on ne connait pas — le repli video
      // prend le relais dans tous les cas.
      this.raison = `Verrou d'écran refusé (${erreur?.name ?? "erreur"}).`;
    }
  }

  /**
   * Le repli video, a partir d'un flux deja ouvert.
   *
   * Appele avec le flux de la camera : il joue deja, on ne fait que l'afficher
   * quelque part ou le navigateur le compte comme une lecture en cours.
   */
  _jouer_video(flux) {
    if (!flux || this.video) return;
    const video = document.createElement("video");
    video.playsInline = true;
    video.muted = true;
    video.autoplay = true;
    video.srcObject = flux;
    // Attache et rendu, mais invisible a l'oeil : `display:none` ou
    // `visibility:hidden` mettrait la lecture en pause, ce qui annulerait
    // tout l'interet.
    video.setAttribute(
      "style",
      "position:fixed;bottom:0;right:0;width:1px;height:1px;opacity:.01;" +
        "pointer-events:none;z-index:-1"
    );
    document.body.appendChild(video);
    video.play().catch(() => {});
    this.video = video;
  }

  /**
   * Garder l'ecran allume.
   *
   * A appeler **au plus pres du clic**, avant toute attente : l'activation de
   * l'utilisateur ne dure pas. `flux` est facultatif et arme le repli video.
   */
  async tenir(flux = null) {
    this.voulu = true;
    await this._demander();
    this._jouer_video(flux);
    return this.tenu;
  }

  /** Rendre la main : l'appareil peut se rendormir normalement. */
  async relacher() {
    this.voulu = false;
    this.raison = null;
    const verrou = this.verrou;
    this.verrou = null;
    this.video?.remove();
    this.video = null;
    try {
      await verrou?.release();
    } catch {
      /* deja relache par le systeme */
    }
  }
}
