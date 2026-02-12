import { getBotConfig, getBotStatus, startBot, stopBot } from "@/api/bot";
import type { BotConfig, BotStatus } from "@/types";
import { useCallback, useEffect, useState } from "react";

export function useBotStatus() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchStatus = useCallback(async () => {
    try {
      const data = await getBotStatus();
      setStatus(data);
    } catch (err) {
      console.error("Failed to fetch bot status:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
    // Poll every 5 seconds
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, [fetchStatus]);

  return { status, isLoading, refetch: fetchStatus };
}

export function useBotConfig() {
  const [config, setConfig] = useState<BotConfig | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchConfig = useCallback(async () => {
    try {
      const data = await getBotConfig();
      setConfig(data);
    } catch (err) {
      console.error("Failed to fetch bot config:", err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  return { config, isLoading, refetch: fetchConfig };
}

export function useBotControls() {
  const [isStarting, setIsStarting] = useState(false);
  const [isStopping, setIsStopping] = useState(false);

  const start = useCallback(async () => {
    setIsStarting(true);
    try {
      await startBot();
    } finally {
      setIsStarting(false);
    }
  }, []);

  const stop = useCallback(async () => {
    setIsStopping(true);
    try {
      await stopBot();
    } finally {
      setIsStopping(false);
    }
  }, []);

  return { start, stop, isStarting, isStopping };
}
