import React, { useState } from "react";
import { Play, Pause, RotateCcw, Square, Sliders } from "lucide-react";
import { api } from "../lib/api";

interface Props {
  patientCode: string;
  onUpdate?: () => void;
}

const SCENARIOS = [
  { id: "stable", name: "1. Stable Baseline" },
  { id: "temporary_variation", name: "2. Temporary Excursion" },
  { id: "gradual_deterioration", name: "3. Gradual Deterioration" },
  { id: "multi_parameter", name: "4. Multi-Parameter Concordance" },
  { id: "missing_data", name: "5. Missing / Quality Issue" },
  { id: "recovery", name: "6. Recovery Trend" },
];

export const SimulatorPanel: React.FC<Props> = ({ patientCode, onUpdate }) => {
  const [scenario, setScenario] = useState("stable");
  const [speed, setSpeed] = useState(1.0);
  const [loading, setLoading] = useState(false);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);

  const handleAction = async (action: "start" | "pause" | "resume" | "stop" | "restart") => {
    setLoading(true);
    try {
      await api.post(`/api/v1/monitoring/demo/${action}`, {
        patient_code: patientCode,
        scenario,
        speed,
      });
      if (action === "start" || action === "restart") setActiveScenario(scenario);
      if (action === "stop") setActiveScenario(null);
      onUpdate?.();
    } catch (err) {
      console.error("Simulator error:", err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-gray-900 border border-blue-900/40 rounded-xl p-5 shadow-elevate">
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-gray-800">
        <div className="flex items-center gap-2 text-blue-400 font-bold text-sm">
          <Sliders className="w-4 h-4" />
          <span>Interactive Simulator Control</span>
        </div>
        <span className="text-xs font-mono text-gray-400 bg-gray-800 px-2.5 py-0.5 rounded border border-gray-700">
          Target: <strong className="text-gray-200">{patientCode}</strong>
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs font-semibold text-gray-400 mb-1">Select Scenario</label>
          <select
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-gray-200 focus:outline-none focus:border-blue-500"
          >
            {SCENARIOS.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-gray-400 mb-1">
            Speed Multiplier: <span className="text-blue-400 font-mono font-bold">{speed}x</span>
          </label>
          <div className="flex items-center gap-2">
            {[1, 5, 10].map((sp) => (
              <button
                key={sp}
                onClick={() => setSpeed(sp)}
                className={`flex-1 py-1.5 rounded-lg text-xs font-mono font-bold border transition-colors ${
                  speed === sp
                    ? "bg-blue-600 text-white border-blue-500"
                    : "bg-gray-950 text-gray-400 border-gray-800 hover:bg-gray-800"
                }`}
              >
                {sp}x
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <button
          onClick={() => handleAction("start")}
          disabled={loading}
          className="flex-1 py-2 px-4 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-semibold text-xs flex items-center justify-center gap-1.5 transition-colors disabled:opacity-50"
        >
          <Play className="w-3.5 h-3.5 fill-current" /> Start Simulation
        </button>

        <button
          onClick={() => handleAction("pause")}
          disabled={loading}
          className="py-2 px-3 bg-amber-600/20 hover:bg-amber-600/30 text-amber-300 border border-amber-500/40 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
        >
          <Pause className="w-3.5 h-3.5" /> Pause
        </button>

        <button
          onClick={() => handleAction("restart")}
          disabled={loading}
          className="py-2 px-3 bg-blue-600/20 hover:bg-blue-600/30 text-blue-300 border border-blue-500/40 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
        >
          <RotateCcw className="w-3.5 h-3.5" /> Restart
        </button>

        <button
          onClick={() => handleAction("stop")}
          disabled={loading}
          className="py-2 px-3 bg-red-600/20 hover:bg-red-600/30 text-red-300 border border-red-500/40 rounded-lg text-xs font-semibold flex items-center justify-center gap-1 transition-colors disabled:opacity-50"
        >
          <Square className="w-3.5 h-3.5" /> Stop
        </button>
      </div>

      {activeScenario && (
        <div className="mt-3 pt-3 border-t border-gray-800 flex items-center gap-2 text-xs text-emerald-400 font-mono">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
          <span>Active: {SCENARIOS.find((s) => s.id === activeScenario)?.name} ({speed}x)</span>
        </div>
      )}
    </div>
  );
};
