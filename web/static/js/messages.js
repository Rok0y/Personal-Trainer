// Jumeau de core/messages.py — tout ce que l'application dit par ecrit.
//
// **Une cle, un message.** Meme convention que le coach vocal, ou
// "debut_serie" designe un .wav : un message est designe par une cle stable,
// qui rend un texte aujourd'hui et rendra un son demain.
//
// Deux consequences a respecter en ajoutant un message :
//
// - une fonction d'erreur d'exercice retourne une **cle**, jamais une phrase ;
//   `moteur.mettre_a_jour_erreur` la resout. Un detecteur inacheve qui
//   retournerait `true` produit alors une cle inconnue, donc rien ;
// - `texte()` ne leve jamais. Elle est appelee depuis la boucle image, ou une
//   exception gele l'affichage : un message manquant doit rester un silence,
//   pas une panne.

export const MESSAGES = {
  // --- Fautes de forme, signalees en temps reel pendant l'effort ---
  forme_buste_pas_assez_penche: "Penche-toi davantage vers l'avant",
  forme_genoux_trop_plies:
    "Garde les jambes presque tendues, plie moins les genoux",
  forme_coudes_trop_tendus:
    "Garde les coudes légèrement fléchis, ne tends pas complètement les bras",
  forme_coudes_trop_plies: "Ne plie pas trop les coudes",
  forme_coude_qui_part_en_avant:
    "Garde le coude collé au buste, ne le laisse pas partir en avant",
  // --- Consignes d'etat : ce qu'il faut faire, pas ce qui est mal fait ---
  corps_absent: "Place-toi devant la caméra, bien en pied.",
  // « la seance » et non « la serie » : cette phase n'existe qu'une fois.
  preparation_bras_en_x: "Croise les bras devant toi pour lancer la séance.",
  preparation_decompte: "C'est parti ! Redescends les bras et mets-toi en place.",
  pause: "Séance en pause. Reprends quand tu veux depuis le site.",
  test_calibration:
    "Premier passage : fais ton maximum, puis croise les bras pour valider.",
};

// Traduction des jetons rendus par les fonctions de detection. Le front
// affichait ces jetons bruts (« debut », « casse ») et devinait la posture en
// comparant des chaines : un debutant n'a rien a faire du vocabulaire interne
// du detecteur.
//
// ATTENTION — `repos` est defini **deux fois** cote Python (« Position
// relachee » pour le jeton de mouvement, puis « Repos » pour l'etape de
// circuit), et le dernier l'emporte. Reproduit tel quel, parce que le Python
// fait autorite et qu'un ecart ici ferait echouer le harnais pour une raison
// qui n'a rien a voir avec le portage. C'est un defaut a corriger des deux
// cotes en meme temps, pas ici tout seul : un gainage relache affiche
// aujourd'hui « Repos », ce qui se lit comme une pause de seance.
export const LIBELLES_ETAPE = {
  debut: "Position de départ",
  milieu: "En mouvement",
  // Neutre a dessein : « fin » est la position qui *valide* une repetition, et
  // ce n'est la position basse que pour le squat et la fente. Sur un curl, une
  // pompe ou un souleve de terre, c'est le haut du mouvement.
  fin: "Position finale",
  maintien: "Position tenue",
  casse: "Position incorrecte",
  echauffement: "Échauffement en cours",
  // Etapes du circuit, pas du mouvement : elles passent par le meme champ
  // parce que c'est la meme question a l'ecran — « ou en suis-je ? ».
  preparation: "Préparation",
  preparation_prete: "Prêt !",
  recuperation: "Récupération",
  repos: "Repos",
  pause: "En pause",
  termine: "Terminé",
  cassee: "Position incorrecte",
};

/**
 * Message correspondant a une cle, ou null si la cle est inconnue.
 *
 * Le format nomme (`{secondes}`) est applique quand des valeurs sont fournies ;
 * une cle de format absente du message est ignoree plutot que fatale, pour la
 * meme raison que l'absence de cle.
 */
export function texte(cle, valeurs = null) {
  const message = MESSAGES[cle];
  if (message === undefined) return null;
  if (!valeurs || Object.keys(valeurs).length === 0) return message;
  return message.replace(/\{(\w+)\}/g, (entier, nom) =>
    nom in valeurs ? String(valeurs[nom]) : entier
  );
}

/**
 * Nom lisible d'une etape de mouvement, ou le jeton brut a defaut.
 *
 * Retomber sur le jeton plutot que sur du vide : une etape non traduite reste
 * visible a l'ecran, donc se corrige, alors qu'un champ vide passe inapercu.
 */
export function libelle_etape(jeton) {
  if (!jeton) return null;
  return jeton in LIBELLES_ETAPE ? LIBELLES_ETAPE[jeton] : jeton;
}
