from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import os
import uuid
from TTS.api import TTS

# Flask App initialisieren
app = Flask(__name__)
CORS(app)  # CORS für alle Routen aktivieren

# TTS-Modell EINMALIG laden (bleibt im Speicher)
MODEL_PATH = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/model_file.pth"
CONFIG_PATH = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/config.json"

print("Lade Coqui-TTS Modell...")
tts = TTS(model_path=MODEL_PATH, config_path=CONFIG_PATH)
tts.to("cuda")  # Falls CUDA vorhanden ist, sonst "cpu"
print("Modell erfolgreich geladen.")

# Pfad für temporäre Dateien
TEMP_DIR = "D:/xampp/temp_mpl"
os.makedirs(TEMP_DIR, exist_ok=True)


@app.route("/synthesize", methods=["POST"])
def synthesize():
    """Synthesisiert Text zu Sprache (TTS)"""
    text = request.form.get("text", "").strip()

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
            time.sleep(512)  # 3 Sekunden warten, dann löschen
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception as e:
                print(f"Fehler beim Löschen der Datei {path}: {e}")

        threading.Thread(target=delayed_delete, args=(temp_file,)).start()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
