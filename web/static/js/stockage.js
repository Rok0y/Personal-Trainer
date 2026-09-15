// Persistance de l'historique dans le navigateur.
//
// Ce module ne connait rien a l'historique : il charge et sauve l'objet que
// `historique.js` fabrique, point. C'est ce decoupage qui rend le portage
// verifiable — la logique se compare au Python dans Node, ou IndexedDB
// n'existe pas.
//
// **IndexedDB et non localStorage.** localStorage est synchrone (il bloque
// l'affichage pendant l'ecriture, ce qui se voit a 36 images par seconde),
// plafonne autour de 5 Mo, et ne stocke que du texte. IndexedDB est
// asynchrone, se compte en centaines de mega-octets, et surtout n'est pas la
// premiere chose qu'un navigateur purge quand la place manque. La demo
// continue d'utiliser localStorage pour ce qui est jetable — un exercice
// deja teste, des mesures de fluidite —, pas pour un historique
// d'entrainement.
//
// La base entiere tient dans **un seul enregistrement**. Quelques centaines
// de seances font quelques centaines de kilo-octets, le Python recalcule deja
// tout a la lecture, et une ecriture unique est atomique : une sauvegarde
// interrompue laisse la version precedente intacte plutot qu'une base a
// moitie ecrite.

import { base_vide, exporter, importer } from "./historique.js";

const NOM_BASE = "coach";
const VERSION = 1;
const MAGASIN = "base";
const CLE = "courante";

function promesse(requete) {
  return new Promise((resoudre, rejeter) => {
    requete.onsuccess = () => resoudre(requete.result);
    requete.onerror = () => rejeter(requete.error);
  });
}

export function disponible() {
  return typeof indexedDB !== "undefined" && indexedDB !== null;
}

function ouvrir() {
  return new Promise((resoudre, rejeter) => {
    const requete = indexedDB.open(NOM_BASE, VERSION);
    requete.onupgradeneeded = () => {
      const bdd = requete.result;
      if (!bdd.objectStoreNames.contains(MAGASIN)) bdd.createObjectStore(MAGASIN);
    };
    requete.onsuccess = () => resoudre(requete.result);
    requete.onerror = () => rejeter(requete.error);
    // Un autre onglet tient une version plus ancienne ouverte : le dire
    // plutot que d'attendre indefiniment sans rien afficher.
    requete.onblocked = () =>
      rejeter(new Error("Ferme les autres onglets de l'application, puis réessaie."));
  });
}

/**
 * La base enregistree, ou une base neuve.
 *
 * Ne leve jamais : un navigateur en navigation privee, ou regle pour bloquer
 * le stockage, doit laisser l'application **fonctionner** — la seance se joue,
 * elle ne se retient simplement pas. Une panne de stockage au demarrage
 * empecherait de s'entrainer, ce qui est pire que d'oublier.
 */
export async function charger() {
  if (!disponible()) return base_vide();
  try {
    const bdd = await ouvrir();
    const transaction = bdd.transaction(MAGASIN, "readonly");
    const contenu = await promesse(transaction.objectStore(MAGASIN).get(CLE));
    bdd.close();
    return contenu ?? base_vide();
  } catch {
    return base_vide();
  }
}

/**
 * Ecrit la base. Rend `true` si elle est bien enregistree.
 *
 * Le booleen n'est pas decoratif : c'est ce qui permet a l'ecran de fin de
 * dire « ta seance n'a pas pu etre enregistree, exporte-la » au lieu de
 * laisser croire qu'elle l'est.
 */
export async function sauver(base) {
  if (!disponible()) return false;
  try {
    const bdd = await ouvrir();
    const transaction = bdd.transaction(MAGASIN, "readwrite");
    await promesse(transaction.objectStore(MAGASIN).put(base, CLE));
    await new Promise((resoudre, rejeter) => {
      transaction.oncomplete = resoudre;
      transaction.onerror = () => rejeter(transaction.error);
      transaction.onabort = () => rejeter(transaction.error);
    });
    bdd.close();
    return true;
  } catch {
    return false;
  }
}

export async function effacer() {
  if (!disponible()) return false;
  try {
    const bdd = await ouvrir();
    const transaction = bdd.transaction(MAGASIN, "readwrite");
    await promesse(transaction.objectStore(MAGASIN).delete(CLE));
    bdd.close();
    return true;
  } catch {
    return false;
  }
}

/**
 * Le stockage de cet appareil est-il durable ?
 *
 * Safari purge les donnees des sites peu visites. Une application ajoutee a
 * l'ecran d'accueil y echappe normalement, et `navigator.storage.persist()`
 * demande explicitement cette garantie — mais « normalement » ne suffit pas
 * pour un historique d'entrainement, d'ou l'export. Cette fonction sert a le
 * **dire** a l'utilisateur, pas a se rassurer.
 */
export async function durable() {
  if (!navigator.storage?.persist) return null;
  try {
    if (await navigator.storage.persisted()) return true;
    return await navigator.storage.persist();
  } catch {
    return null;
  }
}

function nom_de_fichier(maintenant = new Date()) {
  const deux = (n) => String(n).padStart(2, "0");
  return (
    `coach-${maintenant.getFullYear()}-${deux(maintenant.getMonth() + 1)}-` +
    `${deux(maintenant.getDate())}.json`
  );
}

/**
 * Propose la sauvegarde au telechargement.
 *
 * Sur iOS, ca ouvre la feuille de partage : la personne choisit « Fichiers »
 * ou iCloud. C'est aussi le transfert d'un appareil a l'autre tant qu'aucun
 * serveur n'existe.
 */
export function telecharger(base) {
  const contenu = new Blob([exporter(base)], { type: "application/json" });
  const url = URL.createObjectURL(contenu);
  const lien = document.createElement("a");
  lien.href = url;
  lien.download = nom_de_fichier();
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
  // Liberer tout de suite fait echouer le telechargement sur certains
  // navigateurs, qui lisent l'URL apres le clic.
  setTimeout(() => URL.revokeObjectURL(url), 10_000);
}

/** Relit un fichier choisi par l'utilisateur. Leve si le format ne va pas. */
export async function lire_fichier(fichier) {
  return importer(await fichier.text());
}
