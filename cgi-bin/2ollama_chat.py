#!C:/Python39/python.exe
# -*- coding: utf-8 -*-

import cgi
import mysql.connector
import ollama
import pyttsx3
import uuid
import sys
sys.stdout.reconfigure(encoding='utf-8')

# 1) HTTP-Header
print("Content-type: text/html; charset=utf-8\n")

# 2) Datenbank-Verbindung
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="",
    database="ollama_chat"
)
cursor = conn.cursor()

# 3) CGI-Formdaten
form = cgi.FieldStorage()
session_id = form.getvalue("session_id", str(uuid.uuid4()))
user_input = form.getvalue("user_input", "")  # kein "Sag mir etwas Interessantes." mehr
user_input = user_input.strip()

# 4) Nur Insert + Ollama-Aufruf, wenn wirklich was eingegeben wurde
ollama_response = ""  # Start leer
if user_input:
    # User-Eingabe speichern
    cursor.execute(
        "INSERT INTO chats (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, "user", user_input)
    )
    conn.commit()

    # Alten Chatverlauf holen
    cursor.execute(
        "SELECT role, content FROM chats WHERE session_id = %s ORDER BY timestamp ASC",
        (session_id,)
    )
    chat_history = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]

    # Ollama aufrufen
    response = ollama.chat(
        model="llama3",
        messages=chat_history
    )
    ollama_response = response['message']['content']

    # Ollama-Antwort in DB speichern
    cursor.execute(
        "INSERT INTO chats (session_id, role, content) VALUES (%s, %s, %s)",
        (session_id, "assistant", ollama_response)
    )
    conn.commit()
    
    # (E) Ollama-Antwort an die bestehende chat_history-Liste anhängen
    chat_history.append({
        "role": "assistant",
        "content": ollama_response
    })
else:
    # Falls kein user_input (erster Aufruf oder leer)
    # trotzdem vorhandenen Chatverlauf laden
    cursor.execute(
        "SELECT role, content FROM chats WHERE session_id = %s ORDER BY timestamp ASC",
        (session_id,)
    )
    chat_history = [{"role": row[0], "content": row[1]} for row in cursor.fetchall()]


# Serverseitige Sprachausgabe auskommentiert (kein doppeltes Vorlesen)
# engine = pyttsx3.init()
# engine.say(ollama_response)
# engine.runAndWait()

# 5) HTML-Ausgabe
print("""<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <title>Ollama Chat mit Toggle-Spracherkennung</title>
    <script>
    // ---------------------------------------
    // 1) TTS: Antwort automatisch vorlesen
    // ---------------------------------------
    function speakResponse(text) {
        var speech = new SpeechSynthesisUtterance(text);
        speech.lang = "de-DE";
        window.speechSynthesis.speak(speech);
    }

    // ---------------------------------------
    // 2) Toggle-Sprach-Eingabe
    // ---------------------------------------
    let recognition;
    let isListening = false;
    let finalTranscript = "";
    let lastSpeechTime = 0;
    let checkTimer;

    function toggleListening() {
        if (!isListening) {
            // Spracheingabe starten
            isListening = true;
            document.getElementById("toggleBtn").textContent = "Spracheingabe beenden";
            startContinuousRecognition();
        } else {
            // Spracheingabe stoppen
            isListening = false;
            document.getElementById("toggleBtn").textContent = "Spracheingabe starten";
            stopContinuousRecognition();
        }
    }

    function startContinuousRecognition() {
        recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
        recognition.lang = "de-DE";
        recognition.interimResults = true;   // Zwischenergebnisse
        recognition.continuous = true;       // Dauermodus

        recognition.onresult = function(event) {
            let interimTranscript = "";
            for (let i = event.resultIndex; i < event.results.length; i++) {
                let result = event.results[i];
                if (result.isFinal) {
                    finalTranscript += result[0].transcript + " ";
                } else {
                    interimTranscript += result[0].transcript;
                }
            }
            document.getElementById("user_input").value = finalTranscript + interimTranscript;

            // Zeitstempel aktualisieren (wir haben gerade was erkannt)
            lastSpeechTime = Date.now();
        };

        recognition.onstart = function() {
            console.log("Spracherkennung gestartet.");
            finalTranscript = "";
            lastSpeechTime = Date.now();
            checkTimer = setInterval(checkSilence, 1000);
        };

        recognition.onend = function() {
            console.log("Spracherkennung beendet.");
            clearInterval(checkTimer);
        };

        recognition.start();
    }

    function stopContinuousRecognition() {
        if (recognition) {
            recognition.stop();
            recognition = null;
            clearInterval(checkTimer);
        }
    }

    // ---------------------------------------
    // 3) Automatisches Abschicken nach 3s Stille
    // ---------------------------------------
    function checkSilence() {
        const diff = Date.now() - lastSpeechTime;
        if (diff >= 700 && finalTranscript.trim() !== "") {
            // 3 Sekunden Stille => Abschicken
            stopContinuousRecognition();
            isListening = false;
            document.getElementById("toggleBtn").textContent = "Spracheingabe starten";
            document.getElementById("chatForm").submit();
        }
    }

    // ---------------------------------------
    // 4) onload => ggf. Ollama-Antwort vorlesen
    // ---------------------------------------
    window.onload = function() {
        let responseText = \"""" + ollama_response.replace("\\","\\\\").replace("\"","\\\"").replace("\n"," ") + """\";
        if (responseText.trim() !== "") {
            speakResponse(responseText);
        }
    };
    </script>
    <style>
    body {
        font-family: sans-serif;
    }
    .chat-container {
        border:1px solid #ccc;
        padding:10px;
        width:50%;
        height:300px;
        overflow-y:scroll;
        margin-bottom: 20px;
    }
    </style>
</head>
<body>
    <h1>Ollama Chat mit Toggle-Spracherkennung</h1>
    <div class="chat-container">
""")

# 6) Chatverlauf
for msg in chat_history:
    role_label = "Du" if msg["role"] == "user" else "Ollama"
    css_class = "user" if msg["role"] == "user" else "assistant"
    # Direkt aus dem dict "role" und "content"
    print("<p><span class=\"{}\">{}</span>: {}</p>".format(
        css_class,
        role_label,
        msg["content"]
    ))

# Dann das Formular:
print("""
    </div>
    <form id="chatForm" action="/cgi-bin/ollama_chat.py" method="post">
        <input type="hidden" name="session_id" value=\"""" + session_id + """\">
        <label>Deine Nachricht:</label><br>
        <input type="text" id="user_input" name="user_input" style="width:300px;" required>
        <br><br>
        <button type="button" id="toggleBtn" onclick="toggleListening()">Spracheingabe starten</button>
        &nbsp;
        <input type="submit" value="Senden">
    </form>
</body>
</html>
""")

cursor.close()
conn.close()
