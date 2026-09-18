/** WebSocket monitoring hook with reconnect backoff and dedup */
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
  const { accessToken } = useAuthStore();

  const getWsUrl = useCallback(() => {
    const base = import.meta.env.VITE_API_URL || window.location.origin;
    const wsBase = base.replace(/^https?/, (m: string) => (m === "https" ? "wss" : "ws"));
    return `${wsBase}/ws/monitoring?token=${encodeURIComponent(accessToken || "")}`;
  }, [accessToken]);

  const checkHeartbeat = useCallback(() => {
    const age = Date.now() - lastHeartbeatRef.current;
    if (age > HEARTBEAT_TIMEOUT) {
      setStatus("RECONNECTING");
    } else {
      setStatus("LIVE");
    }
  }, []);

  const connect = useCallback(() => {
    if (!accessToken) return;

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    const ws = new WebSocket(getWsUrl());
    wsRef.current = ws;
    setStatus("RECONNECTING");

    ws.onopen = () => {
      retryRef.current = 0;
      lastHeartbeatRef.current = Date.now();
      setStatus("LIVE");
      // Start heartbeat check every 10s
      if (hbTimerRef.current) clearInterval(hbTimerRef.current);
      hbTimerRef.current = window.setInterval(checkHeartbeat, 10000);
    };

    ws.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data);

        if (event.event === "PING") {
          lastHeartbeatRef.current = Date.now();
          setStatus("LIVE");
          ws.send(JSON.stringify({ event: "PONG" }));
          return;
        }

        // Dedup
        if (event.event_id) {
          if (seenIdsRef.current.includes(event.event_id)) return;
          seenIdsRef.current.push(event.event_id);
          if (seenIdsRef.current.length > MAX_DEDUP) {
            seenIdsRef.current = seenIdsRef.current.slice(-MAX_DEDUP);
          }
        }

        onEvent?.(event);
      } catch {}
    };

    ws.onclose = (ev) => {
      if (hbTimerRef.current) clearInterval(hbTimerRef.current);
      setStatus(ev.code === 4401 ? "OFFLINE" : "RECONNECTING");
      if (ev.code !== 4401) {
        const delay = BACKOFF[Math.min(retryRef.current, BACKOFF.length - 1)];
        const jitter = Math.random() * 1000;
        retryRef.current++;
        retryTimerRef.current = window.setTimeout(connect, delay + jitter);
      }
    };

    ws.onerror = () => {
      setStatus("RECONNECTING");
    };
  }, [accessToken, getWsUrl, onEvent, checkHeartbeat]);

  useEffect(() => {
    if (accessToken) connect();
    return () => {
      if (wsRef.current) { wsRef.current.close(); wsRef.current = null; }
      if (hbTimerRef.current) clearInterval(hbTimerRef.current);
      if (retryTimerRef.current) clearTimeout(retryTimerRef.current);
    };
  }, [connect]);

  return { status };
}
