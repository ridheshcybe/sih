import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Connects to /ws/telemetry/{engineId} with automatic reconnection
 * (exponential backoff, capped at 10s). Inbound JSON messages are passed to
 * onMessage; the hook reports connection state.
 */
export function useEngineSocket(engineId, onMessage) {
  const [connected, setConnected] = useState(false);
  const handlersRef = useRef({ onMessage });
  handlersRef.current.onMessage = onMessage;

  useEffect(() => {
    if (!engineId) return undefined;
    let ws = null;
    let closed = false;
    let retries = 0;
    let timer = null;

    const connect = () => {
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      ws = new WebSocket(`${scheme}://${location.host}/ws/telemetry/${engineId}`);
      ws.onopen = () => {
        retries = 0;
        setConnected(true);
      };
      ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          handlersRef.current.onMessage?.(msg);
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) {
          retries += 1;
          timer = setTimeout(connect, Math.min(1000 * 2 ** retries, 10000));
        }
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      ws?.close();
    };
  }, [engineId]);

  return { connected };
}

/** Accumulates points in a ref and flushes to React state on a fixed cadence
 *  so 10 Hz updates never cause render storms. */
export function useSeries(maxPoints = 500) {
  const ref = useRef([]);
  const [data, setData] = useState([]);

  const flush = useCallback(() => setData(ref.current), []);
  useEffect(() => {
    const id = setInterval(flush, 500);
    return () => clearInterval(id);
  }, [flush]);

  const push = useCallback(
    (point) => {
      ref.current.push(point);
      if (ref.current.length > maxPoints) ref.current = ref.current.slice(-maxPoints);
    },
    [maxPoints]
  );

  const clear = useCallback(() => {
    ref.current = [];
    flush();
  }, [flush]);

  return { data, push, clear };
}