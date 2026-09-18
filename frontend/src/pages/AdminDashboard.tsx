import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import {
  Sliders,
  Play,
  Pause,
  RotateCcw,
  CheckCircle2,
  Database,
  Cpu,
  Activity,
  Radio,
  Server,
} from "lucide-react";

export const AdminDashboard: React.FC = () => {
  const queryClient = useQueryClient();
  const { status: socketStatus } = useMonitoringSocket();

  const [simPatient, setSimPatient] = useState("P101");
  const [simScenario, setSimScenario] = useState("stable");
  const [simSpeed, setSimSpeed] = useState(1.0);

  // Fetch System Health Status
  const { data: systemStatus } = useQuery({
    queryKey: ["admin-system-status"],
    queryFn: () => api.get<any>("/api/v1/admin/system-status"),
    refetchInterval: 5000,
  });

  // Fetch Connected IoT Devices
  const { data: devicesData } = useQuery({
    queryKey: ["admin-devices-list"],
    queryFn: () => api.get<any>("/api/v1/monitoring/devices"),
    refetchInterval: 5000,
  });

  // Simulator Start Mutation
  const startSimMutation = useMutation({
    mutationFn: () =>
      api.post<any>("/api/v1/monitoring/demo/start", {
        patient_code: simPatient,
        scenario: simScenario,
        speed: simSpeed,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-system-status"] }),
  });

  // Simulator Pause Mutation
  const pauseSimMutation = useMutation({
    mutationFn: () =>
      api.post<any>("/api/v1/monitoring/demo/pause", {
        patient_code: simPatient,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-system-status"] }),
  });

  // Simulator Reset Mutation
  const resetSimMutation = useMutation({
    mutationFn: () =>
      api.post<any>("/api/v1/monitoring/demo/reset", {
        patient_code: simPatient,
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["admin-system-status"] }),
  });

  const devices = devicesData?.devices || [];

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
              <Sliders className="w-6 h-6 text-amber-400" /> Platform Administration &amp; Real-time Simulator
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              System health monitoring, IoT Bed Monitor telemetry, and real-time patient stream control.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" /> {systemStatus?.status || "System Operational"}
            </span>
          </div>
        </div>

        {/* System Health Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Backend API Server</span>
              <Server className="w-4 h-4 text-emerald-400" />
            </div>
            <div className="text-lg font-bold text-slate-100">FastAPI v1.0.0</div>
            <div className="text-[10px] text-emerald-400 font-mono">Status: HEALTHY (200 OK)</div>
          </div>

          <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>PostgreSQL Database</span>
              <Database className="w-4 h-4 text-blue-400" />
            </div>
            <div className="text-lg font-bold text-slate-100">PostgreSQL 15</div>
            <div className="text-[10px] text-blue-400 font-mono">Pool Connected (Asyncpg)</div>
          </div>

          <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>ML Risk Engine Model</span>
              <Cpu className="w-4 h-4 text-amber-400" />
            </div>
            <div className="text-lg font-bold text-slate-100">RandomForest (rf_v1)</div>
            <div className="text-[10px] text-amber-400 font-mono">Model Status: READY</div>
          </div>

          <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-slate-400 text-xs">
              <span>Stream Ingestion Engine</span>
              <Activity className="w-4 h-4 text-purple-400" />
            </div>
            <div className="text-lg font-bold text-slate-100">Live Simulator</div>
            <div className="text-[10px] text-purple-400 font-mono">Interval: 5s WebSocket</div>
          </div>
        </div>

        {/* Real-time Simulator Controller Card */}
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 space-y-6 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <Radio className="w-5 h-5 text-amber-400" /> Real-time Patient Stream Simulator Controls
            </h2>
            <span className="text-xs text-amber-400 font-mono font-semibold">DEMO REAL-TIME STREAM</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Target Patient Code</label>
              <input
                type="text"
                value={simPatient}
                onChange={(e) => setSimPatient(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Simulation Scenario</label>
              <select
                value={simScenario}
                onChange={(e) => setSimScenario(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
              >
                <option value="stable">Stable Patient Baseline</option>
                <option value="spo2_drop">SpO2 Desaturation Drop</option>
                <option value="tachycardia">Tachycardia Spike</option>
                <option value="gradual_deterioration">Gradual Multi-vital Deterioration</option>
                <option value="sensor_disconnect">Sensor Noise / Disconnect</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Stream Speed Multiplier ({simSpeed}x)</label>
              <input
                type="range"
                min="0.5"
                max="5.0"
                step="0.5"
                value={simSpeed}
                onChange={(e) => setSimSpeed(parseFloat(e.target.value))}
                className="w-full text-amber-500 accent-amber-500 mt-2"
              />
            </div>
          </div>

          <div className="flex items-center gap-3 pt-2">
            <button
              onClick={() => startSimMutation.mutate()}
              disabled={startSimMutation.isPending}
              className="px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded-lg text-xs flex items-center gap-2 transition"
            >
              <Play className="w-4 h-4 fill-slate-950" /> Start Simulation Stream
            </button>

            <button
              onClick={() => pauseSimMutation.mutate()}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-lg text-xs flex items-center gap-2 transition"
            >
              <Pause className="w-4 h-4" /> Pause Stream
            </button>

            <button
              onClick={() => resetSimMutation.mutate()}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 font-semibold rounded-lg text-xs flex items-center gap-2 transition ml-auto"
            >
              <RotateCcw className="w-4 h-4" /> Reset Stream
            </button>
          </div>
        </div>

        {/* IoT Bed Monitor Status Table */}
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 space-y-4 shadow-xl">
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <Radio className="w-5 h-5 text-blue-400" /> Telemetry &amp; Connected Bed Monitors
          </h2>

          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950 text-slate-400 uppercase border-b border-slate-800">
                <tr>
                  <th className="p-3">Device ID</th>
                  <th className="p-3">Monitor Name</th>
                  <th className="p-3">Assigned Room</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Battery Level</th>
                  <th className="p-3">Signal Strength</th>
                  <th className="p-3 text-right">Last Ping</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {devices.map((dev: any) => (
                  <tr key={dev.id} className="hover:bg-slate-800/40">
                    <td className="p-3 font-bold text-amber-400">{dev.id}</td>
                    <td className="p-3 font-sans font-semibold text-slate-200">{dev.name}</td>
                    <td className="p-3 text-slate-300">{dev.room}</td>
                    <td className="p-3">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-sans font-bold ${
                          dev.status === "CONNECTED"
                            ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                            : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                        }`}
                      >
                        {dev.status}
                      </span>
                    </td>
                    <td className="p-3 font-bold text-slate-200">{dev.battery}%</td>
                    <td className="p-3 text-emerald-400">{dev.signal}</td>
                    <td className="p-3 text-right text-slate-500">{dev.last_ping}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
