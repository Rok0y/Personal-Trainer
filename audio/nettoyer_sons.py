from pydub import AudioSegment
from pydub.silence import detect_nonsilent
import os


SOURCE = "audio/a_traiter"
DESTINATION = "audio/fichiers"


os.makedirs(
    DESTINATION,
    exist_ok=True
)


def nettoyer(fichier):

    chemin_source = os.path.join(
        SOURCE,
        fichier
    )

    chemin_destination = os.path.join(
        DESTINATION,
        fichier
    )

    audio = AudioSegment.from_file(
        chemin_source
    )

    zones = detect_nonsilent(
        audio,
        min_silence_len=300,
        silence_thresh=-35
    )

    if not zones:
        print("Aucun son :", fichier)
        return


    debut = max(
        0,
        zones[0][0] - 50
    )

    fin = min(
        len(audio),
        zones[-1][1] + 150
    )


    audio = audio[debut:fin]


    audio = (
        audio
        .fade_in(30)
        .fade_out(150)
    )


    audio.export(
        chemin_destination,
        format="wav"
    )


    print(
        "Traité :",
        fichier
    )


for fichier in os.listdir(SOURCE):

    if fichier.endswith(".wav"):
        nettoyer(fichier)