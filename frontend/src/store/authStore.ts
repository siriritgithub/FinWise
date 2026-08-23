import { create } from "zustand";
import type { User, TokenResponse } from "../types";
import api from "../lib/api";

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (tokens: TokenResponse) => Promise<void>;
  setUser: (user: User | null) => void;
  setToken: (token: string) => void;
  logout: () => void;
  fetchUser: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem("access_token"),
  isAuthenticated: !!localStorage.getItem("access_token"),
  login: async (tokens: TokenResponse) => {
    localStorage.setItem("access_token", tokens.access_token);
    localStorage.setItem("refresh_token", tokens.refresh_token);
    set({ token: tokens.access_token, isAuthenticated: true });
    await get().fetchUser();
  },
  setUser: (user) => set({ user }),
  setToken: (token) => set({ token, isAuthenticated: true }),
  logout: () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    set({ user: null, token: null, isAuthenticated: false });
  },
  fetchUser: async () => {
    const { data } = await api.get<User>("/users/me");
    set({ user: data });
  },
}));