import React from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { VitalChart } from "../components/VitalChart";
import { AlertList } from "../components/AlertList";
import { getRiskBg, getRiskColor, getRiskLabel } from "../lib/utils";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { ArrowLeft, Activity, Info, AlertCircle, HelpCircle, Check } from "lucide-react";

export const PatientDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();

  // Fetch patient metadata
  const { data: patient, refetch: refetchPatient } = useQuery({
    queryKey: ["patient", id],
    queryFn: () => api.get<any>(`/api/v1/patients/${id}`),
    enabled: !!id,
    refetchInterval: 3000,
  });

  // Fetch recent vitals
  const { data: vitals, refetch: refetchVitals } = useQuery({
    queryKey: ["patient-vitals", id],
    queryFn: () => api.get<any[]>(`/api/v1/patients/${id}/vitals?limit=50`),
    enabled: !!id,
    refetchInterval: 3000,
  });

  // Fetch baseline stats
  const { data: baseline } = useQuery({
    queryKey: ["patient-baseline", id],
    queryFn: () => api.get<any>(`/api/v1/patients/${id}/baseline`),
    enabled: !!id,
  });

  // Fetch explanation
  const { data: explanationData } = useQuery({
    queryKey: ["patient-explanation", id],
    queryFn: () => api.get<any>(`/api/v1/patients/${id}/risk/explanation`),
    enabled: !!id,
    refetchInterval: 3000,
  });

  // Fetch why-not breakdown
  const { data: whyNotData } = useQuery({
    queryKey: ["patient-why-not", id],
    queryFn: () => api.get<any>(`/api/v1/patients/${id}/risk/why-not`),
    enabled: !!id,
    refetchInterval: 3000,
  });

  // Fetch patient alerts
  const { data: alertData, refetch: refetchAlerts } = useQuery({
    queryKey: ["patient-alerts", id],
    queryFn: () => api.get<any[]>(`/api/v1/alerts?patient_id=${id}`),
    enabled: !!id,
    refetchInterval: 3000,
  });

  const { status: socketStatus } = useMonitoringSocket(() => {
    refetchPatient();
    refetchVitals();
    refetchAlerts();
  });

  if (!patient) {
    return (
      <AppLayout socketStatus={socketStatus}>
        <div className="p-8 text-center text-gray-400">Loading patient details...</div>
      </AppLayout>
    );
  }

  const state = patient.current_risk_state || "INSUFFICIENT_DATA";
  const score = patient.current_risk_score !== null && patient.current_risk_score !== undefined
    ? Math.round(patient.current_risk_score)
    : "--";

  const rawVitals = vitals || [];
  const explanation = explanationData?.explanation || {};
  const stats = baseline?.stats || {};

  // Extract parameter arrays for charts
  const hrData = rawVitals.map((v) => ({ recorded_at: v.recorded_at, value: v.heart_rate }));
  const spo2Data = rawVitals.map((v) => ({ recorded_at: v.recorded_at, value: v.spo2 }));
  const rrData = rawVitals.map((v) => ({ recorded_at: v.recorded_at, value: v.respiratory_rate }));
  const sbpData = rawVitals.map((v) => ({ recorded_at: v.recorded_at, value: v.systolic_bp }));
  const dbpData = rawVitals.map((v) => ({ recorded_at: v.recorded_at, value: v.diastolic_bp }));
  const tempData = rawVitals.map((v) => ({ recorded_at: v.recorded_at, value: v.temperature }));

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Back Link & Header */}
        <div className="flex items-center justify-between">
          <Link
            to="/dashboard"
            className="inline-flex items-center gap-1 text-sm font-semibold text-gray-400 hover:text-gray-200 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back to Dashboard
          </Link>
          <span className="text-xs font-mono text-gray-400">UUID: {patient.id}</span>
        </div>

        {/* Patient Risk Banner */}
        <div className={`p-6 rounded-2xl border flex flex-col md:flex-row md:items-center justify-between gap-6 ${getRiskBg(state)}`}>
          <div>
            <div className="flex items-center gap-3 mb-1">
              <span className="text-xs font-mono font-bold text-gray-400 uppercase tracking-widest">
                {patient.patient_code}
              </span>
              <span className={`px-2.5 py-0.5 rounded-full text-xs font-bold border ${getRiskBg(state)} ${getRiskColor(state)}`}>
                {getRiskLabel(state)}
              </span>
            </div>
            <h1 className="text-3xl font-black text-gray-100">{patient.display_name}</h1>
            <p className="text-xs text-gray-400 mt-1">
              Status: <span className="capitalize font-semibold text-gray-300">{patient.monitoring_status}</span> | Baseline:{" "}
              <span className="capitalize font-semibold text-gray-300">{patient.baseline_status}</span>
            </p>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-right">
              <div className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Risk Score</div>
              <div className={`text-4xl font-black font-mono ${getRiskColor(state)}`}>
                {score}
                <span className="text-sm text-gray-400 font-normal">/100</span>
              </div>
            </div>
          </div>
        </div>

        {/* Explainability Summary Card */}
        {explanation.headline && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-4">
            <div className="flex items-center gap-2 text-blue-400 font-bold text-sm">
              <Info className="w-4 h-4" />
              <span>Decision Support Explanation</span>
            </div>

            <div className="text-base font-bold text-gray-100">{explanation.headline}</div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
              <div className="p-3 bg-gray-950 rounded-lg border border-gray-800">
                <span className="font-semibold text-gray-300 block mb-1">What Changed:</span>
                <p className="text-gray-400">{explanation.what_happened}</p>
              </div>
              <div className="p-3 bg-gray-950 rounded-lg border border-gray-800">
                <span className="font-semibold text-gray-300 block mb-1">Why Triggered:</span>
                <p className="text-gray-400">{explanation.why_detected}</p>
              </div>
            </div>

            {explanation.contributors && explanation.contributors.length > 0 && (
              <div>
                <span className="text-xs font-semibold text-gray-400 block mb-2">Component Contributions:</span>
                <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
                  {explanation.contributors.map((c: any, i: number) => (
                    <div key={i} className="p-2 bg-gray-950 rounded border border-gray-800 text-center">
                      <div className="text-[10px] text-gray-400 truncate">{c.component}</div>
                      <div className="text-sm font-mono font-bold text-blue-400">{c.contribution_pct}%</div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="p-3 bg-blue-950/40 border border-blue-800/60 rounded-lg text-xs text-blue-300 font-medium">
              <strong>Recommendation:</strong> {explanation.recommendation}
            </div>
          </div>
        )}

        {/* Why-Not Alert Card */}
        {whyNotData && (
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm mb-3">
              <HelpCircle className="w-4 h-4" />
              <span>Why Not Alert / Stabilizing Factors</span>
            </div>
            <div className="text-xs text-gray-300 mb-2">{whyNotData.why_score_is_low}</div>
            <div className="flex flex-wrap gap-2">
              {whyNotData.stabilizing_factors?.map((fact: string, idx: number) => (
                <span key={idx} className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800">
                  <Check className="w-3 h-3" /> {fact}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Vital Charts Grid */}
        <section className="space-y-4">
          <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
            <Activity className="w-5 h-5 text-blue-400" /> Live Vital Sign Trends
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <VitalChart
              title="Heart Rate"
              unit="bpm"
              data={hrData}
              baselineMean={stats.heart_rate?.mean}
              normalMin={50}
              normalMax={100}
              color="#EF4444"
            />
            <VitalChart
              title="SpO2"
              unit="%"
              data={spo2Data}
              baselineMean={stats.spo2?.mean}
              normalMin={94}
              normalMax={100}
              color="#3B82F6"
            />
            <VitalChart
              title="Respiratory Rate"
              unit="/min"
              data={rrData}
              baselineMean={stats.respiratory_rate?.mean}
              normalMin={10}
              normalMax={22}
              color="#F59E0B"
            />
            <VitalChart
              title="Systolic BP"
              unit="mmHg"
              data={sbpData}
              baselineMean={stats.systolic_bp?.mean}
              normalMin={100}
              normalMax={160}
              color="#8B5CF6"
            />
            <VitalChart
              title="Diastolic BP"
              unit="mmHg"
              data={dbpData}
              baselineMean={stats.diastolic_bp?.mean}
              normalMin={60}
              normalMax={100}
              color="#EC4899"
            />
            <VitalChart
              title="Temperature"
              unit="°C"
              data={tempData}
              baselineMean={stats.temperature?.mean}
              normalMin={36.0}
              normalMax={38.0}
              color="#10B981"
            />
          </div>
        </section>

        {/* Clinical & Laboratory Information */}
        <section className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
          <h2 className="text-lg font-bold text-gray-100 flex items-center gap-2">
            <Info className="w-5 h-5 text-amber-400" /> Clinical & Laboratory Data
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 bg-gray-950 rounded-lg border border-gray-800 space-y-2">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Source Dataset Clinical Fields</span>
              <div className="text-xs text-gray-300 space-y-1">
                <p><strong className="text-gray-400">Predicted Disease / Condition:</strong> {patient.extra_data?.predicted_disease || patient.current_risk_state || "Recorded in dataset"}</p>
                <p><strong className="text-gray-400">Fall Detection Status:</strong> {patient.extra_data?.fall_detection !== undefined ? String(patient.extra_data.fall_detection) : "Monitored"}</p>
                <p><strong className="text-gray-400">Data Accuracy Level:</strong> {patient.extra_data?.data_accuracy ? `${patient.extra_data.data_accuracy}%` : "100%"}</p>
              </div>
            </div>
            <div className="p-4 bg-gray-950 rounded-lg border border-gray-800 space-y-2">
              <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider block">Laboratory Values</span>
              <div className="text-xs text-amber-500/80 italic space-y-1 font-mono">
                <p>• White Blood Cell (WBC): Not available in source dataset</p>
                <p>• Cardiac Troponin: Not available in source dataset</p>
                <p>• Blood Glucose: Not available in source dataset</p>
                <p>• Serum Creatinine: Not available in source dataset</p>
              </div>
            </div>
          </div>
        </section>

        {/* Patient Alert History */}
        <section>
          <h2 className="text-lg font-bold text-gray-100 mb-4 flex items-center gap-2">
            <AlertCircle className="w-5 h-5 text-amber-400" /> Patient Alert History
          </h2>
          <AlertList alerts={alertData || []} />
        </section>

      </div>
    </AppLayout>
  );
};
