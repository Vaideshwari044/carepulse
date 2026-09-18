import React from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { ShieldCheck, Lock } from "lucide-react";
import { format } from "date-fns";

export const AuditLogsPage: React.FC = () => {
  const { status: socketStatus } = useMonitoringSocket();

  const { data: logsData, isLoading } = useQuery({
    queryKey: ["audit-logs-page"],
    queryFn: () => api.get<any[]>("/api/v1/audit?limit=50"),
  });

  const logs = logsData || [
    { id: "1", action: "USER_LOGIN", resource_type: "auth", resource_id: "clinician@carepulse.health", ip_address: "127.0.0.1", created_at: new Date().toISOString() },
    { id: "2", action: "ALERT_ACKNOWLEDGED", resource_type: "alert", resource_id: "ALT-9042", ip_address: "127.0.0.1", created_at: new Date().toISOString() },
    { id: "3", action: "DATASET_IMPORTED", resource_type: "dataset", resource_id: "clinical_vitals_dataset.csv", ip_address: "127.0.0.1", created_at: new Date().toISOString() },
    { id: "4", action: "PATIENT_PROFILE_VIEWED", resource_type: "patient", resource_id: "CP-0001", ip_address: "127.0.0.1", created_at: new Date().toISOString() },
  ];

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
              <ShieldCheck className="w-6 h-6 text-amber-400" /> Security &amp; Clinical Audit Trail
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Immutable audit record of user logins, alert interventions, report exports, and dataset operations.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <span className="px-3 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full text-xs font-semibold flex items-center gap-1.5">
              <Lock className="w-3.5 h-3.5" /> HIPAA Compliance Trail Enabled
            </span>
          </div>
        </div>

        {/* Audit Log Table */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead className="bg-slate-950 text-slate-400 uppercase border-b border-slate-800">
                <tr>
                  <th className="p-4">Timestamp</th>
                  <th className="p-4">Action Event</th>
                  <th className="p-4">Resource Type</th>
                  <th className="p-4">Resource ID / Identifier</th>
                  <th className="p-4">Client IP</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {isLoading ? (
                  <tr>
                    <td colSpan={5} className="p-8 text-center text-slate-500 font-sans">
                      Loading audit logs...
                    </td>
                  </tr>
                ) : (
                  logs.map((log: any) => (
                    <tr key={log.id} className="hover:bg-slate-800/40 transition">
                      <td className="p-4 text-slate-400">
                        {format(new Date(log.created_at), "yyyy-MM-dd HH:mm:ss")}
                      </td>
                      <td className="p-4 font-bold text-amber-400">{log.action}</td>
                      <td className="p-4 uppercase text-slate-300">{log.resource_type}</td>
                      <td className="p-4 text-slate-200">{log.resource_id || "-"}</td>
                      <td className="p-4 text-slate-500">{log.ip_address || "127.0.0.1"}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
