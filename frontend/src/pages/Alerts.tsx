import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { AlertList, AlertData } from "../components/AlertList";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { Bell, Filter, RefreshCw } from "lucide-react";

export const AlertsPage: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  const { data: alertsData, refetch, isFetching } = useQuery({
    queryKey: ["all-alerts", statusFilter],
    queryFn: () => {
      const q = statusFilter !== "ALL" ? `?alert_status=${statusFilter}` : "";
      return api.get<AlertData[]>(`/api/v1/alerts${q}`);
    },
    refetchInterval: 5000,
  });

  const { status: socketStatus } = useMonitoringSocket(() => {
    refetch();
  });

  const handleAction = async (alertId: string, action: string) => {
    try {
      await api.post(`/api/v1/alerts/${alertId}/actions`, { action });
      refetch();
    } catch (err) {
      console.error("Alert action error:", err);
    }
  };

  const alerts = alertsData || [];

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-gray-100 flex items-center gap-2">
              <Bell className="w-6 h-6 text-amber-400" /> Alert Center
            </h1>
            <p className="text-xs text-gray-400 mt-1">
              Priority-ranked physiological deterioration warnings &amp; clinical alerts
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2 bg-gray-900 border border-gray-700 rounded-lg px-3 py-1.5 text-xs text-gray-300">
              <Filter className="w-3.5 h-3.5 text-gray-400" />
              <span>Filter:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-transparent text-gray-100 font-bold focus:outline-none"
              >
                <option value="ALL" className="bg-gray-900">All Statuses</option>
                <option value="OPEN" className="bg-gray-900">OPEN</option>
                <option value="ACKNOWLEDGED" className="bg-gray-900">ACKNOWLEDGED</option>
                <option value="SNOOZED" className="bg-gray-900">SNOOZED</option>
                <option value="RESOLVED" className="bg-gray-900">RESOLVED</option>
              </select>
            </div>

            <button
              onClick={() => refetch()}
              className="p-2 bg-gray-900 border border-gray-700 hover:bg-gray-800 rounded-lg text-gray-300 transition-colors"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
            </button>
          </div>
        </div>

        <AlertList alerts={alerts} onAction={handleAction} />
      </div>
    </AppLayout>
  );
};
