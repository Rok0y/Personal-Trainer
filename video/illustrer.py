"""Fait d'une video d'exercice l'illustration de sa fiche : detouree, redessinee en aplats, en boucle.

    python video/illustrer.py video/a_traiter/curl.mp4 "Curl biceps droit"
    python video/illustrer.py video/a_traiter/curl.mp4 "Curl biceps droit" --miroir "Curl biceps gauche"

Ecrit `web/static/videos/<fichier>`, ou `<fichier>` est `fichier_video` du nom
de l'exercice (`web/static/js/videos.js`, appele par node : la regle n'existe
qu'en JS, et l'application relit la video sous ce meme nom). H.264 sans son,
lisible par Safari, recadree sur le corps, en boucle.

**Une video d'exercice se montre en miroir** : l'utilisateur se voit en miroir
dans l'application (camera avant), et l'imite du meme cote de l'ecran. Pour un
exercice « droit », le membre qui travaille est donc a **droite** de l'image —
sinon il imiterait avec l'autre bras, et la detection, qui verifie le bras
droit, ne compterait rien. La prise est supposee en vue vraie, celle que
l'iPad enregistre par defaut (seul son apercu est en miroir) : le script la
retourne. `--miroir` ecrit en plus la vue vraie, qui est l'exercice du cote
oppose. Ne pas activer « Camera avant en miroir » sur l'appareil : la video
serait retournee deux fois.

Ecrit aussi `video/essais/<nom>/controle.png` (non versionne) : le detourage et
le rendu a quelques instants, puis le raccord de la boucle. C'est la qu'on
verifie le sens : seul un oeil sait si la prise etait deja en miroir.

Le detourage croise deux methodes qui se trompent en sens contraires :
- RobustVideoMatting (`video/modeles/`, non versionne) detoure le corps, trous
  compris (un t-shirt blanc devant un mur blanc), mais perd l'haltere : il a
  appris des personnes, pas des objets ;
- la piece vide, si la video commence par elle, voit tout ce qui a change dans
  la piece, haltere compris. On lui prend ce qui est a portee de main du corps.
Les secondes de piece vide se trouvent seules : ce sont les premieres images
ou RVM ne voit personne. Sans elles, on se contente du corps.

N'applique aucune regle du projet hormis le nom de fichier, emprunte au JS.
Demande opencv-python, numpy, onnxruntime et imageio-ffmpeg.
"""

import argparse
import hashlib
import json
import os
import subprocess

import cv2
import numpy as np

MOUVEMENTS = "web/static/donnees/mouvements.json"
DESTINATION = "web/static/videos"
ESSAIS = "video/essais"

MODELE = "video/modeles/rvm_resnet50_fp32.onnx"
MODELE_URL = "https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_resnet50_fp32.onnx"
# Le fichier inspecte a son telechargement (operations standard seulement,
# aucune donnee hors du fichier). Un autre fichier sous ce nom est refuse.
MODELE_SHA256 = "25db300fcb6ee27f941a1b52c97856e8d1f13c7f35817f81a612f89af0e8a85c"
# RVM travaille sur une image reduite a ce cote, puis affine a pleine taille.
RVM_COTE = 512


def _bgr(hexa):
    """`#rrggbb` -> (b, g, r), l'ordre d'OpenCV."""
    return tuple(int(hexa[i:i + 2], 16) for i in (5, 3, 1))


# Couleurs de `web/static/palette.css` : les videos s'affichent sur ce fond.
FOND = _bgr("#0a0d13")
TEXTE = _bgr("#f4f2ec")
ENCRE = _bgr("#11141a")

HAUTEUR = 720
# Part de l'image que le corps doit couvrir pour que quelqu'un soit la.
PRESENCE_MIN = 0.002
# Il faut au moins ce nombre d'images de piece vide pour en tirer un fond.
VIDE_MIN = 15
# Secondes ecartees juste avant que RVM voie quelqu'un : un bras qui entre par
# le bord ne compte pas encore comme une presence, mais il salit le fond.
MARGE_VIDE = 1.0
VIDE_MAX = 45

# Piece vide : ecart de couleur (Lab d'OpenCV, 0-255) au-dela duquel un pixel
# a change. Le seuil se calibre sur le bruit des secondes vides ; voici son
# plancher, et sa marge au-dessus du bruit.
SEUIL_MIN = 18
MARGE_BRUIT = 1.6
# La luminosite compte moins que la teinte (penombres, reflets).
POIDS_LUMINANCE = 0.5
# Distance au corps (pixels a 720 de haut) en deca de laquelle un changement de
# la piece est un objet tenu : un haltere depasse de la main d'une demi-barre.
PORTEE_OBJETS = 70
# Un trou ferme dans le corps plus petit que cette part de l'image est bouche.
TROU_MAX = 0.01

# Une image sur combien sert a choisir la palette des aplats.
PAS_PALETTE = 10
MAX_PIXELS_PALETTE = 200_000
COULEURS = 7
# Une frontiere entre deux couleurs de la palette ne devient un trait qu'au-dela
# de cet ecart (Lab) : en deca, c'est un degrade d'eclairage, pas un contour.
ECART_TRAIT = 35

# La boucle commence dans les premiers BORD de la presence et finit dans les
# derniers, et dure au moins LONGUEUR_MIN secondes.
BORD = 0.4
LONGUEUR_MIN = 2.0
# Images fondues au raccord.
FONDU = 8
# Marge autour du corps dans le cadre final (pixels a 720 de haut).
MARGE_CADRE = 24


# ---------------------------------------------------------------- noms


def nom_de_fichier(*noms):
    """Le fichier video de chaque exercice, par le module JS qui en porte la regle."""
    code = (
        "import { fichier_video } from './web/static/js/videos.js';"
        "console.log(JSON.stringify(process.argv.slice(1).map(fichier_video)))"
    )
    sortie = subprocess.run(
        ["node", "--input-type=module", "-e", code, *noms], capture_output=True, text=True, check=True
    )
    return json.loads(sortie.stdout)


def verifier_exercices(*noms):
    with open(MOUVEMENTS, encoding="utf-8") as f:
        connus = set(json.load(f))
    for nom in noms:
        if nom not in connus:
            raise SystemExit(f"« {nom} » n'est pas un exercice de {MOUVEMENTS}. Exercices : {', '.join(sorted(connus))}")


# ---------------------------------------------------------------- lecture


def redimensionner(image):
    h, w = image.shape[:2]
    echelle = min(1.0, HAUTEUR / h)
    # Dimensions paires : le H.264 en yuv420p les exige.
    nw, nh = max(2, round(w * echelle / 2) * 2), max(2, round(h * echelle / 2) * 2)
    if (nw, nh) == (w, h):
        return image
    return cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)


def lire(chemin, premiere=0, derniere=None):
    """(indice, image) de `premiere` a `derniere` (exclue), redimensionnees."""
    capture = cv2.VideoCapture(chemin)
    if not capture.isOpened():
        raise SystemExit(f"Impossible d'ouvrir {chemin}")
    index = 0
    while derniere is None or index < derniere:
        ok, image = capture.read()
        if not ok:
            break
        if index >= premiere:
            yield index, redimensionner(image)
        index += 1
    capture.release()


# ---------------------------------------------------------------- detourage


def noyau(taille):
    taille = max(1, int(round(taille))) | 1
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (taille, taille))


class Detoureur:
    """RobustVideoMatting : l'opacite du corps, image apres image.

    Le modele garde une memoire d'une image a l'autre (`etat`) : c'est ce qui
    rend son detourage stable dans le temps. Il faut donc lui donner les
    images dans l'ordre, sans en sauter.
    """

    def __init__(self):
        import onnxruntime

        if not os.path.exists(MODELE):
            raise SystemExit(f"Modele absent. Le telecharger dans {MODELE} :\n  {MODELE_URL}")
        empreinte = hashlib.sha256()
        with open(MODELE, "rb") as f:
            for bloc in iter(lambda: f.read(1 << 20), b""):
                empreinte.update(bloc)
        if empreinte.hexdigest() != MODELE_SHA256:
            raise SystemExit(f"{MODELE} n'est pas le fichier inspecte (empreinte differente) : refuse.")
        self.session = onnxruntime.InferenceSession(MODELE, providers=["CPUExecutionProvider"])
        self.etat = None

    def opacite(self, image):
        h, w = image.shape[:2]
        src = (image[..., ::-1].transpose(2, 0, 1)[None] / 255).astype(np.float32)
        ratio = np.array([min(1.0, RVM_COTE / max(h, w))], np.float32)
        # Sans memoire, la premiere image est detouree a l'aveugle : on la
        # repasse quelques fois pour amorcer.
        passes = 1 if self.etat else 10
        if not self.etat:
            self.etat = [np.zeros((1, 1, 1, 1), np.float32)] * 4
        for _ in range(passes):
            _, pha, *self.etat = self.session.run(
                None,
                {"src": src, "r1i": self.etat[0], "r2i": self.etat[1], "r3i": self.etat[2], "r4i": self.etat[3],
                 "downsample_ratio": ratio},
            )
        return pha[0, 0]


def lab_flou(image):
    return cv2.cvtColor(cv2.GaussianBlur(image, (5, 5), 0), cv2.COLOR_BGR2LAB).astype(np.float32)


class PieceVide:
    """Le fond tire des premieres images sans personne, et ce qui s'en ecarte."""

    def __init__(self, images):
        images = images[:: max(1, len(images) // VIDE_MAX)]
        self.lab = lab_flou(np.median(np.stack(images), axis=0).astype(np.uint8))
        bruit = max(np.percentile(self.ecart(i), 99.5) for i in images)
        self.seuil = max(SEUIL_MIN, MARGE_BRUIT * bruit)
        print(f"Piece vide : {len(images)} images, bruit {bruit:.1f}, seuil {self.seuil:.1f}")

    def ecart(self, image):
        d = lab_flou(image) - self.lab
        d[..., 0] *= POIDS_LUMINANCE
        return np.sqrt((d * d).sum(axis=2))

    def objets(self, image, corps):
        """Ce qui a change dans la piece a portee de main du corps."""
        echelle = image.shape[0] / 720
        change = (self.ecart(image) > self.seuil).astype(np.uint8) * 255
        change = cv2.morphologyEx(change, cv2.MORPH_OPEN, noyau(3 * echelle))
        return cv2.bitwise_and(change, cv2.dilate(corps, noyau(PORTEE_OBJETS * echelle)))


def nettoyer(masque):
    """Ne garde que le corps et ce qui lui est comparable, bouche les trous fermes."""
    h, w = masque.shape
    masque = cv2.morphologyEx(masque, cv2.MORPH_CLOSE, noyau(5 * h / 720))
    n, zones, stats, _ = cv2.connectedComponentsWithStats(masque, connectivity=8)
    if n > 1:
        aires = stats[1:, cv2.CC_STAT_AREA]
        garder = np.zeros(n, bool)
        garder[1:] = (aires >= 0.15 * aires.max()) & (aires >= 0.001 * h * w)
        masque = np.where(garder[zones], 255, 0).astype(np.uint8)
    # Un fond entoure par le corps (mains sur les hanches) est du vrai fond,
    # d'ou la limite de taille ; dans les exercices du catalogue, l'espace
    # entre les membres reste ouvert sur un cote.
    n, zones, stats, _ = cv2.connectedComponentsWithStats(255 - masque, connectivity=4)
    x, y, lw, lh, aire = (stats[:, k] for k in range(5))
    touche_le_bord = (x == 0) | (y == 0) | (x + lw == w) | (y + lh == h)
    boucher = ~touche_le_bord & (aire < TROU_MAX * h * w)
    boucher[0] = False
    masque[boucher[zones]] = 255
    return masque


# ---------------------------------------------------------------- analyse


class Analyse:
    """Premier passage : le masque de chaque image, et de quoi choisir palette et boucle."""

    def __init__(self, chemin):
        capture = cv2.VideoCapture(chemin)
        self.fps = capture.get(cv2.CAP_PROP_FPS) or 30.0
        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
        capture.release()

        detoureur = Detoureur()
        piece = None
        vides = []
        self.masques = []  # bits empaquetes : 115 Ko par image au lieu de 900
        self.formes = []  # le masque en vignette, pour comparer deux poses
        self.presents = []
        self.echantillons = []  # (indice, pixels Lab du corps)
        personne_vue = False

        for index, image in lire(chemin):
            corps = ((detoureur.opacite(image) > 0.5) * 255).astype(np.uint8)
            present = corps.mean() / 255 > PRESENCE_MIN
            if not personne_vue and not present:
                vides.append(image)
            elif not personne_vue:
                personne_vue = True
                vides = vides[: max(0, len(vides) - int(MARGE_VIDE * self.fps))]
                if len(vides) >= VIDE_MIN:
                    piece = PieceVide(vides)
                else:
                    print("Pas de piece vide au debut : detourage du corps seul (un haltere peut manquer).")
                vides = None
            if piece is not None and present:
                corps = cv2.bitwise_or(corps, piece.objets(image, corps))
            masque = nettoyer(corps) if present else corps

            self.forme = masque.shape
            self.masques.append(np.packbits(masque > 0))
            self.formes.append(cv2.resize(masque, (64, 36), interpolation=cv2.INTER_AREA).ravel() / 255)
            self.presents.append(present)
            if present and index % PAS_PALETTE == 0:
                coeur = cv2.erode(masque, noyau(9))
                self.echantillons.append((index, cv2.cvtColor(lisser(image), cv2.COLOR_BGR2LAB)[coeur > 0]))
            if index % 30 == 0:
                print(f"  analyse {index}/{total}", end="\r")
        print()
        if not any(self.presents):
            raise SystemExit("Personne n'a ete vu dans la video.")
        self.formes = np.array(self.formes, np.float32)

    def masque(self, index):
        """Le masque d'une image, vote a la majorite avec ses deux voisines.

        Un pixel qui clignote d'une image a l'autre est du bruit ; le vote
        l'efface sans la trainee qu'aurait une moyenne glissante.
        """
        def brut(i):
            return np.unpackbits(self.masques[i])[: np.prod(self.forme)].reshape(self.forme) * 255

        if index == 0 or index == len(self.masques) - 1:
            return brut(index)
        a, b, c = brut(index - 1), brut(index), brut(index + 1)
        return ((a & b) | (a & c) | (b & c)).astype(np.uint8)

    def boucle(self, debut, fin):
        """(i, j) : la boucle joue les images i a j-1, et l'image j ressemble a i.

        On cherche i au debut de la presence, j a la fin, et la paire dont les
        silhouettes se ressemblent le plus.
        """
        presents = np.flatnonzero(self.presents)
        premiere = max(presents[0], int(debut * self.fps), FONDU)
        derniere = min(presents[-1], len(self.presents) - 1 if fin is None else int(fin * self.fps))
        duree = derniere - premiere
        if duree < LONGUEUR_MIN * self.fps:
            raise SystemExit("Moins de deux secondes de presence : impossible d'en faire une boucle.")
        bord = max(1, int(BORD * duree))
        departs = np.arange(premiere, premiere + bord)
        arrivees = np.arange(derniere - bord, derniere + 1)
        a, b = self.formes[departs], self.formes[arrivees]
        # |a - b|² sans materialiser toutes les differences.
        distances = (a * a).sum(1)[:, None] + (b * b).sum(1)[None] - 2 * a @ b.T
        trop_court = arrivees[None] - departs[:, None] < LONGUEUR_MIN * self.fps
        distances[trop_court] = np.inf
        di, dj = np.unravel_index(np.argmin(distances), distances.shape)
        i, j = int(departs[di]), int(arrivees[dj])
        print(f"Boucle : {i / self.fps:.1f} s -> {j / self.fps:.1f} s ({(j - i) / self.fps:.1f} s), "
              f"ecart du raccord {distances[di, dj] / a.shape[1]:.3f}")
        return i, j

    def cadre(self, i, j):
        """Le rectangle qui contient le corps sur toute la boucle, marge comprise."""
        union = np.zeros(self.forme, np.uint8)
        for index in range(i - FONDU, j):
            union |= self.masque(index)
        x, y, w, h = cv2.boundingRect(union)
        marge = int(MARGE_CADRE * self.forme[0] / 720)
        x0, y0 = max(0, x - marge), max(0, y - marge)
        x1, y1 = min(self.forme[1], x + w + marge), min(self.forme[0], y + h + marge)
        # Dimensions paires, pour le H.264.
        x1 -= (x1 - x0) % 2
        y1 -= (y1 - y0) % 2
        return slice(y0, y1), slice(x0, x1)

    def palette(self, i, j):
        """Les couleurs des aplats, choisies une fois sur toute la boucle.

        Une palette par image ferait scintiller le resultat : la meme manche
        changerait de teinte d'une image a l'autre.
        """
        pixels = [p for index, p in self.echantillons if i - FONDU <= index < j]
        pixels = np.concatenate(pixels)
        if len(pixels) > MAX_PIXELS_PALETTE:
            pixels = pixels[np.random.default_rng(0).choice(len(pixels), MAX_PIXELS_PALETTE, replace=False)]
        cv2.setRNGSeed(0)
        criteres = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.5)
        _, _, centres = cv2.kmeans(pixels.astype(np.float32), COULEURS, None, criteres, 5, cv2.KMEANS_PP_CENTERS)
        centres = centres[np.argsort(centres[:, 0])]
        return centres, cv2.cvtColor(centres.astype(np.uint8)[None], cv2.COLOR_LAB2BGR)[0]


# ---------------------------------------------------------------- rendu


def lisser(image):
    """Aplatit les textures (plis, grain) en gardant les bords."""
    return cv2.bilateralFilter(image, 9, 60, 9)


def etiqueter(image, centres, echelle):
    """Chaque pixel -> l'indice de la couleur de palette la plus proche."""
    lab = cv2.cvtColor(lisser(image), cv2.COLOR_BGR2LAB).astype(np.float32)
    h, w = lab.shape[:2]
    # |x - c|² = |x|² - 2 x.c + |c|², et |x|² ne change pas le plus proche.
    distances = (centres ** 2).sum(axis=1)[None] - 2 * lab.reshape(-1, 3) @ centres.T
    etiquettes = distances.argmin(axis=1).astype(np.uint8).reshape(h, w)
    # Le filtre median rend toujours une valeur presente dans sa fenetre : il
    # efface les ilots d'une couleur sans en inventer une.
    return cv2.medianBlur(etiquettes, int(7 * echelle) | 1)


def frontieres(etiquettes, contrastees):
    """Les pixels ou l'on passe d'une couleur a une autre assez differente."""
    f = np.zeros(etiquettes.shape, bool)
    f[:, 1:] |= contrastees[etiquettes[:, 1:], etiquettes[:, :-1]]
    f[1:, :] |= contrastees[etiquettes[1:, :], etiquettes[:-1, :]]
    return f.astype(np.uint8) * 255


def opacite(masque, flou=5):
    """Un masque 0/255 -> une opacite 0-1 aux bords adoucis."""
    return cv2.GaussianBlur(masque.astype(np.float32) / 255, (flou, flou), 0)[..., None]


def poser(dessous, couleur, alpha):
    """Pose une couleur (ou une image) sur `dessous`, a l'opacite `alpha`."""
    return dessous * (1 - alpha) + np.asarray(couleur, np.float32) * alpha


class Aplats:
    """Le style retenu : couleurs en aplats, traits sombres, contour clair."""

    def __init__(self, centres, palette_bgr):
        self.centres = centres
        self.palette = palette_bgr
        distances = np.sqrt(((centres[:, None] - centres[None]) ** 2).sum(axis=2))
        self.contrastees = distances > ECART_TRAIT

    def rendre(self, image, masque):
        echelle = image.shape[0] / 720
        etiquettes = etiqueter(image, self.centres, echelle)
        interieur = cv2.erode(masque, noyau(5 * echelle))
        lignes = cv2.dilate(cv2.bitwise_and(frontieres(etiquettes, self.contrastees), interieur), noyau(2 * echelle))
        contour = cv2.morphologyEx(masque, cv2.MORPH_GRADIENT, noyau(4 * echelle))

        corps = poser(self.palette[etiquettes].astype(np.float32), ENCRE, opacite(lignes, 3))
        rendu = poser(np.full(image.shape, FOND, np.float32), corps, opacite(masque))
        rendu = poser(rendu, TEXTE, opacite(contour, 3))
        return np.clip(rendu, 0, 255).astype(np.uint8)


# ---------------------------------------------------------------- ecriture


class Ecrivain:
    """Une video H.264 sans son, lisible par Safari."""

    def __init__(self, chemin, fps, largeur, hauteur):
        import imageio_ffmpeg

        self.processus = subprocess.Popen(
            [
                imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{largeur}x{hauteur}", "-r", f"{fps}",
                "-i", "-", "-an",
                # `animation` : le reglage de x264 pour les grands aplats.
                "-c:v", "libx264", "-tune", "animation", "-crf", "24", "-preset", "slow", "-pix_fmt", "yuv420p",
                # L'index en tete : la video demarre avant d'etre entierement telechargee.
                "-movflags", "+faststart",
                chemin,
            ],
            stdin=subprocess.PIPE,
        )

    def ecrire(self, image):
        self.processus.stdin.write(np.ascontiguousarray(image).tobytes())

    def fermer(self):
        self.processus.stdin.close()
        if self.processus.wait():
            raise SystemExit("ffmpeg a echoue.")


def vignette(image, hauteur=300):
    h, w = image.shape[:2]
    return cv2.resize(image, (max(1, round(w * hauteur / h)), hauteur), interpolation=cv2.INTER_AREA)


def controle(chemin, paires, raccord, exercice):
    """Planche de controle : le sens a verifier, detourage au-dessus du rendu, puis le raccord."""
    colonnes = [np.vstack([vignette(a), vignette(b)]) for a, b in paires]
    fin, debut = (vignette(x) for x in raccord)
    separation = np.full((fin.shape[0], 6, 3), TEXTE, np.uint8)
    raccord = np.hstack([fin, separation, debut])
    largeur = sum(c.shape[1] for c in colonnes)
    raccord = np.pad(raccord, ((0, 0), (0, max(0, largeur - raccord.shape[1])), (0, 0)))
    haut = np.hstack(colonnes)
    haut = np.pad(haut, ((0, 0), (0, max(0, raccord.shape[1] - haut.shape[1])), (0, 0)))
    # OpenCV n'ecrit pas les accents : le rappel est en ASCII.
    rappel = np.full((40, haut.shape[1], 3), FOND, np.uint8)
    cv2.putText(rappel, f"{exercice} - vue miroir : un exercice 'droit' travaille a DROITE de l'image",
                (10, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.6, TEXTE, 1, cv2.LINE_AA)
    cv2.imwrite(chemin, np.vstack([rappel, haut, raccord]))


# ---------------------------------------------------------------- programme


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("video")
    parser.add_argument("exercice", help="le nom exact de l'exercice dans mouvements.json")
    parser.add_argument("--miroir", help="ecrire aussi la vue vraie, pour cet exercice (le cote oppose)")
    parser.add_argument("--debut", type=float, default=0.0, help="ne pas commencer la boucle avant (secondes)")
    parser.add_argument("--fin", type=float, help="ne pas finir la boucle apres (secondes)")
    args = parser.parse_args()

    exercices = [args.exercice] + ([args.miroir] if args.miroir else [])
    verifier_exercices(*exercices)
    fichiers = nom_de_fichier(*exercices)
    os.makedirs(DESTINATION, exist_ok=True)
    essais = os.path.join(ESSAIS, os.path.splitext(fichiers[0])[0])
    os.makedirs(essais, exist_ok=True)

    analyse = Analyse(args.video)
    i, j = analyse.boucle(args.debut, args.fin)
    lignes, colonnes = analyse.cadre(i, j)
    centres, palette_bgr = analyse.palette(i, j)
    aplats = Aplats(centres, palette_bgr)

    hauteur, largeur = lignes.stop - lignes.start, colonnes.stop - colonnes.start
    chemins = [os.path.join(DESTINATION, f) for f in fichiers]
    ecrivains = [Ecrivain(c, analyse.fps, largeur, hauteur) for c in chemins]

    # Les FONDU images avant i sont rendues d'abord : les dernieres images de
    # la boucle s'y fondent, si bien que la fin rejoint en douceur l'image i.
    amorce = []
    instants = set(np.linspace(i, j - 1, 4).astype(int))
    paires = []
    for index, image in lire(args.video, i - FONDU, j):
        # En miroir des le depart : rendu, controle et raccord sont tous dans
        # le sens que l'utilisateur verra.
        image = cv2.flip(image[lignes, colonnes], 1)
        masque = cv2.flip(analyse.masque(index)[lignes, colonnes], 1)
        rendu = aplats.rendre(image, masque)
        if index < i:
            amorce.append(rendu)
            continue
        if index == i:
            premiere = rendu
        rang = index - (j - FONDU)
        if rang >= 0:
            poids = (rang + 1) / (FONDU + 1)
            rendu = cv2.addWeighted(rendu, 1 - poids, amorce[rang], poids, 0)
        if index in instants:
            paires.append((np.where(masque[..., None] > 0, image, (image * 0.25).astype(np.uint8)), rendu))
        ecrivains[0].ecrire(rendu)
        if len(ecrivains) > 1:
            # Retournee une seconde fois : la vue vraie, qui est l'exercice oppose.
            ecrivains[1].ecrire(cv2.flip(rendu, 1))
        if index % 30 == 0:
            print(f"  rendu {index - i}/{j - i}", end="\r")
    print()
    for ecrivain in ecrivains:
        ecrivain.fermer()

    controle(os.path.join(essais, "controle.png"), paires, (rendu, premiere), args.exercice)
    for chemin in chemins:
        print(f"Ecrit {chemin} ({os.path.getsize(chemin) // 1024} Ko, {largeur}x{hauteur})")
    print(f"Controle : {essais}/controle.png")


if __name__ == "__main__":
    main()
