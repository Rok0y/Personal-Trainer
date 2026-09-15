// Detecte qu'un deploiement est arrive, et va le chercher.
//
// `scripts/empreinte_deploiement.py` marque deja chaque ressource de
// l'empreinte du commit, ce qui garantit qu'un module neuf n'ira pas charger
// une dependance vieille. Mais **le document, lui, ne peut pas etre marque** :
// c'est le point d'entree, il n'y a pas d'adresse parente pour le versionner.
// GitHub Pages le sert en `max-age=600`, et une application ajoutee a l'ecran
// d'accueil sur iOS le garde bien plus longtemps — sans qu'il existe de
// « recharger en ignorant le cache ». On se retrouve donc avec un vieux
// document qui importe de vieux modules par leur ancienne adresse : tout est
// coherent, tout est perime, et rien ne le signale.
//
// La parade : le site publie porte un `version.json` que ce module relit a
// chaque ouverture, et compare a **sa propre empreinte**, lue dans sa propre
// adresse (`import.meta.url`). Si elles different, le document est vieux, et
// on le recharge sous une adresse que le cache n'a jamais vue.
//
// **Ce module ne touche a aucun stockage.** Ni IndexedDB — ou vit
// l'historique d'entrainement —, ni `localStorage`, ni les caches : il ne
// fait que changer d'adresse. Le garde anti-boucle lui-meme vit dans l'URL
// (`?maj=`), pas dans une cle qu'il faudrait poser puis nettoyer. Un
// rechargement ne perd donc aucune seance, par construction.

//: Le parametre qui porte le garde anti-boucle. Si le document recharge est
//: *encore* perime — deploiement a moitie propage, par exemple —, sa presence
//: empeche une seconde tentative : on prefere une version en retard a une
//: application qui tourne en rond.
const PARAMETRE_MAJ = "maj";

/** L'empreinte de ce module, c'est-a-dire celle du document qui l'a importe. */
function empreinte_chargee() {
  try {
    return new URL(import.meta.url).searchParams.get("v");
  } catch (erreur) {
    return null;
  }
}

/** L'empreinte reellement publiee, relue sans passer par le cache. */
async function empreinte_publiee() {
  // Construite avec `new URL` et non ecrite en clair dans un `fetch(...)` :
  // `empreinte_deploiement.py` marque les adresses litterales, et un
  // `version.json?v=<vieille empreinte>` serait relu depuis le cache — donc
  // repondrait l'ancienne version, et ne signalerait jamais rien. Le script
  // l'exclut aussi de son cote ; les deux precautions se doublent a dessein.
  const adresse = new URL("../version.json", import.meta.url);
  adresse.searchParams.set("t", Date.now());
  const reponse = await fetch(adresse, { cache: "no-store" });
  if (!reponse.ok) return null;
  return (await reponse.json()).empreinte ?? null;
}

/**
 * Recharge la page si le deploiement a change depuis que ce document a ete mis en cache.
 *
 * Ne fait rien en developpement (aucune empreinte : le serveur local ne cache
 * rien) ni hors ligne (la lecture echoue, et une application doit pouvoir se
 * jouer sans reseau plutot que de refuser de demarrer).
 */
export async function verifier_version() {
  const chargee = empreinte_chargee();
  if (!chargee) return;

  let publiee = null;
  try {
    publiee = await empreinte_publiee();
  } catch (erreur) {
    return; // hors ligne, ou fichier absent : on joue ce qu'on a.
  }
  if (!publiee || publiee === chargee) return;

  const ici = new URL(location.href);
  if (ici.searchParams.get(PARAMETRE_MAJ) === publiee) return;

  // `replace` et non `assign` : la version perimee n'a pas a rester dans
  // l'historique de navigation, ou un retour arriere y ramenerait.
  ici.searchParams.set(PARAMETRE_MAJ, publiee);
  location.replace(ici);
}

verifier_version();
