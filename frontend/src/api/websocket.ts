// WebSocket connection manager for real-time data
type MessageHandler = (data: unknown) => void;

class WebSocketManager {
  private connections: Map<string, WebSocket> = new Map();
  private handlers: Map<string, Set<MessageHandler>> = new Map();
  private reconnectTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();

  private getBaseUrl(): string {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const host = window.location.host;
    return `${protocol}//${host}/ws`;
  }

  // Connect to a WebSocket endpoint
  connect(channel: string): void {
    if (this.connections.has(channel)) return;

    const token = localStorage.getItem("access_token");
    const url = `${this.getBaseUrl()}/${channel}${token ? `?token=${token}` : ""}`;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log(`[WS] Connected to ${channel}`);
        // Clear any reconnect timer
        const timer = this.reconnectTimers.get(channel);
        if (timer) {
          clearTimeout(timer);
          this.reconnectTimers.delete(channel);
        }
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          const handlers = this.handlers.get(channel);
          if (handlers) {
            handlers.forEach((handler) => handler(data));
          }
        } catch (e) {
          console.error(`[WS] Parse error on ${channel}:`, e);
        }
      };

      ws.onclose = () => {
        console.log(`[WS] Disconnected from ${channel}`);
        this.connections.delete(channel);
        // Auto-reconnect after 3 seconds
        this.scheduleReconnect(channel);
      };

      ws.onerror = (error) => {
        console.error(`[WS] Error on ${channel}:`, error);
      };

      this.connections.set(channel, ws);
    } catch (e) {
      console.error(`[WS] Failed to connect to ${channel}:`, e);
      this.scheduleReconnect(channel);
    }
  }

  // Disconnect from a specific channel
  disconnect(channel: string): void {
    const ws = this.connections.get(channel);
    if (ws) {
      ws.close();
      this.connections.delete(channel);
    }
    const timer = this.reconnectTimers.get(channel);
    if (timer) {
      clearTimeout(timer);
      this.reconnectTimers.delete(channel);
    }
    this.handlers.delete(channel);
  }

  // Disconnect from all channels
  disconnectAll(): void {
    this.connections.forEach((ws, channel) => {
      ws.close();
      const timer = this.reconnectTimers.get(channel);
      if (timer) clearTimeout(timer);
    });
    this.connections.clear();
    this.reconnectTimers.clear();
    this.handlers.clear();
  }

  // Subscribe to messages on a channel
  subscribe(channel: string, handler: MessageHandler): () => void {
    if (!this.handlers.has(channel)) {
      this.handlers.set(channel, new Set());
    }
    this.handlers.get(channel)!.add(handler);

    // Auto-connect if not connected
    if (!this.connections.has(channel)) {
      this.connect(channel);
    }

    // Return unsubscribe function
    return () => {
      const handlers = this.handlers.get(channel);
      if (handlers) {
        handlers.delete(handler);
        if (handlers.size === 0) {
          this.disconnect(channel);
        }
      }
    };
  }

  // Send a message on a channel
  send(channel: string, data: unknown): void {
    const ws = this.connections.get(channel);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data));
    }
  }

  private scheduleReconnect(channel: string): void {
    if (this.reconnectTimers.has(channel)) return;
    const timer = setTimeout(() => {
      this.reconnectTimers.delete(channel);
      if (this.handlers.has(channel) && this.handlers.get(channel)!.size > 0) {
        this.connect(channel);
      }
    }, 3000);
    this.reconnectTimers.set(channel, timer);
  }
}

// Singleton instance
export const wsManager = new WebSocketManager();
export default wsManager;
