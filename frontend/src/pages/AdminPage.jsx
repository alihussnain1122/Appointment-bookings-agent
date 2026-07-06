import { useState } from "react";
import { Link } from "react-router-dom";
import { useAdminMonitor } from "../hooks/useAdminMonitor";

const CLINIC_NAME = import.meta.env.VITE_CLINIC_NAME || "Smile Dental Clinic";

export default function AdminPage() {
  const [pin, setPin] = useState("");
  const {
    connected,
    authError,
    calls,
    selectedCallId,
    setSelectedCallId,
    selectedTranscript,
    connect,
    endCall,
  } = useAdminMonitor(pin);

  return (
    <div className="page">
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            <div className="brand-icon">AD</div>
            <div>
              <h1>{CLINIC_NAME} Admin</h1>
              <p>Monitor live calls and end them when needed</p>
            </div>
          </div>
          <Link to="/" className="button secondary">
            Patient view
          </Link>
        </header>

        {!connected ? (
          <section className="card" style={{ maxWidth: 480 }}>
            <h2>Admin login</h2>
            <p className="hint" style={{ marginBottom: 16 }}>
              Enter your PIN to monitor active patient calls.
            </p>
            <div className="toolbar">
              <input
                className="input"
                type="password"
                placeholder="Admin PIN"
                value={pin}
                onChange={(e) => setPin(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && connect()}
              />
              <button className="button" onClick={connect}>
                Connect
              </button>
            </div>
            {authError && (
              <p className="hint" style={{ color: "var(--danger)" }}>
                {authError}
              </p>
            )}
          </section>
        ) : (
          <div className="admin-layout">
            <section className="card admin-list">
              <h2>Active calls ({calls.length})</h2>
              {calls.length === 0 && (
                <p className="empty">No active calls right now.</p>
              )}
              {calls.map((call) => (
                <button
                  key={call.id}
                  className={`call-item ${selectedCallId === call.id ? "active" : ""}`}
                  onClick={() => setSelectedCallId(call.id)}
                >
                  <strong>Call {call.id}</strong>
                  <span>
                    Started {new Date(call.startedAt).toLocaleTimeString()}
                  </span>
                </button>
              ))}
            </section>

            <section className="card">
              <div className="toolbar">
                <h2 style={{ margin: 0, flex: 1 }}>
                  {selectedCallId
                    ? `Listening to call ${selectedCallId}`
                    : "Select a call"}
                </h2>
                {selectedCallId && (
                  <button
                    className="button danger"
                    onClick={() => endCall(selectedCallId)}
                  >
                    End call
                  </button>
                )}
              </div>

              <div className="transcript">
                {selectedTranscript.length === 0 && (
                  <p className="empty">
                    Transcript will appear here as the patient talks with Maya.
                  </p>
                )}
                {selectedTranscript.map((line, index) => (
                  <div key={index} className={`line ${line.role}`}>
                    <span className="meta">
                      {line.role === "agent" ? "Maya" : "Patient"}
                    </span>
                    {line.text}
                  </div>
                ))}
              </div>
            </section>
          </div>
        )}
      </div>
    </div>
  );
}
