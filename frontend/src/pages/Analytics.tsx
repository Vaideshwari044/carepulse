import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { BarChart2, Cpu, Database, CheckCircle, ShieldAlert, FileText } from "lucide-react";

export const AnalyticsPage: React.FC = () => {
  const { data: analytics } = useQuery({
    queryKey: ["analytics-summary"],
    queryFn: () => api.get<any>("/api/v1/analytics"),
  });

  const { data: modelData } = useQuery({
    queryKey: ["model-info"],
    queryFn: () => api.get<any>("/api/v1/model"),
  });

  const { status: socketStatus } = useMonitoringSocket();

  const card = modelData?.model_card || {};
  const metrics = card?.metrics || {};

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-8">
        <div>
          <h1 className="text-2xl font-black text-gray-100 flex items-center gap-2">
            <BarChart2 className="w-6 h-6 text-blue-400" /> System Analytics &amp; AI Model Card
          </h1>
          <p className="text-xs text-gray-400 mt-1">
            Machine Learning performance metrics, feature architecture, and system telemetry
          </p>
        </div>

        {/* Analytics Counters */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center gap-3">
              <Database className="w-8 h-8 text-blue-400 opacity-80" />
              <div>
                <div className="text-xs font-semibold text-gray-400 uppercase">Total Vital Readings</div>
                <div className="text-2xl font-black font-mono text-gray-100">
                  {analytics?.total_vital_readings ?? "--"}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center gap-3">
              <Cpu className="w-8 h-8 text-indigo-400 opacity-80" />
              <div>
                <div className="text-xs font-semibold text-gray-400 uppercase">Risk Assessments Computed</div>
                <div className="text-2xl font-black font-mono text-gray-100">
                  {analytics?.total_risk_assessments ?? "--"}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center gap-3">
              <CheckCircle className="w-8 h-8 text-emerald-400 opacity-80" />
              <div>
                <div className="text-xs font-semibold text-gray-400 uppercase">Model Status</div>
                <div className="text-xl font-black font-mono text-emerald-400 capitalize">
                  {modelData?.model_status || "Checking..."}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Model Card Section */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-6">
          <div className="flex items-center justify-between pb-4 border-b border-gray-800">
            <div className="flex items-center gap-2 text-blue-400 font-bold text-base">
              <FileText className="w-5 h-5" />
              <span>Machine Learning Model Card (rf_v1)</span>
            </div>
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-blue-950 text-blue-300 border border-blue-800">
              RandomForest (300 trees, max_depth=12)
            </span>
          </div>

          {metrics.accuracy ? (
            <>
              {/* Key Metrics Grid */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="p-4 bg-gray-950 rounded-xl border border-gray-800 text-center">
                  <div className="text-xs text-gray-400">Test Accuracy</div>
                  <div className="text-2xl font-black font-mono text-emerald-400">
                    {(metrics.accuracy * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="p-4 bg-gray-950 rounded-xl border border-gray-800 text-center">
                  <div className="text-xs text-gray-400">Macro F1 Score</div>
                  <div className="text-2xl font-black font-mono text-blue-400">
                    {(metrics.macro_f1 * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="p-4 bg-gray-950 rounded-xl border border-gray-800 text-center">
                  <div className="text-xs text-gray-400">HIGH Sensitivity (Recall)</div>
                  <div className="text-2xl font-black font-mono text-amber-400">
                    {(metrics.high_recall * 100).toFixed(1)}%
                  </div>
                </div>
                <div className="p-4 bg-gray-950 rounded-xl border border-gray-800 text-center">
                  <div className="text-xs text-gray-400">ROC-AUC (OVR)</div>
                  <div className="text-2xl font-black font-mono text-indigo-400">
                    {metrics.roc_auc_ovr ? (metrics.roc_auc_ovr * 100).toFixed(1) + "%" : "N/A"}
                  </div>
                </div>
              </div>

              {/* Data Split & Label Description */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-4 bg-gray-950 rounded-xl border border-gray-800 space-y-2">
                  <span className="font-bold text-gray-200 block">Patient-Level Train/Val/Test Split</span>
                  <div className="text-gray-400 space-y-1 font-mono">
                    <div>Training Set: {card.train_patients} patients ({metrics.n_train} samples)</div>
                    <div>Validation Set: {card.val_patients} patients ({metrics.n_val} samples)</div>
                    <div>Test Set: {card.test_patients} patients ({metrics.n_test} samples)</div>
                  </div>
                </div>

                <div className="p-4 bg-gray-950 rounded-xl border border-gray-800 space-y-2">
                  <span className="font-bold text-gray-200 block">Label Description</span>
                  <p className="text-amber-300/90 font-mono font-medium">
                    {card.label_description}
                  </p>
                  <p className="text-gray-400 text-[11px]">
                    Labels derived from future 15-minute simulated patient trajectory state — NOT rule_score.
                  </p>
                </div>
              </div>

              {/* Feature Space Info */}
              <div className="p-4 bg-gray-950 rounded-xl border border-gray-800 text-xs">
                <span className="font-bold text-gray-200 block mb-2">49-Dimensional Feature Space</span>
                <div className="flex flex-wrap gap-1.5 font-mono">
                  {card.feature_names?.map((f: string) => (
                    <span key={f} className="px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-300">
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            </>
          ) : (
            <div className="text-xs text-gray-400 italic">
              Model metrics loading or model card file unavailable.
            </div>
          )}

          <div className="p-4 bg-amber-950/40 border border-amber-800/60 rounded-xl text-xs text-amber-300/90 flex items-start gap-2">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong>Safety Note:</strong> {card.safety_note || "Not clinically validated. For clinical demonstration only."}
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
