import { useCallback, useEffect, useState } from "react";
import AppShell from "./layouts/AppShell.jsx";
import AccountActionPage from "./pages/AccountActionPage.jsx";
import AuthPage from "./pages/AuthPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import LandingPage from "./pages/LandingPage.jsx";
import { Brand } from "./components/UI.jsx";
import { AuthProvider, useAuth } from "./context/AuthContext.jsx";
import "./styles/global.css";

function currentPath() {
  return window.location.pathname.replace(/\/+$/, "") || "/";
}

function AppContent() {
  const [path, setPath] = useState(currentPath);
  const [selectedBusinessId, setSelectedBusinessId] = useState(null);
  const { user, loading, logout } = useAuth();

  useEffect(() => {
    if (user?.businesses?.length) {
      setSelectedBusinessId((current) => current || user.businesses[0].business_id);
    }
  }, [user]);

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
          <div className="auth-main">
            <Brand />
            <p role="status">Loading your STEER workspace…</p>
          </div>
        </main>
      );
    }
    const page = path.split("/")[2] || "overview";
    const businessId = selectedBusinessId || user.businesses?.[0]?.business_id;
    return (
      <AppShell
        activePage={page}
        navigate={navigate}
        user={user}
        onLogout={logout}
        activeBusinessId={businessId}
        onBusinessChange={setSelectedBusinessId}
      >
        <DashboardPage
          page={page}
          navigate={navigate}
          businessId={businessId}
          businessRole={user.businesses?.find((item) => item.business_id === businessId)?.role || user.businesses?.[0]?.role}
        />
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
