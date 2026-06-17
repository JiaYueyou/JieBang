import request from "./request";

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
  const res = await request.post("/auth/login", params);
  return res.data;
}

export async function registerApi(params: LoginParams): Promise<void> {
  await request.post("/auth/register", params);
}
