import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import {
  GitCommit,
  Database,
  CheckCircle2,
  ShieldCheck,
  Cpu,
  Bell,
  LayoutDashboard,
  ArrowDown,
  Sparkles,
} from "lucide-react";

export const DataPipelinePage: React.FC = () => {
  const { status: socketStatus } = useMonitoringSocket();

  const { data: datasets } = useQuery({
    queryKey: ["datasets-pipeline-info"],
    queryFn: () => api.get<any[]>("/api/v1/datasets"),
  });

  const activeDs = datasets && datasets.length > 0 ? datasets[0] : null;

  const pipelineNodes = [
    {
      step: 1,
      title: "Raw Clinical Dataset Ingestion",
      icon: Database,
      status: activeDs ? "COMPLETED" : "READY",
      detail: activeDs ? `${activeDs.name} (${activeDs.row_count} rows, 70 patients)` : "clinical_vitals_dataset.csv",
      tech: "Pandas / Parquet Parser",
    },
    {
      step: 2,
      title: "Physiological Bounds Validation",
      icon: CheckCircle2,
      status: "ACTIVE",
      detail: "HR [30-220], SpO2 [50-100%], RR [5-60], Temp [30-45°C]",
      tech: "Pydantic & Quality Engine",
    },
    {
      step: 3,
      title: "De-identification & Anonymization",
      icon: ShieldCheck,
      status: "ACTIVE",
      detail: "Patient ID transformation (CP-0001 - CP-0070), PHI masking",
      tech: "De-id Transformer",
    },
    {
      step: 4,
      title: "PostgreSQL Storage & Persistence",
      icon: Database,
      status: "ACTIVE",
      detail: "Tables: patients, vital_readings, patient_baselines, dataset_records",
      tech: "SQLAlchemy 2.0 Async + asyncpg",
    },
    {
      step: 5,
      title: "Feature Engineering Engine",
      icon: Cpu,
      status: "ACTIVE",
      detail: "Rolling baseline (N=30), linear regression slope, rate-of-change",
      tech: "NumPy / SciPy Pipeline",
    },
    {
      step: 6,
      title: "AI Early Warning Risk Engine",
      icon: Cpu,
      status: "ACTIVE",
      detail: "Hybrid RF ML (45%) + Clinical Rule State Machine (55%)",
      tech: "RandomForestClassifier (rf_v1.joblib)",
    },
    {
      step: 7,
      title: "Deterioration Alert Dispatcher",
      icon: Bell,
      status: "ACTIVE",
      detail: "Multi-parameter persistence & escalation trigger",
      tech: "Alert Manager & Cooldown Engine",
    },
    {
      step: 8,
      title: "Real-time Command Dashboard & AI Assistant",
      icon: LayoutDashboard,
      status: "ACTIVE",
      detail: "WebSocket / Polling stream UI & de-identified chatbot context",
      tech: "React 18 + FastAPI + Chatbot Router",
    },
  ];

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
              <GitCommit className="w-6 h-6 text-amber-400" /> End-to-End Clinical Data Pipeline
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Architectural flow from raw dataset ingestion through feature engineering, risk classification, and decision-support UI.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5">
              <Sparkles className="w-4 h-4" /> Pipeline Health: 100% Operational
            </span>
          </div>
        </div>

        {/* Pipeline Nodes Flow */}
        <div className="space-y-4">
          {pipelineNodes.map((node, index) => {
            const Icon = node.icon;
            return (
              <React.Fragment key={node.step}>
                <div className="bg-slate-900/90 rounded-2xl p-5 border border-slate-800 hover:border-amber-500/40 transition shadow-lg flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="flex items-start md:items-center gap-4">
                    <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-bold text-sm shrink-0">
                      0{node.step}
                    </div>

                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
                          <Icon className="w-4 h-4 text-amber-400" /> {node.title}
                        </h3>
                        <span className="px-2 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded text-[10px] font-mono">
                          {node.status}
                        </span>
                      </div>
                      <p className="text-xs text-slate-300">{node.detail}</p>
                    </div>
                  </div>

                  <div className="text-right">
                    <span className="text-[11px] font-mono text-slate-400 px-3 py-1 bg-slate-950 border border-slate-800 rounded-lg">
                      {node.tech}
                    </span>
                  </div>
                </div>

                {index < pipelineNodes.length - 1 && (
                  <div className="flex justify-center my-1">
                    <ArrowDown className="w-5 h-5 text-amber-500/60 animate-bounce" />
                  </div>
                )}
              </React.Fragment>
            );
          })}
        </div>
      </div>
    </AppLayout>
  );
};
