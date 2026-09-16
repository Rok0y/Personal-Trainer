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
4. les écarts volontaires entre les deux pages sont-ils **encore** des écarts ?

La troisième compte autant que les autres : une commande absente du dictionnaire
`commandes_autorisees` reste grisée pour toujours, et une commande que le
navigateur ne connaît pas ne fait simplement rien quand on appuie dessus.

La quatrième existe parce que les deux pages ont fini par **diverger à
dessein** : les cartes « Position » et « Étape » ne servent qu'au réglage d'une
détection, et ce réglage se fait sur la démo. Un tel écart doit être déclaré
(`ECARTS_ASSUMES`) plutôt que toléré, et la déclaration est vérifiée dans les
deux sens — un écart qui n'en est plus un est signalé lui aussi, faute de quoi
la liste pourrit et finit par excuser un vrai oubli.

**Angle mort corrigé au passage.** Les identifiants n'étaient cherchés que sous
la forme `$("nom")`. Or `hud.js` passe par `changer_champ(id, …)` et
`changer_badge(id_badge, id_valeur, …)`, qui appellent `$` avec une *variable* :
`position`, `stage`, `exercice`, `series`, `weight` et leurs trois badges
échappaient donc entièrement au contrôle — c'est-à-dire précisément les
identifiants que ce script dit protéger. Ils sont désormais extraits de leurs
sites d'appel.

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

#: Identifiants qu'une page n'a **pas**, et c'est voulu. `hud.js` continue de
#: les alimenter : `changer_champ` sort en silence quand l'élément est absent,
#: ce qui rend l'écart inoffensif — mais seulement tant qu'il est décidé.
#: Chaque entrée est vérifiée dans les deux sens (cf. `_ecarts`).
ECARTS_ASSUMES = {
    # Le réglage d'une détection se fait sur la démo, qui a un banc d'essai
    # bien plus complet ; en séance ces deux cartes ne font qu'occuper la
    # colonne gauche d'une tablette posée par terre.
    "application": {"position", "stage"},
}


def identifiants_reclames():
    """Tout ce que l'affichage va chercher dans le document.

    Trois formes, et les deux dernières ont longtemps manqué : `$("nom")` en
    direct, mais aussi les identifiants passés en **argument** à
    `changer_champ` et `changer_badge`, qui appellent `$` avec une variable.
    Une regex sur `$("…")` ne peut pas les voir, et ce sont justement ceux du
    bandeau et des badges.
    """
    source = HUD_JS.read_text(encoding="utf-8")
    directs = re.findall(r'\$\("([A-Za-z]\w*)"\)', source)
    champs = re.findall(r'changer_champ\(\s*"([A-Za-z]\w*)"', source)
    badges = re.findall(
        r'changer_badge\(\s*"([A-Za-z]\w*)"\s*,\s*"([A-Za-z]\w*)"', source
    )
    return set(directs) | set(champs) | {nom for paire in badges for nom in paire}


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
        presents = identifiants_de(page)
        assumes = ECARTS_ASSUMES.get(nom, set())

        manquants = (reclames - presents) - assumes
        if manquants:
            problemes.append(
                f"{nom} : {len(manquants)} identifiants que hud.js reclame sont "
                f"absents du balisage — {', '.join(sorted(manquants))}"
            )

        # Le controle dans l'autre sens. Un ecart declare qui n'existe plus est
        # une ligne qui n'excuse plus rien aujourd'hui, mais qui excusera un
        # vrai oubli le jour ou l'identifiant redisparaitra — exactement le
        # genre de repli qui masque un branchement.
        perimes = assumes & presents
        for identifiant in sorted(perimes):
            problemes.append(
                f"{nom} : « {identifiant} » est declare dans ECARTS_ASSUMES "
                "mais existe bel et bien — retirer la ligne devenue fausse"
            )

        oublies = assumes - reclames
        for identifiant in sorted(oublies):
            problemes.append(
                f"{nom} : « {identifiant} » est declare dans ECARTS_ASSUMES "
                "mais hud.js ne le reclame plus — retirer la ligne devenue inutile"
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

    assumes = sum(len(v) for v in ECARTS_ASSUMES.values())
    print(f"{len(reclames)} identifiants reclames par hud.js")
    if assumes:
        detail = "; ".join(
            f"{page} sans {', '.join(sorted(noms))}"
            for page, noms in sorted(ECARTS_ASSUMES.items())
        )
        print(f"  dont {assumes} ecarts assumes et verifies — {detail}")
    print(f"{len(fixe)} commandes, identiques des deux cotes et toutes executables")
    print("\nLes deux montages du HUD sont alignes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
