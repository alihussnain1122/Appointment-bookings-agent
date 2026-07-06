import json
import os
import time

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BACKEND_URL", "http://localhost:5000/api").rstrip("/")
DEFAULT_DOCTOR = os.getenv("CLINIC_DOCTOR", "Dr. Smith")

MAX_RETRIES = 3
RETRY_BACKOFF = 0.6


def _post(endpoint: str, payload: dict) -> str:
    """POST with retries for transient network errors and 5xx responses."""
    last_error = None
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(f"{BASE_URL}{endpoint}", json=payload, timeout=15)
            data = response.json() if response.content else {}

            if response.status_code >= 500:
                last_error = f"server {response.status_code}"
                time.sleep(RETRY_BACKOFF * (attempt + 1))
                continue

            if not response.ok:
                return json.dumps({"success": False, "status": response.status_code, **data})

            return json.dumps({"success": True, **data})
        except (requests.ConnectionError, requests.Timeout) as error:
            last_error = str(error)
            time.sleep(RETRY_BACKOFF * (attempt + 1))
        except requests.RequestException as error:
            return json.dumps({"success": False, "error": str(error)})

    return json.dumps({
        "success": False,
        "error": f"Could not reach the booking system after {MAX_RETRIES} attempts: {last_error}",
        "retryable": True,
    })


def check_availability(date: str, time: str) -> str:
    if not date or not time:
        missing = [k for k, v in (("date", date), ("time", time)) if not v]
        return json.dumps({"success": False, "missing": missing})
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
    try:
        data = json.loads(raw)
    except (ValueError, TypeError):
        return raw

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
