// La video d'un mouvement : sa boucle redessinee, dans `videos/`.
//
// Meme regle que les sons : le nom du fichier se **derive** du nom du
// mouvement, et une video absente est une absence d'illustration, jamais une
// panne. Pas de liste a tenir a jour : on tourne par lots, et chaque video
// deposee dans `videos/` apparait d'elle-meme partout ou le mouvement se lit.
// `video/illustrer.py` ecrit ses fichiers sous le nom que rend
// `fichier_video`, qu'il appelle par node : la regle n'existe qu'ici.

import { normaliser_nom } from "./annonces.js";

/** Le fichier de la video d'un mouvement : `curl_biceps_droit.mp4`. */
export function fichier_video(nom) {
  return `${normaliser_nom(nom)}.mp4`;
}

/**
 * L'adresse de cette video, relative a **ce module** et non a la page : juste
 * depuis `app/`, `dev/` et `demo/` sans que chacune connaisse le chemin.
 */
export function adresse_video(nom) {
  return new URL(`../videos/${fichier_video(nom)}`, import.meta.url).href;
}

/**
 * Met la video de `nom` dans `cadre` (un element qui contient un `<video>`).
 *
 * Le cadre reste cache tant que la video n'a pas charge, et le reste si elle
 * n'existe pas : un mouvement sans video n'affiche pas de rectangle vide.
 * `nom` null vide le cadre. Un meme nom ne recharge rien — l'appelant peut
 * l'appeler a chaque dessin. `apres_chargement` est appele quand la video est
 * prete : c'est la que l'appelant decide de la lire (`jouer_si_visible`), et
 * de montrer ce qui l'entoure.
 */
export function montrer_video(cadre, nom, apres_chargement = null) {
  const video = cadre?.querySelector("video");
  if (!video) return;
  const adresse = nom ? adresse_video(nom) : "";
  if (video.dataset.adresse === adresse) return;
  video.dataset.adresse = adresse;
  cadre.hidden = true;
  if (!adresse) {
    video.removeAttribute("src");
    video.load();
    return;
  }
  video.muted = true;
  video.loop = true;
  video.playsInline = true;
  // Un chargement plus ancien peut finir apres un plus recent : seul celui de
  // l'adresse courante a le droit de montrer le cadre.
  video.onloadeddata = () => {
    if (video.dataset.adresse !== adresse) return;
    cadre.hidden = false;
    apres_chargement?.(video);
  };
  video.onerror = () => {
    if (video.dataset.adresse === adresse) cadre.hidden = true;
  };
  video.src = adresse;
}

/**
 * Lit ou suspend une video selon qu'on la voit. Une video repliee ne decode
 * pas : sur l'iPad, le decodage disputerait sa puissance a la detection de
 * pose pendant l'effort. `play()` peut etre refuse (economie d'energie) : on
 * se tait, la video reste sur sa premiere image.
 */
export function jouer_si_visible(video, visible) {
  if (!video) return;
  if (visible) video.play()?.catch?.(() => {});
  else video.pause();
}
