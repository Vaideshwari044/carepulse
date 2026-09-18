import React from "react";
import { formatDistanceToNow } from "date-fns";
import { AlertCircle, CheckCircle2, Eye, BellOff, Clock } from "lucide-react";

export interface AlertData {
  id: string;
  patient_id: string;
  alert_type: string;
  status: "OPEN" | "ACKNOWLEDGED" | "REVIEWED" | "SNOOZED" | "ESCALATED" | "RESOLVED";
  risk_level: string;
  risk_score: number;
  priority: number;
  contributing_parameters: string[];
  message: string;
  created_at: string;
}

interface Props {
  alerts: AlertData[];
  onAction?: (alertId: string, action: string) => void;
}

export const AlertList: React.FC<Props> = ({ alerts, onAction }) => {
  if (alerts.length === 0) {
    return (
      <div className="p-8 text-center text-gray-400 bg-gray-900 border border-gray-800 rounded-xl">
        <CheckCircle2 className="w-10 h-10 mx-auto mb-2 text-emerald-500 opacity-80" />
        <div className="font-semibold text-gray-200">No active alerts</div>
        <div className="text-xs text-gray-400 mt-1">All monitored patients within parameters.</div>
      </div>
    );
  }

  const statusBadge = (status: string) => {
    const cfg: Record<string, string> = {
      OPEN: "bg-red-900/40 border-red-700 text-red-300",
      ACKNOWLEDGED: "bg-amber-900/40 border-amber-700 text-amber-300",
      REVIEWED: "bg-blue-900/40 border-blue-700 text-blue-300",
      SNOOZED: "bg-purple-900/40 border-purple-700 text-purple-300",
      ESCALATED: "bg-orange-900/40 border-orange-700 text-orange-300",
      RESOLVED: "bg-gray-800 border-gray-700 text-gray-400",
    };
    return (
      <span className={`px-2 py-0.5 text-xs font-mono font-bold rounded border ${cfg[status] || "bg-gray-800 text-gray-400"}`}>
        {status}
      </span>
    );
  };

  return (
    <div className="space-y-3">
      {alerts.map((alert) => (
        <div
          key={alert.id}
          className="bg-gray-900 border border-gray-800 hover:border-gray-700 rounded-xl p-4 transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
        >
          <div className="flex items-start gap-3">
            <AlertCircle className={`w-5 h-5 shrink-0 mt-0.5 ${alert.risk_score >= 75 ? "text-red-400" : "text-amber-400"}`} />
            <div>
              <div className="flex items-center gap-2 mb-1 flex-wrap">
                {statusBadge(alert.status)}
                <span className="text-xs font-mono font-bold text-gray-400">
                  Prio: {(alert.priority * 100).toFixed(0)}
                </span>
                <span className="text-xs text-gray-400 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {formatDistanceToNow(new Date(alert.created_at), { addSuffix: true })}
                </span>
              </div>
              <div className="text-sm font-semibold text-gray-200">{alert.message}</div>
              <div className="text-xs text-gray-400 mt-1">
                Params: <span className="text-gray-300 font-mono">{alert.contributing_parameters.join(", ")}</span>
              </div>
            </div>
          </div>

          {alert.status !== "RESOLVED" && onAction && (
            <div className="flex items-center gap-2 shrink-0 self-end md:self-center">
              {alert.status === "OPEN" && (
                <button
                  onClick={() => onAction(alert.id, "acknowledge")}
                  className="px-3 py-1.5 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
                >
                  <Eye className="w-3.5 h-3.5" /> Acknowledge
                </button>
              )}
              <button
                onClick={() => onAction(alert.id, "resolve")}
                className="px-3 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-300 border border-emerald-500/40 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Resolve
              </button>
              <button
                onClick={() => onAction(alert.id, "snooze")}
                className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 text-gray-300 border border-gray-700 rounded-lg text-xs font-semibold flex items-center gap-1 transition-colors"
              >
                <BellOff className="w-3.5 h-3.5" /> Snooze
              </button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
};
