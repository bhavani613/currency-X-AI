import { useEffect, useState } from "react";
import { checkBackendHealth } from "../services/api";

const POLL_INTERVAL_MS = 60_000;

/**
 * Lightweight backend connectivity indicator for the navbar.
 * Pings GET /health on mount and once a minute — never hammers the API.
 * Purely informational: the app stays fully usable when the backend is
 * offline (individual actions surface their own clear errors).
 */
export default function BackendStatus() {
  const [state, setState] = useState("checking"); // checking | online | offline

  useEffect(() => {
    let cancelled = false;
    const probe = async () => {
      const online = await checkBackendHealth();
      if (!cancelled) setState(online ? "online" : "offline");
    };
    probe();
    const id = setInterval(probe, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  const label =
    state === "online" ? "Backend Connected" : state === "offline" ? "Backend Offline" : "Checking…";

  return (
    <div className={`backend-status ${state}`} title={`API: /health`}>
      <span className="backend-status-dot" aria-hidden="true" />
      <span className="backend-status-label">{label}</span>
    </div>
  );
}