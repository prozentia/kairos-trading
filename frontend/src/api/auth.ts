import type { LoginRequest, LoginResponse, RegisterRequest, User } from "@/types";
import apiClient from "./client";

export async function login(data: LoginRequest): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>("/auth/login", data);
  return response.data;
}

export async function register(data: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>("/auth/register", data);
  return response.data;
}

export async function refreshToken(refresh_token: string) {
  const response = await apiClient.post("/auth/refresh", { refresh_token });
  return response.data;
}

export async function getMe(): Promise<User> {
  const response = await apiClient.get<User>("/auth/me");
  return response.data;
}

export async function updateProfile(data: Partial<User>): Promise<User> {
  const response = await apiClient.put<User>("/auth/me", data);
  return response.data;
}

export async function changePassword(currentPassword: string, newPassword: string) {
  const response = await apiClient.post("/auth/change-password", {
    current_password: currentPassword,
    new_password: newPassword,
  });
  return response.data;
}
