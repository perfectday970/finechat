#!C:\Python\Python310\python.exe
# -*- coding: utf-8 -*-

import os
import sys

os.environ["HOME"] = "D:/xampp/temp_mpl"
#os.environ["HOME"] = "C:/Users/veit-"
os.environ["MPLCONFIGDIR"] = "C:/Users/veit-.config/matplotlib"

sys.stdout.reconfigure(encoding='utf-8')  # UTF-8 Ausgabe sicherstellen

import cgi
import mysql.connector
import json
import uuid
import requests  # Für Anfragen an den DeepSeek-Server
import logging

LOG_FILE = "D:/xampp/temp_mpl/distributor.log"
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

#import matplotlib
#matplotlib.use("Agg")

# -- Konfiguration --
TEMP_DIR = "D:/xampp/temp_mpl"
os.makedirs(TEMP_DIR, exist_ok=True)



# -- 1) Formulardaten auslesen --
form = cgi.FieldStorage()
session_id = form.getvalue("session_id", "")  # ggf. leer
user_text = form.getvalue("user_input", "").strip()
text = form.getvalue("text", "browser").strip() # Text to synthesize
selected_model = form.getvalue("aiModel", "ollama")  # Standardmäßig Ollama verwenden
tts_mode = form.getvalue("ttsMode", "browser")  # TTS-Option (Browser oder Coqui)
requestType = form.getvalue("requestType", "browser")
processingUnit = form.getvalue("processingUnit", "cpu").strip()
systemPrompt = form.getvalue("systemPrompt", "").strip()

firstMessage = False

logging.info(f"form: {form}")
logging.info(f"session_id: {session_id}")
logging.info(f"user_input: {user_text}")
logging.info(f"aiModel: {selected_model}")
logging.info(f"ttsMode: {tts_mode}")
logging.info(f"requestType: {requestType}")
logging.info(f"processingUnit: {processingUnit}")
logging.info(f"processingUnit: {systemPrompt}")

if requestType == "ttsMode":
    # Weiterleitung an TTS-Server
    tts_url = "http://localhost:5001/synthesize"
    try:
        import re
        clean_text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

        files = {'text': (None, clean_text)}
        tts_response = requests.post(tts_url, files=files)
        tts_response.raise_for_status()

        # Sende die Audioantwort direkt an den Client
        print("Content-Type: audio/wav\n")
        sys.stdout.flush()
        sys.stdout.buffer.write(tts_response.content)
        sys.exit(0)

    except Exception as e:
        error_msg = f"TTS Error: {str(e)}"
        print(json.dumps({"error": error_msg}))
        sys.exit(1)

else:
    # MySQL Datenbankverbindung
    conn = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="ollama_chat",
        charset="utf8mb4",
        use_unicode=True
    )
    cursor = conn.cursor()
    cursor.execute("SET NAMES utf8mb4")

    # Falls keine Session-ID: Neue generieren
    if not session_id:
        firstMessage = True
        session_id = str(uuid.uuid4())

    # User-Eingabe in DB speichern
    cursor.execute(
        "INSERT INTO chats (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, "user", user_text)
    )
    conn.commit()

    # Chatverlauf aus der Datenbank abrufen
    cursor.execute(
        "SELECT role, content FROM chats WHERE session_id=%s ORDER BY timestamp ASC",
        (session_id,)
    )
    rows = cursor.fetchall()

    chat_history = [{"role": row[0], "content": row[1]} for row in rows]
    ai_response = ""

    if requestType == "aiModel":
        print("Content-Type: text/event-stream\n")  # SSE header for streaming
        print("Cache-Control: no-cache\n")
        print("Connection: keep-alive\n")
        sys.stdout.flush()

        # **KI-Server auswählen**
        if selected_model == "deepseek":
            logging.info(f"Send to deepseek")
            # Anfrage an DeepSeek Flask-Server senden
            deepseek_url = "http://localhost:5000/generate"
            payload = {
                "chat_history": chat_history,
                "processingUnit": processingUnit,
                "firstMessage": firstMessage,
                "systemPrompt": systemPrompt
            }
            try:
                # Stream the response from DeepSeek
                with requests.post(deepseek_url, json=payload, stream=True) as response:
                    response.raise_for_status()
                    for chunk in response.iter_content(chunk_size=None):
                        if chunk:
                            # Send each chunk to the client
                            print(f"data: {chunk.decode('utf-8')}\n\n")
                            sys.stdout.flush()

            except requests.exceptions.RequestException as e:
                error_msg = f"Fehler bei DeepSeek: {str(e)}"
                print(f"data: {json.dumps({'error': error_msg})}\n\n")
                sys.stdout.flush()

    # -- 5) Gesamten Chatverlauf zurückgeben --
   # cursor.execute(
      #  "SELECT role, content FROM chats WHERE session_id=%s ORDER BY timestamp ASC",
     #   (session_id,)
   # )
 #   all_rows = cursor.fetchall()

  #  chat_data = []
 #   for r in all_rows:
  #      chat_data.append({
    #        "role": r[0],
     #       "content": r[1]
     #   })

    #result = {
   #     "session_id": session_id,
  #      "chat": chat_data
  #  }

  #  print(json.dumps(result, ensure_ascii=False))  # UTF-8 Ausgabe

  #  cursor.close()
  #  conn.close()
