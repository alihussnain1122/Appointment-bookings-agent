import { useCallback, useEffect, useRef, useState } from "react";
import { isSpeechSupported, listenOnce, speak } from "../utils/speech";

const WS_URL = import.meta.env.VITE_VOICE_WS_URL || "ws://localhost:8000/ws/call";

export function useVoiceCall() {
  const wsRef = useRef(null);
  const activeRef = useRef(false);
  const listeningRef = useRef(false);
  const [status, setStatus] = useState("idle");
  const [callId, setCallId] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [error, setError] = useState("");
  const [supported] = useState(isSpeechSupported());

  const addLine = useCallback((role, text) => {
    setTranscript((prev) => [
      ...prev,
      { role, text, at: new Date().toISOString() },
    ]);
  }, []);

  const listenAndSend = useCallback(async () => {
    if (!activeRef.current || listeningRef.current) return;
    listeningRef.current = true;

    try {
      const text = await listenOnce();
      if (!activeRef.current) return;

      if (!text) {
        await speak("Sorry, I didn't catch that. Could you say that again?");
        listeningRef.current = false;
        listenAndSend();
        return;
      }

      addLine("caller", text);
      wsRef.current?.send(JSON.stringify({ type: "message", text }));
    } catch (listenError) {
      if (activeRef.current) setError(listenError.message);
    } finally {
      listeningRef.current = false;
    }
  }, [addLine]);

  const endCall = useCallback(() => {
    activeRef.current = false;
    listeningRef.current = false;
    setStatus("ended");
    speechSynthesis.cancel();
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "hangup" }));
      wsRef.current.close();
    }
  }, []);

  const startCall = useCallback(() => {
    if (!supported) {
      setError("Please use Chrome or Edge for voice calling.");
      return;
    }

    setError("");
    setTranscript([]);
    setStatus("connecting");

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("active");
      activeRef.current = true;
    };

    ws.onmessage = async (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "connected") {
        setCallId(data.callId);
        addLine("agent", data.greeting);
        await speak(data.greeting);
        listenAndSend();
      }

      if (data.type === "agent_response") {
        addLine("agent", data.text);
        await speak(data.text);
        listenAndSend();
      }

      if (data.type === "call_ended") {
        activeRef.current = false;
        setStatus("ended");
        speechSynthesis.cancel();
        if (data.reason === "admin_ended") {
          await speak("This call has been ended by the clinic. Thank you for calling.");
        }
      }
    };

    ws.onerror = () => {
      setError("Could not connect to the clinic line. Is the voice server running?");
      setStatus("idle");
      activeRef.current = false;
    };

    ws.onclose = () => {
      activeRef.current = false;
      setStatus((current) => (current === "active" ? "ended" : current));
    };
  }, [addLine, listenAndSend, supported]);

  useEffect(() => {
    return () => {
      activeRef.current = false;
      wsRef.current?.close();
      speechSynthesis.cancel();
    };
  }, []);

  return {
    status,
    callId,
    transcript,
    error,
    supported,
    startCall,
    endCall,
    isLive: status === "active",
  };
}
