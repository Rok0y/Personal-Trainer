"""Genere les cas de reference qui prouvent que le portage JS est fidele.

Les detections sont des fonctions **pures** d'un corps vers un jeton : les
deux implementations doivent donc s'accorder sur n'importe quelle entree,
anatomiquement plausible ou non. Des poses tirees au hasard couvrent bien
mieux les abords des seuils qu'une captation reelle, ou l'on repasse sans
cesse par les memes configurations — et elles ne demandent ni camera ni
patience.

Sortie : scripts/fixtures_detections.jsonl, une pose par ligne, avec les
jetons attendus. A rejouer avec `node scripts/comparer_detections.mjs`.

    python -m scripts.generer_fixtures [nombre_de_poses]
"""

import inspect
import json
import math
import random
import sys
from pathlib import Path

from mouvements import echauffements, exercices, positions
from vision.body import Body, LandmarkPoint
from vision.landmarks import LANDMARKS

GRAINE = 20260909
"""Fixe pour que le fichier genere soit reproductible : deux executions
produisent les memes poses, donc un diff du harnais signale un changement de
logique et jamais un changement de tirage."""

DESTINATION = Path(__file__).parent / "fixtures_detections.jsonl"


def fonctions_publiques(module):
    """Les fonctions du module qui prennent un corps et rendent un jeton.

    Recensees par introspection plutot que listees a la main : une detection
    ajoutee sans jumelle JS doit faire echouer le harnais, pas passer
    inapercue parce que personne n'a pense a l'inscrire ici.
    """
    trouvees = {}
    for nom, objet in inspect.getmembers(module, inspect.isfunction):
        if nom.startswith("_") or objet.__module__ != module.__name__:
            continue
        if list(inspect.signature(objet).parameters) == ["corps"]:
            trouvees[nom] = objet
    return trouvees


def pose_au_hasard(rng):
    points = {}
    for nom in LANDMARKS:
        points[nom] = LandmarkPoint(
            x=rng.random(), y=rng.random(), z=rng.random() * 2 - 1, visibilite=rng.random()
        )
    return Body(points)


NOMBRE_POSES_DE_GESTE = 500
"""Poses construites bras leves, en plus des poses au hasard.

Le hasard n'atteint presque jamais « deux bras leves » : mesure, 4 poses sur
5 000 levent les deux bras, et aucune n'a le buste debout. La condition de
buste ajoutee a `deux_bras_leves` n'etait donc comparee par rien — la retirer
d'un seul cote passait vert. Meme lecon que les scenarios ecrits du harnais de
seances : un etat etroit se vise, il ne se tire pas."""


def pose_bras_leves(rng):
    """Deux bras tendus au-dessus des epaules, buste oriente au hasard.

    Le buste tourne de -90 a +90 degres autour du milieu des epaules : debout a
    zero, allonge aux extremes, et la frontiere a 45 degres visitee au passage.
    Le reste du corps garde ses valeurs tirees au hasard, ce qui fait aussi
    tourner les detections d'exercice sur ces poses.
    """
    corps = pose_au_hasard(rng)
    points = corps.points
    milieu_x, milieu_y = 0.3 + rng.random() * 0.4, 0.3 + rng.random() * 0.4
    demi_largeur = 0.03 + rng.random() * 0.08
    for cote, signe in (("gauche", -1), ("droite", 1)):
        suffixe_bras = "gauche" if cote == "gauche" else "droit"
        ex, ey = milieu_x + signe * demi_largeur, milieu_y
        points[f"epaule_{cote}"] = LandmarkPoint(ex, ey, 0, 1)
        # Le bras est tendu vers le haut, a quelques degres pres : l'angle du
        # coude reste au-dessus de 160 la plupart du temps, pas toujours.
        derive = (rng.random() - 0.5) * 0.04
        points[f"coude_{suffixe_bras}"] = LandmarkPoint(ex + derive, ey - 0.12, 0, 1)
        points[f"poignet_{suffixe_bras}"] = LandmarkPoint(ex + 2 * derive, ey - 0.24, 0, 1)
    angle = math.radians(rng.uniform(-90, 90))
    distance = 0.15 + rng.random() * 0.2
    hx = milieu_x + distance * math.sin(angle)
    hy = milieu_y + distance * math.cos(angle)
    points["hanche_gauche"] = LandmarkPoint(hx - demi_largeur, hy, 0, 1)
    points["hanche_droite"] = LandmarkPoint(hx + demi_largeur, hy, 0, 1)
    return Body(points)


NOMBRE_POSES_UN_BRAS = 500
"""Poses construites un seul bras leve, pour les gestes +1 / -1.

Meme raison que les poses bras leves : `seul_bras_droit_leve` exige un bras
tendu en haut, l'autre poignet **sous** son epaule et le buste debout — une
conjonction que le hasard ne visite pas. Le poignet de l'autre bras est tire
de part et d'autre de la hauteur de son epaule, pour que la frontiere qui
coupe le geste quand le second bras monte soit visitee des deux cotes."""


def pose_un_bras_leve(rng):
    """Un bras tendu au-dessus de l'epaule, l'autre autour de l'epaule.

    Le cote leve est tire au hasard, le buste oriente de -90 a +90 degres
    comme pour `pose_bras_leves`.
    """
    corps = pose_au_hasard(rng)
    points = corps.points
    milieu_x, milieu_y = 0.3 + rng.random() * 0.4, 0.3 + rng.random() * 0.4
    demi_largeur = 0.03 + rng.random() * 0.08
    leve = rng.choice(("gauche", "droite"))
    for cote, signe in (("gauche", -1), ("droite", 1)):
        suffixe_bras = "gauche" if cote == "gauche" else "droit"
        ex, ey = milieu_x + signe * demi_largeur, milieu_y
        points[f"epaule_{cote}"] = LandmarkPoint(ex, ey, 0, 1)
        if cote == leve:
            derive = (rng.random() - 0.5) * 0.04
            points[f"coude_{suffixe_bras}"] = LandmarkPoint(ex + derive, ey - 0.12, 0, 1)
            points[f"poignet_{suffixe_bras}"] = LandmarkPoint(ex + 2 * derive, ey - 0.24, 0, 1)
        else:
            # Autour de l'epaule, un peu au-dessus comme bien en dessous.
            hauteur = rng.uniform(-0.1, 0.25)
            points[f"coude_{suffixe_bras}"] = LandmarkPoint(ex + signe * 0.05, ey + hauteur / 2, 0, 1)
            points[f"poignet_{suffixe_bras}"] = LandmarkPoint(ex + signe * 0.06, ey + hauteur, 0, 1)
    angle = math.radians(rng.uniform(-90, 90))
    distance = 0.15 + rng.random() * 0.2
    hx = milieu_x + distance * math.sin(angle)
    hy = milieu_y + distance * math.cos(angle)
    points["hanche_gauche"] = LandmarkPoint(hx - demi_largeur, hy, 0, 1)
    points["hanche_droite"] = LandmarkPoint(hx + demi_largeur, hy, 0, 1)
    return Body(points)


NOMBRE_POSES_PAR_FAMILLE = 300
"""Poses construites pour les detections que le hasard n'atteint pas.

Mesure par `verifier_instruments.mjs` : sur 5 000 poses tirees au hasard,
aucune n'atteint la fin de l'elevation laterale (six conditions a la fois), ni
le debut du squat (un coude a moins de 0,05 du genou), et les maintiens de
gainage ne sont atteints que par 7 a 10 poses. Leurs seuils n'etaient donc
compares par rien. Chaque famille construit la position visee **autour** de ses
seuils, pour visiter les deux cotes de chacun."""


def pose_elevation(rng):
    """Debout de face, chaque bras leve d'un angle au hasard, plus ou moins
    sur le cote (1) ou devant soi (0), plus ou moins plie."""
    corps = pose_au_hasard(rng)
    points = corps.points
    cx, ey = 0.35 + rng.random() * 0.3, 0.25 + rng.random() * 0.1
    demi_largeur = 0.06 + rng.random() * 0.05
    buste = 0.2 + rng.random() * 0.1
    longueur = buste * (0.9 + rng.random() * 0.3)
    # Une pose sur deux vise la position haute : sa fin demande six conditions
    # sur les deux bras a la fois, qu'un tirage uniforme ne reunit presque jamais.
    vise_le_haut = rng.random() < 0.5
    for cote, signe in (("gauche", 1), ("droite", -1)):
        bras = "gauche" if cote == "gauche" else "droit"
        ex = cx + signe * demi_largeur
        points[f"epaule_{cote}"] = LandmarkPoint(ex, ey, 0, 1)
        points[f"hanche_{cote}"] = LandmarkPoint(ex, ey + buste, 0, 1)
        if vise_le_haut:
            leve = math.radians(rng.uniform(70, 105))
            cote_lateral = rng.uniform(0.2, 1.0)
            pli = rng.uniform(-0.08, 0.08) * longueur
        else:
            leve = math.radians(rng.uniform(0, 120))
            cote_lateral = rng.uniform(-0.3, 1.0)
            pli = rng.uniform(-0.12, 0.12) * longueur
        dx, dy = signe * cote_lateral * math.sin(leve), math.cos(leve)
        points[f"coude_{bras}"] = LandmarkPoint(
            ex + dx * longueur / 2 - dy * pli, ey + dy * longueur / 2 + dx * pli, 0, 1
        )
        points[f"poignet_{bras}"] = LandmarkPoint(ex + dx * longueur, ey + dy * longueur, 0, 1)
    return Body(points)


def pose_planche(rng):
    """De profil, allonge face au sol : epaules plus ou moins soulevees au-dessus
    des coudes, hanches plus ou moins decollees, du corps a plat au gainage."""
    corps = pose_au_hasard(rng)
    points = corps.points
    sol = 0.75 + rng.random() * 0.15
    x0 = 0.15 + rng.random() * 0.15
    longueur = 0.5 + rng.random() * 0.2
    epaule = rng.uniform(0, 0.2)
    hanche = rng.uniform(-0.03, 1.3) * epaule
    for cote, decalage in (("gauche", 0.0), ("droite", 0.01)):
        bras = "gauche" if cote == "gauche" else "droit"
        points[f"coude_{bras}"] = LandmarkPoint(x0 + decalage, sol, 0, 1)
        points[f"epaule_{cote}"] = LandmarkPoint(x0 + decalage, sol - epaule, 0, 1)
        points[f"hanche_{cote}"] = LandmarkPoint(x0 + longueur * 0.5 + decalage, sol - hanche, 0, 1)
        genou = LandmarkPoint(x0 + longueur * 0.75, sol - hanche * rng.uniform(0.2, 0.7), 0, 1)
        points[f"genou_{bras}"] = genou
        points[f"cheville_{cote}"] = LandmarkPoint(x0 + longueur, sol, 0, 1)
    return Body(points)


def pose_planche_laterale(rng):
    """De face, allonge sur un cote tire au hasard : buste plus ou moins
    souleve sur l'avant-bras, hanche plus ou moins decollee du sol."""
    corps = pose_au_hasard(rng)
    points = corps.points
    bas, haut = (("gauche", "droite") if rng.random() < 0.5 else ("droite", "gauche"))
    bras_bas = "gauche" if bas == "gauche" else "droit"
    sol = 0.75 + rng.random() * 0.15
    x0 = 0.15 + rng.random() * 0.15
    longueur = 0.5 + rng.random() * 0.2
    epaule = rng.uniform(0, 0.2)
    hanche = rng.uniform(-0.03, 1.2) * epaule * 0.55
    points[f"coude_{bras_bas}"] = LandmarkPoint(x0, sol, 0, 1)
    points[f"epaule_{bas}"] = LandmarkPoint(x0, sol - epaule, 0, 1)
    points[f"epaule_{haut}"] = LandmarkPoint(x0 + 0.01, sol - epaule - rng.uniform(-0.02, 0.1), 0, 1)
    points[f"hanche_{bas}"] = LandmarkPoint(x0 + longueur * 0.5, sol - hanche, 0, 1)
    points[f"cheville_{bas}"] = LandmarkPoint(x0 + longueur, sol - rng.uniform(0, 0.02), 0, 1)
    return Body(points)


def pose_contacts(rng):
    """Coudes pres des genoux (squat) et poignets pres des chevilles (souleve
    de terre), a une distance tiree autour des deux seuils de chacun."""
    corps = pose_au_hasard(rng)
    points = corps.points
    for proche, repere in (
        ("coude_gauche", "genou_gauche"), ("coude_droit", "genou_droit"),
        ("poignet_gauche", "cheville_gauche"), ("poignet_droit", "cheville_droite"),
    ):
        r, a = rng.uniform(0, 0.25), rng.uniform(0, 2 * math.pi)
        base = points[repere]
        points[proche] = LandmarkPoint(base.x + r * math.cos(a), base.y + r * math.sin(a), 0, 1)
    return Body(points)


def pose_mur(rng):
    """De profil, debout ou penche, le bras le mieux vu tendu plus ou moins
    devant soi : poignet a une hauteur et une avancee tirees autour des
    bornes de `pompe_mur_detection`, coude a un angle tire de 40 a 180 degres.

    L'angle est **construit** et non subi : le coude est place sur la
    mediatrice epaule-poignet, a la distance qui donne exactement cet angle
    avec deux segments de meme longueur. Le hasard ne reunit jamais seul un
    buste debout, des mains a hauteur de poitrine et un coude plie."""
    corps = pose_au_hasard(rng)
    points = corps.points
    x0, ey = 0.3 + rng.random() * 0.4, 0.2 + rng.random() * 0.15
    buste = 0.2 + rng.random() * 0.1
    # Du debout au couche, pour visiter les deux cotes de la condition de buste.
    penche = math.radians(rng.uniform(0, 70))
    sens = 1 if rng.random() < 0.5 else -1
    vu, cache = (("gauche", "droite") if rng.random() < 0.5 else ("droite", "gauche"))
    for cote, visibilite in ((vu, 1.0), (cache, 0.3)):
        bras = "gauche" if cote == "gauche" else "droit"
        decalage = 0.0 if cote == vu else rng.uniform(-0.02, 0.02)
        ex, ey_ = x0 + decalage, ey + decalage
        points[f"epaule_{cote}"] = LandmarkPoint(ex, ey_, 0, visibilite)
        points[f"hanche_{cote}"] = LandmarkPoint(
            ex - sens * buste * math.sin(penche), ey_ + buste * math.cos(penche), 0, visibilite
        )
        hauteur = rng.uniform(-0.6, 0.9) * buste
        avancee = rng.uniform(0, 0.9) * buste
        wx, wy = ex + sens * avancee, ey_ + hauteur
        d = math.hypot(wx - ex, wy - ey_)
        angle = math.radians(rng.uniform(40, 180))
        demi = d / 2
        segment = demi / max(math.sin(angle / 2), 1e-6)
        fleche = math.sqrt(max(segment ** 2 - demi ** 2, 0))
        mx, my = (ex + wx) / 2, (ey_ + wy) / 2
        nx, ny = (-(wy - ey_) / d, (wx - ex) / d) if d > 0 else (0, 1)
        if ny < 0:
            nx, ny = -nx, -ny
        points[f"coude_{bras}"] = LandmarkPoint(mx + nx * fleche, my + ny * fleche, 0, visibilite)
        points[f"poignet_{bras}"] = LandmarkPoint(wx, wy, 0, visibilite)
    return Body(points)


FAMILLES = [pose_elevation, pose_planche, pose_planche_laterale, pose_contacts, pose_mur]


def serialiser(corps):
    """La pose au format que lira le JS : un tableau indexe comme MediaPipe."""
    tableau = [None] * (max(LANDMARKS.values()) + 1)
    for nom, index in LANDMARKS.items():
        p = corps.points[nom]
        tableau[index] = {
            "x": p.x,
            "y": p.y,
            "z": p.z,
            "visibility": p.visibilite,
        }
    return tableau


def natif(jeton):
    """Ramene un jeton a un type Python standard.

    `calculer_angle` passe par numpy, si bien qu'une comparaison d'angle rend
    un `numpy.bool_` et non un `bool` : invisible dans un `if`, mais refuse
    par json.dumps. Les detections rendent une chaine, les fonctions d'erreur
    None, les positions un booleen.
    """
    if jeton is None or isinstance(jeton, str):
        return jeton
    return bool(jeton)


def main():
    nombre = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    rng = random.Random(GRAINE)

    # `echauffements` est dans la liste depuis qu'une detection definie la —
    # et nulle part ailleurs — a traverse tout le harnais sans etre vue.
    # `fonctions_publiques` filtre sur `objet.__module__`, donc les detections
    # que ce module **importe** d'`exercices` ne sont pas comptees deux fois :
    # seules celles qui lui sont propres s'ajoutent. C'est exactement la classe
    # d'oubli que l'introspection devait empecher, et elle ne l'empechait que
    # sur les modules qu'on avait pense a lui donner.
    fonctions = {
        **fonctions_publiques(exercices),
        **fonctions_publiques(echauffements),
        **fonctions_publiques(positions),
    }

    with DESTINATION.open("w", encoding="utf-8") as fichier:
        # Les poses construites viennent **apres** : les premieres restent
        # celles d'avant, tirees de la meme graine.
        generateurs = (
            [pose_au_hasard] * nombre
            + [pose_bras_leves] * NOMBRE_POSES_DE_GESTE
            + [f for f in FAMILLES for _ in range(NOMBRE_POSES_PAR_FAMILLE)]
            + [pose_un_bras_leve] * NOMBRE_POSES_UN_BRAS
        )
        for generateur in generateurs:
            corps = generateur(rng)
            jetons = {
                nom: natif(fonction(corps)) for nom, fonction in fonctions.items()
            }
            ligne = {"landmarks": serialiser(corps), "jetons": jetons}
            fichier.write(json.dumps(ligne, ensure_ascii=False) + "\n")

    print(
        f"{nombre} poses au hasard, {NOMBRE_POSES_DE_GESTE} poses bras leves et "
        f"{NOMBRE_POSES_PAR_FAMILLE * len(FAMILLES)} poses construites et "
        f"{NOMBRE_POSES_UN_BRAS} poses un bras leve ecrites dans {DESTINATION}"
    )
    print(f"{len(fonctions)} fonctions couvertes :")
    for nom in sorted(fonctions):
        print(f"  {nom}")


if __name__ == "__main__":
    main()
