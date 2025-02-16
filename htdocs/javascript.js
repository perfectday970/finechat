// ------------------ GLOBALE VARIABLEN ------------------
let recognition;              // Instanz der Web Speech API
let isListening = false;      // Merker für ein/aus
let finalTranscript = "";     // hier sammeln wir erkannte Endergebnisse
let lastSpeechTime = 0;       // Zeitstempel letztes onresult
let checkTimer;               // setInterval ID
let userInput = document.getElementById("user_input");
//let isTTSRunning = false;
let firstRequest = true;
let chatArray = [];
let waiting = false;
//let audioQueue = [];  // Warteschlange für Sprachdateien
let isPlaying = false;  // Merkt sich, ob gerade eine Sprachdatei abgespielt wird
let currentUtterance = null; // global
let audioQueue = new Map();       // Puffer für Audio-Dateien (key: sequenceId, value: audioData)
let expectedSequenceId = 0;      // Erwartete Sequenz-ID für die Wiedergabe
let isTTSRunning = false;        // Merkt sich, ob gerade eine Sprachdatei abgespielt wird
let currentSequenceId = -1;      // ID der aktuell abgespielten Nachricht
let lastAudioTime = 0;

// System-Prompts (vorbelegt)
const systemPrompts = {
  de: "Du bist ein hilfsbereiter Assistent. Antworte klar und präzise auf Deutsch. Wenn eine Frage einfach ist, antworten Sie direkt und schnell, auf natürliche Art und Weise, ohne nachzudenken.\n" +
          "Nur wenn eine Frage ein **tiefes Nachdenken** erfordert, erläutern Sie Ihre Gedanken im Detail, innerhalb des Denkbereichs, aber analysieren Sie nicht zu sehr.\n",
  en: "You are a helpful assistant. Respond clearly and concisely in English. If a question is simple, answer directly and quickly, in a natural way, without thinking.\n" +
          "Only if a question requires **deep thought**, explain your thoughts in detail, within the range of thought, but don't over analyze.\n"
};

// Setze den System-Prompt basierend auf der Sprache
function setSystemPrompt(lang) {
  document.getElementById("systemPrompt").value = systemPrompts[lang];
}


// ------------------ SESSION / SERVER ------------------
// Wir nehmen an, dass du am Server ein ollama_chat_api.py hast, das JSON zurückgibt.
// (Anpassen, wenn dein Pfad anders ist)
let sessionId = "";

// ------------------ TOGGLE-FUNKTION ------------------
function toggleListening() {
  if (isTTSRunning) {
    console.log("Mikrofonsteuerung deaktiviert, da Sprachausgabe läuft.");
    return;
  }

  if (!isListening) {
    // Start
    isListening = true;
    document.getElementById("toggleBtn").textContent = "Mikrofon ausschalten";
    startContinuousRecognition();
  } else {
    // Stop
    isListening = false;
    document.getElementById("toggleBtn").textContent = "Mikrofon einschalten";
    stopContinuousRecognition();
    userInput.disabled = false;
  }
}

// ------------------ START/STOP ERKENNUNG ------------------
function startContinuousRecognition() {
  recognition = new (window.SpeechRecognition || window.webkitSpeechRecognition)();
  recognition.lang = "de-DE";
  recognition.interimResults = false;
  recognition.continuous = true;

  recognition.onstart = function() {
    console.log("Spracherkennung gestartet");
    finalTranscript = "";
    lastSpeechTime = Date.now();
    // Jede Sekunde checken, ob >=3s Pause
    checkTimer = setInterval(checkSilence, 200);
  };

  recognition.onresult = function(event) {
    console.log("Es wurde eine Spracheingabe verstanden");
   //  let interimTranscript = "";
     for (let i = event.resultIndex; i < event.results.length; i++) {

        if (!isTTSRunning) {
            let result = event.results[i];
            if(result.isFinal)
            {
              console.log(" TTS läuft nicht. " + finalTranscript);

            //     let chunk = result[0].transcript.toLowerCase().trim();
              finalTranscript += result[0].transcript + " ";

              userInput.value = finalTranscript.trim();
              userInput.disabled = true;
            }
            lastSpeechTime = Date.now();
        }
     }
  };

  recognition.onend = function() {
    console.log("Spracherkennung endete – neu starten, falls toggle noch an");
    clearInterval(checkTimer);
    // Chrome beendet manchmal trotz continuous = true
    // => Also neu starten, wenn isListening
    if (isListening) {
      recognition.start();
    }
  };
  recognition.start();
}

function stopContinuousRecognition() {
  if (recognition) {
    recognition.onend = null;  // nicht wieder neu starten
    recognition.stop();
    recognition = null;
    clearInterval(checkTimer);
  }
}

// ------------------ AUTO-SEND NACH 3S PAUSE ------------------
function checkSilence() {
  let diff = Date.now() - lastSpeechTime;
  // Nach 3s ohne neue Erkennung => abschicken, wenn finalTranscript nicht leer ist
  if (diff >= 200 && finalTranscript.trim() !== "") {
    let text = finalTranscript.trim();
    finalTranscript = "";
    sendMessageToServer(text);
    // Eingabefeld leeren + freigeben
    userInput.value = "";
    userInput.disabled = false;
  }
}

// ------------------ MANUELLES SENDEN ------------------
function sendManual() {
  // Nur senden, wenn Feld nicht leer
  let text = userInput.value.trim();
  if (text === "") return;

  sendMessageToServer(text);

  // Feld leeren + freigeben
  userInput.value = "";
  userInput.disabled = false;
}

function getAPIEndpoint() {
  return "/cgi-bin/distributor.py";  // Ollama Chat API

}

// ------------------ SERVER-AUFUFR (AJAX) ------------------
function sendMessageToServer(text) {
    resetAudioQueue();
    console.log("Sende an Server:", text);
    chatArray.push({ role: "user", content: text });
    renderChat(true);

    let apiUrl = getAPIEndpoint();  // Wählt den richtigen API-Endpunkt
    let aiModel = document.getElementById("aiModel").value;
    let ttsMode = document.getElementById("ttsMode").value;
    let processingUnit = document.getElementById("processingUnit").value;

    let formData = new FormData();
    formData.append("session_id", sessionId);
    formData.append("user_input", text);
    formData.append("aiModel", aiModel);
    formData.append("ttsMode", ttsMode);
    formData.append("requestType", "aiModel");
    formData.append("processingUnit", processingUnit);

    if (firstRequest) {
        let systemPrompt = document.getElementById("systemPrompt").value;
        formData.append("systemPrompt", systemPrompt);
    }
    firstRequest = false;

    // Use EventSource for streaming
    const eventSource = new EventSource(`${apiUrl}?${new URLSearchParams(formData).toString()}`);

    let assistantResponse = "";  // Sammelt die gestreamte Antwort

    let messageCounter = 0;  // Globale Zählvariable für Sequenz-IDs
    let lastSpokenIndex = 0; // Index des letzten gesprochenen Textes

    eventSource.onmessage = function(event) {
        // Entferne das "data: "-Präfix
        const rawData = event.data;
        const jsonData = rawData.replace("data: ", "");

        if (jsonData === "<end>") {
            eventSource.close();

            // Verbleibenden Text ohne Satzzeichen verarbeiten
            const remainingText = assistantResponse.substring(lastSpokenIndex);
            if (remainingText.trim() !== "") {
                const currentMessageId = messageCounter++;
                speakResponse(remainingText, currentMessageId);
            }
            return;
        }

        try {
            const data = JSON.parse(jsonData);

            // Akkumuliere die Antwort
            assistantResponse += data.response;
            updateChatWithStream(assistantResponse);

            // Satzenden finden und mit Sequenz-ID verarbeiten
            let sentenceEndIndex;
            while ((sentenceEndIndex = findSentenceEnd(assistantResponse, lastSpokenIndex)) !== -1) {
                const sentence = assistantResponse.substring(lastSpokenIndex, sentenceEndIndex + 1);
                const currentMessageId = messageCounter++;

                // Spreche den Satz mit eindeutiger Sequenz-ID
                speakResponse(sentence, currentMessageId);

                lastSpokenIndex = sentenceEndIndex + 1;
            }

        } catch (error) {
            console.error("Fehler beim Parsen der Server-Antwort:", error);
        }
    };


    eventSource.onerror = function() {
        console.error("Fehler bei der Verbindung zum Server.");
        eventSource.close();
    };
}

function containsSentenceEnd(text) {
    const sentenceEndings = [".", "!", "?"];
    return sentenceEndings.some((char) => text.includes(char));
}

function findSentenceEnd(text, startIndex) {
    const sentenceEndings = [".", "!", "?"];
    for (let i = startIndex; i < text.length; i++) {
        if (sentenceEndings.includes(text[i])) {
            return i;
        }
    }
    return -1;  // Kein Satzende gefunden
}

function updateChatWithStream(response) {
    // Entferne den letzten Eintrag des Assistenten (falls vorhanden)
    if (chatArray.length > 0 && chatArray[chatArray.length - 1].role === "assistant") {
        chatArray.pop();
    }

    // Füge die aktualisierte Antwort des Assistenten hinzu
    chatArray.push({ role: "assistant", content: response });
    renderChat(false);
}

// ------------------ CHAT DARSTELLEN ------------------

function renderChat(waiting) {
    const chatbox = document.getElementById("chatbox");
    chatbox.innerHTML = "";
    chatArray.forEach(msg => {
        let p = document.createElement("p");
        let formattedContent = formatTextWithBold(msg.content)
            .replace(/\n/g, '<br>')  // Zeilenumbrüche erhalten
            .replace(/<think>/g, '<think>') // Think-Tags erhalten
            .replace(/<\/think>/g, '</think>');

        if (msg.role === "user") {
            p.innerHTML = `<span class='user'>Du:</span> ${formattedContent}`;
        } else {
            p.innerHTML = `<span class='assistant'>Assistent:</span> ${formattedContent}`;
        }
        chatbox.appendChild(p);
    });
    if (waiting) {
        let waitElement = document.createElement("p");
        waitElement.innerHTML = `<span class='waiting'></span> `;
        chatbox.appendChild(waitElement);
    }
    chatbox.scrollTop = chatbox.scrollHeight;
}

function formatTextWithBold(text) {
    // Ersetze **Wort** durch <strong>Wort</strong>
    return text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
}


// ------------------ TTS ------------------

function speakResponse(text, sequenceId) {
    const mode = document.getElementById("ttsMode").value;

    // Generiere Audio-Datei und speichere sie im Puffer
    if (mode === "browser") {
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "de-DE";
        audioQueue.set(sequenceId, { type: "browser", data: utterance });
    } else {
        fetchCoquiTTS(text, sequenceId);
    }

    checkAndPlayAudio();  // Prüfe, ob die nächste Audio abgespielt werden kann
}

function cancelTTS() {
  if (currentUtterance) {
    speechSynthesis.cancel(); // Abbrechen
    currentUtterance = null;
  }
  finalTranscript = "";
  isTTSRunning = false;
  console.log("TTS manuell abgebrochen!");
}

function playNextAudio() {
    if (isTTSRunning || audioQueue.length === 0) {
        return;  // Nichts tun, falls bereits etwas abgespielt wird oder die Warteschlange leer ist
    }

    const nextAudio = audioQueue.shift();  // Nimm das nächste Element aus der Warteschlange
    isTTSRunning = true;

    if (nextAudio.type === "browser") {
        // Browser-TTS
        if (currentUtterance) {
            speechSynthesis.cancel();  // Stoppe die aktuelle Wiedergabe
        }

        currentUtterance = nextAudio.data;
        currentUtterance.onstart = function() {
            console.log("TTS hat begonnen.");
            isListening = false;
            document.getElementById("toggleBtn").disabled = true;
            document.getElementById("toggleBtn").textContent = "Sprachausgabe läuft gerade";
            stopContinuousRecognition();
            userInput.disabled = false;
        };

        currentUtterance.onend = function() {
            console.log("TTS ist fertig.");
            isTTSRunning = false;
            currentUtterance = null;
            isListening = true;
            document.getElementById("toggleBtn").disabled = false;
            document.getElementById("toggleBtn").textContent = "Mikrofon ausschalten";
            startContinuousRecognition();

            // Spiele das nächste Audio ab
            playNextAudio();
        };

        window.speechSynthesis.speak(currentUtterance);
    } else if (nextAudio.type === "coqui") {
        // Coqui-TTS
        let audio = new Audio(nextAudio.data);

        audio.onplay = () => {
            console.log("Coqui-TTS hat begonnen.");
            isTTSRunning = true;
            isListening = false;
            document.getElementById("toggleBtn").disabled = true;
            document.getElementById("toggleBtn").textContent = "Sprachausgabe läuft gerade";
            stopContinuousRecognition();
            userInput.disabled = false;
        };

        audio.onended = () => {
            console.log("Coqui-TTS ist fertig.");
            isTTSRunning = false;
            isListening = true;
            document.getElementById("toggleBtn").disabled = false;
            document.getElementById("toggleBtn").textContent = "Mikrofon ausschalten";
            startContinuousRecognition();

            // Spiele das nächste Audio ab
            playNextAudio();
        };

        audio.play();
    }
}

function fetchCoquiTTS(text, sequenceId) {
    const formData = new FormData();
    formData.append("text", text);
    formData.append("requestType", "ttsMode");

    fetch("/cgi-bin/distributor.py", {
        method: "POST",
        body: formData
    })
    .then(response => response.blob())
    .then(blob => {
        const audioUrl = URL.createObjectURL(blob);
        audioQueue.set(sequenceId, { type: "coqui", data: audioUrl });
        checkAndPlayAudio();  // Prüfe erneut nach erfolgreichem Fetch
    })
    .catch(err => console.error("Fehler bei TTS:", err));
}

function checkAndPlayAudio() {
    // Wenn eine Sequenz länger als 2 Sekunden nicht kommt, überspringen
    if (expectedSequenceId > 0 && Date.now() - lastAudioTime > 10000 && !isTTSRunning) {
        expectedSequenceId++;
    }

    // Wenn die erwartete Audio verfügbar ist UND nichts gerade abgespielt wird
    if (audioQueue.has(expectedSequenceId) && !isTTSRunning) {
        const audioData = audioQueue.get(expectedSequenceId);
        audioQueue.delete(expectedSequenceId);
        playAudio(audioData, expectedSequenceId);
        expectedSequenceId++; // Nächste Sequenz-ID erwarten
    }
}


function playAudio(audioData, sequenceId) {
    isTTSRunning = true;
    currentSequenceId = sequenceId;
    lastAudioTime = Date.now();

    if (audioData.type === "browser") {
        const utterance = audioData.data;
        utterance.onstart = () => handleTTSStart();
        utterance.onend = () => handleTTSEnd();
        window.speechSynthesis.speak(utterance);
    } else {
        const audio = new Audio(audioData.data);
        audio.onplay = () => handleTTSStart();
        audio.onended = () => handleTTSEnd();
        audio.play();
    }
}
function resetAudioQueue() {
    audioQueue.clear(); // Leere die Audio-Warteschlange
    expectedSequenceId = 0; // Setze die erwartete Sequenz-ID zurück
    currentSequenceId = -1; // Setze die aktuelle Sequenz-ID zurück
    isTTSRunning = false; // Setze den TTS-Status zurück
    if (currentUtterance) {
        speechSynthesis.cancel(); // Stoppe die aktuelle Sprachausgabe
        currentUtterance = null;
    }
}
function handleTTSStart() {
    isTTSRunning = true;
    isListening = false;
    document.getElementById("toggleBtn").disabled = true;
    document.getElementById("toggleBtn").textContent = "Sprachausgabe läuft gerade";
    stopContinuousRecognition();
}

function handleTTSEnd() {
    isTTSRunning = false;
    currentSequenceId = -1;
    isListening = true;
    document.getElementById("toggleBtn").disabled = false;
    document.getElementById("toggleBtn").textContent = "Mikrofon ausschalten";
    startContinuousRecognition();
    checkAndPlayAudio();  // Nächste Audio prüfen
}