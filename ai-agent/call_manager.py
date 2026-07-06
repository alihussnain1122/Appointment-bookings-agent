import asyncio
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv()

CLINIC_NAME = os.getenv("CLINIC_NAME", "Smile Dental Clinic")


def greeting_text() -> str:
    return (
        f"Hi there! Welcome to {CLINIC_NAME}. "
        "I'm Maya, and I'd be happy to help you schedule your visit. "
        "Are you looking to book an appointment today?"
    )


@dataclass
class CallSession:
    id: str
    caller_ws: object
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "active"
    transcript: list = field(default_factory=list)
    agent_state: dict = field(default_factory=dict)

    def add_line(self, role: str, text: str):
        entry = {
            "role": role,
            "text": text,
            "at": datetime.now(timezone.utc).isoformat(),
        }
        self.transcript.append(entry)
        return entry


class CallManager:
    def __init__(self):
        self.sessions: dict[str, CallSession] = {}
        self.admin_connections: set = set()
        self._lock = asyncio.Lock()

    async def create_session(self, caller_ws) -> CallSession:
        from agent.agent import create_session_state

        session = CallSession(
            id=str(uuid.uuid4())[:8],
            caller_ws=caller_ws,
            agent_state=create_session_state(),
        )
        async with self._lock:
            self.sessions[session.id] = session
        await self._broadcast_admins(
            {"type": "call_started", "call": self._call_summary(session)}
        )
        return session

    async def end_session(self, session_id: str, reason: str = "ended"):
        async with self._lock:
            session = self.sessions.pop(session_id, None)
        if not session:
            return
        session.status = reason
        await self._broadcast_admins(
            {"type": "call_ended", "callId": session_id, "reason": reason}
        )
        try:
            await session.caller_ws.send_json(
                {"type": "call_ended", "reason": reason}
            )
        except Exception:
            pass
        try:
            await session.caller_ws.close()
        except Exception:
            pass

    async def register_admin(self, ws):
        self.admin_connections.add(ws)
        calls = [self._call_summary(s) for s in self.sessions.values()]
        await ws.send_json({"type": "active_calls", "calls": calls})

    async def unregister_admin(self, ws):
        self.admin_connections.discard(ws)

    async def add_transcript(self, session_id: str, role: str, text: str):
        session = self.sessions.get(session_id)
        if not session:
            return
        entry = session.add_line(role, text)
        await self._broadcast_admins(
            {
                "type": "transcript",
                "callId": session_id,
                "entry": entry,
            }
        )

    def get_session(self, session_id: str) -> CallSession | None:
        return self.sessions.get(session_id)

    def _call_summary(self, session: CallSession) -> dict:
        return {
            "id": session.id,
            "startedAt": session.started_at,
            "status": session.status,
            "transcript": session.transcript,
        }

    async def _broadcast_admins(self, payload: dict):
        dead = []
        for ws in self.admin_connections:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.admin_connections.discard(ws)


call_manager = CallManager()
