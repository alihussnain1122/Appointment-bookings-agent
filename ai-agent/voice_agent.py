import json
import os
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.agent import reset_conversation, run_agent
from tools.api_tools import health_check
from voice.input import init_whisper, record_audio, transcribe_audio
from voice.output import init_voice, speak

CLINIC_NAME = os.getenv("CLINIC_NAME", "Smile Dental Clinic")


def greeting():
    return (
        f"Hi there! Welcome to {CLINIC_NAME}. "
        "I'm Maya, and I'd be happy to help you schedule your visit. "
        "Are you looking to book an appointment today?"
    )


def main():
    health = json.loads(health_check())
    if not health.get("ok"):
        print("Server not reachable. Start it first:")
        print('  cd "d:\\voice agent\\server"')
        print("  npm run dev")
        sys.exit(1)

    print("Backend connected:", health)
    reset_conversation()

    init_voice()
    speak(greeting())

    print("\nLoading speech recognition (first run may take a moment)...")
    init_whisper()
    print("Ready. Speak when you see 'Recording...'\n")

    while True:
        try:
            speak("I'm listening.")
            record_audio()
            user_text = transcribe_audio().strip()
            if not user_text:
                speak("Sorry, I didn't catch that. Could you say that again?")
                continue

            print("You:", user_text)
            response = run_agent(user_text)
            speak(response)
        except KeyboardInterrupt:
            print("\nExiting...")
            speak("Thank you for calling. Have a wonderful day!")
            break


if __name__ == "__main__":
    main()
