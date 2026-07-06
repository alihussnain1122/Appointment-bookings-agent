import { Link } from "react-router-dom";
import { useVoiceCall } from "../hooks/useVoiceCall";

const CLINIC_NAME = import.meta.env.VITE_CLINIC_NAME || "Smile Dental Clinic";

export default function CallPage() {
  const {
    status,
    callId,
    transcript,
    error,
    supported,
    startCall,
    endCall,
    isLive,
  } = useVoiceCall();

  const statusLabel =
    status === "idle"
      ? "Ready to connect"
      : status === "connecting"
        ? "Connecting..."
        : status === "active"
          ? "Call in progress"
          : "Call ended";

  return (
    <div className="page">
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-icon">SD</div>
            <div>
              <h1>{CLINIC_NAME}</h1>
              <p>Book your dental visit by voice</p>
            </div>
          </div>
          <Link to="/admin" className="button secondary">
            Admin
          </Link>
        </header>

        <div className="call-layout">
          <section className="card phone-panel">
            <span className={`status-pill ${isLive ? "live" : ""}`}>
              <span className="status-dot" />
              {statusLabel}
            </span>

            {callId && <p className="hint">Call reference: {callId}</p>}

            {!isLive ? (
              <button
                className="call-button start"
                onClick={startCall}
                disabled={!supported || status === "connecting"}
              >
                {status === "connecting" ? "..." : "Call"}
              </button>
            ) : (
              <button className="call-button end" onClick={endCall}>
                End
              </button>
            )}

            <p className="hint">
              Tap call and allow microphone access. Maya will guide you step by
              step to book your appointment.
            </p>

            {error && <p className="hint" style={{ color: "var(--danger)" }}>{error}</p>}
            {!supported && (
              <p className="hint" style={{ color: "var(--danger)" }}>
                Voice calling works best in Chrome or Edge.
              </p>
            )}
          </section>

          <section className="card">
            <div className="transcript">
              <h2>Live transcript</h2>
              {transcript.length === 0 && (
                <p className="empty">Your conversation will appear here.</p>
              )}
              {transcript.map((line, index) => (
                <div key={index} className={`line ${line.role}`}>
                  <span className="meta">
                    {line.role === "agent" ? "Maya" : "You"}
                  </span>
                  {line.text}
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
