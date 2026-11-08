import { useCallback, useEffect, useState } from "react";
import AppShell from "./layouts/AppShell.jsx";
import AccountActionPage from "./pages/AccountActionPage.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import "./styles/global.css";

function currentPath() {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

function AppContent() {
  const [path, setPath] = useState(currentPath);
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    const handlePopState = () => setPath(currentPath());
    window.addEventListener("popstate", handlePopState);
    return () => window.removeEventListener("popstate", handlePopState);
  }, []);

  const navigate = useCallback((nextPath) => {
    window.history.pushState({}, "", nextPath);
    setPath(currentPath());
    window.scrollTo({ top: 0, behavior: "smooth" });
  }, []);

  useEffect(() => {
    if (path.startsWith("/app") && !loading && !user) navigate("/login");
  }, [path, loading, user, navigate]);

  useEffect(() => {
    if (
      !loading &&
      user &&
      (path === "/login" || path === "/register")
    ) {
      navigate("/app/overview");
    }
  }, [path, loading, user, navigate]);

  if (path === "/login" || path === "/register" || path === "/forgot-password") {
    return <AuthPage key={path} mode={path.slice(1)} navigate={navigate} />;
  }

  if (path === "/verify-email" || path === "/reset-password") {
    return <AccountActionPage key={path} mode={path.slice(1)} navigate={navigate} />;
  }

  if (path.startsWith("/app")) {
    if (loading || !user) {
      return (
        <main className="auth-page auth-page--single">
          <div className="auth-main"><p role="status">Loading your account…</p></div>
        </main>
      );
    }
    const page = path.split("/")[2] || "overview";
    return (
      <AppShell activePage={page} navigate={navigate} user={user} onLogout={logout}>
        <DashboardPage page={page} navigate={navigate} />
      </AppShell>
    );
  }

  return <LandingPage navigate={navigate} />;
}

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;
