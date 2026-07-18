import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";
import { apiRequest, clearTokens, getAccessToken, setTokens } from "../api/client";
import { User } from "../types";

interface LoginResponse {
  requires_2fa: boolean;
  two_factor_token: string | null;
  access_token: string | null;
  refresh_token: string | null;
  requires_2fa_setup: boolean;
}

export type LoginResult =
  | { status: "ok"; requiresTwoFactorSetup: boolean }
  | { status: "requires_2fa"; twoFactorToken: string };

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<LoginResult>;
  completeTwoFactorLogin: (twoFactorToken: string, code: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const me = await apiRequest<User>("/auth/me");
      setUser(me);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    const response = await apiRequest<LoginResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    if (response.requires_2fa) {
      return { status: "requires_2fa", twoFactorToken: response.two_factor_token! };
    }
    setTokens(response.access_token!, response.refresh_token!);
    const me = await apiRequest<User>("/auth/me");
    setUser(me);
    return { status: "ok", requiresTwoFactorSetup: response.requires_2fa_setup };
  }, []);

  const completeTwoFactorLogin = useCallback(async (twoFactorToken: string, code: string) => {
    const response = await apiRequest<LoginResponse>("/auth/2fa/verify-login", {
      method: "POST",
      body: { two_factor_token: twoFactorToken, code },
      auth: false,
    });
    setTokens(response.access_token!, response.refresh_token!);
    const me = await apiRequest<User>("/auth/me");
    setUser(me);
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, completeTwoFactorLogin, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
