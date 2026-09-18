/** Zustand auth store */
import { create } from "zustand";
import { api, getAccessToken, setAccessToken } from "../lib/api";

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  role: "admin" | "clinician";
}

interface AuthState {
  user: AuthUser | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  restore: () => Promise<boolean>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: getAccessToken(),
  isAuthenticated: !!getAccessToken(),

  login: async (email: string, password: string) => {
    const data: { access_token: string; user: AuthUser } = await api.post("/api/v1/auth/login", { email, password });
    setAccessToken(data.access_token);
    set({ user: data.user, accessToken: data.access_token, isAuthenticated: true });
  },

  logout: () => {
    setAccessToken(null);
    localStorage.removeItem("cp_access_token");
    set({ user: null, accessToken: null, isAuthenticated: false });
    window.location.href = "/login";
  },

  restore: async () => {
    const token = getAccessToken();
    if (!token) return false;
    try {
      const user: AuthUser = await api.get("/api/v1/users/me");
      set({ user, accessToken: token, isAuthenticated: true });
      return true;
    } catch {
      setAccessToken(null);
      set({ user: null, accessToken: null, isAuthenticated: false });
      return false;
    }
  },
}));
