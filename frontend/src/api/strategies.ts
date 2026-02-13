import type { Strategy, StrategyListResponse, StrategyValidation, SuccessResponse } from "@/types";
import apiClient from "./client";

// API returns json_definition as a string; the frontend expects parsed fields.
interface ApiStrategy {
  id: string;
  name: string;
  description: string;
  version: string;
  json_definition: string;
  is_active: boolean;
  is_validated: boolean;
  total_trades: number;
  winning_trades: number;
  total_pnl: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

function parseStrategy(raw: ApiStrategy): Strategy {
  let def: Record<string, unknown> = {};
  try {
    def = JSON.parse(raw.json_definition || "{}");
  } catch {
    /* keep empty */
  }
  return {
    id: raw.id as unknown as number,
    name: raw.name,
    description: raw.description,
    version: raw.version,
    pairs: (def.pairs as string[]) ?? [],
    timeframe: (def.timeframe as string) ?? "5m",
    entry_conditions: (def.entry_conditions as Strategy["entry_conditions"]) ?? [],
    exit_conditions: (def.exit_conditions as Strategy["exit_conditions"]) ?? [],
    filters: (def.filters as Strategy["filters"]) ?? [],
    risk: (def.risk as Strategy["risk"]) ?? {
      stop_loss_pct: 0,
      trailing_activation_pct: 0,
      trailing_distance_pct: 0,
      take_profit_levels: [],
      max_position_size_pct: 0,
    },
    indicators_needed: (def.indicators_needed as string[]) ?? [],
    is_active: raw.is_active,
    metadata: (def.metadata as Record<string, unknown>) ?? {},
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  };
}

export async function getStrategies(): Promise<StrategyListResponse> {
  const response = await apiClient.get<{ total: number; strategies: ApiStrategy[] }>("/strategies");
  return {
    total: response.data.total,
    strategies: response.data.strategies.map(parseStrategy),
  };
}

export async function getStrategy(id: number): Promise<Strategy> {
  const response = await apiClient.get<ApiStrategy>(`/strategies/${id}`);
  return parseStrategy(response.data);
}

export async function createStrategy(data: Partial<Strategy>): Promise<Strategy> {
  const response = await apiClient.post<Strategy>("/strategies", data);
  return response.data;
}

export async function updateStrategy(id: number, data: Partial<Strategy>): Promise<Strategy> {
  const response = await apiClient.put<Strategy>(`/strategies/${id}`, data);
  return response.data;
}

export async function deleteStrategy(id: number): Promise<SuccessResponse> {
  const response = await apiClient.delete<SuccessResponse>(`/strategies/${id}`);
  return response.data;
}

export async function activateStrategy(id: number): Promise<SuccessResponse> {
  const response = await apiClient.post<SuccessResponse>(`/strategies/${id}/activate`);
  return response.data;
}

export async function deactivateStrategy(id: number): Promise<SuccessResponse> {
  const response = await apiClient.post<SuccessResponse>(`/strategies/${id}/deactivate`);
  return response.data;
}

export async function validateStrategy(id: number): Promise<StrategyValidation> {
  const response = await apiClient.post<StrategyValidation>(`/strategies/${id}/validate`);
  return response.data;
}

export async function duplicateStrategy(id: number): Promise<Strategy> {
  const response = await apiClient.post<Strategy>(`/strategies/${id}/duplicate`);
  return response.data;
}
