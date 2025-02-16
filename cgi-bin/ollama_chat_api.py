#!C:/Python39/python.exe
# -*- coding: utf-8 -*-

import sys
sys.stdout.reconfigure(encoding='utf-8')  # Wichtig für UTF-8-Ausgabe unter Windows

import cgi
import mysql.connector
import ollama
import json
import uuid

print("Content-Type: application/json; charset=utf-8\n")  # JSON-Header

# -- 1) Datenbank-Verbindung aufbauen --
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

# -- 2) Formulardaten auslesen --
form = cgi.FieldStorage()
session_id = form.getvalue("session_id", "")  # ggf. leer
user_text = form.getvalue("user_input", "")   # erkannter Text vom Browser
user_text = user_text.strip()

# Falls keine Session-ID: neue generieren
if not session_id:
    session_id = str(uuid.uuid4())

# -- 3) Nur wenn user_text nicht leer, in DB speichern und Ollama abrufen --
if user_text:
    # User-Eingabe speichern
    cursor.execute(
        "INSERT INTO chats (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, "user", user_text)
    )
    conn.commit()

    # Chatverlauf abrufen
    cursor.execute(
        "SELECT role, content FROM chats WHERE session_id=%s ORDER BY timestamp ASC",
        (session_id,)
    )
    chat_history = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

    # Ollama aufrufen
    response = ollama.chat(
        model="llama3",  # ggf. Modellnamen anpassen
        messages=chat_history
    )
    ollama_response = response["message"]["content"]

    # Ollama-Antwort speichern
    cursor.execute(
        "INSERT INTO chats (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, "assistant", ollama_response)
    )
    conn.commit()

# -- 4) Gesamten Chatverlauf zurückgeben (jetzt inkl. eventueller neuer Antwort) --
cursor.execute(
    "SELECT role, content FROM chats WHERE session_id=%s ORDER BY timestamp ASC",
    (session_id,)
)
all_rows = cursor.fetchall()

chat_data = []
for r in all_rows:
    chat_data.append({
        "role": r[0],
        "content": r[1]
    })

result = {
    "session_id": session_id,
    "chat": chat_data
}

print(json.dumps(result, ensure_ascii=False))  # UTF-8 Ausgabe

cursor.close()
conn.close()
