import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import { isSpeechSupported, listenOnce, speak } from "../utils/speech";

const WS_URL = import.meta.env.VITE_VOICE_WS_URL || "ws://localhost:8000/ws/call";

const CallContext = createContext(null);

export function CallProvider({ children }) {
  const wsRef = useRef(null);
  const activeRef = useRef(false);
  const listeningRef = useRef(false);
  const endingRef = useRef(false);
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
        wsRef.current?.send(JSON.stringify({ type: "message", text: "" }));
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
    endingRef.current = true;
    setStatus("ended");
    speechSynthesis.cancel();
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "hangup" }));
      wsRef.current.close();
    }
    wsRef.current = null;
  }, []);

  const startCall = useCallback(() => {
    if (!supported) {
      setError("Please use Chrome or Edge for voice calling.");
      return;
    }
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    setError("");
    setTranscript([]);
    setCallId(null);
    endingRef.current = false;
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
        if (data.greeting) {
          addLine("agent", data.greeting);
          await speak(data.greeting);
        }
        listenAndSend();
      }

      if (data.type === "agent_response") {
        addLine("agent", data.text);
        await speak(data.text);
        if (data.endCall) {
          activeRef.current = false;
          listeningRef.current = false;
          endingRef.current = true;
          setStatus("ended");
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify({ type: "hangup" }));
            wsRef.current.close();
          }
          wsRef.current = null;
          return;
        }
        listenAndSend();
      }

      if (data.type === "call_ended") {
        activeRef.current = false;
        listeningRef.current = false;
        setStatus("ended");
        if (!endingRef.current) {
          speechSynthesis.cancel();
        }
        endingRef.current = false;
        wsRef.current = null;
        if (data.reason === "admin_ended") {
          await speak("This call has been ended by the clinic. Thank you for calling.");
        }
      }
    };

    ws.onerror = () => {
      setError("Could not connect to the clinic line. Is the voice server running?");
      setStatus("idle");
      activeRef.current = false;
      wsRef.current = null;
    };

    ws.onclose = () => {
      activeRef.current = false;
      listeningRef.current = false;
      wsRef.current = null;
      setStatus((current) =>
        current === "active" || current === "connecting" ? "ended" : current
      );
    };
  }, [addLine, listenAndSend, supported]);

  useEffect(() => {
    const onUnload = () => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "hangup" }));
      }
    };
    window.addEventListener("beforeunload", onUnload);
    return () => window.removeEventListener("beforeunload", onUnload);
  }, []);

  const value = {
    status,
    callId,
    transcript,
    error,
    supported,
    startCall,
    endCall,
    isLive: status === "active" || status === "connecting",
  };

  return <CallContext.Provider value={value}>{children}</CallContext.Provider>;
}

export function useCall() {
  const ctx = useContext(CallContext);
  if (!ctx) throw new Error("useCall must be used within CallProvider");
  return ctx;
}
