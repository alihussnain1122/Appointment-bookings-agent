import pyttsx3

_engine = None


def _pick_female_us_voice(engine):
    voices = engine.getProperty("voices") or []
    if not voices:
        return

    def score(voice):
        label = f"{voice.name} {voice.id}".lower()
        points = 0
        if "zira" in label or "samantha" in label:
            points += 10
        if "female" in label:
            points += 5
        if "en-us" in label or "english_united_states" in label.replace("-", "_"):
            points += 4
        if "united states" in label or "us)" in label:
            points += 3
        if "english" in label:
            points += 1
        return points

    best = max(voices, key=score)
    if score(best) > 0:
        engine.setProperty("voice", best.id)
        print(f"Voice: {best.name}")


def init_voice():
    global _engine
    if _engine is None:
        _engine = pyttsx3.init("sapi5")
        _engine.setProperty("rate", 150)
        _engine.setProperty("volume", 1.0)
        _pick_female_us_voice(_engine)
    return _engine


def speak(text):
    if not text:
        return
    print("AI:", text)
    engine = init_voice()
    engine.say(text)
    engine.runAndWait()
