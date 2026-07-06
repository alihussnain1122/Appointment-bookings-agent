import numpy as np
import sounddevice as sd
from scipy.io.wavfile import write

fs = 44100
seconds = 5
AUDIO_FILE = "input.wav"

_model = None


def init_whisper():
    global _model
    if _model is None:
        import whisper
        print("Loading Whisper model...")
        _model = whisper.load_model("base")
        print("Whisper ready.")
    return _model


def record_audio():
    print("Recording... speak now")
    recording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    audio = np.clip(recording, -1.0, 1.0)
    write(AUDIO_FILE, fs, (audio * 32767).astype(np.int16))
    print("Recording done.")


def transcribe_audio():
    model = init_whisper()
    result = model.transcribe(AUDIO_FILE, fp16=False)
    return result.get("text", "")
