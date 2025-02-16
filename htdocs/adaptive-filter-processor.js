class AdaptiveFilterProcessor extends AudioWorkletProcessor {
  constructor() {
    super();
    // Initialisiere den Filter: z. B. 128 Koeffizienten (kannst du anpassen)
    this.coeffs = new Float32Array(128).fill(0);
    // Puffer, um die letzten 128 Referenzsamples zu speichern
    this.refBuffer = new Float32Array(128).fill(0);
    // Lernrate für den LMS-Algorithmus (mu)
    this.mu = 0.01;
  }

  process(inputs, outputs, parameters) {
    // Wir erwarten zwei Eingänge:
    // inputs[0]: Mikrofonsignal
    // inputs[1]: TTS-Referenzsignal
    const micInput = inputs[0][0];
    const refInput = inputs[1] ? inputs[1][0] : null;
    const output = outputs[0][0];

    if (!micInput || !refInput) {
      // Falls einer der Eingänge fehlt, einfach durchreichen
      for (let i = 0; i < output.length; i++) {
        output[i] = micInput ? micInput[i] : 0;
      }
      return true;
    }

    for (let i = 0; i < micInput.length; i++) {
      // Schiebe den neuen Referenzwert in den Puffer
      this.refBuffer.copyWithin(1, 0);
      this.refBuffer[0] = refInput[i];

      // Berechne die Filterausgabe y[n] = Sum(coeffs * refBuffer)
      let y = 0;
      for (let j = 0; j < this.refBuffer.length; j++) {
        y += this.coeffs[j] * this.refBuffer[j];
      }

      // Fehler: Differenz zwischen Mikrofonsignal und geschätzter TTS-Komponente
      const e = micInput[i] - y;

      // LMS-Update: Koeffizienten anpassen
      for (let j = 0; j < this.refBuffer.length; j++) {
        this.coeffs[j] += this.mu * e * this.refBuffer[j];
      }

      // Gib den Fehler (also das "gefilterte" Signal) als Output aus
      output[i] = e;
    }
    return true;
  }
}

registerProcessor('adaptive-filter-processor', AdaptiveFilterProcessor);
