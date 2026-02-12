import type { BotConfig, BotStatus, SuccessResponse } from "@/types";
import apiClient from "./client";

export async function getBotStatus(): Promise<BotStatus> {
  const response = await apiClient.get<BotStatus>("/bot/status");
  return response.data;
}

export async function startBot(): Promise<SuccessResponse> {
  const response = await apiClient.post<SuccessResponse>("/bot/start");
  return response.data;
}

export async function stopBot(): Promise<SuccessResponse> {
  const response = await apiClient.post<SuccessResponse>("/bot/stop");
  return response.data;
}

export async function restartBot(): Promise<SuccessResponse> {
  const response = await apiClient.post<SuccessResponse>("/bot/restart");
  return response.data;
}

export async function getBotConfig(): Promise<BotConfig> {
  const response = await apiClient.get<BotConfig>("/bot/config");
  return response.data;
}

export async function updateBotConfig(data: Partial<BotConfig>): Promise<BotConfig> {
  const response = await apiClient.put<BotConfig>("/bot/config", data);
  return response.data;
}

export async function getBotLogs(lines = 100, level?: string): Promise<{ lines: string[] }> {
  const response = await apiClient.get<{ lines: string[] }>("/bot/logs", {
    params: { lines, level },
  });
  return response.data;
}
