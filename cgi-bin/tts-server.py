from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import uuid
import torch
from TTS.api import TTS

# Flask-App initialisieren
app = Flask(__name__)
CORS(app) # CORS für alle Routen aktivieren

# Pfad für temporäre Audio-Dateien
TEMP_DIR = "D:\\xampp\\temp_mpl"
os.makedirs(TEMP_DIR, exist_ok=True)

# TTS-Modell EINMALIG laden (Coqui-TTS)
TTS_MODEL_PATH = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/model_file.pth"
TTS_CONFIG_PATH = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/config.json"

print("Lade Coqui-TTS Modell...")
tts = TTS(model_path=TTS_MODEL_PATH, config_path=TTS_CONFIG_PATH)
tts.to("cuda" if torch.cuda.is_available() else "cpu")
#tts.to("cpu")
print("TTS-Modell erfolgreich geladen.")


@app.route("/synthesize", methods=["POST"])
def synthesize():
    """Synthesisiert Text zu Sprache (TTS)"""
    text = request.form.get("text", "").strip()

    if not text:
        return jsonify({"error": "No text provided"}), 400

    # Generate a unique filename
    temp_file = os.path.join(TEMP_DIR, f"coqui_{uuid.uuid4()}.wav")

    try:
        # Generate the audio file
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
