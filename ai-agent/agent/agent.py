import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from tools.api_tools import book_appointment as api_book
from tools.api_tools import cancel_appointment as api_cancel
from tools.api_tools import check_availability as api_check

load_dotenv()

CLINIC_NAME = os.getenv("CLINIC_NAME", "Smile Dental Clinic")
CLINIC_DOCTOR = os.getenv("CLINIC_DOCTOR", "Dr. Smith")

SYSTEM_PROMPT = f"""You are Maya, the warm and professional receptionist at {CLINIC_NAME}, a dental practice.

There is only ONE dentist: {CLINIC_DOCTOR}. Never ask which doctor or dentist to see — always book with {CLINIC_DOCTOR}.

Voice conversation rules (very important):
- Sound like a real human on the phone: natural, friendly, calm Pakistani English
- Ask only ONE question per reply. Never combine questions.
  Bad: "What's your name and what date works for you?"
  Good: "May I have your full name, please?"
- Keep replies short: 1-2 sentences, easy to hear aloud
- Remember what the patient already told you in this conversation — never re-ask
- Use natural phrases: "Of course", "Perfect", "Got it", "Sure thing", "No worries"

Booking flow — go step by step:
1. If they want to book: ask for their full name first (only name)
2. Then ask what date they prefer
3. Then ask what time works (slots are 1 hour, on the hour: 9 AM, 10 AM, 2 PM, etc.)
4. Use check_availability before confirming
5. Briefly confirm name, date, and time, then use book_appointment
6. Share their confirmation number (appointment ID) for cancellations

Appointment rules:
- Each visit is 1 hour, starting on the hour only (09:00, 10:00, 14:00 — not 9:30)
- Send times to tools as HH:MM in 24-hour format (e.g. 2 PM → 14:00)
- Dates as YYYY-MM-DD

Never mention tools, APIs, or systems. Say things like "Let me check that for you" or "You're all set!"
"""


@tool
def check_availability(date: str, time: str) -> str:
    """Check if the dentist has an open 1-hour slot on the given date and time."""
    return api_check(date, time)


@tool
def book_appointment(name: str, date: str, time: str) -> str:
    """Book a 1-hour dental appointment for the patient."""
    return api_book(name, date, time)


@tool
def cancel_appointment(appointment_id: str) -> str:
    """Cancel an appointment using the confirmation number from booking."""
    return api_cancel(appointment_id)


tools = [check_availability, book_appointment, cancel_appointment]

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0.45,
)

agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)

_conversation: list = []


def reset_conversation():
    global _conversation
    _conversation = []


def run_agent(user_input: str) -> str:
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key":
        return "Please set a valid GROQ_API_KEY in ai-agent/.env"

    global _conversation
    _conversation.append(HumanMessage(content=user_input))
    result = agent.invoke({"messages": _conversation})
    _conversation = list(result["messages"])
    return _conversation[-1].content
