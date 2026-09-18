import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  BarChart2,
  RefreshCw,
} from "lucide-react";

export const DatasetQuality: React.FC = () => {
  const { status: socketStatus } = useMonitoringSocket();

  const { data: datasets } = useQuery({
    queryKey: ["datasets-list"],
    queryFn: () => api.get<any[]>("/api/v1/datasets"),
  });

  const activeDatasetId = datasets && datasets.length > 0 ? datasets[0].id : null;

  const { data: qualityData, refetch, isFetching } = useQuery({
    queryKey: ["dataset-quality-full", activeDatasetId],
    queryFn: () => api.get<any>(`/api/v1/datasets/${activeDatasetId}/quality`),
    enabled: !!activeDatasetId,
  });

  const missing = qualityData?.missing_summary || {};
  const indicator = qualityData?.quality_indicator || "GOOD";

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-gray-100 flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-emerald-400" /> Dataset Quality &amp; Integrity Report
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Physiologically grounded missingness analysis, valid vs invalid row counts, and status indicators
            </p>
          </div>

          <button
            onClick={() => refetch()}
            className="px-3 py-2 bg-gray-900 border border-gray-700 hover:bg-gray-800 rounded-xl text-xs text-gray-300 flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} /> Refresh Report
          </button>
        </div>

        {/* Quality Indicator Status Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 flex flex-col md:flex-row items-center justify-between gap-6">
          <div>
            <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-1">
              Overall Dataset Quality Status
            </div>
            <div className="flex items-center gap-3">
              <span
                className={`px-3 py-1 rounded-xl font-mono font-bold text-sm border flex items-center gap-1.5 ${
                  indicator === "GOOD"
                    ? "bg-emerald-950 text-emerald-300 border-emerald-800"
                    : indicator === "WARNING"
                    ? "bg-amber-950 text-amber-300 border-amber-800"
                    : "bg-red-950 text-red-300 border-red-800"
                }`}
              >
                {indicator === "GOOD" && <CheckCircle2 className="w-4 h-4" />}
                {indicator === "WARNING" && <AlertTriangle className="w-4 h-4" />}
                {indicator === "ERROR" && <XCircle className="w-4 h-4" />}
                {indicator}
              </span>
              <span className="text-xs text-gray-400">
                Validated against clinical vital bounds &amp; de-identification guidelines.
              </span>
            </div>
          </div>

          <div className="flex items-center gap-4 text-center">
            <div className="p-3 bg-gray-950 rounded-xl border border-gray-800">
              <div className="text-[10px] text-gray-400 uppercase">Total Rows</div>
              <div className="text-xl font-black font-mono text-gray-100">{qualityData?.total_rows ?? "--"}</div>
            </div>
            <div className="p-3 bg-gray-950 rounded-xl border border-gray-800">
              <div className="text-[10px] text-gray-400 uppercase">Valid Rows</div>
              <div className="text-xl font-black font-mono text-emerald-400">{qualityData?.valid_rows ?? "--"}</div>
            </div>
            <div className="p-3 bg-gray-950 rounded-xl border border-gray-800">
              <div className="text-[10px] text-gray-400 uppercase">Invalid Rows</div>
              <div className="text-xl font-black font-mono text-amber-400">{qualityData?.invalid_rows ?? "0"}</div>
            </div>
          </div>
        </div>

        {/* Vital Measurement Missingness Breakdown */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-4">
          <h2 className="text-base font-bold text-gray-100 flex items-center gap-2">
            <BarChart2 className="w-5 h-5 text-blue-400" /> Vital Sign Completeness Breakdown
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(missing).map(([field, info]: [string, any]) => (
              <div key={field} className="p-4 bg-gray-950 rounded-xl border border-gray-800 space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-gray-200 capitalize">{field.replace("_", " ")}</span>
                  <span className="text-[10px] font-mono text-blue-400 bg-blue-950/60 px-2 py-0.5 rounded border border-blue-900">
                    Col: {info.detected_column || "N/A"}
                  </span>
                </div>

                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-gray-400">Valid Readings:</span>
                  <span className="text-emerald-400 font-bold">{info.valid_count}</span>
                </div>

                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-gray-400">Missing Count:</span>
                  <span className="text-amber-400 font-bold">{info.missing_count} ({info.missing_pct}%)</span>
                </div>

                <div className="flex items-center justify-between text-xs font-mono">
                  <span className="text-gray-400">Out-of-Bounds:</span>
                  <span className="text-red-400 font-bold">{info.invalid_count}</span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-gray-800 rounded-full h-1.5 mt-2">
                  <div
                    className="bg-emerald-500 h-1.5 rounded-full"
                    style={{ width: `${Math.max(0, 100 - info.missing_pct)}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
