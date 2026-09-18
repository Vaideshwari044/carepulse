import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { FileText, Download, Printer, ShieldAlert, FileSpreadsheet } from "lucide-react";

export const ReportsPage: React.FC = () => {
  const { status: socketStatus } = useMonitoringSocket();
  const [selectedReport, setSelectedReport] = useState("patient_monitoring");

  const { data: summaryData } = useQuery({
    queryKey: ["reports-summary-info"],
    queryFn: () => api.get<any>("/api/v1/reports/summary"),
  });

  const reports = summaryData?.reports_available || [
    { id: "patient_monitoring", title: "Patient Monitoring Report", description: "Comprehensive vitals, baselines, and risk scores across all active patients", format: ["CSV", "PDF"] },
    { id: "risk_summary", title: "Clinical Risk & Early Warning Summary", description: "Risk distribution, contributing factors, and deterioration timelines", format: ["CSV", "PDF"] },
    { id: "alert_history", title: "Alert & Intervention Audit Report", description: "Alert triggers, resolution times, and clinician intervention notes", format: ["CSV", "PDF"] },
    { id: "dataset_quality", title: "Dataset & Ingestion Quality Report", description: "Data completeness, physiological bounds validation, and mapping metrics", format: ["CSV", "PDF"] },
  ];

  const handleDownloadCsv = (type: string) => {
    window.open(`/api/v1/reports/export/csv?report_type=${type}`, "_blank");
  };

  const handlePrintPdf = () => {
    window.print();
  };

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
              <FileText className="w-6 h-6 text-amber-400" /> Clinical Reports &amp; Documentation Export
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Generate formatted PDF summary reports, export CSV data records, and print audit summaries.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handlePrintPdf}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-2 transition"
            >
              <Printer className="w-4 h-4 text-amber-400" /> Print / Save as PDF
            </button>
          </div>
        </div>

        {/* Report Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {reports.map((rep: any) => (
            <div
              key={rep.id}
              className={`p-6 rounded-2xl border transition space-y-4 ${
                selectedReport === rep.id
                  ? "bg-slate-900 border-amber-500 shadow-xl shadow-amber-500/10"
                  : "bg-slate-900/80 border-slate-800 hover:border-slate-700"
              }`}
              onClick={() => setSelectedReport(rep.id)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="space-y-1">
                  <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                    <FileSpreadsheet className="w-5 h-5 text-amber-400" /> {rep.title}
                  </h3>
                  <p className="text-xs text-slate-400">{rep.description}</p>
                </div>
                <span className="px-2 py-0.5 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded text-[10px] font-mono font-bold">
                  PDF &amp; CSV
                </span>
              </div>

              <div className="flex items-center justify-between pt-2 border-t border-slate-800">
                <button
                  onClick={() => handleDownloadCsv(rep.id)}
                  className="px-3 py-1.5 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-semibold transition flex items-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" /> Export CSV Data
                </button>
                <button
                  onClick={handlePrintPdf}
                  className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-semibold transition flex items-center gap-1.5"
                >
                  <Printer className="w-3.5 h-3.5" /> Preview PDF Report
                </button>
              </div>
            </div>
          ))}
        </div>

        {/* Formatted Printable Preview Container */}
        <div className="bg-slate-900/90 rounded-2xl p-8 border border-slate-800 space-y-6 print:bg-white print:text-black shadow-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-4">
            <div>
              <span className="text-xs font-bold text-amber-400 uppercase tracking-widest block">CarePulse Clinical Documentation</span>
              <h2 className="text-xl font-black text-slate-100">
                {reports.find((r: any) => r.id === selectedReport)?.title || "Patient Monitoring Report"}
              </h2>
            </div>
            <div className="text-right text-xs text-slate-400">
              <div>Facility: ICU Ward 3 — Central Hospital</div>
              <div>Generated: {new Date().toLocaleDateString()}</div>
            </div>
          </div>

          <div className="p-4 bg-slate-950 border border-slate-800 rounded-xl text-xs space-y-2">
            <div className="font-bold text-amber-400 uppercase tracking-wider">Report Summary &amp; Scope</div>
            <p className="text-slate-300">
              This clinical document summarizes all recorded patient vital measurements, baseline status calculations, deterioration risk state transitions, and clinician intervention audit logs.
            </p>
          </div>

          <div className="text-center py-6 border-t border-slate-800 text-xs text-slate-500 flex items-center justify-center gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400" />
            <span>CONFIDENTIAL MEDICAL DECISION SUPPORT DOCUMENT — SYNTHETIC DATASET — NOT FOR CLINICAL CARE</span>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
