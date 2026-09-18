/** Risk state color utilities */

export type RiskState = "STABLE" | "EARLY_CHANGE" | "DETERIORATION_WARNING" | "HIGH_PRIORITY" | "RECOVERY" | "INSUFFICIENT_DATA";

export function getRiskColor(state: string | null | undefined): string {
  switch (state) {
    case "STABLE": return "text-emerald-400";
    case "EARLY_CHANGE": return "text-yellow-400";
    case "DETERIORATION_WARNING": return "text-orange-400";
    case "HIGH_PRIORITY": return "text-red-400";
    case "RECOVERY": return "text-indigo-400";
    case "INSUFFICIENT_DATA": return "text-gray-400";
    default: return "text-gray-400";
  }
}

export function getRiskBg(state: string | null | undefined): string {
  switch (state) {
    case "STABLE": return "bg-emerald-900/30 border-emerald-700";
    case "EARLY_CHANGE": return "bg-yellow-900/30 border-yellow-700";
    case "DETERIORATION_WARNING": return "bg-orange-900/30 border-orange-700";
    case "HIGH_PRIORITY": return "bg-red-900/30 border-red-700 animate-pulse";
    case "RECOVERY": return "bg-indigo-900/30 border-indigo-700";
    case "INSUFFICIENT_DATA": return "bg-gray-800 border-gray-700";
    default: return "bg-gray-800 border-gray-700";
  }
}

export function getRiskLabel(state: string | null | undefined): string {
  switch (state) {
    case "STABLE": return "Stable";
    case "EARLY_CHANGE": return "Early Change";
    case "DETERIORATION_WARNING": return "Deterioration Warning";
    case "HIGH_PRIORITY": return "High Priority";
    case "RECOVERY": return "Recovery";
    case "INSUFFICIENT_DATA": return "Insufficient Data";
    default: return "Unknown";
  }
}

export function cn(...classes: (string | false | undefined | null)[]): string {
  return classes.filter(Boolean).join(" ");
}
