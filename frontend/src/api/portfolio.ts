import type { PortfolioOverview, Position } from "@/types";
import apiClient from "./client";

export async function getPortfolio(): Promise<PortfolioOverview> {
  const response = await apiClient.get<PortfolioOverview>("/portfolio");
  return response.data;
}

export async function getPositions(): Promise<Position[]> {
  const response = await apiClient.get<Position[]>("/portfolio/positions");
  return response.data;
}

export async function getAllocation(): Promise<Array<{ pair: string; value_usdt: number; pct: number }>> {
  const response = await apiClient.get("/portfolio/allocation");
  return response.data;
}

export async function getRiskMetrics() {
  const response = await apiClient.get("/portfolio/risk");
  return response.data;
}

export async function getEquityCurve(days = 30) {
  const response = await apiClient.get("/portfolio/equity-curve", {
    params: { days },
  });
  return response.data;
}
