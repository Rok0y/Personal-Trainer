"""Les deux pages du HUD portent-elles toujours les mêmes points d'accroche ?

`web/static/js/hud.js` peint **un seul** écran de séance, monté deux fois : le
gabarit Flask du poste fixe et la page de l'application web. Partager le code
d'affichage ne suffit pas à empêcher la dérive — il reste le *balisage*, et
rien dans le navigateur ne signale un identifiant manquant : `$("reps")` rend
`null`, la ligne suivante lève, et la boucle d'affichage s'arrête au milieu.
Sur le poste fixe l'erreur part dans la console d'un onglet que personne ne
regarde ; sur une tablette posée par terre, personne ne la verra jamais.

Ce script relit donc les trois fichiers et pose trois questions :

1. chaque identifiant que `hud.js` réclame existe-t-il **dans les deux pages** ?
2. les deux pages proposent-elles **les mêmes commandes** ?
3. ces commandes sont-elles bien celles que le contrôleur autorise
   (`commandes_autorisees`) et que le navigateur sait exécuter ?

La troisième compte autant que les autres : une commande absente du dictionnaire
`commandes_autorisees` reste grisée pour toujours, et une commande que le
navigateur ne connaît pas ne fait simplement rien quand on appuie dessus.

Usage : `python -m scripts.verifier_hud`
"""

import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

HUD_JS = RACINE / "web/static/js/hud.js"
PAGES = {
    "poste fixe": RACINE / "web/templates/index.html",
    "application": RACINE / "web/static/app/index.html",
}
#: Où vivent les deux moitiés de la règle « cette commande est-elle possible ? ».
CONTROLEUR = RACINE / "session/controleur.py"
APPLICATION = RACINE / "web/static/app/index.html"


def identifiants_reclames():
    """Les `$("...")` de `hud.js` : tout ce que l'affichage va chercher."""
    return set(re.findall(r'\$\("([A-Za-z]\w*)"\)', HUD_JS.read_text(encoding="utf-8")))


def identifiants_de(page):
    return set(re.findall(r'id="([A-Za-z]\w*)"', page.read_text(encoding="utf-8")))


def commandes_de(page):
    return set(
        re.findall(r'data-commande="(\w+)"', page.read_text(encoding="utf-8"))
    )


def commandes_autorisees():
    """Les clés du dictionnaire `commandes` de `SessionManager.etat()`."""
    source = CONTROLEUR.read_text(encoding="utf-8")
    debut = source.index("commandes = {")
    fin = source.index("\n            }", debut)
    return set(re.findall(r'"(\w+)":', source[debut:fin]))


def commandes_du_navigateur():
    """Les clés du dictionnaire `COMMANDES` de l'application."""
    source = APPLICATION.read_text(encoding="utf-8")
    debut = source.index("const COMMANDES = {")
    fin = source.index("\n};", debut)
    return set(re.findall(r"^  (\w+):", source[debut:fin], re.M))


def main():
    problemes = []

    reclames = identifiants_reclames()
    for nom, page in PAGES.items():
        manquants = reclames - identifiants_de(page)
        if manquants:
            problemes.append(
                f"{nom} : {len(manquants)} identifiants que hud.js reclame sont "
                f"absents du balisage — {', '.join(sorted(manquants))}"
            )

    commandes = {nom: commandes_de(page) for nom, page in PAGES.items()}
    fixe, application = commandes["poste fixe"], commandes["application"]
    if fixe != application:
        for absente in sorted(fixe - application):
            problemes.append(f"commande « {absente} » : sur le poste fixe, pas dans l'application")
        for absente in sorted(application - fixe):
            problemes.append(f"commande « {absente} » : dans l'application, pas sur le poste fixe")

    # `pause` et `reprendre` ne dependent pas de `commandes_autorisees` mais du
    # statut de la session : `hud.js` les traite a part, et le controleur n'a
    # donc aucune raison de les lister.
    hors_autorisations = {"pause", "reprendre"}
    inconnues = (fixe - hors_autorisations) - commandes_autorisees()
    for commande in sorted(inconnues):
        problemes.append(
            f"commande « {commande} » : aucun bouton ne s'activera, "
            "SessionManager.etat() ne l'autorise nulle part"
        )

    sans_effet = application - commandes_du_navigateur()
    for commande in sorted(sans_effet):
        problemes.append(
            f"commande « {commande} » : le bouton existe dans l'application "
            "mais COMMANDES ne sait pas l'executer"
        )

    if problemes:
        print(f"{len(problemes)} problemes :\n")
        for probleme in problemes:
            print(f"  - {probleme}")
        return 1

    print(f"{len(reclames)} identifiants presents dans les deux pages")
    print(f"{len(fixe)} commandes, identiques des deux cotes et toutes executables")
    print("\nLes deux montages du HUD sont alignes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
