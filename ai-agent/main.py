from dotenv import load_dotenv

from agent.agent import reset_conversation, run_agent
from tools.api_tools import health_check

load_dotenv()


def main():
    health = health_check()
    print("Backend:", health)
    reset_conversation()
    print("\nAI Booking Agent started (type 'exit' to quit)\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            break
        response = run_agent(user_input)
        print("AI:", response, "\n")


if __name__ == "__main__":
    main()
