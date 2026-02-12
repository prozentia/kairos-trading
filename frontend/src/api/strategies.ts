import type { Strategy, StrategyListResponse, StrategyValidation, SuccessResponse } from "@/types";
import apiClient from "./client";

export async function getStrategies(): Promise<StrategyListResponse> {
  const response = await apiClient.get<StrategyListResponse>("/strategies");
  return response.data;
}

export async function getStrategy(id: number): Promise<Strategy> {
  const response = await apiClient.get<Strategy>(`/strategies/${id}`);
  return response.data;
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
