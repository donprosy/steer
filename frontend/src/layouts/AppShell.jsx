import { useState } from "react";
import Icon from "../components/Icon.jsx";
import { Avatar, Brand, DemoNotice } from "../components/UI.jsx";

const navigation = [
  { section: "WORKSPACE", items: [
    ["overview", "Overview", "grid"],
    ["sales", "Sales", "activity"],
    ["expenses", "Expenses", "wallet"],
    ["customers", "Customers", "users"],
    ["products", "Products", "cube"],
    ["inventory", "Inventory", "package"],
  ] },
  { section: "INSIGHTS", items: [
    ["reports", "Reports", "trend"],
    ["assistant", "AI assistant", "sparkles", "Soon"],
  ] },
  { section: "PREFERENCES", items: [
    ["settings", "Settings", "settings"],
  ] },
];

const routeTitles = {
  overview: "Overview",
  sales: "Sales",
  expenses: "Expenses",
  customers: "Customers",
  products: "Products",
  inventory: "Inventory",
  reports: "Reports",
  assistant: "AI assistant",
  settings: "Settings",
};

function getInitials(name = "") {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0]).join("").toUpperCase() || "U";
}

function AppShell({ activePage, navigate, user, onLogout, children }) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [search, setSearch] = useState("");
  const [notificationsOpen, setNotificationsOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);
  const [sidebarProfileOpen, setSidebarProfileOpen] = useState(false);
  const [logoutError, setLogoutError] = useState("");
  const pageTitle = routeTitles[activePage] || "Overview";
  const businessName = user.businesses?.[0]?.business_name || "Business account";
  const userInitials = getInitials(user.name);
  const userRole = user.businesses?.[0]?.role === "owner" ? "Business owner" : "Team member";
  const searchResults = navigation.flatMap((group) => group.items)
    .filter((item) => item[1].toLowerCase().includes(search.trim().toLowerCase()));

  function go(page) {
    navigate(`/app/${page}`);
    setSidebarOpen(false);
    setSearch("");
  }

  async function signOut() {
    setLogoutError("");
    try {
      await onLogout();
      navigate("/login");
    } catch (error) {
      setLogoutError(error.message);
    }
  }

  return (
    <div className={`app-shell${collapsed ? " app-shell--collapsed" : ""}`}>
      {sidebarOpen && <button className="sidebar-backdrop" aria-label="Close navigation" onClick={() => setSidebarOpen(false)} />}
      <aside className={`sidebar${sidebarOpen ? " sidebar--open" : ""}`}>
        <div className="sidebar__brand"><button aria-label="Go to overview" onClick={() => go("overview")}><Brand light /></button><button className="sidebar-collapse" aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"} aria-expanded={!collapsed} onClick={() => setCollapsed(!collapsed)}><Icon name="menu" size={18} /></button></div>
        <button className="business-switcher" onClick={() => go("settings")} title="Open business settings">
          <span className="business-switcher__mark">{businessName[0]?.toUpperCase() || "B"}</span><span className="business-switcher__text"><b>{businessName}</b><small>Demo workspace</small></span><Icon name="arrowDown" size={15} />
        </button>
        <nav className="side-nav" aria-label="Workspace navigation">
          {navigation.map((group) => <div className="side-nav__group" key={group.section}>
            <span className="side-nav__label">{group.section}</span>
            {group.items.map(([id, label, icon, badge]) => <button key={id} title={label} className={`side-nav__item${activePage === id ? " side-nav__item--active" : ""}`} onClick={() => go(id)} aria-current={activePage === id ? "page" : undefined}>
              <Icon name={icon} size={19} /><span>{label}</span>{badge && <small className="nav-soon">{badge}</small>}
            </button>)}
          </div>)}
        </nav>
        <div className="sidebar-spacer" />
        <div className="sidebar-help"><span className="help-mark"><Icon name="help" size={17} /></span><b>Need a hand?</b><p>We’re building a better way to run business.</p><a href="mailto:hello@donprosy.com">Contact the team <Icon name="arrowRight" size={13} /></a></div>
        <button className="sidebar-profile" aria-expanded={sidebarProfileOpen} onClick={() => setSidebarProfileOpen(!sidebarProfileOpen)}>
          <Avatar initials={userInitials} color="teal" /><span><b>{user.name}</b><small>{userRole}</small></span><Icon name="more" size={18} />
        </button>
        {sidebarProfileOpen && <div className="profile-menu"><button onClick={() => go("settings")}><Icon name="settings" size={16} />Account settings</button><button onClick={signOut}><Icon name="logout" size={16} />Sign out</button>{logoutError && <p className="form-feedback form-feedback--error" role="alert">{logoutError}</p>}</div>}
      </aside>

      <div className="app-main">
        <header className="topbar">
          <button className="mobile-nav-button" aria-label="Open navigation" onClick={() => setSidebarOpen(true)}><Icon name="menu" /></button>
          <div className="topbar__title"><span>Workspace</span><Icon name="chevron" size={14} /><b>{pageTitle}</b></div>
          <div className="topbar__right">
            <label className="global-search"><Icon name="search" size={17} /><input aria-label="Search navigation" placeholder="Search pages..." value={search} onChange={(event) => setSearch(event.target.value)} /><kbd>⌘ K</kbd></label>
            {search.trim() && <div className="search-results">{searchResults.length ? searchResults.map(([id, label, icon]) => <button key={id} onClick={() => go(id)}><Icon name={icon} size={16} />{label}<Icon name="arrowRight" size={14} /></button>) : <span>No pages found</span>}</div>}
            <div className="topbar-popover-wrap">
              <button className={`topbar-icon-button${notificationsOpen ? " is-active" : ""}`} aria-label="Notifications" aria-expanded={notificationsOpen} onClick={() => { setNotificationsOpen(!notificationsOpen); setProfileOpen(false); }}><Icon name="bell" size={19} /><i /></button>
              {notificationsOpen && <div className="notification-popover"><div><b>Notifications</b><span>DEMO</span></div><p><Icon name="package" size={16} /> 3 products are below their sample reorder level.</p><small>Example alert · demonstration workspace</small></div>}
            </div>
            <button className="topbar-user" aria-expanded={profileOpen} onClick={() => { setProfileOpen(!profileOpen); setNotificationsOpen(false); }}><Avatar initials={userInitials} color="teal" small /><span>{user.name}</span><Icon name="arrowDown" size={15} /></button>
            {profileOpen && <div className="profile-menu profile-menu--topbar"><button onClick={() => { setProfileOpen(false); go("settings"); }}><Icon name="settings" size={16} />Account settings</button><button onClick={signOut}><Icon name="logout" size={16} />Sign out</button>{logoutError && <p className="form-feedback form-feedback--error" role="alert">{logoutError}</p>}</div>}
          </div>
        </header>
        <main className="dashboard-content">
          <DemoNotice />
          {children}
          <footer className="app-footer"><span>© 2026 STEER</span><span><Icon name="shield" size={14} /> Demonstration workspace · sample figures only</span></footer>
        </main>
      </div>
    </div>
  );
}

export default AppShell;
