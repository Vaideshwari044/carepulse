import React from "react";
import { Link } from "react-router-dom";
import { getRiskBg, getRiskColor, getRiskLabel } from "../lib/utils";
import { ChevronRight, Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";

export interface PatientSummary {
  id: string;
  patient_code: string;
  display_name: string;
  monitoring_status: string;
  baseline_status: string;
  current_risk_score?: number | null;
  current_risk_state?: string | null;
  current_confidence?: number | null;
  last_update?: string | null;
}

interface Props {
  patient: PatientSummary;
}

export const PatientCard: React.FC<Props> = ({ patient }) => {
  const state = patient.current_risk_state || "INSUFFICIENT_DATA";
  const score = patient.current_risk_score !== undefined && patient.current_risk_score !== null
    ? Math.round(patient.current_risk_score)
    : "--";

  const updatedTime = patient.last_update
    ? formatDistanceToNow(new Date(patient.last_update), { addSuffix: true })
    : "No updates";

  return (
    <Link
      to={`/patients/${patient.id}`}
      className={`block p-5 rounded-xl border transition-all duration-200 hover:scale-[1.01] hover:shadow-lg ${getRiskBg(state)}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-xs font-mono font-bold text-gray-400 uppercase tracking-wider">
            {patient.patient_code}
          </div>
          <h3 className="text-lg font-bold text-gray-100">{patient.display_name}</h3>
        </div>
        <div className="text-right">
          <div className={`text-2xl font-black font-mono ${getRiskColor(state)}`}>
            {score}
            <span className="text-xs text-gray-400 font-normal">/100</span>
          </div>
        </div>
      </div>

      <div className="flex items-center justify-between pt-3 border-t border-gray-800/60 text-xs">
        <div className="flex items-center gap-2">
          <span className={`px-2 py-0.5 rounded-md font-semibold border ${getRiskBg(state)} ${getRiskColor(state)}`}>
            {getRiskLabel(state)}
          </span>
          <span className="text-gray-400 capitalize">
            Base: {patient.baseline_status}
          </span>
        </div>

        <div className="flex items-center gap-1 text-gray-400">
          <Clock className="w-3.5 h-3.5" />
          <span>{updatedTime}</span>
          <ChevronRight className="w-4 h-4 ml-1 text-gray-400" />
        </div>
      </div>
    </Link>
  );
};
