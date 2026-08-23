import axios, { type InternalAxiosRequestConfig } from "axios";
import { useAuthStore } from "../store/authStore";

const api = axios.create({ baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000" });
let refreshing: Promise<string | null> | null = null;

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as (InternalAxiosRequestConfig & { _retry?: boolean }) | undefined;
    if (error.response?.status === 401 && original && !original._retry && !String(original.url).includes("/auth/refresh")) {
      original._retry = true;
      const refreshToken = localStorage.getItem("refresh_token");
      if (refreshToken) {
        if (!refreshing) {
          refreshing = axios.post(`${import.meta.env.VITE_API_URL || "http://localhost:8000"}/auth/refresh`, { refresh_token: refreshToken })
            .then(({ data }) => {
              localStorage.setItem("access_token", data.access_token);
              localStorage.setItem("refresh_token", data.refresh_token);
              useAuthStore.getState().setToken(data.access_token);
              return data.access_token as string;
            })
            .catch(() => null)
            .finally(() => { refreshing = null; });
        }
        const token = await refreshing;
        if (token) {
          original.headers.Authorization = `Bearer ${token}`;
          return api(original);
        }
      }
      useAuthStore.getState().logout();
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
