import contextvars
import json
import os
import random
import re
import time
from datetime import datetime, timedelta

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq

from tools.api_tools import book_appointment as api_book
from tools.api_tools import cancel_appointment as api_cancel
from tools.api_tools import check_availability as api_check

load_dotenv()

session_ctx = contextvars.ContextVar("agent_session", default=None)

CLINIC_NAME = os.getenv("CLINIC_NAME", "Smile Dental Clinic")
CLINIC_DOCTOR = os.getenv("CLINIC_DOCTOR", "Dr. Smith")

DENTAL_SERVICES = """
- Oral examination / checkup
- Tooth scaling and polishing
- Teeth whitening
- Dental filling
- Root canal treatment
- Tooth extraction
- Braces consultation
- Gum treatment
"""

SERVICE_KEYWORDS = {
    "routine checkup": "oral examination / checkup",
    "routine check up": "oral examination / checkup",
    "check up": "oral examination / checkup",
    "checkup": "oral examination / checkup",
    "check-up": "oral examination / checkup",
    "examination": "oral examination / checkup",
    "exam": "oral examination / checkup",
    "tooth scaling": "tooth scaling and polishing",
    "teeth scaling": "tooth scaling and polishing",
    "scaling": "tooth scaling and polishing",
    "spelling": "tooth scaling and polishing",  # common speech-to-text typo
    "polish": "tooth scaling and polishing",
    "cleaning": "tooth scaling and polishing",
    "whitening": "teeth whitening",
    "bleach": "teeth whitening",
    "filling": "dental filling",
    "cavity": "dental filling",
    "root canal": "root canal treatment",
    "extraction": "tooth extraction",
    "remove tooth": "tooth extraction",
    "pull tooth": "tooth extraction",
    "braces": "braces consultation",
    "orthodont": "braces consultation",
    "gum": "gum treatment",
    "periodont": "gum treatment",
}

CLINIC_OPEN_HOUR = 9
CLINIC_CLOSE_HOUR = 17

BOOKING_FIELDS = ("name", "service", "date", "time")

SPOKEN_SERVICE = {
    "oral examination / checkup": "a routine checkup",
    "tooth scaling and polishing": "teeth scaling",
    "teeth whitening": "teeth whitening",
    "dental filling": "a filling",
    "root canal treatment": "a root canal",
    "tooth extraction": "an extraction",
    "braces consultation": "a braces consultation",
    "gum treatment": "gum treatment",
}

ASK_PROMPTS = {
    "name": [
        "Of course! What's your full name?",
        "Sure thing — may I have your name, please?",
        "Lovely. And who am I speaking with today?",
    ],
    "service": [
        "What are you coming in for — a checkup, scaling, filling, or something else?",
        "And what treatment do you need? We do checkups, scaling, fillings, whitening, and more.",
        "What can we help you with today — checkup, cleaning, filling, or another service?",
    ],
    "date": [
        "When would you like to come in? Tomorrow works, or just tell me a date.",
        "What day suits you best?",
        "And which day were you thinking — tomorrow, the day after, or a specific date?",
    ],
    "time": [
        "What time works for you? We're here nine to five, on the hour.",
        "And what time would suit you — morning or afternoon is fine, as long as it's on the hour.",
        "Nearly done — what time would you like? Somewhere between 9 AM and 5 PM.",
    ],
}

REPEAT_PROMPTS = {
    "name": [
        "Sorry, I didn't quite catch your name — could you say that again for me?",
        "I'm sorry, I missed that. What's your full name?",
    ],
    "service": [
        "Sorry, I didn't catch that — are you looking for a checkup, scaling, a filling, or something else?",
        "I'm sorry, could you repeat the treatment? A checkup, scaling, filling, or whitening?",
    ],
    "date": [
        "Sorry, I didn't get the date — could you tell me again? Tomorrow is absolutely fine.",
        "I'm sorry, I missed that. Which day were you hoping for?",
    ],
    "time": [
        "Sorry, I didn't catch the time — could you say that again? We're open 9 to 5 on the hour.",
        "I'm sorry, what time works for you? Any hour between 9 AM and 5 PM.",
    ],
}

SILENCE_PROMPTS = [
    "Hello? I'm still here — would you like to book an appointment?",
    "Sorry, I can't hear you?",
    "Hello? Just let me know if you'd like to book.",
]

MAX_SILENCE_ATTEMPTS = 3
SILENCE_GOODBYE = (
    "I haven't heard back from you. "
    "Please call us again whenever you're ready. Goodbye!"
)

ACK_TRANSITIONS = {
    "service": [
        "Lovely, {name}.",
        "Thank you, {name}.",
        "Nice to meet you, {name}.",
    ],
    "date": [
        "Got it — {service}.",
        "Perfect, {service}.",
        "Alright, {service}.",
    ],
    "time": [
        "Okay, {date}.",
        "Great, {date}.",
        "{date} — lovely.",
    ],
}

FILLER_WORDS = {"umm", "uh", "uhh", "hmm", "er", "erm", "like", "something", "anything"}

BOOKING_INTENT = (
    "book", "appointment", "schedule", "visit", "see the dentist",
    "dental appointment", "make an appointment",
)
AFFIRMATIVE = (
    "yes", "yeah", "yep", "sure", "please", "i would", "i'd like",
    "i would like", "correct", "that's right", "that is right",
)

SYSTEM_PROMPT = f"""You are Maya, a warm human receptionist at {CLINIC_NAME}. One dentist: {CLINIC_DOCTOR}.

Rules:
- Sound natural and friendly — like a real person at the front desk, not a robot
- Pakistani English, short warm replies (1-2 sentences)
- ONE question at a time
- If you don't understand, politely ask the patient to repeat
- NEVER write code, JSON, XML, or function syntax
- Use tools only for cancellations or ending calls

Booking is handled by the system. You help with cancellations and general questions.
Never share booking IDs.
"""

GOODBYE_PHRASES = (
    "no thanks", "no thank you", "that's all", "that is all", "nothing else",
    "goodbye", "good bye", "bye", "see you", "i'm good", "im good", "all set",
    "no that's it", "no thats it", "thank you bye", "thanks bye", "nope",
)


@tool
def check_availability(date: str, time: str) -> str:
    """Check if the dentist has an open 1-hour slot on the given date and time."""
    return api_check(date, time)


@tool
def book_appointment(name: str, service: str, date: str, time: str) -> str:
    """Book a 1-hour dental appointment. ALL of name, service, date, time are required."""
    session = session_ctx.get() or {}
    booking = session.get("booking", {})

    name = (name or booking.get("name") or "").strip()
    service = (service or booking.get("service") or "").strip()
    date = (date or booking.get("date") or "").strip()
    time = (time or booking.get("time") or "").strip()

    missing = [k for k, v in (("name", name), ("service", service), ("date", date), ("time", time)) if not v]
    if missing:
        return json.dumps({
            "success": False,
            "missing": missing,
            "message": f"Cannot book yet — still need: {', '.join(missing)}.",
        })

    booking.update({"name": name, "service": service, "date": date, "time": time})
    result = api_book(name, service, date, time)
    data = json.loads(result)
    if data.get("success"):
        booking["booked"] = True
        booking["awaiting_followup"] = True
        booking["active"] = False
        session["booking"] = booking
    return result


@tool
def cancel_appointment(name: str, date: str, time: str) -> str:
    """Cancel an appointment using the patient's name, date, and time."""
    return api_cancel(name, date, time)


@tool
def end_call() -> str:
    """End the call when the patient needs nothing else."""
    session = session_ctx.get()
    if session is not None:
        session["end_call"] = True
    return json.dumps({"success": True})


TOOLS = [check_availability, book_appointment, cancel_appointment, end_call]
TOOL_MAP = {t.name: t for t in TOOLS}

llm = ChatGroq(
    groq_api_key=os.getenv("GROQ_API_KEY"),
    model_name=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
    temperature=0.2,
)
llm_with_tools = llm.bind_tools([cancel_appointment, end_call])

_cli_session: dict = {}

_LEAK_RE = re.compile(
    r"<function\s*=\s*([a-zA-Z_]+)\s*>\s*(\{.*\})?",
    re.DOTALL | re.IGNORECASE,
)

_DATE_RE = re.compile(
    r"\b(\d{4})-(\d{2})-(\d{2})\b"
    r"|\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b"
    r"|\b(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december)(?:\s+(\d{4}))?\b"
    r"|\b(january|february|march|april|may|june|july|august|september|october|november|december)"
    r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:,?\s*(\d{4}))?\b",
    re.IGNORECASE,
)

_TIME_RE = re.compile(
    r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?\s*m\.?|p\.?\s*m\.?)\b"
    r"|\b(\d{1,2}):(\d{2})\b"
    r"|\b(at\s+)?(\d{1,2})\s*o'?clock\b",
    re.IGNORECASE,
)

_WEEKDAYS = {
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3,
    "friday": 4, "saturday": 5, "sunday": 6,
}

_MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
}


def reset_conversation():
    global _cli_session
    _cli_session = _empty_state()


def create_session_state() -> dict:
    return _empty_state()


def _empty_state() -> dict:
    return {
        "messages": [],
        "end_call": False,
        "booking": {
            "active": False,
            "name": None,
            "service": None,
            "date": None,
            "time": None,
            "booked": False,
            "awaiting_followup": False,
            "silence_count": 0,
        },
    }


def _sanitize(text: str) -> str:
    if not text:
        return ""
    cleaned = re.sub(r"<function\b.*?(?:</function>|$)", "", text, flags=re.DOTALL | re.IGNORECASE)
    cleaned = re.sub(r"```[\s\S]*?```", "", cleaned)
    cleaned = re.sub(r"\{[^{}]*\"(?:name|service|date|time)\"[^{}]*\}", "", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned


def _is_goodbye(text: str) -> bool:
    lower = text.lower().strip()
    return any(p in lower for p in GOODBYE_PHRASES)


def _is_booking_intent(text: str) -> bool:
    lower = text.lower()
    return any(p in lower for p in BOOKING_INTENT)


def _is_affirmative(text: str) -> bool:
    lower = text.lower().strip()
    return any(lower == p or lower.startswith(p + " ") or p in lower for p in AFFIRMATIVE)


def _missing_field(booking: dict) -> str | None:
    for field in BOOKING_FIELDS:
        if not booking.get(field):
            return field
    return None


def _pick(options: list[str]) -> str:
    return random.choice(options)


def _spoken_service(service: str) -> str:
    return SPOKEN_SERVICE.get(service, service)


def _spoken_date(date_str: str) -> str:
    if not date_str:
        return ""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        today = _today().date()
        delta = (dt.date() - today).days
        if delta == 0:
            return "today"
        if delta == 1:
            return "tomorrow"
        if delta == 2:
            return "the day after tomorrow"
        return dt.strftime("%A the %d of %B").replace(" 0", " ")
    except ValueError:
        return date_str


def _advance_prompt(field: str, booking: dict) -> str:
    if field == "service" and booking.get("name"):
        name = booking["name"]
        return f"{_pick(ACK_TRANSITIONS['service']).format(name=name)} {_ask_field('service')}"
    if field == "date":
        service = _spoken_service(booking.get("service", ""))
        ack = _pick(ACK_TRANSITIONS["date"]).format(service=service)
        return f"{ack} {_ask_field('date')}"
    if field == "time":
        date = _spoken_date(booking.get("date") or "")
        ack = _pick(ACK_TRANSITIONS["time"]).format(date=date)
        return f"{ack} {_ask_field('time')}"
    return _ask_field(field)


def _ask_field(field: str) -> str:
    return _pick(ASK_PROMPTS[field])


def _repeat_field(field: str) -> str:
    return _pick(REPEAT_PROMPTS[field])


def _handle_silence(booking: dict) -> tuple[str, bool]:
    count = booking.get("silence_count", 0) + 1
    booking["silence_count"] = count

    if count > MAX_SILENCE_ATTEMPTS:
        return SILENCE_GOODBYE, True

    if booking.get("awaiting_followup"):
        return "Hello? Are you still there — is there anything else I can help with?", False

    if booking.get("active"):
        missing = _missing_field(booking)
        if missing:
            return _repeat_field(missing), False

    return SILENCE_PROMPTS[count - 1], False


def _parse_service(text: str) -> str | None:
    lower = text.lower()
    for keyword, label in sorted(SERVICE_KEYWORDS.items(), key=lambda x: -len(x[0])):
        if keyword in lower:
            return label
    if "teeth" in lower and any(t in lower for t in ("spell", "scal", "clean", "polish")):
        return "tooth scaling and polishing"
    if "routine" in lower and "check" in lower:
        return "oral examination / checkup"
    return None


def _today() -> datetime:
    return datetime.now()


def _finalize_date(year: int, month: int, day: int) -> str:
    from datetime import date

    candidate = date(year, month, day)
    today = _today().date()
    if candidate < today:
        candidate = date(year + 1, month, day)
    return candidate.strftime("%Y-%m-%d")


def _parse_date(text: str) -> str | None:
    lower = text.lower().strip()
    base = _today().date()

    if re.search(r"\bday after tomorrow\b", lower):
        return (base + timedelta(days=2)).strftime("%Y-%m-%d")
    if re.search(r"\btomorrow\b", lower):
        return (base + timedelta(days=1)).strftime("%Y-%m-%d")
    if re.search(r"\btoday\b", lower):
        return base.strftime("%Y-%m-%d")

    for name, weekday in _WEEKDAYS.items():
        if re.search(rf"\b(?:this\s+|next\s+)?{name}\b", lower):
            days_ahead = (weekday - base.weekday()) % 7
            if days_ahead == 0 and "next" in lower:
                days_ahead = 7
            return (base + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    match = _DATE_RE.search(text)
    if not match:
        return None

    if match.group(1):
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"

    if match.group(4):
        day, month, year = int(match.group(4)), int(match.group(5)), int(match.group(6))
        if year < 100:
            year += 2000
        return f"{year:04d}-{month:02d}-{day:02d}"

    if match.group(7):
        day = int(match.group(7))
        month_name = match.group(8).lower()
        year = int(match.group(9)) if match.group(9) else _today().year
        month = _MONTHS[month_name]
        return _finalize_date(year, month, day)

    month_name = match.group(10).lower()
    day = int(match.group(11))
    year = int(match.group(12)) if match.group(12) else _today().year
    month = _MONTHS[month_name]
    return _finalize_date(year, month, day)


def _normalize_meridiem(value: str) -> str:
    compact = re.sub(r"[\s.]", "", value.lower())
    if compact.startswith("a"):
        return "am"
    if compact.startswith("p"):
        return "pm"
    return compact


def _parse_time_raw(text: str) -> tuple[int, int] | None:
    """Parse hour/minute without clinic-hour validation."""
    match = _TIME_RE.search(text)
    if not match:
        return None

    if match.group(1) and match.group(3):
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = _normalize_meridiem(match.group(3))
        if meridiem == "pm" and hour < 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0
    elif match.group(4):
        hour = int(match.group(4))
        minute = int(match.group(5))
    else:
        hour = int(match.group(7))
        minute = 0

    return hour, minute


def _parse_time(text: str) -> str | None:
    parsed = _parse_time_raw(text)
    if not parsed:
        return None

    hour, minute = parsed
    if minute != 0:
        return None
    if hour < CLINIC_OPEN_HOUR or hour > CLINIC_CLOSE_HOUR:
        return None
    return f"{hour:02d}:00"


def _time_rejection_message(text: str) -> str | None:
    parsed = _parse_time_raw(text)
    if not parsed:
        return None
    hour, minute = parsed
    if minute != 0:
        return (
            "We book in one-hour slots on the hour — "
            "so 10 AM, 2 PM, that sort of thing. What hour works for you?"
        )
    if hour < CLINIC_OPEN_HOUR or hour > CLINIC_CLOSE_HOUR:
        spoken = text.strip()
        return (
            f"Ah, {spoken} is outside our hours — we're open 9 AM to 5 PM. "
            "What time between those would suit you?"
        )
    return None


def _looks_like_name(text: str) -> bool:
    lower = text.lower()
    if _parse_date(text) or _parse_time(text) or _parse_service(text):
        return False
    if _is_affirmative(text) or _is_booking_intent(text) or _is_goodbye(text):
        return False
    words = text.strip().split()
    return 1 <= len(words) <= 5 and all(w.replace(".", "").replace("-", "").isalpha() for w in words)


def _apply_user_to_booking(user_input: str, booking: dict) -> None:
    """Extract booking fields from the patient's message."""
    if not booking.get("name") and _looks_like_name(user_input):
        booking["name"] = user_input.strip().title()

    service = _parse_service(user_input)
    if service:
        booking["service"] = service

    date = _parse_date(user_input)
    if date:
        booking["date"] = date

    time_val = _parse_time(user_input)
    if time_val:
        booking["time"] = time_val


def _input_attempts_field(user_input: str, field: str) -> bool:
    text = user_input.strip()
    if not text:
        return False
    if field == "name":
        return (
            not _is_affirmative(text)
            and not _is_booking_intent(text)
            and not _is_goodbye(text)
        )
    if field == "service":
        if _parse_service(text):
            return True
        words = {w.lower() for w in text.split()}
        if _looks_like_name(text) and not words & FILLER_WORDS:
            return False
        return bool(text) and not _parse_date(text) and _parse_time_raw(text) is None
    if field == "date":
        return bool(_parse_date(text)) or _parse_time_raw(text) is not None
    if field == "time":
        return _parse_time_raw(text) is not None
    return bool(text)


def _field_parse_failed(user_input: str, field: str) -> bool:
    text = user_input.strip()
    if not text:
        return True
    if field == "name":
        return not _looks_like_name(text)
    if field == "service":
        return not _parse_service(text)
    if field == "date":
        return not _parse_date(text)
    if field == "time":
        return _parse_time(text) is None
    return False


def _booking_prompt(missing: str, user_input: str, booking: dict, before: dict) -> str:
    before_missing = _missing_field(before)

    if not user_input.strip():
        return _repeat_field(missing)

    if missing == "time":
        hint = _time_rejection_message(user_input)
        if hint:
            return hint

    if before_missing and before_missing != missing:
        return _advance_prompt(missing, booking)

    if _input_attempts_field(user_input, missing) and _field_parse_failed(user_input, missing):
        return _repeat_field(missing)

    return _ask_field(missing)


def _format_slot(date: str, time_val: str) -> str:
    try:
        dt = datetime.strptime(f"{date} {time_val}", "%Y-%m-%d %H:%M")
        return dt.strftime("%B %d at %I:%M %p").replace(" 0", " ")
    except ValueError:
        return f"{date} at {time_val}"


def _followup_message(booking: dict) -> str:
    name = booking.get("name", "")
    svc = _spoken_service(booking.get("service", "your appointment"))
    slot = _format_slot(booking.get("date", ""), booking.get("time", ""))
    if name:
        return (
            f"Lovely, {name} — you're all booked for {svc} on {slot}. "
            "Is there anything else I can help you with?"
        )
    return (
        f"You're all booked for {svc} on {slot}. "
        "Is there anything else I can help you with?"
    )


def _orchestrate_booking(user_input: str, state: dict) -> tuple[str, bool] | None:
    """Deterministic booking flow — no LLM tool calls needed."""
    booking = state.get("booking", {})

    if booking.get("awaiting_followup"):
        return None

    if not booking.get("active"):
        if _is_booking_intent(user_input) or _is_affirmative(user_input):
            booking["active"] = True
        else:
            return None

    before = {field: booking.get(field) for field in BOOKING_FIELDS}
    _apply_user_to_booking(user_input, booking)

    missing = _missing_field(booking)
    if missing:
        return _booking_prompt(missing, user_input, booking, before), False

    if booking.get("booked"):
        return None

    avail_raw = api_check(booking["date"], booking["time"])
    avail = json.loads(avail_raw)
    if not avail.get("success"):
        return (
            "Bear with me — I'm having a little trouble with the system. "
            "Could you tell me the date and time once more?"
        ), False

    if not avail.get("available"):
        booking.update({"date": None, "time": None})
        reason = avail.get("reason") or avail.get("message") or "that slot's already taken."
        return (
            f"Oh, I'm sorry — {reason} "
            "What other day and time might work for you?"
        ), False

    token = session_ctx.set(state)
    try:
        result_raw = book_appointment.invoke({
            "name": booking["name"],
            "service": booking["service"],
            "date": booking["date"],
            "time": booking["time"],
        })
    finally:
        session_ctx.reset(token)

    result = json.loads(result_raw)
    if not result.get("success"):
        msg = result.get("message") or result.get("error") or "something went wrong on my end"
        return f"Oh dear, {msg} — shall we try a different time?", False

    return _followup_message(booking), False


def _parse_leaks(text: str) -> list[tuple[str, dict]]:
    if not text or "<function" not in text.lower():
        return []
    found = []
    for match in _LEAK_RE.finditer(text):
        name = match.group(1)
        body = match.group(2) or "{}"
        try:
            args = json.loads(body)
        except (ValueError, TypeError):
            args = {}
        found.append((name, args))
    return found


def _run_tool(name: str, args: dict, state: dict) -> str:
    tool_fn = TOOL_MAP.get(name)
    if not tool_fn:
        return json.dumps({"success": False, "message": "Unknown action."})
    if name == "end_call":
        state["end_call"] = True
        return end_call.invoke({})
    if name in ("book_appointment", "check_availability"):
        return json.dumps({
            "success": False,
            "message": "Booking is handled by the reception system. Ask for name, service, date, and time.",
        })
    return tool_fn.invoke(args)


def _tool_loop(state: dict, max_steps: int = 6) -> str:
    """LLM loop for cancellations and general chat only."""
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    for _ in range(max_steps):
        try:
            response = llm_with_tools.invoke(messages)
        except Exception as error:
            print("LLM error:", error)
            time.sleep(0.5)
            return "I'm having a little trouble. Could you please say that again?"

        state["messages"].append(response)
        messages.append(response)

        content = response.content if isinstance(response.content, str) else str(response.content or "")
        leaks = _parse_leaks(content)
        if leaks:
            for name, args in leaks:
                result = _run_tool(name, args, state)
                messages.append(ToolMessage(content=result, tool_call_id=f"leak_{name}"))
                state["messages"].append(messages[-1])
            continue

        if not response.tool_calls:
            return _sanitize(content)

        for tc in response.tool_calls:
            result = _run_tool(tc["name"], tc["args"], state)
            msg = ToolMessage(content=result, tool_call_id=tc["id"])
            messages.append(msg)
            state["messages"].append(msg)

        if state.get("end_call"):
            final = llm.invoke(messages + [
                HumanMessage(content="Say a brief warm goodbye to the patient. One sentence only.")
            ])
            return _sanitize(final.content or "Thank you for calling. Goodbye!")

    return "How else may I help you today?"


def _handle_followup(user_input: str, state: dict) -> tuple[str, bool] | None:
    booking = state.get("booking", {})

    if booking.get("awaiting_followup"):
        if _is_goodbye(user_input):
            booking["awaiting_followup"] = False
            state["end_call"] = True
            name = booking.get("name", "")
            prefix = f"Thank you, {name}. " if name else ""
            return f"{prefix}Take care, and have a lovely day. Goodbye!", True
        booking["awaiting_followup"] = False
        booking["booked"] = False
        booking["active"] = False
        booking.update({"name": None, "service": None, "date": None, "time": None})
        return "Of course — happy to help. What else can I do for you?", False

    return None


def run_agent(user_input: str, session_state: dict | None = None) -> tuple[str, bool]:
    if not os.getenv("GROQ_API_KEY") or os.getenv("GROQ_API_KEY") == "your_groq_api_key":
        return "Please set a valid GROQ_API_KEY in ai-agent/.env", False

    user_input = (user_input or "").strip()
    state = session_state if session_state is not None else _cli_session
    state.setdefault("messages", [])
    state.setdefault("booking", _empty_state()["booking"])
    state["end_call"] = False

    booking = state["booking"]
    if not user_input:
        text, ended = _handle_silence(booking)
        state["messages"].append(AIMessage(content=text))
        if ended:
            state["end_call"] = True
        return _sanitize(text), ended

    booking["silence_count"] = 0

    followup = _handle_followup(user_input, state)
    if followup:
        text, ended = followup
        return _sanitize(text), ended

    orchestrated = _orchestrate_booking(user_input, state)
    if orchestrated:
        text, ended = orchestrated
        state["messages"].append(HumanMessage(content=user_input))
        state["messages"].append(AIMessage(content=text))
        return _sanitize(text), ended

    token = session_ctx.set(state)
    try:
        state["messages"].append(HumanMessage(content=user_input))
        text = _tool_loop(state)
        clean = _sanitize(text)

        if not clean:
            clean = "Sorry, I didn't quite follow — could you tell me again?"

        return clean, bool(state.get("end_call"))
    finally:
        session_ctx.reset(token)
