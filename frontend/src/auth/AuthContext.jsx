/* eslint-disable react-refresh/only-export-components */
/**
 * Authentication state for the whole app. Wraps the existing backend JWT flow —
 * it does NOT implement a second auth system. Responsibilities:
 *   - bootstrap the session from a persisted token (GET /auth/me)
 *   - expose login / register / logout
 *   - hold the current user (role available to the UI via `isAdmin`)
 *   - react to backend 401s (expired/invalid token) by clearing state so
 *     protected routes redirect to login gracefully
 *
 * Secrets are never stored here beyond the opaque JWT the backend issued; no
 * password, hash, or API key is ever held in the client.
 */

import {
  createContext,
  useContext,
  useState,
  useEffect,
  useCallback,
  useMemo,
} from "react";
import { getToken, clearToken, onUnauthorized } from "../lib/apiClient.js";
import * as authService from "../services/authService.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // loading | authenticated | anonymous. Start "anonymous" when there is no
  // token so we never synchronously setState in the bootstrap effect.
  const [status, setStatus] = useState(() => (getToken() ? "loading" : "anonymous"));

  // Bootstrap: if we have a token, validate it by loading the current user.
  useEffect(() => {
    let active = true;
    if (!getToken()) return; // already "anonymous" from the initializer
    authService
      .me()
      .then((u) => {
        if (!active) return;
        setUser(u);
        setStatus("authenticated");
      })
      .catch(() => {
        if (!active) return;
        clearToken();
        setUser(null);
        setStatus("anonymous");
      });
    return () => {
      active = false;
    };
  }, []);

  // Any 401 from the API layer (expired/invalid token) ends the session.
  useEffect(() => {
    return onUnauthorized(() => {
      setUser(null);
      setStatus("anonymous");
    });
  }, []);

  const login = useCallback(async (email, password) => {
    await authService.login(email, password);
    const u = await authService.me();
    setUser(u);
    setStatus("authenticated");
    return u;
  }, []);

  const register = useCallback(
    async (email, password) => {
      await authService.register(email, password);
      // Registration does not return a token — log in to obtain one.
      return login(email, password);
    },
    [login]
  );

  const logout = useCallback(() => {
    clearToken();
    setUser(null);
    setStatus("anonymous");
  }, []);

  const value = useMemo(
    () => ({
      user,
      status,
      isLoading: status === "loading",
      isAuthenticated: status === "authenticated",
      isAdmin: !!user?.is_admin,
      login,
      register,
      logout,
    }),
    [user, status, login, register, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within <AuthProvider>");
  return ctx;
}
