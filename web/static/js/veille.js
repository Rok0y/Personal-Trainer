// Empecher l'appareil de s'endormir pendant une seance.
//
// Une seance, c'est plusieurs minutes sans toucher l'ecran : l'iPad l'eteint,
// la camera s'arrete, le comptage aussi. Le `Screen Wake Lock` l'en empeche.
//
// **Le point qui fait toute la difference est la reprise.** Un verrou est
// libere par le systeme des que la page devient invisible — onglet en arriere
// plan, application quittee, ecran verrouille a la main, notification qui prend
// le dessus — et il **ne revient pas tout seul** quand on revient. Le demander
// une fois au demarrage, comme le faisait la demo, protege donc la premiere
// interruption pres : c'est precisement ce qu'on a observe, un iPad qui
// s'endort en pleine seance apres un coup d'oeil ailleurs.
//
// D'ou un objet qui retient ce qu'on lui a demande (`voulu`) et redemande le
// verrou a chaque retour au premier plan, tant qu'on ne l'a pas relache
// explicitement.
//
// Deux limites acceptees. L'API n'existe pas partout — Safari ne l'a que depuis
// iOS 16.4 —, et le navigateur peut refuser sans raison. Les deux cas se
// traitent pareil : l'ecran s'eteindra peut-etre, c'est genant, ce n'est pas
// bloquant, et surtout ca ne doit jamais empecher la seance de se jouer.

export class VerrouEcran {
  constructor() {
    this.voulu = false;
    this.verrou = null;

    // `visibilitychange` et non `focus` : c'est l'evenement qui accompagne
    // reellement la liberation du verrou par le systeme.
    document.addEventListener("visibilitychange", () => {
      if (this.voulu && document.visibilityState === "visible") this._demander();
    });
  }

  /** Le navigateur sait-il faire ? */
  get disponible() {
    return typeof navigator !== "undefined" && "wakeLock" in navigator;
  }

  async _demander() {
    if (!this.disponible || this.verrou) return;
    try {
      this.verrou = await navigator.wakeLock.request("screen");
      // Le systeme peut relacher de son cote : on oublie la reference, sans
      // quoi la reprise croirait le verrou encore actif et ne redemanderait
      // rien.
      this.verrou.addEventListener("release", () => {
        this.verrou = null;
      });
    } catch {
      this.verrou = null;
    }
  }

  /** Garder l'ecran allume, et le redemander a chaque retour au premier plan. */
  async tenir() {
    this.voulu = true;
    await this._demander();
    return Boolean(this.verrou);
  }

  /** Rendre la main : l'appareil peut se rendormir normalement. */
  async relacher() {
    this.voulu = false;
    const verrou = this.verrou;
    this.verrou = null;
    try {
      await verrou?.release();
    } catch {
      /* deja relache par le systeme */
    }
  }
}
