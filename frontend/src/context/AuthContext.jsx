import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { authApi } from "../services/authApi.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [initializationError, setInitializationError] = useState("");

  const acceptAuthenticatedUser = useCallback((authenticatedUser) => {
    setUser(authenticatedUser);
  }, []);

  useEffect(() => {
    let active = true;
    const timeout = window.setTimeout(() => {
      if (active) setLoading(false);
    }, 10000);
    authApi.currentUser()
      .then((response) => {
        if (active) setUser(response.user);
      })
      .catch((error) => {
        if (!active) return;
        if (error.status !== 401) {
          setInitializationError(error.message);
          setLoading(false);
        }
      })
      .finally(() => {
        window.clearTimeout(timeout);
        if (active) setLoading(false);
      });
    return () => {
      active = false;
      window.clearTimeout(timeout);
    };
  }, []);

  const value = useMemo(() => ({
    user,
    loading,
    initializationError,
    async login(email, password, rememberMe) {
      const response = await authApi.login(email, password, rememberMe);
      setUser(response.user);
    },
    acceptAuthenticatedUser,
    clearAuthenticatedUser() {
      setUser(null);
    },
    async logout() {
      await authApi.logout();
      setUser(null);
    },
  }), [user, loading, initializationError, acceptAuthenticatedUser]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used within AuthProvider.");
  return context;
}
