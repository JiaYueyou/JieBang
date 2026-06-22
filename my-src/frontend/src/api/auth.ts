import request from "./request";
import type { ApiResponse } from "./types";

export interface LoginParams {
  username: string;
  password: string;
}

export interface LoginResult {
  access_token: string;
  token_type: string;
  username: string;
}

export async function loginApi(params: LoginParams): Promise<LoginResult> {
  const res = await request.post<ApiResponse<LoginResult>>("/auth/login", params);
  if (!res.data.data) throw new Error("登录响应缺少数据");
  return res.data.data;
}

export async function registerApi(params: LoginParams): Promise<void> {
  await request.post<ApiResponse<null>>("/auth/register", params);
}
