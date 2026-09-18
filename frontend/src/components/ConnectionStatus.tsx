import React from "react";
import { ConnectionStatus as StatusType } from "../hooks/useMonitoringSocket";

interface Props {
  status: StatusType;
}

export const ConnectionStatusBadge: React.FC<Props> = ({ status }) => {
  const config = {
    LIVE: { color: "bg-emerald-500", text: "LIVE MONITORING", border: "border-emerald-500/30 text-emerald-400" },
    RECONNECTING: { color: "bg-amber-500 animate-ping", text: "RECONNECTING...", border: "border-amber-500/30 text-amber-400" },
    OFFLINE: { color: "bg-red-500", text: "OFFLINE", border: "border-red-500/30 text-red-400" },
  }[status];

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border bg-gray-900/80 text-xs font-mono font-semibold ${config.border}`}>
      <span className={`w-2 h-2 rounded-full ${config.color}`} />
      <span>{config.text}</span>
    </div>
  );
};
