import { useCallback, useEffect, useRef, useState } from "react";

const WS_URL = import.meta.env.VITE_ADMIN_WS_URL || "ws://localhost:8000/ws/admin";

export function useAdminMonitor(pin) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [authError, setAuthError] = useState("");
  const [calls, setCalls] = useState([]);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [transcripts, setTranscripts] = useState({});

  const connect = useCallback(() => {
    if (!pin) {
      setAuthError("Enter admin PIN.");
      return;
    }

    setAuthError("");
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      ws.send(JSON.stringify({ pin }));
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);

      if (data.type === "auth_failed") {
        setAuthError("Invalid admin PIN.");
        ws.close();
        return;
      }

      if (data.type === "auth_ok") {
        setConnected(true);
      }

      if (data.type === "active_calls") {
        setCalls(data.calls);
        const map = {};
        data.calls.forEach((call) => {
          map[call.id] = call.transcript || [];
        });
        setTranscripts(map);
        if (data.calls.length && !selectedCallId) {
          setSelectedCallId(data.calls[0].id);
        }
      }

      if (data.type === "call_started") {
        setCalls((prev) => {
          const exists = prev.some((call) => call.id === data.call.id);
          return exists ? prev : [...prev, data.call];
        });
        setTranscripts((prev) => ({
          ...prev,
          [data.call.id]: data.call.transcript || [],
        }));
        setSelectedCallId((current) => current || data.call.id);
      }

      if (data.type === "transcript") {
        setTranscripts((prev) => ({
          ...prev,
          [data.callId]: [...(prev[data.callId] || []), data.entry],
        }));
      }

      if (data.type === "call_ended") {
        setCalls((prev) => prev.filter((call) => call.id !== data.callId));
        setSelectedCallId((current) =>
          current === data.callId ? null : current
        );
      }
    };

    ws.onclose = () => {
      setConnected(false);
    };

    ws.onerror = () => {
      setAuthError("Could not connect to admin channel.");
      setConnected(false);
    };
  }, [pin, selectedCallId]);

  const endCall = useCallback((callId) => {
    wsRef.current?.send(JSON.stringify({ type: "end_call", callId }));
  }, []);

  useEffect(() => {
    return () => wsRef.current?.close();
  }, []);

  const selectedTranscript = selectedCallId
    ? transcripts[selectedCallId] || []
    : [];

  return {
    connected,
    authError,
    calls,
    selectedCallId,
    setSelectedCallId,
    selectedTranscript,
    connect,
    endCall,
  };
}
