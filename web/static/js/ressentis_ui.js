// La saisie du ressenti, partagee par l'ecran de fin et l'historique.
//
// **Ce module ne decide rien** : la regle de progression vit dans
// `ressenti.js`, et la seule chose qui se joue ici
// est *quelles reponses proposer*. Elle en decoule directement, et c'est pour
// ca qu'elle doit etre ecrite une fois : proposer « trop dur » apres une
// reussite afficherait un bouton dont la table d'ajustement ne fait rien.
//
// Deux decisions de fond.
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
 * `jugement` est ce que rend `Ressenti.juger` — `{reussi, ressenti}`.
 * `au_choix(nom, valeur)` recoit la chaine vide quand la reponse est annulee,
 * et c'est l'appelant qui decide ou l'ecrire.
 *
 * Recliquer sur son propre choix l'annule : « je prefere ne rien dire » doit
 * rester atteignable sans recharger la page.
 *
 * `jugement.variante`, quand il existe, est une proposition de
 * `variantes.propositions` — `{sens, original, vers}` : jouer une variante plus
 * facile la prochaine fois. Elle n'apparait que si l'appelant fournit
 * `au_variante(original, vers)`, qui ecrit la table du profil et rend vrai si
 * c'est fait. Comme pour le ressenti, ce module ne decide rien : la
 * proposition arrive toute faite.
 *
 * `sens: "montee"` n'est pas une proposition mais une **annonce** : la
 * seance vient de faire remonter la chaine (`variantes.montees`), la table
 * est deja ecrite, et `nouveau` dit ce qui sera joue. Le bouton propose le
 * contraire — rester sur `vers`, la variante qu'on vient de maitriser —, par
 * le meme `au_variante`.
 */
export function construire_ligne(zone, nom, jugement, au_choix, au_variante = null) {
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

  const proposition = jugement.variante;
  if (proposition?.sens === "montee") {
    zone.appendChild(annonce_de_montee(proposition, au_variante));
  } else if (proposition && au_variante) {
    const bouton = document.createElement("button");
    bouton.type = "button";
    bouton.className = `variante ${proposition.sens}`;
    bouton.textContent =
      proposition.sens === "facile"
        ? `La prochaine fois : ${proposition.vers}`
        : `Prochaine séance : essaie ${proposition.vers}`;
    bouton.addEventListener("click", async () => {
      bouton.disabled = true;
      const fait = await au_variante(proposition.original, proposition.vers);
      if (!fait) {
        bouton.disabled = false;
        return;
      }
      // Une confirmation qui dit la portee du geste : toutes les seances, et
      // pas seulement celle-ci.
      const note = document.createElement("span");
      note.className = "variante-retenue";
      note.textContent =
        proposition.vers === proposition.original
          ? `${proposition.original} revient dans tes séances.`
          : `${proposition.vers} remplace ${proposition.original} dans tes séances.`;
      bouton.replaceWith(note);
    });
    zone.appendChild(bouton);
  }
  zone.classList.add("visible");
}

/**
 * « Cap franchi : la prochaine fois, pompes inclinees », et de quoi rester.
 *
 * La montee est faite avant que l'ecran ne s'affiche : rien a accepter, donc
 * pas de bouton pour l'accepter. Ne garder que le moyen de la defaire, et le
 * dire, est ce qui rend une decision automatique acceptable.
 */
function annonce_de_montee(montee, au_variante) {
  const bloc = document.createElement("span");
  bloc.className = "variante-montee";
  const texte = document.createElement("span");
  texte.textContent = `Cap franchi : la prochaine fois, ${montee.nouveau}.`;
  bloc.appendChild(texte);
  if (!au_variante) return bloc;

  const bouton = document.createElement("button");
  bouton.type = "button";
  bouton.className = "variante rester";
  bouton.textContent = `Rester sur ${montee.vers}`;
  bouton.addEventListener("click", async () => {
    bouton.disabled = true;
    if (!(await au_variante(montee.original, montee.vers))) {
      bouton.disabled = false;
      return;
    }
    texte.textContent = `${montee.vers} reste dans tes séances.`;
    bouton.remove();
  });
  bloc.appendChild(bouton);
  return bloc;
}

/**
 * Une montee (`{original, depuis, vers}`, rendue par `variantes.montees`)
 * sous la forme que `construire_ligne` affiche. Ecrite ici une fois, pour que
 * l'ecran de fin et l'historique disent la meme chose.
 */
export function proposition_de_montee(montee) {
  return { sens: "montee", original: montee.original, vers: montee.depuis, nouveau: montee.vers };
}
