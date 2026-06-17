import axios from "axios";
import { ElMessage } from "element-plus";

const request = axios.create({
  baseURL: "/api/v1",
  timeout: 15000,
  headers: { "Content-Type": "application/json" },
});

request.interceptors.request.use((config) => {
  const token = localStorage.getItem("token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (response) => {
    const data = response.data;
    if (data.code !== 200) {
      ElMessage.error(data.message || "请求失败");
      if (data.code === 40100) {
        localStorage.removeItem("token");
        window.location.href = "/login";
      }
      return Promise.reject(new Error(data.message));
    }
    return data;
  },
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token");
      window.location.href = "/login";
    }
    ElMessage.error("网络错误，请稍后重试");
    return Promise.reject(error);
  }
);

export default request;
