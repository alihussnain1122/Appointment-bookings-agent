import json
import sys

from dotenv import load_dotenv

load_dotenv()

from agent.agent import run_agent
from tools.api_tools import health_check
from voice.input import init_whisper, record_audio, transcribe_audio
from voice.output import speak


def main():
    health = json.loads(health_check())
    if not health.get("ok"):
        print("Server not reachable. Start it first:")
        print('  cd "d:\\voice agent\\server"')
        print("  npm run dev")
        sys.exit(1)

    print("Backend connected:", health)
    init_whisper()
    speak("Voice agent is ready. How can I help you book an appointment?")

    while True:
        try:
            record_audio()
            user_text = transcribe_audio().strip()
            if not user_text:
                speak("I did not catch that. Please try again.")
                continue

            print("You:", user_text)
            response = run_agent(user_text)
            speak(response)
        except KeyboardInterrupt:
            print("\nExiting...")
            speak("Goodbye.")
            break


if __name__ == "__main__":
    main()
