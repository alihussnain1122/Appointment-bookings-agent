import json
import os

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:5000/api").rstrip("/")
DEFAULT_DOCTOR = os.getenv("CLINIC_DOCTOR", "Dr. Smith")


def _post(endpoint: str, payload: dict) -> str:
    try:
        response = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=15)
        data = response.json() if response.content else {}
        if not response.ok:
            return json.dumps({"success": False, "status": response.status_code, **data})
        return json.dumps({"success": True, **data})
    except requests.RequestException as error:
        return json.dumps({"success": False, "error": str(error)})


def check_availability(date: str, time: str) -> str:
    return _post(
        "/check-availability",
        {"doctor": DEFAULT_DOCTOR, "date": date, "time": time},
    )


def book_appointment(name: str, service: str, date: str, time: str) -> str:
    raw = _post(
        "/book",
        {
            "name": name,
            "doctor": DEFAULT_DOCTOR,
            "service": service,
            "date": date,
            "time": time,
        },
    )
    data = json.loads(raw)
    if data.get("success") and data.get("appointment"):
        appt = data["appointment"]
        return json.dumps({
            "success": True,
            "message": data.get("message"),
            "appointment": {
                "name": appt.get("name"),
                "service": appt.get("service"),
                "date": appt.get("date"),
                "time": appt.get("time"),
                "status": appt.get("status"),
            },
        })
    return raw


def cancel_appointment(name: str, date: str, time: str) -> str:
    return _post("/cancel", {"name": name, "date": date, "time": time})


def health_check() -> str:
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        return json.dumps(response.json())
    except requests.RequestException as error:
        return json.dumps({"ok": False, "error": str(error)})
