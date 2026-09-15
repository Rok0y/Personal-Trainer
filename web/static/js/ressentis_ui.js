// La saisie du ressenti, partagee par les deux applications.
//
// **Ce module ne decide rien** : la regle de progression vit dans
// `ressenti.js` / `progression/ressenti.py`, et la seule chose qui se joue ici
// est *quelles reponses proposer*. Elle en decoule directement, et c'est pour
// ca qu'elle doit etre ecrite une fois : proposer « trop dur » apres une
// reussite afficherait un bouton dont la table d'ajustement ne fait rien.
//
// Deux decisions de fond, reprises telles quelles du poste fixe.
//
// **Les reponses dependent de ce qui s'est passe** : apres une reussite on
// demande si c'etait facile, apres un echec si c'etait trop dur. Proposer les
// cinq d'un coup laisserait croire a un effet la ou il n'y en a pas.
//
// **Aucun bouton ne dit « normal »**, volontairement : ne rien selectionner
// *est* la reponse neutre. Un bouton neutre ferait croire qu'une reponse est
// attendue, alors que le cas courant est de passer son chemin.
//
// L'echelle stockee compte pourtant cinq valeurs (`ok` et `dur` en plus) :
// elles valent l'absence de reponse, et restent lisibles pour le jour ou on
// voudra les exploiter.

export const OPTIONS_REUSSITE = [
  { valeur: "facile", libelle: "C'était facile" },
  { valeur: "trop_facile", libelle: "C'était trop facile" },
];

export const OPTIONS_ECHEC = [{ valeur: "trop_dur", libelle: "C'était trop dur" }];

/**
 * Remplit une zone avec le verdict d'un exercice et ses reponses possibles.
 *
 * `jugement` est ce que rend `Ressenti.juger` — `{reussi, ressenti}` — que le
 * poste fixe va chercher par HTTP et que le navigateur calcule sur place.
 * `au_choix(nom, valeur)` recoit la chaine vide quand la reponse est annulee,
 * et c'est l'appelant qui decide ou l'ecrire.
 *
 * Recliquer sur son propre choix l'annule : « je prefere ne rien dire » doit
 * rester atteignable sans recharger la page.
 */
export function construire_ligne(zone, nom, jugement, au_choix) {
  zone.replaceChildren();

  const verdict = document.createElement("span");
  verdict.className = `verdict ${jugement.reussi ? "reussi" : "echoue"}`;
  verdict.textContent = jugement.reussi ? "Réussi" : "Non atteint";
  zone.appendChild(verdict);

  for (const option of jugement.reussi ? OPTIONS_REUSSITE : OPTIONS_ECHEC) {
    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.dataset.valeur = option.valeur;
    bouton.textContent = option.libelle;
    if (jugement.ressenti === option.valeur) bouton.classList.add("actif");

    bouton.addEventListener("click", () => {
      const deja = bouton.classList.contains("actif");
      zone.querySelectorAll("button").forEach((b) => b.classList.remove("actif"));
      if (!deja) bouton.classList.add("actif");
      au_choix(nom, deja ? "" : option.valeur);
    });

    zone.appendChild(bouton);
  }
  zone.classList.add("visible");
}
