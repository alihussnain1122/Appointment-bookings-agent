import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

fs = 44100
seconds = 6
AUDIO_FILE = "input.wav"
SILENCE_RMS = 0.01

_model = None


def init_whisper():
    global _model
    if _model is None:
        import whisper
        print("Loading Whisper model...")
        _model = whisper.load_model("base")
        print("Whisper ready.")
    return _model


def record_audio(duration: float = seconds) -> bool:
    """Record a window of audio. Returns True if speech (non-silence) was detected."""
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    audio = np.clip(recording.flatten(), -1.0, 1.0)
    write(AUDIO_FILE, fs, (audio * 32767).astype(np.int16))

    if audio.size == 0:
        return False
    rms = float(np.sqrt(np.mean(np.square(audio))))
    return rms >= SILENCE_RMS


def transcribe_audio() -> str:
    model = init_whisper()
    result = model.transcribe(AUDIO_FILE, fp16=False)
    return result.get("text", "")


def transcribe_file(path: str) -> str:
    model = init_whisper()
    result = model.transcribe(path, fp16=False)
    return result.get("text", "").strip()
