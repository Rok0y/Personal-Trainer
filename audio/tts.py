import wave
import hashlib
from pathlib import Path
from piper import PiperVoice

DOSSIER_CACHE = Path(__file__).with_name("Fichiers") / "tts_cache"
DOSSIER_CACHE.mkdir(parents=True, exist_ok=True)

# Adapte le chemin selon où download_voices a mis le modèle
CHEMIN_MODELE = Path(__file__).with_name("voix") / "fr_FR-tom-medium.onnx"

_voix = None


def _charger_voix():
    global _voix
    if _voix is None:
        _voix = PiperVoice.load(str(CHEMIN_MODELE))
    return _voix


def chemin_cache(texte):
    cle = hashlib.sha1(texte.encode("utf-8")).hexdigest()
    return DOSSIER_CACHE / f"{cle}.wav"


def generer(texte):
    """Renvoie le chemin d'un .wav pour ce texte (généré une seule fois, puis mis en cache)."""
    chemin = chemin_cache(texte)

    if chemin.exists():
        return chemin

    voix = _charger_voix()
    with wave.open(str(chemin), "wb") as fichier_wav:
        voix.synthesize_wav(texte, fichier_wav)

    return chemin


def prechauffer(phrases):
    """À appeler au démarrage pour générer les phrases fréquentes à l'avance."""
    for texte in phrases:
        generer(texte)