from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
from transformers import StoppingCriteria, StoppingCriteriaList
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import os
import uuid
import torch
from TTS.api import TTS

class EndOfTurnCriteria(StoppingCriteria):
    def __init__(self, stop_token_id):
        super().__init__()
        self.stop_token_id = stop_token_id

    def __call__(self, input_ids, scores, **kwargs):
        # Check if last token is the stop token
        return input_ids[0][-1] == self.stop_token_id

# Flask-App initialisieren
app = Flask(__name__)
CORS(app)  # CORS für alle Routen aktivieren

# Pfad für temporäre Audio-Dateien
TEMP_DIR = "D:/xampp/temp_mpl"
os.makedirs(TEMP_DIR, exist_ok=True)


# DeepSeek-R1-Distill-Qwen-32B Modell laden
MODEL_PATH = "D:/KI-Modelle/DeepSeek-R1-Distill-Qwen-1.5B"
#MODEL_PATH = "D:/KI-Modelle/DeepSeek-R1-Distill-Llama-8B"
#MODEL_PATH = "D:/KI-Modelle/Llama-3.2-3B-Hermes"

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True
)
try:
    print("Lade DeepSeek Modell...")
    #bnb_config = BitsAndBytesConfig(load_in_8bit=True)  # Nutze 8-bit Quantisierung
    #bnb_config = BitsAndBytesConfig(load_in_4bit=True)  # Speicheroptimierung
    bnb_config = BitsAndBytesConfig()

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_PATH,
        quantization_config=bnb_config,
        torch_dtype="auto",
        device_map="auto",
        trust_remote_code=True
    )

    print("Modell erfolgreich geladen!")
except Exception as e:
    print(f"Fehler beim Laden des Modells: {str(e)}")


print("Modelle erfolgreich geladen!")

# TTS-Modell EINMALIG laden (Coqui-TTS)
#TTS_MODEL_PATH = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/model_file.pth"
#TTS_CONFIG_PATH = "D:/KI-Modelle/my_coqui_models/thorsten_vits/VITS/config.json"

#print("Lade Coqui-TTS Modell...")
#tts = TTS(model_path=TTS_MODEL_PATH, config_path=TTS_CONFIG_PATH)
#tts.to("cuda" if torch.cuda.is_available() else "cpu")
#print("TTS-Modell erfolgreich geladen.")

@app.route("/generate", methods=["POST"])
def generate():
#Verarbeitet eine Textanfrage und gibt die KI-Antwort zurück
    data = request.json
    prompt = data.get("text", "")
    processingUnit = data.get("processingUnit", "").strip()
    firstMessage = data.get("firstMessage", "")
    systemPrompt = data.get("systemPrompt", "")

    LlamaLike = False

    print(f"/generate")

    print(f"systemPrompt: -{systemPrompt}-")

    if LlamaLike:
        """      # Konvertiere den Chatverlauf in ein geeignetes Format für den Tokenizer
           prompt = "\n".join([f"<|im_start|>{msg['role']}\n {msg['content']}<|im_end|>" for msg in prompt])
           prompt = prompt + "\n<|im_start|>assistent\n"

           if firstMessage and systemPrompt != "":
               prompt_template = f'''<|im_start|>system\n {systemPrompt}<|im_end|>\n<|im_start|>assistent\n <think>The user wants me to be a helpful assistant and respond simply and directly.</think> Ok, I will stick to it. <|im_end|>{prompt}
               '''
               prompt = prompt_template"""
    else:
        # Konvertiere den Chatverlauf in ein geeignetes Format für den Tokenizer
        prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in prompt])
        prompt = prompt + "\n asisstent: <think>"
        if firstMessage and systemPrompt != "":
            prompt_template = f'''user: {systemPrompt} \nassistent: <think>The user wants me to be an helpful assistant and respond simple and directly. </think>\n Ok, i will stick to it. \nuser: Are you ready to start?\nassistent: Yes, let's start :)\n{prompt} 
            '''
            prompt = prompt_template

    print(f"Prompt: {prompt}")
    print(f"processingUnit: {processingUnit}")


    answer_tokens = 500
    #if not isinstance(prompt, str) or not prompt.strip():
      #  return jsonify({"error": "Ungültiger Eingabetext."}), 400

    if LlamaLike:

        # Get the stop token ID from tokenizer
        stop_token = "<|im_end|>"
        stop_token_id = tokenizer.convert_tokens_to_ids(stop_token)
        # Create stopping criteria
        stopping_criteria = StoppingCriteriaList([EndOfTurnCriteria(stop_token_id)])

        chat_history = [
            {"role": "user", "content": "Hello!"},
            {"role": "assistant", "content": "I am here."},
            {"role": "user", "content": "What is your name?"},
        ]
        print(f"chat_history: {chat_history}")
        input = tokenizer.apply_chat_template(
            prompt, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        ).to(model.device)

        attention_mask = input.ne(tokenizer.pad_token_id).to(model.device)

        output = model.generate(
            input,
            attention_mask=attention_mask,
            repetition_penalty=1.05,
            max_new_tokens=answer_tokens,
            eos_token_id=stop_token_id,
            stopping_criteria=stopping_criteria,
            pad_token_id=tokenizer.eos_token_id
        )
    else:
        # Eingabetext tokenisieren und KI-Text generieren
        if processingUnit == "gpu":
            inputs = tokenizer(prompt, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
        else:
            inputs = tokenizer(prompt, return_tensors="pt").to("cpu")

        output = model.generate(
            **inputs,
            max_new_tokens=answer_tokens, # Maximale Länge der Antwort
            temperature=0.6,  # Kontrolliert die Kreativität (niedriger = deterministischer) # Steuert, wie fokussiert die Antwort bleibt
            do_sample=True,  # Aktiviert zufällige Generierung
            repetition_penalty=1.1,  # Verhindert endlose Wiederholungen
            no_repeat_ngram_size=2
        )

    response_text = tokenizer.decode(output[0], skip_special_tokens=True)
    #response_text = tokenizer.decode(output[0])
    """
    response_text = tokenizer.decode(
        output[0][len(input[0]):], skip_special_tokens=True
    )"""

    # Überprüfen, ob die Antwort zu lang ist
    if len(output[0]) >= (answer_tokens+400):
        response_text = "<error>Fehler: Die Antwort des Assistenten ist zu lang.</error>"
    else:

        if response_text.startswith(prompt):
            response_text = response_text[len(prompt):].strip()

        print(f"response_text: {response_text}")

        # Überprüfen, ob kein öffnendes <think> vorhanden ist, aber ein schließendes </think>
        if not response_text.startswith("<think>") and "</think>" in response_text:
            response_text = f"<think>\n{response_text.strip()}"

        if not response_text.startswith("<think>") and "</think>" not in response_text:
            # Suche nach zwei Zeilenumbrüchen (\n\n)
            double_newline_index = response_text.find("\n\n")
            if double_newline_index != -1:
                # Füge <think> am Anfang hinzu und ersetze \n\n durch </think>
                response_text = f"<thinking>\n{response_text[:double_newline_index]}</thinking>{response_text[double_newline_index + 2:]}"

        # Füge <|im_end|> am Ende hinzu, falls noch nicht vorhanden
        if not response_text.endswith("<|im_end|>") and LlamaLike:
            response_text += "<|im_end|>"

    return jsonify({"response": response_text})


@app.route("/synthesize", methods=["POST"])
def synthesize():
    """Synthesisiert Text zu Sprache (TTS)"""
    text = request.form.get("text", "").strip()

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


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
