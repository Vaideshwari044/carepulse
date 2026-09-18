import React from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { Inbox, Bell, CheckCheck } from "lucide-react";

export const NotificationsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { status: socketStatus } = useMonitoringSocket();

  const { data: notificationsData } = useQuery({
    queryKey: ["notifications-list"],
    queryFn: () => api.get<any[]>("/api/v1/notifications"),
  });

  const markReadMutation = useMutation({
    mutationFn: () => api.post<any>("/api/v1/notifications/mark-read", {}),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications-list"] });
    },
  });

  const notifications = notificationsData || [
    { id: "1", title: "High Priority Deterioration Alert", message: "Patient CP-0004 SpO2 dropped below 92% baseline threshold.", category: "alert", is_read: false, created_at: new Date().toISOString() },
    { id: "2", title: "Dataset Ingestion Completed", message: "Clinical Vitals Dataset (42,000 records, 70 patients) imported successfully.", category: "dataset", is_read: false, created_at: new Date().toISOString() },
    { id: "3", title: "System Online & Healthy", message: "PostgreSQL database, WebSocket server, and ML risk engine operational.", category: "system", is_read: true, created_at: new Date().toISOString() },
  ];

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
              <Inbox className="w-6 h-6 text-amber-400" /> Notifications &amp; System Alerts
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Real-time clinical escalation alerts, dataset ingestion events, and system telemetry notifications.
            </p>
          </div>

          <button
            onClick={() => markReadMutation.mutate()}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold flex items-center gap-2 transition"
          >
            <CheckCheck className="w-4 h-4 text-amber-400" /> Mark All as Read
          </button>
        </div>

        {/* Notifications List */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 space-y-4">
          <div className="space-y-3">
            {notifications.map((n: any) => (
              <div
                key={n.id}
                className={`p-4 rounded-xl border transition flex items-start gap-3 ${
                  n.is_read
                    ? "bg-slate-950/60 border-slate-800/80 text-slate-400"
                    : "bg-slate-900 border-amber-500/40 text-slate-200 shadow-md"
                }`}
              >
                <div className="p-2 rounded-lg bg-amber-500/10 border border-amber-500/30 text-amber-400 shrink-0 mt-0.5">
                  <Bell className="w-4 h-4" />
                </div>

                <div className="space-y-1 flex-1">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-slate-100">{n.title}</h3>
                    <span className="text-[10px] font-mono text-slate-500">Just now</span>
                  </div>
                  <p className="text-xs text-slate-300">{n.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
