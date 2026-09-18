import React from "react";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  CartesianGrid,
} from "recharts";
import { format } from "date-fns";

export interface VitalPoint {
  recorded_at: string;
  value: number | null;
}

interface Props {
  title: string;
  unit: string;
  data: VitalPoint[];
  baselineMean?: number | null;
  normalMin?: number;
  normalMax?: number;
  color?: string;
}

export const VitalChart: React.FC<Props> = ({
  title,
  unit,
  data,
  baselineMean,
  normalMin,
  normalMax,
  color = "#3B82F6",
}) => {
  const chartData = data
    .filter((d) => d.value !== null)
    .map((d) => ({
      time: format(new Date(d.recorded_at), "HH:mm:ss"),
      val: d.value,
    }))
    .reverse();

  const latestVal = chartData.length > 0 ? chartData[chartData.length - 1].val : null;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <div>
          <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">{title}</span>
          <div className="text-2xl font-black font-mono text-gray-100">
            {latestVal !== null ? latestVal : "--"}
            <span className="text-xs text-gray-400 font-normal ml-1">{unit}</span>
          </div>
        </div>
        {baselineMean !== undefined && baselineMean !== null && (
          <div className="text-right text-xs text-gray-400 font-mono">
            <span>Base: {baselineMean.toFixed(1)} {unit}</span>
          </div>
        )}
      </div>

      <div className="h-36 w-full mt-2">
        {chartData.length > 0 ? (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" opacity={0.5} />
              <XAxis dataKey="time" stroke="#9CA3AF" fontSize={10} tickLine={false} />
              <YAxis stroke="#9CA3AF" fontSize={10} domain={["auto", "auto"]} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: "#1F2937", borderColor: "#374151", borderRadius: "0.5rem", fontSize: "12px" }}
                itemStyle={{ color: "#F3F4F6" }}
              />
              {baselineMean !== undefined && baselineMean !== null && (
                <ReferenceLine y={baselineMean} stroke="#6B7280" strokeDasharray="4 4" label={{ value: "Baseline", fill: "#9CA3AF", fontSize: 10, position: "insideTopRight" }} />
              )}
              {normalMin !== undefined && (
                <ReferenceLine y={normalMin} stroke="#EF4444" strokeDasharray="2 2" opacity={0.6} />
              )}
              {normalMax !== undefined && (
                <ReferenceLine y={normalMax} stroke="#EF4444" strokeDasharray="2 2" opacity={0.6} />
              )}
              <Line type="monotone" dataKey="val" stroke={color} strokeWidth={2} dot={false} activeDot={{ r: 4 }} />
            </LineChart>
          </ResponsiveContainer>
        ) : (
          <div className="h-full flex items-center justify-center text-xs text-amber-500/80 font-mono italic">
            Not available in source dataset
          </div>

        )}
      </div>
    </div>
  );
};
