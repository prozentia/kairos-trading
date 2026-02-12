import type { Trade, TradeJournal, TradeListResponse, TradeStats } from "@/types";
import apiClient from "./client";

interface TradeFilters {
  pair?: string;
  strategy?: string;
  status?: string;
  start_date?: string;
  end_date?: string;
  page?: number;
  per_page?: number;
}

export async function getTrades(filters: TradeFilters = {}): Promise<TradeListResponse> {
  const response = await apiClient.get<TradeListResponse>("/trades", {
    params: filters,
  });
  return response.data;
}

export async function getTrade(tradeId: string): Promise<Trade> {
  const response = await apiClient.get<Trade>(`/trades/${tradeId}`);
  return response.data;
}

export async function getTradeStats(filters: Partial<TradeFilters> = {}): Promise<TradeStats> {
  const response = await apiClient.get<TradeStats>("/trades/stats", {
    params: filters,
  });
  return response.data;
}

export async function exportTradesCsv(filters: Partial<TradeFilters> = {}): Promise<Blob> {
  const response = await apiClient.get("/trades/export/csv", {
    params: filters,
    responseType: "blob",
  });
  return response.data;
}

export async function addTradeJournal(
  tradeId: string,
  data: { notes: string; tags: string[]; rating?: number }
): Promise<TradeJournal> {
  const response = await apiClient.post<TradeJournal>(`/trades/${tradeId}/journal`, data);
  return response.data;
}

export async function getTradeJournal(tradeId: string): Promise<TradeJournal[]> {
  const response = await apiClient.get<TradeJournal[]>(`/trades/${tradeId}/journal`);
  return response.data;
}
