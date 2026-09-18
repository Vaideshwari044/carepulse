import React from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { useAuthStore } from "../store/auth";
import {
  Activity,
  Users,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Bell,
  TrendingUp,
  Bot,
  Database,
  ArrowRight,
  ShieldCheck,
  Building2,
  Clock,
} from "lucide-react";
import { format } from "date-fns";

export const Dashboard: React.FC = () => {
  const { user } = useAuthStore();
  const { status: socketStatus } = useMonitoringSocket();

  // Fetch monitoring overview from database
  const { data: monitoringData } = useQuery({
    queryKey: ["monitoring-overview"],
    queryFn: () => api.get<any>("/api/v1/monitoring"),
    refetchInterval: 5000,
  });

  // Fetch alerts summary from database
  const { data: alertsData } = useQuery({
    queryKey: ["alerts-dashboard"],
    queryFn: () => api.get<any[]>("/api/v1/alerts?status=OPEN"),
    refetchInterval: 5000,
  });

  // Fetch active patients list
  const { data: patientsData } = useQuery({
    queryKey: ["patients-dashboard"],
    queryFn: () => api.get<any>("/api/v1/patients?size=10"),
    refetchInterval: 5000,
  });

  const activePatients = monitoringData?.patients || [];
  const openAlerts = alertsData || [];
  const totalPatients = patientsData?.total || activePatients.length || 0;

  // Compute live breakdown counts from database values
  const monitoringCount = activePatients.length;
  const stableCount = activePatients.filter((p: any) => !p.risk_state || p.risk_state === "STABLE" || p.risk_state === "RECOVERY").length;
  const earlyChangeCount = activePatients.filter((p: any) => p.risk_state === "EARLY_CHANGE").length;
  const warningCount = activePatients.filter((p: any) => p.risk_state === "DETERIORATION_WARNING").length;
  const criticalCount = activePatients.filter((p: any) => p.risk_state === "HIGH_PRIORITY").length;
  const activeAlertsCount = openAlerts.length;

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Welcome Header Banner */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-gradient-to-r from-slate-900 via-slate-900 to-amber-950/40 p-6 rounded-2xl border border-slate-800 shadow-xl">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-slate-100 tracking-tight">
                Good morning, {user?.display_name || "Clinician"}
              </h1>
              <span className="px-2.5 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full text-[11px] font-bold uppercase tracking-wider">
                {user?.role || "Clinician"}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1 flex items-center gap-2">
              <Building2 className="w-3.5 h-3.5 text-amber-400" /> Real-time AI decision-support monitoring active for ICU &amp; Telemetry units.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link
              to="/live-monitoring"
              className="px-4 py-2.5 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded-xl text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 transition flex items-center gap-2"
            >
              <Activity className="w-4 h-4" /> Open Live Monitoring
            </Link>
          </div>
        </div>

        {/* Real-time Metric Overview Grid (Database-backed) */}
        <div>
          <h2 className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-3">Live Clinical Overview</h2>
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
            {/* Total Patients */}
            <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[11px] font-medium">Total Registered</span>
                <Users className="w-4 h-4 text-slate-400" />
              </div>
              <div className="text-2xl font-black text-slate-100">{totalPatients}</div>
              <div className="text-[10px] text-slate-500 font-mono">In Database</div>
            </div>

            {/* Currently Monitoring */}
            <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[11px] font-medium">Monitoring</span>
                <Activity className="w-4 h-4 text-blue-400" />
              </div>
              <div className="text-2xl font-black text-blue-400">{monitoringCount}</div>
              <div className="text-[10px] text-blue-400/80 font-mono">Active Stream</div>
            </div>

            {/* Stable */}
            <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[11px] font-medium">Stable</span>
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              </div>
              <div className="text-2xl font-black text-emerald-400">{stableCount}</div>
              <div className="text-[10px] text-emerald-400/80 font-mono">Normal Vitals</div>
            </div>

            {/* Early Change */}
            <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[11px] font-medium">Early Change</span>
                <TrendingUp className="w-4 h-4 text-yellow-400" />
              </div>
              <div className="text-2xl font-black text-yellow-400">{earlyChangeCount}</div>
              <div className="text-[10px] text-yellow-400/80 font-mono">Baseline Drift</div>
            </div>

            {/* Warning */}
            <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[11px] font-medium">Warning</span>
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-black text-amber-400">{warningCount}</div>
              <div className="text-[10px] text-amber-400/80 font-mono">Elevated Risk</div>
            </div>

            {/* Critical */}
            <div className="bg-slate-900/90 rounded-xl p-4 border border-slate-800 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[11px] font-medium">Critical</span>
                <AlertOctagon className="w-4 h-4 text-red-400 animate-pulse" />
              </div>
              <div className="text-2xl font-black text-red-400">{criticalCount}</div>
              <div className="text-[10px] text-red-400/80 font-mono">High Priority</div>
            </div>

            {/* Active Alerts */}
            <div className="bg-slate-900/90 rounded-xl p-4 border border-amber-500/30 space-y-1">
              <div className="flex items-center justify-between text-slate-400">
                <span className="text-[11px] font-medium text-amber-300">Active Alerts</span>
                <Bell className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-2xl font-black text-amber-400">{activeAlertsCount}</div>
              <div className="text-[10px] text-amber-400/80 font-mono">Needs Action</div>
            </div>
          </div>
        </div>

        {/* Main Grid: Active Alerts & Patient Monitor Table */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Active Alerts Panel (Left 2 Columns) */}
          <div className="lg:col-span-2 space-y-4">
            <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2">
                  <Bell className="w-5 h-5 text-amber-400" />
                  <h3 className="text-base font-bold text-slate-100">High Priority Active Alerts</h3>
                  <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded text-xs font-mono">
                    {openAlerts.length} OPEN
                  </span>
                </div>

                <Link to="/alerts" className="text-xs font-semibold text-amber-400 hover:underline flex items-center gap-1">
                  View Alert Center <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              {openAlerts.length > 0 ? (
                <div className="space-y-3">
                  {openAlerts.slice(0, 4).map((alert: any) => (
                    <div
                      key={alert.id}
                      className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 hover:border-amber-500/40 transition flex flex-col md:flex-row md:items-center justify-between gap-3"
                    >
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                              alert.risk_level === "HIGH" || alert.risk_level === "CRITICAL"
                                ? "bg-red-500/20 text-red-400 border border-red-500/30"
                                : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                            }`}
                          >
                            {alert.risk_level}
                          </span>
                          <span className="text-xs font-bold text-slate-200">
                            Patient {alert.patient_code || "CP-0001"}
                          </span>
                          <span className="text-[11px] text-slate-500 font-mono">
                            Risk Score: {alert.risk_score}
                          </span>
                        </div>
                        <p className="text-xs text-slate-300 font-medium">{alert.message}</p>
                        <div className="text-[10px] text-slate-500 flex items-center gap-2">
                          <Clock className="w-3 h-3 text-slate-500" />
                          <span>{format(new Date(alert.created_at), "HH:mm:ss MMM dd")}</span>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        <Link
                          to={`/patients/${alert.patient_id}`}
                          className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition"
                        >
                          View Patient
                        </Link>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500 text-xs flex flex-col items-center gap-2">
                  <CheckCircle2 className="w-8 h-8 text-emerald-500/50" />
                  <span>No active high-priority alerts in database. All monitored patients stable.</span>
                </div>
              )}
            </div>

            {/* Monitored Patients Snapshot Table */}
            <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <Activity className="w-5 h-5 text-blue-400" /> Monitored Patients Vitals Stream
                </h3>
                <Link to="/live-monitoring" className="text-xs font-semibold text-amber-400 hover:underline flex items-center gap-1">
                  Full Live Table <ArrowRight className="w-3.5 h-3.5" />
                </Link>
              </div>

              <div className="overflow-x-auto rounded-xl border border-slate-800">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950 text-slate-400 uppercase font-mono border-b border-slate-800">
                    <tr>
                      <th className="p-3">Patient Code</th>
                      <th className="p-3">Display Name</th>
                      <th className="p-3">Risk State</th>
                      <th className="p-3">Risk Score</th>
                      <th className="p-3">Baseline</th>
                      <th className="p-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {activePatients.slice(0, 5).map((p: any) => (
                      <tr key={p.patient_code} className="hover:bg-slate-800/40">
                        <td className="p-3 font-mono font-bold text-amber-400">{p.patient_code}</td>
                        <td className="p-3 font-medium">{p.display_name}</td>
                        <td className="p-3">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                              p.risk_state === "HIGH_PRIORITY"
                                ? "bg-red-500/20 text-red-400 border border-red-500/30"
                                : p.risk_state === "DETERIORATION_WARNING"
                                ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                                : p.risk_state === "EARLY_CHANGE"
                                ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30"
                                : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                            }`}
                          >
                            {p.risk_state || "STABLE"}
                          </span>
                        </td>
                        <td className="p-3 font-mono">{p.risk_score !== null ? Math.round(p.risk_score) : "-"}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 bg-slate-800 text-slate-300 rounded text-[10px]">
                            {p.baseline_status || "collecting"}
                          </span>
                        </td>
                        <td className="p-3 text-right">
                          <Link
                            to={`/patients/${p.patient_code}`}
                            className="text-amber-400 hover:text-amber-300 font-semibold"
                          >
                            Profile &rarr;
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* Quick Action Navigation Cards (Right Column) */}
          <div className="space-y-4">
            <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 space-y-4">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-amber-400" /> Platform Modules
              </h3>

              <div className="space-y-3">
                <Link
                  to="/health-assistant"
                  className="p-4 bg-gradient-to-r from-amber-500/10 to-amber-950/20 border border-amber-500/30 hover:border-amber-500 rounded-xl block space-y-1 transition group"
                >
                  <div className="flex items-center justify-between text-amber-400 font-bold text-xs">
                    <span className="flex items-center gap-1.5"><Bot className="w-4 h-4" /> AI Health Assistant</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Query de-identified patient vitals trends and clinical risk factors.
                  </p>
                </Link>

                <Link
                  to="/dataset-explorer"
                  className="p-4 bg-slate-950/80 border border-slate-800 hover:border-slate-700 rounded-xl block space-y-1 transition group"
                >
                  <div className="flex items-center justify-between text-slate-200 font-bold text-xs">
                    <span className="flex items-center gap-1.5"><Database className="w-4 h-4 text-purple-400" /> Dataset Explorer</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Explore 42,000+ ingested records across 70 patients.
                  </p>
                </Link>

                <Link
                  to="/data-pipeline"
                  className="p-4 bg-slate-950/80 border border-slate-800 hover:border-slate-700 rounded-xl block space-y-1 transition group"
                >
                  <div className="flex items-center justify-between text-slate-200 font-bold text-xs">
                    <span className="flex items-center gap-1.5"><Activity className="w-4 h-4 text-emerald-400" /> Data Pipeline</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <p className="text-[11px] text-slate-400">
                    View raw dataset to PostgreSQL feature engineering pipeline flow.
                  </p>
                </Link>

                <Link
                  to="/reports"
                  className="p-4 bg-slate-950/80 border border-slate-800 hover:border-slate-700 rounded-xl block space-y-1 transition group"
                >
                  <div className="flex items-center justify-between text-slate-200 font-bold text-xs">
                    <span className="flex items-center gap-1.5"><TrendingUp className="w-4 h-4 text-blue-400" /> Reports &amp; PDF Export</span>
                    <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" />
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Generate printable clinical summary reports and CSV exports.
                  </p>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
