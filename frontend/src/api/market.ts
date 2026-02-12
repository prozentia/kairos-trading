import type { Candle, Ticker } from "@/types";
import apiClient from "./client";

export async function getPrice(pair: string): Promise<{ pair: string; price: number; timestamp: string | null }> {
  const response = await apiClient.get(`/market/price/${pair}`);
  return response.data;
}

export async function getAllPrices(): Promise<Array<{ pair: string; price: number; change_24h_pct: number }>> {
  const response = await apiClient.get("/market/prices");
  return response.data;
}

export async function getCandles(pair: string, timeframe = "5m", limit = 200): Promise<Candle[]> {
  const response = await apiClient.get<Candle[]>(`/market/candles/${pair}`, {
    params: { timeframe, limit },
  });
  return response.data;
}

export async function getTicker(pair: string): Promise<Ticker> {
  const response = await apiClient.get<Ticker>(`/market/ticker/${pair}`);
  return response.data;
}

export async function getOrderbook(pair: string, depth = 20) {
  const response = await apiClient.get(`/market/orderbook/${pair}`, {
    params: { depth },
  });
  return response.data;
}
