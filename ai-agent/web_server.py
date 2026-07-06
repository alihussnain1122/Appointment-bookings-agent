import asyncio
import base64
import os
import tempfile
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from agent.agent import run_agent
from call_manager import call_manager, greeting_text
from voice.input import transcribe_file

load_dotenv()

ADMIN_PIN = os.getenv("ADMIN_PIN", "1234")
WHISPER_LOADING = False


@asynccontextmanager
async def lifespan(_app: FastAPI):
    global WHISPER_LOADING
    WHISPER_LOADING = True

    async def load_whisper():
        from voice.input import init_whisper
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, init_whisper)
        global WHISPER_LOADING
        WHISPER_LOADING = False
        print("Whisper ready for web calls.")

    asyncio.create_task(load_whisper())
    yield


app = FastAPI(title="Voice Call API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {
        "ok": True,
        "service": "voice-call-api",
        "whisperReady": not WHISPER_LOADING,
    }


@app.get("/api/calls/active")
async def active_calls():
    return {
        "calls": [
            call_manager._call_summary(s) for s in call_manager.sessions.values()
        ]
    }


async def transcribe_web_audio(audio_b64: str) -> str:
    audio_bytes = base64.b64decode(audio_b64)
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
        tmp.write(audio_bytes)
        path = tmp.name

    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, lambda: transcribe_file(path))
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


@app.websocket("/ws/call")
async def websocket_call(websocket: WebSocket):
    await websocket.accept()
    session = await call_manager.create_session(websocket)

    greeting = greeting_text()
    await call_manager.add_transcript(session.id, "agent", greeting)
    await websocket.send_json(
        {
            "type": "connected",
            "callId": session.id,
            "greeting": greeting,
        }
    )

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                user_text = (data.get("text") or "").strip()
                if not user_text:
                    await websocket.send_json(
                        {
                            "type": "agent_response",
                            "text": "Sorry, I didn't catch that. Could you say that again?",
                        }
                    )
                    continue

                await call_manager.add_transcript(session.id, "caller", user_text)

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: run_agent(user_text, session.agent_state),
                )

                await call_manager.add_transcript(session.id, "agent", response)
                await websocket.send_json(
                    {"type": "agent_response", "text": response}
                )

            elif data.get("type") == "audio":
                if WHISPER_LOADING:
                    await websocket.send_json(
                        {
                            "type": "agent_response",
                            "text": "One moment please, I'm still getting ready.",
                        }
                    )
                    continue

                user_text = await transcribe_web_audio(data["audio"])
                if not user_text:
                    await websocket.send_json(
                        {
                            "type": "agent_response",
                            "text": "Sorry, I didn't catch that. Could you say that again?",
                        }
                    )
                    continue

                await call_manager.add_transcript(session.id, "caller", user_text)

                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: run_agent(user_text, session.agent_state),
                )

                await call_manager.add_transcript(session.id, "agent", response)
                await websocket.send_json(
                    {"type": "agent_response", "text": response}
                )

            elif data.get("type") == "hangup":
                await call_manager.end_session(session.id, "caller_hangup")
                break

    except WebSocketDisconnect:
        await call_manager.end_session(session.id, "disconnected")
    except Exception as error:
        print(f"Call error: {error}")
        await call_manager.end_session(session.id, "error")


@app.websocket("/ws/admin")
async def websocket_admin(websocket: WebSocket):
    await websocket.accept()

    try:
        auth = await websocket.receive_json()
        if auth.get("pin") != ADMIN_PIN:
            await websocket.send_json({"type": "auth_failed"})
            await websocket.close()
            return

        await websocket.send_json({"type": "auth_ok"})
        await call_manager.register_admin(websocket)

        while True:
            data = await websocket.receive_json()
            if data.get("type") == "end_call":
                call_id = data.get("callId")
                if call_id:
                    await call_manager.end_session(call_id, "admin_ended")

    except WebSocketDisconnect:
        pass
    finally:
        await call_manager.unregister_admin(websocket)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("VOICE_PORT", "8000"))
    uvicorn.run("web_server:app", host="0.0.0.0", port=port, reload=False)
