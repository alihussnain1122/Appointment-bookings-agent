const SpeechRecognition =
  window.SpeechRecognition || window.webkitSpeechRecognition;

const LISTEN_TIMEOUT_MS = 12000;

export function isSpeechSupported() {
  return Boolean(SpeechRecognition) && "speechSynthesis" in window;
}

function pickFemaleVoice() {
  const voices = speechSynthesis.getVoices();
  return (
    voices.find((v) => /zira|samantha|google us english/i.test(v.name)) ||
    voices.find((v) => v.lang.startsWith("en-US") && /female/i.test(v.name)) ||
    voices.find((v) => v.lang.startsWith("en-US")) ||
    voices[0]
  );
}

export function speak(text) {
  return new Promise((resolve) => {
    if (!text) {
      resolve();
      return;
    }

    const utterance = new SpeechSynthesisUtterance(text);
    const voice = pickFemaleVoice();
    if (voice) utterance.voice = voice;
    utterance.lang = "en-US";
    utterance.rate = 0.95;
    utterance.pitch = 1.05;
    utterance.onend = () => resolve();
    utterance.onerror = () => resolve();
    speechSynthesis.cancel();
    speechSynthesis.speak(utterance);
  });
}

export function listenOnce(timeoutMs = LISTEN_TIMEOUT_MS) {
  return new Promise((resolve, reject) => {
    if (!SpeechRecognition) {
      reject(new Error("Speech recognition is not supported in this browser."));
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;

    let settled = false;

    const finish = (text) => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      try {
        recognition.stop();
      } catch {
        // ignore if recognition already stopped
      }
      resolve(text);
    };

    const timer = setTimeout(() => finish(""), timeoutMs);

    recognition.onresult = (event) => {
      const text = event.results[0]?.[0]?.transcript?.trim() || "";
      finish(text);
    };

    recognition.onerror = (event) => {
      if (event.error === "no-speech" || event.error === "aborted") {
        finish("");
        return;
      }
      if (!settled) {
        settled = true;
        clearTimeout(timer);
        reject(new Error(event.error));
      }
    };

    recognition.onend = () => {
      if (!settled) finish("");
    };

    try {
      recognition.start();
    } catch (error) {
      clearTimeout(timer);
      reject(error);
    }
  });
}

if ("speechSynthesis" in window) {
  speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => speechSynthesis.getVoices();
}
