import React from "react";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { useAuthStore } from "../store/auth";
import { Settings, User, Info } from "lucide-react";

export const SettingsPage: React.FC = () => {
  const { user } = useAuthStore();
  const { status: socketStatus } = useMonitoringSocket();

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
            <Settings className="w-6 h-6 text-amber-400" /> System &amp; User Settings
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Configure clinician preferences, security credentials, notification channels, and visual themes.
          </p>
        </div>

        {/* Profile Card */}
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 space-y-4 shadow-xl">
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <User className="w-5 h-5 text-amber-400" /> User Profile &amp; Role Credentials
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="block text-slate-400 mb-1">Display Name</label>
              <input
                type="text"
                readOnly
                value={user?.display_name || "Dr. Demo Clinician"}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Hospital Email</label>
              <input
                type="email"
                readOnly
                value={user?.email || "clinician@carepulse.health"}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Assigned Role</label>
              <input
                type="text"
                readOnly
                value={user?.role?.toUpperCase() || "CLINICIAN"}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-amber-400 font-bold font-mono"
              />
            </div>
            <div>
              <label className="block text-slate-400 mb-1">Security Authentication</label>
              <input
                type="text"
                readOnly
                value="JWT Bearer token + Refresh Token (HS256)"
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-300 font-mono"
              />
            </div>
          </div>
        </div>

        {/* System Information Card */}
        <div className="bg-slate-900/90 rounded-2xl p-6 border border-slate-800 space-y-4 shadow-xl">
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <Info className="w-5 h-5 text-amber-400" /> CarePulse System Information
          </h2>

          <div className="space-y-2 text-xs text-slate-300">
            <div><strong className="text-amber-400">Application Title:</strong> CarePulse Real-Time Healthcare System</div>
            <div><strong className="text-amber-400">Environment:</strong> Clinical Research Mode</div>
            <div><strong className="text-amber-400">Primary Color Theme:</strong> Champagne / Gold Healthcare Palette</div>
            <div><strong className="text-amber-400">Safety Notice:</strong> Synthetic &amp; replayed datasets only. Not clinically validated. Not a medical device.</div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
