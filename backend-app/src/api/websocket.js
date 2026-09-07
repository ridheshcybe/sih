const WS_BASE_URL = (process.env.NEXT_PUBLIC_WS_BASE_URL || "ws://localhost:8000").replace(/\/$/, "");
let socket = null;
let reconnectTimer = null;
let reconnectAttempts = 0;
let manuallyClosed = false;

export function connectWebSocket(engineId, callbacks = {}) {
  disconnectWebSocket();
  manuallyClosed = false;

  const connect = () => {
    socket = new WebSocket(`${WS_BASE_URL}/ws/telemetry/${encodeURIComponent(engineId)}`);
    socket.onopen = () => {
      reconnectAttempts = 0;
      console.info("Telemetry WebSocket connected");
      callbacks.onConnect?.();
    };
    socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        callbacks.onMessage?.(message.event || message.type, message.payload || message.data || message);
      } catch (error) {
        callbacks.onError?.(error);
      }
    };
    socket.onerror = (error) => {
      console.error("Telemetry WebSocket error", error);
      callbacks.onError?.(error);
    };
    socket.onclose = () => {
      callbacks.onDisconnect?.();
      if (!manuallyClosed && reconnectAttempts < 3) {
        reconnectAttempts += 1;
        reconnectTimer = window.setTimeout(connect, 3000);
      } else if (!manuallyClosed) {
        callbacks.onError?.(new Error("Telemetry connection unavailable after 3 retries"));
      }
    };
  };
  connect();
  return disconnectWebSocket;
}

export function disconnectWebSocket() {
  manuallyClosed = true;
  if (reconnectTimer) window.clearTimeout(reconnectTimer);
  reconnectTimer = null;
  reconnectAttempts = 0;
  if (socket) socket.close();
  socket = null;
}