from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import uuid
# facebook
# from transformers import VitsModel, AutoTokenizer
# import scipy
# facebook end
import torch
from TTS.api import TTS

# Flask-App initialisieren
app = Flask(__name__)
CORS(app) # CORS für alle Routen aktivieren

# Pfad für temporäre Audio-Dateien
TEMP_DIR = "D:\\xampp\\temp_mpl"
os.makedirs(TEMP_DIR, exist_ok=True)

# TTS-Modell EINMALIG laden (Coqui-TTS)
# Thorsten
#TTS_MODEL_PATH = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/model_file.pth"
#TTS_CONFIG_PATH = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/config.json"
# XTTS-v2
TTS_MODEL_PATH = "D:/KI-Modelle/XTTS-v2/model.pth"
TTS_CONFIG_PATH = "D:/KI-Modelle/XTTS-v2/config.json"
TTS_MODEL_DIR = "D:/KI-Modelle/XTTS-v2"
# facebook
#model = VitsModel.from_pretrained("D:/KI-Modelle/mms-tts-deu")
#tokenizer = AutoTokenizer.from_pretrained("D:/KI-Modelle/mms-tts-deu")

print("Lade Coqui-TTS Modell...")
# Thorsten
#tts = TTS(model_path=TTS_MODEL_PATH, config_path=TTS_CONFIG_PATH)
#tts = TTS(checkpoint_path="D:/KI-Modelle/XTTS-v2/speakers_xtts.pth", config_path=TTS_CONFIG_PATH)
# XTTS-v2
tts = TTS(model_path=TTS_MODEL_DIR, config_path=TTS_CONFIG_PATH)
tts.to("cuda" if torch.cuda.is_available() else "cpu")
#tts.to("cpu")
print("TTS-Modell erfolgreich geladen.")


@app.route("/synthesize", methods=["POST"])
def synthesize():
    print("synthesize")
    """Synthesisiert Text zu Sprache (TTS)"""
    text = request.form.get("text", "").strip()
    # facebook
    #inputs = tokenizer(text, return_tensors="pt")

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Generate a unique filename
    temp_file = os.path.join(TEMP_DIR, f"coqui_{uuid.uuid4()}.wav")

    try:
        #facebook
        #torch.manual_seed(42)
        #with torch.no_grad():
        #    output = model(**inputs).waveform

       # waveform = output.squeeze().cpu().numpy()
       # print("Output shape:", output.shape)
       # print("Output dtype:", output.dtype)

        #waveform_int16 = (waveform * 32767).astype('int16')
      #  scipy.io.wavfile.write(temp_file, rate=model.config.sampling_rate, data=waveform_int16)
        # Thorsten
      #  tts.tts_to_file(text, file_path=temp_file, use_phonemes=False)
        try:
            # XTTS-v2
            tts.tts_to_file(
                text=text,
                file_path=temp_file,
                speaker_wav="D:/KI-Modelle/XTTS-v2/veit.wav",
                language="de")
        except Exception as e:
            print("Fehler beim Aufruf von tts_to_file:", e)


        # Sende WAV-Datei an den Client
        print(f"Dateipfad: {temp_file}")
        response = send_file(
            temp_file,
            mimetype='audio/wav',
            as_attachment=False,
            download_name=os.path.basename(temp_file)
        )
        return response
        # Return the file path to the distributor
        #return jsonify({"file_path": temp_file})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
"""
    print(f"/synthesize")
    print(f"text: {text}")

    if not text:
        return jsonify({"error": "Kein Text angegeben"}), 400

    # Temporäre Datei für die Sprachausgabe
    temp_file = os.path.join(TEMP_DIR, f"coqui_{uuid.uuid4()}.wav")

    try:
        tts.tts_to_file(text, file_path=temp_file, use_phonemes=False)

        # Sende WAV-Datei an den Client
        print(f"Dateipfad: {temp_file}")
        response = send_file(
            temp_file,
            mimetype='audio/wav',
            as_attachment=False,
            download_name=os.path.basename(temp_file)
        )
        return response

    except Exception as e:
        print(f"Fehler bei der TTS-Erzeugung: {e}")
        return jsonify({"error": str(e)}), 500

    finally:
        # Verzögertes Löschen, damit Audio-Player die Datei erst nutzen kann
        import threading
        def delayed_delete(path):
            import time
            time.sleep(5)  # 5 Sekunden warten, dann löschen
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Fehler beim Löschen der Datei {path}: {e}")

        threading.Thread(target=delayed_delete, args=(temp_file,)).start()

"""
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
