import React, { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuthStore } from "../../store/auth";
import { ConnectionStatusBadge } from "../ConnectionStatus";
import { ConnectionStatus } from "../../hooks/useMonitoringSocket";
import {
  Activity,
  Bell,
  BarChart2,
  Bot,
  ShieldAlert,
  LogOut,
  Database,
  ShieldCheck,
  Sliders,
  Users,
  TrendingUp,
  GitCommit,
  FileText,
  CheckSquare,
  Inbox,
  Settings,
  Search,
  Building2,
  ChevronLeft,
  ChevronRight,
  Menu,
  X,
  Sparkles,
} from "lucide-react";

interface AppLayoutProps {
  children: React.ReactNode;
  socketStatus?: ConnectionStatus;
}

export const AppLayout: React.FC<AppLayoutProps> = ({ children, socketStatus = "LIVE" }) => {
  const { user, logout } = useAuthStore();
  const location = useLocation();
  const navigate = useNavigate();

  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [facility, setFacility] = useState("Central General Hospital — ICU Ward 3");

  const navItems = [
    { path: "/dashboard", label: "Dashboard", icon: Activity },
    { path: "/patients", label: "Patients", icon: Users },
    { path: "/live-monitoring", label: "Live Monitoring", icon: Activity },
    { path: "/alerts", label: "Alert Center", icon: Bell },
    { path: "/analytics", label: "Risk Analytics", icon: BarChart2 },
    { path: "/trends", label: "Vital Trends", icon: TrendingUp },
    { path: "/data-pipeline", label: "Data Pipeline", icon: GitCommit },
    { path: "/dataset-explorer", label: "Dataset Explorer", icon: Database },
    { path: "/health-assistant", label: "AI Health Assistant", icon: Bot },
    { path: "/reports", label: "Reports & Export", icon: FileText },
    { path: "/tasks", label: "Clinician Tasks", icon: CheckSquare },
    { path: "/notifications", label: "Notifications", icon: Inbox },
    { path: "/audit-logs", label: "Audit Logs", icon: ShieldCheck },
    { path: "/admin", label: "Administration", icon: Sliders },
    { path: "/settings", label: "Settings", icon: Settings },
  ];

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    const q = searchQuery.toLowerCase();
    if (q.includes("alert")) navigate("/alerts");
    else if (q.includes("data") || q.includes("dataset")) navigate("/dataset-explorer");
    else if (q.includes("report")) navigate("/reports");
    else navigate(`/patients?search=${encodeURIComponent(searchQuery)}`);
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-amber-500/30 selection:text-amber-200">
      {/* Top Header */}
      <header className="sticky top-0 z-40 bg-slate-900/95 backdrop-blur border-b border-slate-800 px-4 lg:px-6 py-2.5">
        <div className="flex items-center justify-between gap-4">
          {/* Left: Mobile Toggle & Branding */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileOpen(!mobileOpen)}
              className="md:hidden p-2 rounded-lg text-slate-400 hover:text-slate-100 hover:bg-slate-800"
            >
              {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
            </button>

            <Link to="/dashboard" className="flex items-center gap-2.5 group">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-amber-400 via-amber-500 to-amber-700 flex items-center justify-center shadow-lg shadow-amber-500/20 group-hover:scale-105 transition-transform">
                <Activity className="w-5 h-5 text-slate-950 stroke-[2.5]" />
              </div>
              <div className="hidden sm:block">
                <div className="flex items-center gap-1.5">
                  <span className="font-black text-lg tracking-tight bg-gradient-to-r from-amber-200 via-amber-400 to-yellow-500 bg-clip-text text-transparent">
                    CarePulse
                  </span>
                  <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    HEALTHCARE SYSTEM
                  </span>
                </div>
                <div className="text-[10px] text-slate-400 font-mono flex items-center gap-1">
                  <Sparkles className="w-3 h-3 text-amber-400" /> AI Early-Warning System
                </div>
              </div>
            </Link>
          </div>

          {/* Center: Global Search & Facility Selector */}
          <div className="hidden lg:flex items-center gap-4 flex-1 max-w-2xl mx-4">
            {/* Global Search */}
            <form onSubmit={handleSearchSubmit} className="relative flex-1">
              <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search patient ID, name, alerts, datasets, reports..."
                className="w-full bg-slate-950/80 border border-slate-800 focus:border-amber-500/60 rounded-lg pl-9 pr-4 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none transition-all"
              />
            </form>

            {/* Facility Selector */}
            <div className="flex items-center gap-2 bg-slate-950/80 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300">
              <Building2 className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <select
                value={facility}
                onChange={(e) => setFacility(e.target.value)}
                className="bg-transparent border-none text-xs text-slate-300 focus:outline-none cursor-pointer"
              >
                <option value="Central General Hospital — ICU Ward 3" className="bg-slate-900 text-slate-200">
                  ICU Ward 3 — Central Hospital
                </option>
                <option value="St. Jude Medical Center — Step-down Unit" className="bg-slate-900 text-slate-200">
                  Step-down Unit — St. Jude
                </option>
                <option value="Telemetry Hub — Ward B" className="bg-slate-900 text-slate-200">
                  Telemetry Hub — Ward B
                </option>
              </select>
            </div>
          </div>

          {/* Right: Live Status & Profile */}
          <div className="flex items-center gap-3">
            {/* System Online Badge */}
            <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 bg-emerald-500/10 border border-emerald-500/30 rounded-full text-xs font-semibold text-emerald-400">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping inline-block" />
              <span>System Online</span>
            </div>

            <ConnectionStatusBadge status={socketStatus} />

            <Link
              to="/notifications"
              className="relative p-2 rounded-lg text-slate-400 hover:text-amber-400 hover:bg-slate-800/80 transition-colors"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              <span className="absolute top-1 right-1 w-2 h-2 rounded-full bg-amber-400" />
            </Link>

            {user && (
              <div className="flex items-center gap-2.5 pl-3 border-l border-slate-800">
                <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-amber-600 to-amber-400 flex items-center justify-center text-slate-950 font-bold text-xs shadow-md">
                  {user.display_name.charAt(0).toUpperCase()}
                </div>
                <div className="hidden xl:block text-left">
                  <div className="text-xs font-bold text-slate-200 leading-tight">{user.display_name}</div>
                  <div className="text-[10px] text-amber-400 uppercase font-mono tracking-wider">{user.role}</div>
                </div>
                <button
                  onClick={logout}
                  title="Logout"
                  className="p-1.5 rounded-lg text-slate-400 hover:text-red-400 hover:bg-slate-800 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Body with Sidebar & Main Content */}
      <div className="flex flex-1 relative overflow-hidden">
        {/* Left Sidebar (Desktop) */}
        <aside
          className={`hidden md:flex flex-col bg-slate-900/90 border-r border-slate-800 transition-all duration-300 z-30 ${
            collapsed ? "w-16" : "w-64"
          }`}
        >
          {/* Navigation Links List */}
          <div className="flex-1 py-4 px-2 space-y-1 overflow-y-auto scrollbar-thin">
            {navItems.map((item) => {
              const Icon = item.icon;
              const active = location.pathname === item.path || (item.path !== "/dashboard" && location.pathname.startsWith(item.path));
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  title={collapsed ? item.label : undefined}
                  className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    active
                      ? "bg-amber-500/15 text-amber-300 border border-amber-500/40 font-bold shadow-sm shadow-amber-500/10"
                      : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                  }`}
                >
                  <Icon className={`w-4 h-4 shrink-0 ${active ? "text-amber-400" : "text-slate-400"}`} />
                  {!collapsed && <span className="truncate">{item.label}</span>}
                </Link>
              );
            })}
          </div>

          {/* Collapse Toggle Button at Sidebar Footer */}
          <div className="p-2 border-t border-slate-800 flex items-center justify-end">
            <button
              onClick={() => setCollapsed(!collapsed)}
              className="p-1.5 rounded-lg text-slate-400 hover:text-amber-400 hover:bg-slate-800/80 transition-colors"
              title={collapsed ? "Expand Sidebar" : "Collapse Sidebar"}
            >
              {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
            </button>
          </div>
        </aside>

        {/* Mobile Sidebar Overlay Drawer */}
        {mobileOpen && (
          <div className="md:hidden fixed inset-0 z-50 flex">
            <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm" onClick={() => setMobileOpen(false)} />
            <div className="relative w-64 bg-slate-900 border-r border-slate-800 p-4 flex flex-col h-full z-10 space-y-4">
              <div className="flex items-center justify-between pb-3 border-b border-slate-800">
                <span className="font-bold text-amber-400 text-sm">CarePulse Menu</span>
                <button onClick={() => setMobileOpen(false)} className="text-slate-400 hover:text-slate-100">
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 space-y-1 overflow-y-auto">
                {navItems.map((item) => {
                  const Icon = item.icon;
                  const active = location.pathname === item.path;
                  return (
                    <Link
                      key={item.path}
                      to={item.path}
                      onClick={() => setMobileOpen(false)}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium ${
                        active
                          ? "bg-amber-500/15 text-amber-300 border border-amber-500/40 font-bold"
                          : "text-slate-400 hover:text-slate-100 hover:bg-slate-800/60"
                      }`}
                    >
                      <Icon className={`w-4 h-4 ${active ? "text-amber-400" : ""}`} />
                      <span>{item.label}</span>
                    </Link>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* Main Content Area */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6 bg-slate-950 max-w-7xl mx-auto w-full">
          {children}
        </main>
      </div>

      {/* Mandatory Healthcare Safety Disclaimer Footer */}
      <footer className="bg-slate-900/90 border-t border-slate-800 py-3 px-4 text-center text-xs text-amber-400/90 font-medium z-30">
        <div className="max-w-7xl mx-auto flex items-center justify-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
          <span>
            RESEARCH DATA / SYNTHETIC DEMO — NOT CLINICALLY VALIDATED. AI Decision-Support System for demonstration only.
          </span>

        </div>
      </footer>
    </div>
  );
};
