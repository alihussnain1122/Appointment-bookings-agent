import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

const WS_URL = import.meta.env.VITE_ADMIN_WS_URL || "ws://localhost:8000/ws/admin";
const API_URL = import.meta.env.VITE_VOICE_API_URL || "http://localhost:8000";

const AdminContext = createContext(null);

function mergeCalls(existing, incoming) {
  const map = new Map(existing.map((c) => [c.id, c]));
  incoming.forEach((c) => map.set(c.id, { ...map.get(c.id), ...c }));
  return Array.from(map.values());
}

export function AdminProvider({ children }) {
  const wsRef = useRef(null);
  const pinRef = useRef("");
  const [connected, setConnected] = useState(false);
  const [authError, setAuthError] = useState("");
  const [calls, setCalls] = useState([]);
  const [selectedCallId, setSelectedCallId] = useState(null);
  const [transcripts, setTranscripts] = useState({});

  const applyActiveCalls = useCallback((incomingCalls) => {
    setCalls((prev) => mergeCalls(prev, incomingCalls));
    setTranscripts((prev) => {
      const next = { ...prev };
      incomingCalls.forEach((call) => {
        next[call.id] = call.transcript || next[call.id] || [];
      });
      return next;
    });
    setSelectedCallId((current) => current || incomingCalls[0]?.id || null);
  }, []);

  const fetchActiveCalls = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/api/calls/active`);
      if (!res.ok) return;
      const data = await res.json();
      if (data.calls?.length) applyActiveCalls(data.calls);
    } catch {
      /* voice server offline */
    }
  }, [applyActiveCalls]);

  const handleAdminMessage = useCallback(
    (data) => {
      if (data.type === "auth_failed") {
        setAuthError("Invalid admin PIN.");
        setConnected(false);
        sessionStorage.removeItem("admin_pin");
        wsRef.current?.close();
        return;
      }

      if (data.type === "auth_ok") {
        setConnected(true);
        setAuthError("");
        sessionStorage.setItem("admin_pin", pinRef.current);
      }

      if (data.type === "active_calls") {
        applyActiveCalls(data.calls || []);
      }

      if (data.type === "call_started") {
        setCalls((prev) => mergeCalls(prev, [data.call]));
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
    },
    [applyActiveCalls]
  );

  const connect = useCallback(
    (pin) => {
      const usePin = pin || pinRef.current || sessionStorage.getItem("admin_pin");
      if (!usePin) {
        setAuthError("Enter admin PIN.");
        return;
      }

      if (
        wsRef.current?.readyState === WebSocket.OPEN ||
        wsRef.current?.readyState === WebSocket.CONNECTING
      ) {
        return;
      }

      pinRef.current = usePin;
      setAuthError("");

      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        ws.send(JSON.stringify({ pin: usePin }));
      };

      ws.onmessage = (event) => {
        handleAdminMessage(JSON.parse(event.data));
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
      };

      ws.onerror = () => {
        setAuthError("Could not connect to admin channel. Is the voice server running?");
        setConnected(false);
      };

      fetchActiveCalls();
    },
    [fetchActiveCalls, handleAdminMessage]
  );

  const disconnect = useCallback(() => {
    wsRef.current?.close();
    wsRef.current = null;
    setConnected(false);
    sessionStorage.removeItem("admin_pin");
  }, []);

  const endCall = useCallback((callId) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "end_call", callId }));
    }
  }, []);

  useEffect(() => {
    const savedPin = sessionStorage.getItem("admin_pin");
    if (savedPin) {
      pinRef.current = savedPin;
      connect(savedPin);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!connected) return;
    const id = setInterval(fetchActiveCalls, 3000);
    return () => clearInterval(id);
  }, [connected, fetchActiveCalls]);

  const selectedTranscript = selectedCallId
    ? transcripts[selectedCallId] || []
    : [];

  return (
    <AdminContext.Provider
      value={{
        connected,
        authError,
        calls,
        selectedCallId,
        setSelectedCallId,
        selectedTranscript,
        connect,
        disconnect,
        endCall,
        savedPin: pinRef.current || sessionStorage.getItem("admin_pin") || "",
      }}
    >
      {children}
    </AdminContext.Provider>
  );
}

export function useAdmin() {
  const ctx = useContext(AdminContext);
  if (!ctx) throw new Error("useAdmin must be used within AdminProvider");
  return ctx;
}
