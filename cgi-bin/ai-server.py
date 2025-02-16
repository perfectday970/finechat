from flask import Flask, request, send_file, jsonify, Response
from flask_cors import CORS
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    GenerationConfig,
    StoppingCriteria,
    StoppingCriteriaList,
    TextIteratorStreamer
)
import os
import uuid
import torch
from threading import Thread
import json

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
#MODEL_PATH = "D:/KI-Modelle/DeepSeek-R1-Distill-Qwen-1.5B"
#MODEL_PATH = "D:/KI-Modelle/deepseek-llm-7b-chat"
#MODEL_PATH = "D:/KI-Modelle/DeepSeek-R1-Distill-Llama-8B"
MODEL_PATH = "D:/KI-Modelle/Llama-3.2-3B-Hermes"
LlamaLike = True

tokenizer = AutoTokenizer.from_pretrained(
    MODEL_PATH,
    trust_remote_code=True
)

try:
    print(f"Lade {MODEL_PATH}...")
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

@app.route("/generate", methods=["POST"])
def generate():
    data = request.json
    chat_history = data.get("chat_history", "")
    processingUnit = data.get("processingUnit", "").strip()
    firstMessage = data.get("firstMessage", "")
    systemPrompt = data.get("systemPrompt", "")

    print(f"/generate")
    print(f"systemPrompt: -{systemPrompt}-")
    print(f"chat_history: {chat_history}")
    print(f"processingUnit: {processingUnit}")

    answer_tokens = 500

    if LlamaLike:
        stop_token = "<|im_end|>"
        stop_token_id = tokenizer.convert_tokens_to_ids(stop_token)
        stopping_criteria = StoppingCriteriaList([EndOfTurnCriteria(stop_token_id)])

        input = tokenizer.apply_chat_template(
            chat_history, tokenize=True, add_generation_prompt=True, return_tensors="pt"
        ).to(model.device)

        attention_mask = input.ne(tokenizer.pad_token_id).to(model.device)

        streamer = TextIteratorStreamer(tokenizer, skip_prompt=True, skip_special_tokens=True)

        generation_kwargs = {
            "input_ids": input.to(model.device),
            "attention_mask": attention_mask,
            "max_new_tokens": answer_tokens,
            "temperature": 0.6,
            "do_sample": True,
            "repetition_penalty": 1.1,
            "no_repeat_ngram_size": 2,
            "streamer": streamer,
            "eos_token_id": stop_token_id,
            "stopping_criteria": stopping_criteria,
            "pad_token_id": tokenizer.eos_token_id
        }

        thread = Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        def generate_response():
            for text in streamer:
                yield f"data: {json.dumps({'response': text})}\n\n"
            yield "data: <end>\n\n"

        return Response(generate_response(), mimetype='text/event-stream')

        #start_tag_index = response_text_full.rfind("<|im_start|>assistant")
        #end_tag_index = response_text_full.rfind("<|im_end|>")

        #start_tag_length = len("<|im_start|>assistant")
        #response_text = response_text_full[start_tag_index + start_tag_length:end_tag_index].strip()

    else:
        model.generation_config = GenerationConfig.from_pretrained(MODEL_PATH)
        model.generation_config.pad_token_id = model.generation_config.eos_token_id

        # Konvertiere den Chatverlauf in ein geeignetes Format für den Tokenizer
        #chat_history = "\n".join([f"<｜begin▁of▁sentence｜>{msg['role']}\n {msg['content']}<｜end▁of▁sentence｜>" for msg in chat_history])
        #chat_history = chat_history + "asisstent\n"
        #if firstMessage and systemPrompt != "":
          #  prompt_template = f'''user: {systemPrompt} \nassistent: <think>The user wants me to be an helpful assistant and respond simple and directly. </think>\n Ok, i will stick to it. \nuser: Are you ready to start?\nassistent: Yes, let's start :)\n{chat_history}
          #  '''
          #  chat_history = prompt_template

        # Eingabetext tokenisieren und KI-Text generieren
        if processingUnit == "gpu":
            #inputs = tokenizer(chat_history, return_tensors="pt").to("cuda" if torch.cuda.is_available() else "cpu")
            input = tokenizer.apply_chat_template(chat_history, add_generation_prompt=True, return_tensors="pt")
        else:
            input = tokenizer(chat_history, return_tensors="pt").to("cpu")

        attention_mask = input.ne(tokenizer.pad_token_id).to(model.device)

        output = model.generate(
            input.to(model.device),
            attention_mask=attention_mask,
            max_new_tokens=answer_tokens, # Maximale Länge der Antwort
            temperature=0.6,  # Kontrolliert die Kreativität (niedriger = deterministischer) # Steuert, wie fokussiert die Antwort bleibt
            do_sample=True,  # Aktiviert zufällige Generierung
            repetition_penalty=1.1,  # Verhindert endlose Wiederholungen
            no_repeat_ngram_size=2,
            num_return_sequences=1
        )

        #response_text = tokenizer.decode(output[0])
        #response_text = tokenizer.decode(output[0], skip_special_tokens=True)
        response_text = tokenizer.decode(output[0][input.shape[1]:], skip_special_tokens=True)

        # Überprüfen, ob die Antwort zu lang ist
        if len(output[0]) >= (answer_tokens):
            response_text = "<error>Fehler: Die Antwort des Assistenten ist zu lang.</error>"
        else:
            #if response_text.startswith(chat_history):
             #   response_text = response_text[len(chat_history):].strip()

            print(f"response_text: {response_text}")

            # Überprüfen, ob kein öffnendes <think> vorhanden ist, aber ein schließendes </think>
            if not response_text.startswith("<think>") and "</think>" in response_text:
                response_text = f"<think>\n{response_text.strip()}"

       #     if not response_text.startswith("<think>") and "</think>" not in response_text:
                # Suche nach zwei Zeilenumbrüchen (\n\n)
          #      double_newline_index = response_text.find("\n\n")
           #     if double_newline_index != -1:
                    # Füge <think> am Anfang hinzu und ersetze \n\n durch </think>
            #        response_text = f"<thinking>\n{response_text[:double_newline_index]}</thinking>{response_text[double_newline_index + 2:]}"

    #return jsonify({"response": response_text})
    return jsonify({"response": "Unsupported model type"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
