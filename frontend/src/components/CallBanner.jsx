import { Link } from "react-router-dom";
import { useCall } from "../context/CallProvider";

export default function CallBanner() {
  const { callId, status } = useCall();

  return (
    <div className="call-banner">
      <span>
        {status === "connecting" ? "Connecting call..." : "Call in progress"}
        {callId ? ` (${callId})` : ""}
      </span>
      <Link to="/" className="call-banner-link">
        Return to call
      </Link>
    </div>
  );
}
