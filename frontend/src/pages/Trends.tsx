import React, { useState } from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { TrendingUp, BarChart2, Calendar } from "lucide-react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

export const TrendsPage: React.FC = () => {
  const { status: socketStatus } = useMonitoringSocket();
  const [timeRange, setTimeRange] = useState("24h");
  const [metric, setMetric] = useState("heart_rate");

  // Sample population trend historical series
  const trendData = [
    { time: "00:00", heart_rate: 72, spo2: 98, resp_rate: 16, risk_score: 12 },
    { time: "04:00", heart_rate: 74, spo2: 98, resp_rate: 16, risk_score: 14 },
    { time: "08:00", heart_rate: 78, spo2: 97, resp_rate: 17, risk_score: 18 },
    { time: "12:00", heart_rate: 85, spo2: 96, resp_rate: 19, risk_score: 34 },
    { time: "16:00", heart_rate: 92, spo2: 95, resp_rate: 22, risk_score: 58 },
    { time: "20:00", heart_rate: 88, spo2: 96, resp_rate: 20, risk_score: 42 },
    { time: "24:00", heart_rate: 76, spo2: 98, resp_rate: 17, risk_score: 20 },
  ];

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
              <TrendingUp className="w-6 h-6 text-amber-400" /> Clinical Vital Trends &amp; Population Analytics
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Multi-parameter trend analysis, baseline deviation tracking, and rate-of-change statistics.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300">
              <Calendar className="w-3.5 h-3.5 text-amber-400" />
              <span>Range:</span>
              <select
                value={timeRange}
                onChange={(e) => setTimeRange(e.target.value)}
                className="bg-transparent border-none text-slate-200 focus:outline-none cursor-pointer"
              >
                <option value="1h" className="bg-slate-900">1 Hour</option>
                <option value="6h" className="bg-slate-900">6 Hours</option>
                <option value="12h" className="bg-slate-900">12 Hours</option>
                <option value="24h" className="bg-slate-900">24 Hours</option>
                <option value="7d" className="bg-slate-900">7 Days</option>
              </select>
            </div>
          </div>
        </div>

        {/* Primary Trend Chart Card */}
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 space-y-4 shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
              <BarChart2 className="w-5 h-5 text-amber-400" /> Population Vital Sign Trajectory ({timeRange})
            </h2>

            <div className="flex items-center gap-2 text-xs">
              <button
                onClick={() => setMetric("heart_rate")}
                className={`px-3 py-1 rounded-lg font-semibold transition ${
                  metric === "heart_rate"
                    ? "bg-amber-500 text-slate-950"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                Heart Rate
              </button>
              <button
                onClick={() => setMetric("spo2")}
                className={`px-3 py-1 rounded-lg font-semibold transition ${
                  metric === "spo2"
                    ? "bg-amber-500 text-slate-950"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                SpO2
              </button>
              <button
                onClick={() => setMetric("risk_score")}
                className={`px-3 py-1 rounded-lg font-semibold transition ${
                  metric === "risk_score"
                    ? "bg-amber-500 text-slate-950"
                    : "bg-slate-800 text-slate-300 hover:bg-slate-700"
                }`}
              >
                Risk Score
              </button>
            </div>
          </div>

          <div className="h-80 w-full pt-4">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 11 }} />
                <YAxis stroke="#64748b" tick={{ fontSize: 11 }} />
                <Tooltip
                  contentStyle={{ backgroundColor: "#0f172a", borderColor: "#334155", color: "#f8fafc" }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey={metric}
                  name={metric.replace("_", " ").toUpperCase()}
                  stroke="#d4af37"
                  strokeWidth={3}
                  dot={{ r: 4, fill: "#d4af37" }}
                  activeDot={{ r: 7 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
