import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import {
  Database,
  Filter,
  Search,
  RefreshCw,
  Sliders,
} from "lucide-react";
import { format } from "date-fns";

export interface DatasetRecord {
  id: string;
  dataset_id: string;
  patient_code: string;
  raw_patient_id?: string;
  recorded_at: string;
  heart_rate?: number | null;
  spo2?: number | null;
  respiratory_rate?: number | null;
  systolic_bp?: number | null;
  diastolic_bp?: number | null;
  temperature?: number | null;
  raw_label?: string | null;
  scenario?: string | null;
}

export const DatasetExplorer: React.FC = () => {
  const [patientFilter, setPatientFilter] = useState<string>("");
  const [labelFilter, setLabelFilter] = useState<string>("");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [page, setPage] = useState(1);

  const { status: socketStatus } = useMonitoringSocket();

  // Fetch registered datasets
  const { data: datasets } = useQuery({
    queryKey: ["datasets-list"],
    queryFn: () => api.get<any[]>("/api/v1/datasets"),
  });

  const activeDataset = datasets && datasets.length > 0 ? datasets[0] : null;
  const activeDatasetId = activeDataset?.id;

  // Fetch dataset records
  const { data: recordsData, isFetching, refetch } = useQuery({
    queryKey: ["dataset-records", activeDatasetId, patientFilter, labelFilter, page],
    queryFn: () => {
      if (!activeDatasetId) return { total: 0, records: [] };
      let q = `/api/v1/datasets/${activeDatasetId}/records?page=${page}&size=50`;
      if (patientFilter) q += `&patient_code=${encodeURIComponent(patientFilter)}`;
      if (labelFilter) q += `&raw_label=${encodeURIComponent(labelFilter)}`;
      return api.get<{ total: number; records: DatasetRecord[] }>(q);
    },
    enabled: !!activeDatasetId,
  });

  // Fetch quality & mappings summary
  const { data: qualityData } = useQuery({
    queryKey: ["dataset-quality-summary", activeDatasetId],
    queryFn: () => api.get<any>(`/api/v1/datasets/${activeDatasetId}/quality`),
    enabled: !!activeDatasetId,
  });

  const records = recordsData?.records || [];
  const total = recordsData?.total || 0;
  const mappings = qualityData?.column_mappings || {};

  // Filter records by local search query if provided
  const filteredRecords = records.filter((r) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase();
    return (
      r.patient_code.toLowerCase().includes(q) ||
      (r.raw_label && r.raw_label.toLowerCase().includes(q)) ||
      (r.scenario && r.scenario.toLowerCase().includes(q))
    );
  });

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Page Title & Status */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-gray-100 flex items-center gap-2">
              <Database className="w-6 h-6 text-blue-400" /> Dataset Explorer
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Explore simple, clean dataset records, mapped vital measurements, and dataset labels
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => refetch()}
              className="px-3 py-2 bg-gray-900 border border-gray-700 hover:bg-gray-800 rounded-xl text-xs text-gray-300 flex items-center gap-2"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${isFetching ? "animate-spin" : ""}`} /> Refresh
            </button>
          </div>
        </div>

        {/* Top Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-[10px] font-semibold text-gray-400 uppercase">Total Records</div>
            <div className="text-xl font-black font-mono text-gray-100 mt-1">
              {activeDataset?.row_count ?? total}
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-[10px] font-semibold text-gray-400 uppercase">Monitored Patients</div>
            <div className="text-xl font-black font-mono text-blue-400 mt-1">
              {activeDataset?.patient_count ?? "--"}
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-[10px] font-semibold text-gray-400 uppercase">Dataset Format</div>
            <div className="text-sm font-bold font-mono text-emerald-400 mt-1 uppercase">
              {activeDataset?.file_format || "PARQUET / CSV"}
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-[10px] font-semibold text-gray-400 uppercase">Quality Indicator</div>
            <div className="text-sm font-bold font-mono text-emerald-400 mt-1">
              {qualityData?.quality_indicator || "GOOD"}
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
            <div className="text-[10px] font-semibold text-gray-400 uppercase">Dataset Source</div>
            <div className="text-[11px] font-mono text-amber-300 truncate mt-1">
              {activeDataset?.filename || "synthetic_vitals"}
            </div>
          </div>
        </div>

        {/* Detected Column Mapping Banner */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4">
          <div className="flex items-center gap-2 text-xs font-bold text-gray-300 mb-2">
            <Sliders className="w-4 h-4 text-blue-400" />
            <span>Detected Column Mapping Layer:</span>
          </div>
          <div className="flex flex-wrap gap-2 text-xs">
            {Object.entries(mappings).map(([field, rawCol]) => (
              <span key={field} className="px-2.5 py-1 rounded bg-gray-950 border border-gray-800 font-mono text-gray-300">
                <span className="text-blue-400 font-semibold">{field}</span> &larr; {String(rawCol)}
              </span>
            ))}
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2 w-full md:w-auto">
            <Search className="w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search patient ID or label..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-blue-500 w-full md:w-64"
            />
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto flex-wrap">
            <div className="flex items-center gap-1.5 text-xs text-gray-400">
              <Filter className="w-3.5 h-3.5" /> Filter Patient:
            </div>
            <input
              type="text"
              placeholder="e.g. P101 or CP-0001"
              value={patientFilter}
              onChange={(e) => setPatientFilter(e.target.value)}
              className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 font-mono focus:outline-none"
            />

            <select
              value={labelFilter}
              onChange={(e) => setLabelFilter(e.target.value)}
              className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-200 focus:outline-none"
            >
              <option value="">All Dataset Labels</option>
              <option value="LOW">LOW</option>
              <option value="MODERATE">MODERATE</option>
              <option value="HIGH">HIGH</option>
            </select>
          </div>
        </div>

        {/* Data Table */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs text-gray-300">
              <thead className="bg-gray-950 border-b border-gray-800 uppercase text-[10px] font-mono text-gray-400 tracking-wider">
                <tr>
                  <th className="py-3 px-4">Patient ID</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4">Heart Rate (bpm)</th>
                  <th className="py-3 px-4">SpO2 (%)</th>
                  <th className="py-3 px-4">Temperature (°C)</th>
                  <th className="py-3 px-4">Blood Pressure</th>
                  <th className="py-3 px-4">Resp Rate (/min)</th>
                  <th className="py-3 px-4">Dataset Label</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/60 font-mono">
                {filteredRecords.length > 0 ? (
                  filteredRecords.map((r) => (
                    <tr key={r.id} className="hover:bg-gray-800/40 transition-colors">
                      <td className="py-3 px-4 font-bold text-blue-400">{r.patient_code}</td>
                      <td className="py-3 px-4 text-gray-400">
                        {format(new Date(r.recorded_at), "yyyy-MM-dd HH:mm:ss")}
                      </td>
                      <td className="py-3 px-4 font-bold text-gray-100">
                        {r.heart_rate !== null && r.heart_rate !== undefined ? r.heart_rate.toFixed(0) : "--"}
                      </td>
                      <td className="py-3 px-4 font-bold text-blue-300">
                        {r.spo2 !== null && r.spo2 !== undefined ? `${r.spo2.toFixed(1)}%` : "--"}
                      </td>
                      <td className="py-3 px-4 text-emerald-400">
                        {r.temperature !== null && r.temperature !== undefined ? `${r.temperature.toFixed(1)}` : "--"}
                      </td>
                      <td className="py-3 px-4 text-purple-300">
                        {r.systolic_bp !== null && r.diastolic_bp !== null
                          ? `${r.systolic_bp?.toFixed(0)}/${r.diastolic_bp?.toFixed(0)}`
                          : "--"}
                      </td>
                      <td className="py-3 px-4 text-amber-400">
                        {r.respiratory_rate !== null && r.respiratory_rate !== undefined ? r.respiratory_rate.toFixed(0) : "--"}
                      </td>
                      <td className="py-3 px-4">
                        {r.raw_label ? (
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                              r.raw_label === "HIGH"
                                ? "bg-red-950 text-red-300 border-red-800"
                                : r.raw_label === "MODERATE"
                                ? "bg-amber-950 text-amber-300 border-amber-800"
                                : "bg-emerald-950 text-emerald-300 border-emerald-800"
                            }`}
                          >
                            {r.raw_label}
                          </span>
                        ) : (
                          <span className="text-gray-500">N/A</span>
                        )}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-gray-500 italic">
                      No dataset records match current filter criteria
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Controls */}
          <div className="p-4 bg-gray-950 border-t border-gray-800 flex items-center justify-between text-xs text-gray-400">
            <div>
              Showing page <strong className="text-gray-200">{page}</strong> (Total records: {total})
            </div>
            <div className="flex items-center gap-2">
              <button
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
                className="px-3 py-1.5 bg-gray-900 border border-gray-800 hover:bg-gray-800 rounded-lg text-gray-300 disabled:opacity-40"
              >
                Previous
              </button>
              <button
                disabled={page * 50 >= total}
                onClick={() => setPage((p) => p + 1)}
                className="px-3 py-1.5 bg-gray-900 border border-gray-800 hover:bg-gray-800 rounded-lg text-gray-300 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
