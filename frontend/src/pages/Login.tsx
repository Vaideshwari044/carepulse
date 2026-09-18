import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "../store/auth";
import { Activity, ShieldCheck, Sparkles, Lock, Mail, UserCheck } from "lucide-react";

export const Login: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuthStore();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const executeLogin = async (loginEmail: string, loginPw: string) => {
    setErrorMsg("");
    setLoading(true);
    try {
      await login(loginEmail, loginPw);
      navigate("/dashboard");
    } catch (err: any) {
      if (err?.status === 401) {
        setErrorMsg("Email or password is incorrect.");
      } else if (err?.status >= 500) {
        setErrorMsg("CarePulse services are temporarily unavailable. Please try again.");
      } else {
        setErrorMsg("Unable to connect to CarePulse services.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeLogin(email, password);
  };

  const handleDemoClick = (role: "admin" | "clinician") => {
    const demoEmail = role === "admin" ? "admin@carepulse.health" : "clinician@carepulse.health";
    const demoPw = role === "admin" ? "CarePulseAdmin!23" : "CarePulseClinician!23";
    setEmail(demoEmail);
    setPassword(demoPw);
    executeLogin(demoEmail, demoPw);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-between p-4 sm:p-6 lg:p-8 font-sans">
      {/* Background Subtle Gradient */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-amber-950/20 via-slate-950 to-slate-950 pointer-events-none" />

      {/* Header Branding */}
      <div className="max-w-7xl mx-auto w-full flex items-center justify-between relative z-10">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-2xl bg-gradient-to-br from-amber-400 via-amber-500 to-amber-700 flex items-center justify-center shadow-lg shadow-amber-500/20">
            <Activity className="w-6 h-6 text-slate-950 stroke-[2.5]" />
          </div>
          <div>
            <span className="font-black text-xl tracking-tight bg-gradient-to-r from-amber-200 via-amber-400 to-yellow-500 bg-clip-text text-transparent uppercase">
              CARE PULSE
            </span>
          </div>
        </div>

        <div className="hidden sm:flex items-center gap-2 text-xs font-semibold text-amber-400 bg-amber-500/10 border border-amber-500/30 px-3 py-1.5 rounded-full">
          <Sparkles className="w-4 h-4" /> AI Early-Warning System
        </div>
      </div>

      {/* Main Login Card */}
      <div className="max-w-md w-full mx-auto my-auto relative z-10 space-y-6">
        <div className="bg-slate-900/90 rounded-2xl p-8 border border-slate-800 shadow-2xl space-y-6">
          <div className="text-center space-y-2">
            <h1 className="text-2xl font-black text-slate-100 tracking-tight uppercase">CARE PULSE</h1>
            <p className="text-xs font-semibold text-amber-400">
              AI-Assisted Early Warning Decision Support
            </p>
          </div>

          {/* Quick Demo Access Buttons */}
          <div className="bg-slate-950/80 p-3.5 rounded-xl border border-slate-800/80 space-y-2.5">
            <div className="text-[11px] font-bold uppercase tracking-wider text-amber-400 flex items-center justify-between">
              <span>Quick Demo Access</span>
              <UserCheck className="w-3.5 h-3.5" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => handleDemoClick("clinician")}
                disabled={loading}
                className="px-3 py-2 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg text-xs font-semibold transition text-left truncate disabled:opacity-50"
              >
                Dr. Demo Clinician
              </button>
              <button
                type="button"
                onClick={() => handleDemoClick("admin")}
                disabled={loading}
                className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition text-left truncate disabled:opacity-50"
              >
                Demo Administrator
              </button>
            </div>
          </div>

          {errorMsg && (
            <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-xl text-xs text-red-300 font-medium text-center">
              {errorMsg}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Hospital Email</label>
              <div className="relative">
                <Mail className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="clinician@carepulse.health"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-200 focus:outline-none transition"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-400 mb-1">Password</label>
              <div className="relative">
                <Lock className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full bg-slate-950 border border-slate-800 focus:border-amber-500 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-200 focus:outline-none transition"
                />
              </div>
            </div>

            <div className="flex items-center justify-between text-xs text-slate-400">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="rounded bg-slate-950 border-slate-800 text-amber-500 focus:ring-amber-500/20" />
                <span>Remember session</span>
              </label>
              <a href="#forgot" onClick={(e) => e.preventDefault()} className="text-amber-400 hover:underline">
                Forgot password?
              </a>
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded-xl text-xs uppercase tracking-wider shadow-lg shadow-amber-500/20 transition disabled:opacity-50"
            >
              {loading ? "Signing In..." : "Sign In"}
            </button>
          </form>
        </div>
      </div>

      {/* Safety Notice Footer */}
      <div className="max-w-md w-full mx-auto text-center space-y-2 relative z-10 pt-4">
        <div className="flex items-center justify-center gap-1.5 text-[11px] font-semibold text-amber-400/90">
          <ShieldCheck className="w-4 h-4" />
          <span>RESEARCH DATASET • NOT CLINICALLY VALIDATED</span>
        </div>
      </div>
    </div>
  );
};
