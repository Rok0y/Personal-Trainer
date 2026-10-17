// Rendre commune une creation perso : d'une sauvegarde de l'application vers
// le brouillon de l'outil maitre (`dev/createur.html`).
//
// Un profil cree une seance ou un programme sur l'iPad ; l'outil maitre lit
// son export (`historique.importer`) et en fait une version commune, a coller
// dans `seances.json` / `programmes.json`. Le brouillon est `{seances,
// programmes}`, de la forme des deux fichiers. Les fonctions sont pures :
// elles rendent un nouveau brouillon, et la page decide de le garder.
//
// Deux regles :
// - **Rien de ce qui appartient a un profil ne devient commun** :
//   `cible_manuelle` (des identifiants de profil) est retiree des blocs.
// - **Une collision est nommee, jamais ecrasee en silence** : une seance ou
//   une cle commune deja la n'est remplacee que sur demande (`remplacer`).
//   C'est le cas ordinaire d'une copie perso qui garde le nom de la commune
//   qu'elle modifie : la promouvoir, c'est publier la modification.

import { PREFIXE_PROGRAMME_PERSO, programmes_perso, seances_perso } from "./historique.js";

/** Les blocs d'une seance perso, debarrasses de ce qui appartient au profil. */
export function blocs_communs(blocs) {
  return (blocs ?? []).map((bloc) => {
    const { cible_manuelle, ...commun } = bloc;
    return structuredClone(commun);
  });
}

/**
 * Une cle de programme commun tiree de son nom : minuscules, sans accent,
 * mots separes de tirets (`full-body-sans-materiel`). Jamais le prefixe des
 * cles perso, que `verifier_donnees` refuserait.
 */
export function cle_depuis_nom(nom) {
  const cle = (nom ?? "")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "programme";
  return cle.startsWith(PREFIXE_PROGRAMME_PERSO) ? `programme-${cle}` : cle;
}

/** Leve si un nom est deja pris et qu'on n'a pas demande a le remplacer. */
function _collision(pris, nom, remplacer, quoi) {
  if (pris && !remplacer) {
    throw new Error(`${quoi} « ${nom} » existe déjà : coche « remplacer » pour la publier par-dessus.`);
  }
}

/**
 * Rend commune une seance perso du profil : `{brouillon, nom}`.
 *
 * `nom` (par defaut celui de la seance perso) est le nom commun. Renommer
 * ici n'est pas anodin : l'historique et les programmes relisent les seances
 * par nom.
 */
export function promouvoir_seance(brouillon, profil, nom_perso, { nom = nom_perso, remplacer = false } = {}) {
  const blocs = seances_perso(profil)[nom_perso];
  if (!blocs) throw new Error(`« ${nom_perso} » n'est pas une séance personnalisée de ce profil.`);
  const propre = (nom ?? "").trim();
  if (!propre) throw new Error("Une séance a besoin d'un nom.");
  _collision(propre in (brouillon.seances ?? {}), propre, remplacer, "La séance commune");
  return {
    brouillon: {
      ...brouillon,
      seances: { ...brouillon.seances, [propre]: blocs_communs(blocs) },
    },
    nom: propre,
  };
}

/**
 * Rend commun un programme perso du profil, et les seances perso qu'il fait
 * jouer : `{brouillon, cle, seances}` (`seances` : les noms promus avec lui).
 *
 * Une seance liee qui n'est pas perso est deja commune (ou absente : le
 * controle du programme le dira). Une seance perso liee **du meme nom**
 * qu'une commune est une copie modifiee : elle n'est promue que si
 * `remplacer` le demande, faute de quoi le programme commun ferait jouer la
 * version commune, sans le dire — d'ou le refus.
 */
export function promouvoir_programme(brouillon, profil, cle_perso, { cle = null, remplacer = false } = {}) {
  const programme = programmes_perso(profil)[cle_perso];
  if (!programme) throw new Error(`« ${cle_perso} » n'est pas un programme personnalisé de ce profil.`);
  const retenue = cle || cle_depuis_nom(programme.nom);
  _collision(retenue in (brouillon.programmes ?? {}), retenue, remplacer, "Le programme commun");

  const perso = seances_perso(profil);
  const seances = { ...brouillon.seances };
  const promues = [];
  for (const nom of new Set(Object.values(programme.seances ?? {}))) {
    if (!(nom in perso)) continue;
    _collision(nom in seances, nom, remplacer, "La séance commune");
    seances[nom] = blocs_communs(perso[nom]);
    promues.push(nom);
  }
  return {
    brouillon: {
      ...brouillon,
      seances,
      programmes: { ...brouillon.programmes, [retenue]: structuredClone(programme) },
    },
    cle: retenue,
    seances: promues,
  };
}
