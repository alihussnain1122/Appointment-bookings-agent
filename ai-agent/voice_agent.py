import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.agent import reset_conversation, run_agent
from call_manager import greeting_text
from tools.api_tools import health_check
from voice.input import init_whisper, record_audio, transcribe_audio
from voice.output import init_voice, speak

CLINIC_NAME = os.getenv("CLINIC_NAME", "Smile Dental Clinic")


def run_call():
    """Handle a single call: greet, then listen and respond until it ends."""
    reset_conversation()
    greeting = greeting_text()
    print("AI:", greeting)
    speak(greeting)

    while True:
        print("Listening...")
        has_speech = record_audio()

        if not has_speech:
            response, should_end = run_agent("")
            if response:
                print("AI:", response)
                speak(response)
            if should_end:
                print("\nCall ended.\n")
                return
            continue

        user_text = transcribe_audio().strip()
        if not user_text:
            continue

        print("You:", user_text)
        response, should_end = run_agent(user_text)
        print("AI:", response)
        speak(response)

        if should_end:
            print("\nCall ended.\n")
            return


def main():
    health = json.loads(health_check())
    if not health.get("ok"):
        print("Server not reachable. Start it first:")
        print('  cd "d:\\voice agent\\server"')
        print("  npm run dev")
        sys.exit(1)

    print("Backend connected:", health)
    init_voice()
    print("Loading speech recognition (first run may take a moment)...")
    init_whisper()
    print(f"\n{CLINIC_NAME} voice agent is live. (Ctrl+C to stop)\n")

    while True:
        try:
            run_call()
        except KeyboardInterrupt:
            print("\nShutting down...")
            try:
                speak("Thank you for calling. Have a wonderful day!")
            except Exception:
                pass
            break


if __name__ == "__main__":
    main()
