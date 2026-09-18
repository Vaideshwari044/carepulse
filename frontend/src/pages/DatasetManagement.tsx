import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import {
  Upload,
  CheckCircle2,
  AlertTriangle,
  AlertOctagon,
  Database,
  Trash2,
  Play,
  FileSpreadsheet,
  Layers,
  Eye,
  RefreshCw,
  ShieldAlert,
} from "lucide-react";

export interface ValidationResult {
  file_path: string;
  filename: string;
  valid: boolean;
  analysis: {
    total_rows: number;
    valid_rows: number;
    invalid_rows: number;
    patient_count: number;
    columns_detected: string[];
    column_mappings: Record<string, string>;
    missing_summary: Record<string, number>;
    quality_indicator: "GOOD" | "WARNING" | "ERROR";
  };
}

export const DatasetManagement: React.FC = () => {
  const queryClient = useQueryClient();
  const { status: socketStatus } = useMonitoringSocket();

  const [filePath, setFilePath] = useState<string>("data/clinical_vitals_dataset.csv");
  const [datasetName, setDatasetName] = useState<string>("Clinical Vitals Dataset (Synthetic Demo)");
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [previewRows, setPreviewRows] = useState<any[]>([]);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Fetch registered datasets
  const { data: datasets, refetch: refetchDatasets } = useQuery({
    queryKey: ["datasets-list"],
    queryFn: () => api.get<any[]>("/api/v1/datasets"),
  });

  const activeDataset = datasets && datasets.length > 0 ? datasets[0] : null;

  // Mutation: Validate Dataset
  const validateMutation = useMutation({
    mutationFn: (path: string) =>
      api.post<ValidationResult>("/api/v1/datasets/validate", {
        file_path: path,
      }),
    onSuccess: (data) => {
      setValidationResult(data);
      setMessage({ type: "success", text: "Dataset validated successfully. Auto-detected column mappings loaded." });
    },
    onError: (err: any) => {
      const errMsg = err?.response?.data?.detail?.error?.message || err?.message || "Validation failed";
      setMessage({ type: "error", text: `Validation Error: ${errMsg}` });
    },
  });

  // Mutation: Import Dataset
  const importMutation = useMutation({
    mutationFn: () =>
      api.post<any>("/api/v1/datasets/import", {
        name: datasetName,
        file_path: filePath,
        column_mappings: validationResult?.analysis.column_mappings || {},
      }),
    onSuccess: () => {
      setMessage({ type: "success", text: "Dataset imported and synced with patient risk engine!" });
      queryClient.invalidateQueries({ queryKey: ["datasets-list"] });
      queryClient.invalidateQueries({ queryKey: ["dataset-records"] });
      queryClient.invalidateQueries({ queryKey: ["dataset-quality-summary"] });
      refetchDatasets();
    },
    onError: (err: any) => {
      const errMsg = err?.response?.data?.detail?.error?.message || err?.message || "Import failed";
      setMessage({ type: "error", text: `Import Error: ${errMsg}` });
    },
  });

  // Mutation: Preview Dataset
  const previewMutation = useMutation({
    mutationFn: (id: string) => api.get<any>(`/api/v1/datasets/${id}/preview?limit=10`),
    onSuccess: (data) => {
      setPreviewRows(data.preview_rows || []);
      setMessage({ type: "success", text: `Loaded ${data.preview_rows?.length || 0} preview rows.` });
    },
    onError: () => {
      setMessage({ type: "error", text: "Failed to load preview rows." });
    },
  });

  // Mutation: Clear Dataset
  const clearMutation = useMutation({
    mutationFn: (id: string) => api.delete<void>(`/api/v1/datasets/${id}`),
    onSuccess: () => {
      setMessage({ type: "success", text: "Dataset records cleared from system." });
      setValidationResult(null);
      setPreviewRows([]);
      queryClient.invalidateQueries({ queryKey: ["datasets-list"] });
      refetchDatasets();
    },
    onError: (err: any) => {
      const errMsg = err?.response?.data?.detail?.error?.message || err?.message || "Deletion failed";
      setMessage({ type: "error", text: `Clear Error: ${errMsg}` });
    },
  });

  const getQualityBadge = (status?: string) => {
    switch (status) {
      case "GOOD":
        return (
          <span className="px-3 py-1 bg-green-500/20 text-green-400 border border-green-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5 w-fit">
            <CheckCircle2 className="w-4 h-4" /> Quality Status: GOOD
          </span>
        );
      case "WARNING":
        return (
          <span className="px-3 py-1 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5 w-fit">
            <AlertTriangle className="w-4 h-4" /> Quality Status: WARNING
          </span>
        );
      case "ERROR":
        return (
          <span className="px-3 py-1 bg-red-500/20 text-red-400 border border-red-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5 w-fit">
            <AlertOctagon className="w-4 h-4" /> Quality Status: ERROR
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 bg-gray-500/20 text-gray-400 border border-gray-500/30 rounded-full text-xs font-semibold">
            Status: UNCHECKED
          </span>
        );
    }
  };

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-gray-100 flex items-center gap-2">
              <Database className="w-6 h-6 text-purple-400" /> Dataset Management (Admin)
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Select, validate, preview, and ingest clinical datasets into CarePulse baseline and risk engine.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-yellow-500/10 text-yellow-400 border border-yellow-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5">
              <ShieldAlert className="w-4 h-4 text-yellow-400" /> SYNTHETIC DEMO DATA — NOT CLINICALLY VALIDATED
            </span>
          </div>
        </div>

        {/* Message Banner */}
        {message && (
          <div
            className={`p-4 rounded-xl border text-sm flex items-center justify-between ${
              message.type === "success"
                ? "bg-green-500/10 border-green-500/30 text-green-300"
                : "bg-red-500/10 border-red-500/30 text-red-300"
            }`}
          >
            <span>{message.text}</span>
            <button
              onClick={() => setMessage(null)}
              className="text-xs font-semibold opacity-70 hover:opacity-100"
            >
              Dismiss
            </button>
          </div>
        )}

        {/* Active Registered Dataset Card */}
        <div className="bg-gray-800/80 rounded-xl p-6 border border-gray-700/60 space-y-4">
          <div className="flex items-center justify-between border-b border-gray-700/60 pb-3">
            <h2 className="text-lg font-bold text-gray-200 flex items-center gap-2">
              <FileSpreadsheet className="w-5 h-5 text-blue-400" /> Currently Active Dataset
            </h2>
            {activeDataset && getQualityBadge(activeDataset.meta_info?.quality || "GOOD")}
          </div>

          {activeDataset ? (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
              <div className="bg-gray-900/60 p-3 rounded-lg border border-gray-700/40">
                <span className="text-xs text-gray-400 block">Dataset Name</span>
                <span className="font-semibold text-gray-200 truncate block">{activeDataset.name}</span>
              </div>
              <div className="bg-gray-900/60 p-3 rounded-lg border border-gray-700/40">
                <span className="text-xs text-gray-400 block">Total Records</span>
                <span className="font-semibold text-blue-400 block">{activeDataset.row_count.toLocaleString()}</span>
              </div>
              <div className="bg-gray-900/60 p-3 rounded-lg border border-gray-700/40">
                <span className="text-xs text-gray-400 block">Patients Mapped</span>
                <span className="font-semibold text-purple-400 block">{activeDataset.patient_count}</span>
              </div>
              <div className="bg-gray-900/60 p-3 rounded-lg border border-gray-700/40 flex items-center justify-between">
                <div>
                  <span className="text-xs text-gray-400 block">File Path</span>
                  <span className="font-mono text-xs text-gray-300 truncate block max-w-[120px]" title={activeDataset.file_path}>
                    {activeDataset.file_path}
                  </span>
                </div>
                <button
                  onClick={() => clearMutation.mutate(activeDataset.id)}
                  disabled={clearMutation.isPending}
                  className="p-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded-lg transition"
                  title="Clear Imported Demo Data"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          ) : (
            <div className="text-center py-6 text-gray-400 text-sm">
              No active dataset registered yet. Use the controls below to validate and import a dataset.
            </div>
          )}
        </div>

        {/* Dataset Selection & Ingestion Form */}
        <div className="bg-gray-800/80 rounded-xl p-6 border border-gray-700/60 space-y-6">
          <h2 className="text-lg font-bold text-gray-200 flex items-center gap-2">
            <Upload className="w-5 h-5 text-purple-400" /> Ingestion & Validation Setup
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Dataset File Path</label>
              <input
                type="text"
                value={filePath}
                onChange={(e) => setFilePath(e.target.value)}
                placeholder="e.g. data/clinical_vitals_dataset.csv"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
              <span className="text-[11px] text-gray-500 mt-1 block">
                Available files: `data/clinical_vitals_dataset.csv`, `backend/data/training/synthetic_vitals.parquet`
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-400 mb-1">Dataset Title / Identifier</label>
              <input
                type="text"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="e.g. Clinical Vitals Dataset"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
              />
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={() => validateMutation.mutate(filePath)}
              disabled={validateMutation.isPending}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-medium rounded-lg text-sm flex items-center gap-2 transition disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${validateMutation.isPending ? "animate-spin" : ""}`} />
              Validate & Auto-Detect Mappings
            </button>

            <button
              onClick={() => importMutation.mutate()}
              disabled={importMutation.isPending || !validationResult}
              className="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white font-medium rounded-lg text-sm flex items-center gap-2 transition disabled:opacity-50"
            >
              <Play className="w-4 h-4" />
              Import & Sync with CarePulse
            </button>

            {activeDataset && (
              <button
                onClick={() => previewMutation.mutate(activeDataset.id)}
                disabled={previewMutation.isPending}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-gray-200 font-medium rounded-lg text-sm flex items-center gap-2 transition"
              >
                <Eye className="w-4 h-4 text-emerald-400" />
                Preview Active Dataset (10 rows)
              </button>
            )}

            {activeDataset && (
              <button
                onClick={() => clearMutation.mutate(activeDataset.id)}
                disabled={clearMutation.isPending}
                className="px-4 py-2 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/30 font-medium rounded-lg text-sm flex items-center gap-2 transition ml-auto"
              >
                <Trash2 className="w-4 h-4" />
                Clear Imported Demo Data
              </button>
            )}
          </div>
        </div>

        {/* Validation Mappings Preview Section */}
        {validationResult && (
          <div className="bg-gray-800/80 rounded-xl p-6 border border-gray-700/60 space-y-6">
            <div className="flex items-center justify-between border-b border-gray-700/60 pb-3">
              <h3 className="text-base font-bold text-gray-200 flex items-center gap-2">
                <Layers className="w-5 h-5 text-emerald-400" /> Auto-Detected Column Mapping Layer
              </h3>
              {getQualityBadge(validationResult.analysis.quality_indicator)}
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div className="bg-gray-900/60 p-3 rounded-lg border border-gray-700/40">
                <span className="text-xs text-gray-400 block">Total Ingested Rows</span>
                <span className="font-semibold text-gray-200">{validationResult.analysis.total_rows.toLocaleString()}</span>
              </div>
              <div className="bg-gray-900/60 p-3 rounded-lg border border-gray-700/40">
                <span className="text-xs text-gray-400 block">Valid Physiological Rows</span>
                <span className="font-semibold text-green-400">{validationResult.analysis.valid_rows.toLocaleString()}</span>
              </div>
              <div className="bg-gray-900/60 p-3 rounded-lg border border-gray-700/40">
                <span className="text-xs text-gray-400 block">Unique Patient Identifiers</span>
                <span className="font-semibold text-purple-400">{validationResult.analysis.patient_count}</span>
              </div>
              <div className="bg-gray-900/60 p-3 rounded-lg border border-gray-700/40">
                <span className="text-xs text-gray-400 block">Detected Columns</span>
                <span className="font-semibold text-blue-400">{validationResult.analysis.columns_detected.length}</span>
              </div>
            </div>

            {/* Mappings Table */}
            <div>
              <h4 className="text-xs font-bold text-gray-400 uppercase tracking-wider mb-2">Column Mappings</h4>
              <div className="overflow-x-auto rounded-lg border border-gray-700/60">
                <table className="w-full text-left text-xs">
                  <thead className="bg-gray-900 text-gray-400 uppercase border-b border-gray-700">
                    <tr>
                      <th className="p-3">Standard CarePulse Field</th>
                      <th className="p-3">Mapped Dataset Column</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800 text-gray-300 font-mono">
                    {Object.entries(validationResult.analysis.column_mappings).map(([standardKey, mappedCol]) => (
                      <tr key={standardKey} className="hover:bg-gray-700/30">
                        <td className="p-3 font-semibold text-blue-400">{standardKey}</td>
                        <td className="p-3 text-purple-300">{mappedCol}</td>
                        <td className="p-3">
                          <span className="px-2 py-0.5 bg-green-500/10 text-green-400 border border-green-500/30 rounded text-[10px]">
                            Auto-Mapped
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Data Preview Table Section */}
        {previewRows.length > 0 && (
          <div className="bg-gray-800/80 rounded-xl p-6 border border-gray-700/60 space-y-4">
            <h3 className="text-base font-bold text-gray-200 flex items-center gap-2">
              <Eye className="w-5 h-5 text-blue-400" /> First 10 Raw Preview Rows
            </h3>

            <div className="overflow-x-auto rounded-lg border border-gray-700/60">
              <table className="w-full text-left text-xs">
                <thead className="bg-gray-900 text-gray-400 uppercase border-b border-gray-700">
                  <tr>
                    {Object.keys(previewRows[0] || {}).map((col) => (
                      <th key={col} className="p-3 font-mono">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-800 text-gray-300 font-mono">
                  {previewRows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-gray-700/30">
                      {Object.values(row).map((val: any, valIdx) => (
                        <td key={valIdx} className="p-3 whitespace-nowrap">
                          {val !== null && val !== undefined ? String(val) : <span className="text-gray-600">-</span>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};
