import os

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent

from tools.api_tools import book_appointment as api_book
from tools.api_tools import cancel_appointment as api_cancel
from tools.api_tools import check_availability as api_check

load_dotenv()

SYSTEM_PROMPT = """You are a friendly American medical appointment booking assistant.

Help users check doctor availability, book appointments, and cancel bookings.
Always use the provided tools for booking actions — never guess availability or confirm a booking without calling a tool.

Appointment rules:
- Each appointment is exactly 1 hour long
- Slots start on the hour only: 09:00, 10:00, 11:00, 14:00 (not 09:30 or 10:15)
- Dates must be YYYY-MM-DD (e.g. 2026-07-10)
- Times sent to tools must be HH:MM in 12-hour format (convert from what the user says)
- A doctor cannot have two appointments that overlap the same 1-hour slot
- Ask for missing details (name, doctor, date, time) before booking
- After booking, share the appointment ID so the user can cancel later
- Be concise, warm, and conversational with a natural American female like tone.
- Don't mention the tools in your response. Just book the appointment.
- And speak slowly and clearly.
"""


@tool
def check_availability(doctor: str, date: str, time: str) -> str:
    """Check if a doctor is available on a specific date and time."""
    return api_check(doctor, date, time)


@tool
def book_appointment(name: str, doctor: str, date: str, time: str) -> str:
    """Book an appointment for a patient with a doctor at a date and time."""
    return api_book(name, doctor, date, time)


@tool
def cancel_appointment(appointment_id: str) -> str:
    """Cancel an appointment using its ID (returned when booking)."""
    return api_cancel(appointment_id)


tools = [check_availability, book_appointment, cancel_appointment]

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0.2,
)

agent = create_react_agent(llm, tools, prompt=SYSTEM_PROMPT)


def run_agent(user_input: str) -> str:
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key":
        return "Please set a valid GROQ_API_KEY in ai-agent/.env"

    result = agent.invoke({"messages": [HumanMessage(content=user_input)]})
    return result["messages"][-1].content
