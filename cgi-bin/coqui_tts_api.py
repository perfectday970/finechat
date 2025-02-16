#!C:\Python\Python310\python.exe
# -*- coding: utf-8 -*-

import os
os.environ["MPLCONFIGDIR"] = "D:/xampp/temp_mpl"
#os.environ["TTS_ACCEPT_TOS"] = "true"
os.environ["COQUI_TOS_AGREED"] = "1"

import matplotlib
matplotlib.use("Agg")

import cgi
import sys
import uuid
from TTS.api import TTS
tts.to('cuda')
from TTS.utils.manage import ModelManager
# print HTTP-Header
print("Content-Type: audio/wav\n")

# 1) Coqui-Modell nur einmal laden (z.B. Thorsten, VITS)
# model_name = "tts_models/de/thorsten/vits"
# tts = TTS(model_name)
# tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
#manager = ModelManager()
#manager.set_agree_terms(True)

#tts = TTS(
#    model_name="tts_models/multilingual/multi-dataset/xtts_v2",
#    manager=manager,
#    gpu=True  # Falls gewünscht
#)
# Lokale Pfade zum entpackten Modell
model_path = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/model_file.pth"
config_path = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/config.json"

tts = TTS(model_path=model_path, config_path=config_path)

# 2) Form auslesen
form = cgi.FieldStorage()
text = form.getvalue("text", "").strip()

if not text:
    # Kein Text => leere WAV oder Fehler
    sys.exit(0)

# 3) Temporäre Datei
temp_file = f"D:/xampp/temp_mpl/coqui_{uuid.uuid4()}.wav"
tts.tts_to_file(text, file_path=temp_file)
#tts.tts_to_file(text, file_path=temp_file, language="de-de")

# 4) Datei auslesen + als HTTP-Response
with open(temp_file, "rb") as f:
    audio_data = f.read()

# Datei entfernen (auf Wunsch)
os.remove(temp_file)

sys.stdout.flush()
sys.stdout.buffer.write(audio_data)
