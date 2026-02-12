import { wsManager } from "@/api/websocket";
import { useEffect, useRef, useState } from "react";

// Hook to subscribe to a WebSocket channel
export function useWebSocket<T = unknown>(channel: string, enabled = true) {
  const [lastMessage, setLastMessage] = useState<T | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const handlerRef = useRef<((data: unknown) => void) | null>(null);

  useEffect(() => {
    if (!enabled) return;

    handlerRef.current = (data: unknown) => {
      setLastMessage(data as T);
      setIsConnected(true);
    };

    const unsubscribe = wsManager.subscribe(channel, handlerRef.current);

    return () => {
      unsubscribe();
      setIsConnected(false);
    };
  }, [channel, enabled]);

  const send = (data: unknown) => {
    wsManager.send(channel, data);
  };

  return { lastMessage, isConnected, send };
}
