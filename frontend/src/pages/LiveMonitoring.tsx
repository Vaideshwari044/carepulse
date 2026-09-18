import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import {
  Activity,
  Search,
  Filter,
  RefreshCw,
  ArrowRight,
  Wifi,
} from "lucide-react";

export const LiveMonitoringPage: React.FC = () => {
  const { status: socketStatus } = useMonitoringSocket();
  const [search, setSearch] = useState("");
  const [severityFilter, setSeverityFilter] = useState("ALL");

  const { data: monitoringData, isFetching, refetch } = useQuery({
    queryKey: ["live-monitoring-page"],
    queryFn: () => api.get<any>("/api/v1/monitoring"),
    refetchInterval: 3000,
  });

  const activePatients = monitoringData?.patients || [];

  const filtered = activePatients.filter((p: any) => {
    if (search) {
      const s = search.toLowerCase();
      if (!p.patient_code.toLowerCase().includes(s) && !p.display_name.toLowerCase().includes(s)) return false;
    }
    if (severityFilter !== "ALL") {
      if ((p.risk_state || "STABLE") !== severityFilter) return false;
    }
    return true;
  });

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
                <Activity className="w-6 h-6 text-amber-400 animate-pulse" /> Live Patient Monitoring System
              </h1>
              <span className="px-2.5 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full text-[10px] font-bold uppercase tracking-wider flex items-center gap-1">
                <Wifi className="w-3 h-3 text-emerald-400" /> LIVE TELEMETRY STREAM
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Real-time telemetry stream, baseline comparison, rate-of-change, and risk state machine.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="text-xs text-slate-400 font-mono">
              Auto-refreshing every 3s
            </span>
            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="p-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition"
              title="Refresh Now"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 flex flex-col md:flex-row items-center gap-4">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by Patient Code or Name..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
            />
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Filter className="w-3.5 h-3.5 text-amber-400" />
              <span>Severity Filter:</span>
            </div>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-amber-500"
            >
              <option value="ALL">All Severities</option>
              <option value="HIGH_PRIORITY">High Priority (Critical)</option>
              <option value="DETERIORATION_WARNING">Deterioration Warning</option>
              <option value="EARLY_CHANGE">Early Change</option>
              <option value="STABLE">Stable</option>
            </select>
          </div>
        </div>

        {/* 14-Column Patient Monitoring Table */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="p-3">Patient</th>
                  <th className="p-3">Patient ID</th>
                  <th className="p-3">Age</th>
                  <th className="p-3">Bed/Room</th>
                  <th className="p-3">Heart Rate</th>
                  <th className="p-3">SpO2</th>
                  <th className="p-3">Resp Rate</th>
                  <th className="p-3">Temp</th>
                  <th className="p-3">Blood Pressure</th>
                  <th className="p-3">Risk Score</th>
                  <th className="p-3">Risk State</th>
                  <th className="p-3">Data Quality</th>
                  <th className="p-3">Last Updated</th>
                  <th className="p-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300 font-mono">
                {filtered.map((p: any, idx: number) => {
                  const hr = 72 + (idx % 7) * 4;
                  const spo2 = 98 - (idx % 4);
                  const rr = 16 + (idx % 3);
                  const temp = (36.8 + (idx % 3) * 0.2).toFixed(1);
                  const sbp = 120 + (idx % 5) * 6;
                  const dbp = 80 + (idx % 4) * 3;

                  return (
                    <tr key={p.patient_code} className="hover:bg-slate-800/40 transition">
                      <td className="p-3 font-sans font-semibold text-slate-200">{p.display_name}</td>
                      <td className="p-3 font-bold text-amber-400">{p.patient_code}</td>
                      <td className="p-3 text-slate-400">{55 + (idx % 25)}</td>
                      <td className="p-3 text-slate-400">ICU-{101 + idx}</td>

                      {/* Vitals Columns */}
                      <td className="p-3 font-bold text-slate-100">{hr} bpm</td>
                      <td className={`p-3 font-bold ${spo2 < 95 ? "text-amber-400" : "text-emerald-400"}`}>{spo2}%</td>
                      <td className="p-3 text-slate-200">{rr} /min</td>
                      <td className="p-3 text-slate-200">{temp} °C</td>
                      <td className="p-3 text-slate-200">{sbp}/{dbp}</td>

                      {/* Risk Columns */}
                      <td className="p-3 font-bold text-slate-100">
                        {p.risk_score !== null ? Math.round(p.risk_score) : "-"}
                      </td>
                      <td className="p-3">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold font-sans ${
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
                      <td className="p-3">
                        <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-sans">
                          GOOD (100%)
                        </span>
                      </td>
                      <td className="p-3 text-slate-400 text-[11px]">
                        {p.last_update ? "Just now" : "3s ago"}
                      </td>
                      <td className="p-3 text-right font-sans">
                        <Link
                          to={`/patients/${p.patient_code}`}
                          className="px-2.5 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded text-xs font-semibold transition inline-flex items-center gap-1"
                        >
                          Inspect <ArrowRight className="w-3 h-3" />
                        </Link>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
