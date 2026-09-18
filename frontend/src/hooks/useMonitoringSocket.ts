/** WebSocket monitoring hook with reconnect backoff and stable ref callbacks */
import { useEffect, useRef, useState, useCallback } from "react";
import { useAuthStore } from "../store/auth";

export type ConnectionStatus = "LIVE" | "RECONNECTING" | "OFFLINE";

export interface WsEvent {
  event: string;
  event_id: string;
  emitted_at: string;
  patient_code: string | null;
  payload: unknown;
}

type EventHandler = (event: WsEvent) => void;

const BACKOFF = [1000, 2000, 4000, 8000, 16000, 30000];
const MAX_DEDUP = 500;
const HEARTBEAT_TIMEOUT = 45000;

export function useMonitoringSocket(onEvent?: EventHandler) {
  const [status, setStatus] = useState<ConnectionStatus>("OFFLINE");
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const lastHeartbeatRef = useRef<number>(Date.now());
  const seenIdsRef = useRef<string[]>([]);
  const hbTimerRef = useRef<number | null>(null);
  const retryTimerRef = useRef<number | null>(null);
  const onEventRef = useRef<EventHandler | undefined>(onEvent);

  const { accessToken } = useAuthStore();

  // Keep onEventRef updated without triggering re-connection effects
  useEffect(() => {
    onEventRef.current = onEvent;
  }, [onEvent]);

  const checkHeartbeat = useCallback(() => {
    const age = Date.now() - lastHeartbeatRef.current;
    if (age > HEARTBEAT_TIMEOUT) {
      setStatus("RECONNECTING");
    } else if (wsRef.current?.readyState === WebSocket.OPEN) {
      setStatus("LIVE");
    }
  }, []);

  const connect = useCallback(() => {
    if (!accessToken) {
      setStatus("OFFLINE");
      return;
    }

    // Do not reconnect if socket is currently OPEN or CONNECTING
    if (
      wsRef.current &&
      (wsRef.current.readyState === WebSocket.CONNECTING ||
        wsRef.current.readyState === WebSocket.OPEN)
    ) {
      return;
    }

    // Clean up closed socket reference
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }

    const base = import.meta.env.VITE_API_URL || window.location.origin;
    const wsBase = base.replace(/^https?/, (m: string) => (m === "https" ? "wss" : "ws"));
    const wsUrl = `${wsBase}/ws/monitoring?token=${encodeURIComponent(accessToken || "")}`;

    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;
      setStatus("RECONNECTING");

      ws.onopen = () => {
        retryRef.current = 0;
        lastHeartbeatRef.current = Date.now();
        setStatus("LIVE");

        if (hbTimerRef.current) clearInterval(hbTimerRef.current);
        hbTimerRef.current = window.setInterval(checkHeartbeat, 10000);
      };

      ws.onmessage = (msg) => {
        try {
          const event: WsEvent = JSON.parse(msg.data);

          if (event.event === "PING") {
            lastHeartbeatRef.current = Date.now();
            setStatus("LIVE");
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ event: "PONG" }));
            }
            return;
          }

          if (event.event_id) {
            if (seenIdsRef.current.includes(event.event_id)) return;
            seenIdsRef.current.push(event.event_id);
            if (seenIdsRef.current.length > MAX_DEDUP) {
              seenIdsRef.current = seenIdsRef.current.slice(-MAX_DEDUP);
            }
          }

          onEventRef.current?.(event);
        } catch {}
      };

      ws.onclose = (ev) => {
        if (hbTimerRef.current) clearInterval(hbTimerRef.current);
        wsRef.current = null;
        const isAuthError = ev.code === 4401 || ev.code === 4001;
        setStatus(isAuthError ? "OFFLINE" : "RECONNECTING");

        if (!isAuthError && accessToken) {
          const delay = BACKOFF[Math.min(retryRef.current, BACKOFF.length - 1)];
          const jitter = Math.random() * 500;
          retryRef.current++;
          if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
          retryTimerRef.current = window.setTimeout(connect, delay + jitter);
        }
      };

      ws.onerror = () => {
        setStatus("RECONNECTING");
      };
    } catch {
      setStatus("OFFLINE");
    }
  }, [accessToken, checkHeartbeat]);

  useEffect(() => {
    if (accessToken) {
      connect();
    }
    return () => {
      if (hbTimerRef.current) clearInterval(hbTimerRef.current);
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [accessToken, connect]);

  return { status };
}
