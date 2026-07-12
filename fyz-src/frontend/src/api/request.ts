import axios, { AxiosError } from "axios";
import { ElMessage } from "element-plus";
import { ApiError, type ApiResponse } from "./types";

const request = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

request.interceptors.request.use((config) => {
  // Let the browser generate multipart/form-data with its boundary. Keeping the
  // instance-level application/json header makes FastAPI report a missing file.
  if (config.data instanceof FormData) {
    config.headers.delete("Content-Type");
  }
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse<unknown>;
    if (data && typeof data === "object" && "code" in data && data.code !== 200) {
      ElMessage.error(data.message || "请求失败");
      return Promise.reject(new ApiError(data.message, data.code, response.status));
    }
    return response;
  },
  (error: AxiosError<ApiResponse<unknown>>) => {
    const response = error.response;
    const data = response?.data;
    const code = data?.code;
    const message = data?.message;
    const hadAuthorization = Boolean(error.config?.headers?.Authorization);
    const shouldLogout =
      code === 40100 ||
      (response?.status === 401 && hadAuthorization && code !== 40001);

    if (shouldLogout) {
      localStorage.removeItem("token");
      localStorage.removeItem("username");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }

    if (data && typeof code === "number") {
      ElMessage.error(message || "请求失败");
      return Promise.reject(
        new ApiError(message || "请求失败", code, response?.status || 0),
      );
    }

    const networkMessage =
      error.code === "ECONNABORTED" ? "请求超时，请稍后重试" : "网络错误，请稍后重试";
    ElMessage.error(networkMessage);
    return Promise.reject(new ApiError(networkMessage, 0, response?.status || 0));
  }
);

export default request;
