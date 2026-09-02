/* ==========================================================================
   Réordonnancement des blocs par glisser-déposer.

   Partagé par creer_seance.html et editer_seance.html : les deux pages ont
   la même structure de blocs et la même contrainte d'entrelacement.

   ATTENTION — pourquoi `surChangement` est obligatoire : `entrelace_avec`
   n'est pas stocké comme un nom mais comme un drapeau « avec le bloc juste
   en dessous », résolu en nom seulement à l'enregistrement. Déplacer un bloc
   change donc avec qui il est entrelacé, et le dernier bloc ne peut pas
   l'être du tout. Chaque page passe ici sa fonction de rafraîchissement pour
   que cet état soit recalculé après chaque dépôt.
   ========================================================================== */

/**
 * Active le glisser-déposer sur les enfants `.bloc` d'un conteneur.
 *
 * @param {HTMLElement} conteneur      L'élément qui contient les blocs.
 * @param {Function}    surChangement  Appelée après chaque réordonnancement.
 */
function activerReordonnancement(conteneur, surChangement) {
    let blocDeplace = null;

    const nettoyerCibles = () => {
        conteneur.querySelectorAll(".cible-avant, .cible-apres").forEach((bloc) => {
            bloc.classList.remove("cible-avant", "cible-apres");
        });
    };

    // Un bloc n'est rendu draggable qu'au moment où l'on appuie sur sa
    // poignée : sinon un glissement démarré dans un champ de saisie
    // déplacerait le bloc au lieu de sélectionner le texte.
    conteneur.addEventListener("mousedown", (evenement) => {
        const poignee = evenement.target.closest(".drag-poignee");
        if (!poignee) return;
        poignee.closest(".bloc").draggable = true;
    });

    // Un simple clic sur la poignée, sans glissement, ne déclenche jamais
    // `dragend` : sans ce retrait le bloc resterait draggable, et un
    // glissement ultérieur parti d'un champ de saisie le déplacerait.
    document.addEventListener("mouseup", () => {
        if (blocDeplace) return;
        conteneur.querySelectorAll(".bloc[draggable]").forEach((bloc) => {
            bloc.draggable = false;
        });
    });

    conteneur.addEventListener("dragstart", (evenement) => {
        const bloc = evenement.target.closest(".bloc");
        if (!bloc || !bloc.draggable) return;
        blocDeplace = bloc;
        bloc.classList.add("en-deplacement");
        evenement.dataTransfer.effectAllowed = "move";
        // Firefox n'amorce pas de glissement sans données transférées.
        evenement.dataTransfer.setData("text/plain", "");
    });

    conteneur.addEventListener("dragover", (evenement) => {
        if (!blocDeplace) return;
        evenement.preventDefault();
        evenement.dataTransfer.dropEffect = "move";

        const survole = evenement.target.closest(".bloc");
        nettoyerCibles();
        if (!survole || survole === blocDeplace) return;

        // On dépose avant ou après selon la moitié du bloc survolée.
        const cadre = survole.getBoundingClientRect();
        const apres = evenement.clientY > cadre.top + cadre.height / 2;
        survole.classList.add(apres ? "cible-apres" : "cible-avant");
    });

    conteneur.addEventListener("drop", (evenement) => {
        if (!blocDeplace) return;
        evenement.preventDefault();

        const survole = evenement.target.closest(".bloc");
        if (survole && survole !== blocDeplace) {
            const cadre = survole.getBoundingClientRect();
            const apres = evenement.clientY > cadre.top + cadre.height / 2;
            survole.insertAdjacentElement(
                apres ? "afterend" : "beforebegin",
                blocDeplace
            );
        }

        nettoyerCibles();
        surChangement();
    });

    // dragend se déclenche même sur un dépôt annulé (touche Échap, dépôt hors
    // zone) : c'est le seul endroit sûr pour remettre le bloc à l'état normal.
    conteneur.addEventListener("dragend", (evenement) => {
        const bloc = evenement.target.closest(".bloc");
        if (bloc) {
            bloc.draggable = false;
            bloc.classList.remove("en-deplacement");
        }
        nettoyerCibles();
        blocDeplace = null;
    });
}
