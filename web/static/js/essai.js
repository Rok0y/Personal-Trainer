// La version d'essai : le site de la branche `test`, publie **dans** celui de
// `main`, sous `app/essai/` (`.github/workflows/demo.yml`).
//
// Pourquoi la, et pas a cote : l'application se joue en web app sur l'iPad,
// ajoutee a l'ecran d'accueil. Une web app a son propre stockage, separe de
// Safari — la base d'entrainement vit dedans. Pour essayer avec sa vraie base,
// la version d'essai doit donc s'ouvrir **dans** la web app, et rester dans
// sa portee : sans manifeste, iOS la deduit du dossier de depart, `app/`.
// Une adresse hors de ce dossier s'ouvrirait dans Safari, devant une base
// vide.
//
// Les adresses sont relatives a la page courante : rien ici ne connait le nom
// du depot ni l'hote.

export const DOSSIER_ESSAI = "essai";

const MARQUE = `/app/${DOSSIER_ESSAI}/`;

/** La page est-elle celle de la version d'essai ? */
export function est_version_essai(href) {
  return new URL(href).pathname.includes(MARQUE);
}

/** L'application d'essai, vue depuis l'application principale. */
export function adresse_version_essai(href) {
  return new URL(`${DOSSIER_ESSAI}/app/`, new URL("./", href)).href;
}

/** L'application principale, vue depuis la version d'essai. */
export function adresse_version_principale(href) {
  const adresse = new URL(href);
  const debut = adresse.pathname.indexOf(MARQUE);
  return adresse.origin + adresse.pathname.slice(0, debut + "/app/".length);
}
