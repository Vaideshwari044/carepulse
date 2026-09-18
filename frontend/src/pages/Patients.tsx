import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { Users, Search, Filter, ArrowRight, Plus, Edit2, Archive, CheckCircle2, X } from "lucide-react";

export const PatientsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { status: socketStatus } = useMonitoringSocket();
  const [search, setSearch] = useState("");
  const [riskFilter, setRiskFilter] = useState("ALL");
  const [statusFilter, setStatusFilter] = useState("active");

  // Modal State for Patient Form
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingPatient, setEditingPatient] = useState<any | null>(null);
  const [patientCodeInput, setPatientCodeInput] = useState("");
  const [displayNameInput, setDisplayNameInput] = useState("");
  const [monitoringStatusInput, setMonitoringStatusInput] = useState("active");
  const [formError, setFormError] = useState("");

  const { data: patientsData, isLoading } = useQuery({
    queryKey: ["patients-list-page", search, riskFilter, statusFilter],
    queryFn: () => {
      let q = `/api/v1/patients?size=50`;
      if (statusFilter !== "ALL") q += `&monitoring_status=${statusFilter}`;
      return api.get<any>(q);
    },
  });

  // Create Patient Mutation
  const createPatientMutation = useMutation({
    mutationFn: () =>
      api.post<any>("/api/v1/patients", {
        patient_code: patientCodeInput.trim() || undefined,
        display_name: displayNameInput.trim(),
        monitoring_status: monitoringStatusInput,
      }),
    onSuccess: () => {
      setIsModalOpen(false);
      resetForm();
      queryClient.invalidateQueries({ queryKey: ["patients-list-page"] });
    },
    onError: (err: any) => {
      setFormError(err?.message || "Failed to create patient record.");
    },
  });

  // Edit Patient Mutation
  const updatePatientMutation = useMutation({
    mutationFn: () =>
      api.put<any>(`/api/v1/patients/${editingPatient.id}`, {
        display_name: displayNameInput.trim(),
        monitoring_status: monitoringStatusInput,
      }),
    onSuccess: () => {
      setIsModalOpen(false);
      resetForm();
      queryClient.invalidateQueries({ queryKey: ["patients-list-page"] });
    },
    onError: (err: any) => {
      setFormError(err?.message || "Failed to update patient record.");
    },
  });

  // Archive Patient Mutation
  const archivePatientMutation = useMutation({
    mutationFn: (id: string) => api.delete<void>(`/api/v1/patients/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["patients-list-page"] });
    },
  });

  const resetForm = () => {
    setEditingPatient(null);
    setPatientCodeInput("");
    setDisplayNameInput("");
    setMonitoringStatusInput("active");
    setFormError("");
  };

  const openAddModal = () => {
    resetForm();
    setIsModalOpen(true);
  };

  const openEditModal = (p: any) => {
    resetForm();
    setEditingPatient(p);
    setPatientCodeInput(p.patient_code);
    setDisplayNameInput(p.display_name);
    setMonitoringStatusInput(p.monitoring_status);
    setIsModalOpen(true);
  };

  const patients = patientsData?.patients || [];

  const filteredPatients = patients.filter((p: any) => {
    if (search) {
      const s = search.toLowerCase();
      const matchName = p.display_name.toLowerCase().includes(s);
      const matchCode = p.patient_code.toLowerCase().includes(s);
      if (!matchName && !matchCode) return false;
    }
    if (riskFilter !== "ALL") {
      if ((p.current_risk_state || "STABLE") !== riskFilter) return false;
    }
    return true;
  });

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
              <Users className="w-6 h-6 text-amber-400" /> Patient Registry &amp; Directory
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Manage registered patients, monitor baseline status, and review active clinical risk states.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <span className="px-3 py-1 bg-amber-500/10 text-amber-400 border border-amber-500/30 rounded-full text-xs font-semibold">
              {filteredPatients.length} Patients
            </span>
            <button
              onClick={openAddModal}
              className="px-4 py-2 bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold rounded-xl text-xs flex items-center gap-1.5 transition shadow-lg shadow-amber-500/20"
            >
              <Plus className="w-4 h-4 stroke-[3]" /> Add Patient
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 flex flex-col md:flex-row items-center gap-4">
          <div className="relative flex-1 w-full">
            <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search by Patient Code (e.g. CP-0001, P101) or Display Name..."
              className="w-full bg-slate-950 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
            />
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto">
            <div className="flex items-center gap-1.5 text-xs text-slate-400">
              <Filter className="w-3.5 h-3.5 text-amber-400" />
              <span>Risk State:</span>
            </div>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-amber-500"
            >
              <option value="ALL">All Risk States</option>
              <option value="STABLE">Stable</option>
              <option value="EARLY_CHANGE">Early Change</option>
              <option value="DETERIORATION_WARNING">Deterioration Warning</option>
              <option value="HIGH_PRIORITY">High Priority</option>
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-amber-500"
            >
              <option value="ALL">All Statuses</option>
              <option value="active">Active Monitoring</option>
              <option value="paused">Paused</option>
              <option value="discharged">Discharged</option>
            </select>
          </div>
        </div>

        {/* Patients Grid / Table */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 uppercase font-mono border-b border-slate-800">
                <tr>
                  <th className="p-4">Patient Code</th>
                  <th className="p-4">Display Name</th>
                  <th className="p-4">Monitoring Status</th>
                  <th className="p-4">Baseline Status</th>
                  <th className="p-4">Current Risk Score</th>
                  <th className="p-4">Current Risk State</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {isLoading ? (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-500">
                      Loading patient records from database...
                    </td>
                  </tr>
                ) : filteredPatients.length > 0 ? (
                  filteredPatients.map((p: any) => (
                    <tr key={p.id} className="hover:bg-slate-800/40 transition">
                      <td className="p-4 font-mono font-bold text-amber-400">{p.patient_code}</td>
                      <td className="p-4 font-semibold text-slate-200">{p.display_name}</td>
                      <td className="p-4">
                        <span className="px-2.5 py-1 bg-slate-800 border border-slate-700 rounded-full text-[10px] uppercase font-bold text-slate-300">
                          {p.monitoring_status}
                        </span>
                      </td>
                      <td className="p-4">
                        <span className="px-2.5 py-1 bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded-full text-[10px] font-bold">
                          {p.baseline_status || "collecting"}
                        </span>
                      </td>
                      <td className="p-4 font-mono font-bold text-slate-200">
                        {p.current_risk_score !== null && p.current_risk_score !== undefined
                          ? Math.round(p.current_risk_score)
                          : "-"}
                      </td>
                      <td className="p-4">
                        <span
                          className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${
                            p.current_risk_state === "HIGH_PRIORITY"
                              ? "bg-red-500/20 text-red-400 border border-red-500/30"
                              : p.current_risk_state === "DETERIORATION_WARNING"
                              ? "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                              : p.current_risk_state === "EARLY_CHANGE"
                              ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30"
                              : "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                          }`}
                        >
                          {p.current_risk_state || "STABLE"}
                        </span>
                      </td>
                      <td className="p-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Link
                            to={`/patients/${p.patient_code}`}
                            className="px-2.5 py-1 bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 rounded-lg font-semibold transition inline-flex items-center gap-1"
                          >
                            View <ArrowRight className="w-3 h-3" />
                          </Link>

                          <button
                            onClick={() => openEditModal(p)}
                            className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                            title="Edit Patient"
                          >
                            <Edit2 className="w-3.5 h-3.5" />
                          </button>

                          <button
                            onClick={() => archivePatientMutation.mutate(p.id)}
                            className="p-1.5 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 rounded-lg transition"
                            title="Archive Patient"
                          >
                            <Archive className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={7} className="p-8 text-center text-slate-500">
                      No matching patients found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Patient Form Modal (Add & Edit) */}
        {isModalOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                  <Users className="w-5 h-5 text-amber-400" />
                  {editingPatient ? "Edit Patient Record" : "Add New Patient Record"}
                </h3>
                <button onClick={() => setIsModalOpen(false)} className="text-slate-400 hover:text-slate-200">
                  <X className="w-5 h-5" />
                </button>
              </div>

              {formError && (
                <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-xs text-red-300 font-medium">
                  {formError}
                </div>
              )}

              <div className="space-y-3 text-xs">
                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Patient Code (e.g. CP-0071, P106)</label>
                  <input
                    type="text"
                    value={patientCodeInput}
                    disabled={!!editingPatient}
                    onChange={(e) => setPatientCodeInput(e.target.value)}
                    placeholder="Auto-generated if left empty"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500 disabled:opacity-50"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Patient Display Name / Identifier</label>
                  <input
                    type="text"
                    required
                    value={displayNameInput}
                    onChange={(e) => setDisplayNameInput(e.target.value)}
                    placeholder="e.g. Patient 106 — Telemetry Monitoring"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500"
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-semibold mb-1">Monitoring Status</label>
                  <select
                    value={monitoringStatusInput}
                    onChange={(e) => setMonitoringStatusInput(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-amber-500"
                  >
                    <option value="active">Active Monitoring</option>
                    <option value="paused">Paused</option>
                    <option value="discharged">Discharged</option>
                  </select>
                </div>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 font-semibold rounded-xl text-xs transition"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => (editingPatient ? updatePatientMutation.mutate() : createPatientMutation.mutate())}
                  disabled={!displayNameInput.trim() || createPatientMutation.isPending || updatePatientMutation.isPending}
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-xl text-xs transition disabled:opacity-50 flex items-center gap-1.5"
                >
                  <CheckCircle2 className="w-4 h-4 stroke-[3]" />
                  {editingPatient ? "Save Changes" : "Create Patient"}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
};
