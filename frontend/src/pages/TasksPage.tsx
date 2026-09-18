import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { AppLayout } from "../components/layout/AppLayout";
import { useMonitoringSocket } from "../hooks/useMonitoringSocket";
import { CheckSquare, Plus, CheckCircle2, Clock, UserCheck } from "lucide-react";

export const TasksPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { status: socketStatus } = useMonitoringSocket();
  const [newTitle, setNewTitle] = useState("");
  const [newPriority, setNewPriority] = useState("medium");

  const { data: tasksData } = useQuery({
    queryKey: ["tasks-list"],
    queryFn: () => api.get<any[]>("/api/v1/tasks"),
  });

  const createTaskMutation = useMutation({
    mutationFn: () =>
      api.post<any>("/api/v1/tasks", {
        title: newTitle,
        priority: newPriority,
      }),
    onSuccess: () => {
      setNewTitle("");
      queryClient.invalidateQueries({ queryKey: ["tasks-list"] });
    },
  });

  const updateTaskMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: string }) =>
      api.patch<any>(`/api/v1/tasks/${id}`, { status }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks-list"] });
    },
  });

  const tasks = tasksData || [
    { id: "1", title: "Review SpO2 baseline drift for Patient CP-0004", priority: "urgent", status: "pending", created_at: new Date().toISOString() },
    { id: "2", title: "Acknowledge deterioration warning alert on Ward B", priority: "high", status: "pending", created_at: new Date().toISOString() },
    { id: "3", title: "Validate dataset ingestion mappings for ICU Ward 3", priority: "medium", status: "completed", created_at: new Date().toISOString() },
  ];

  return (
    <AppLayout socketStatus={socketStatus}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h1 className="text-2xl font-black text-slate-100 flex items-center gap-2">
              <CheckSquare className="w-6 h-6 text-amber-400" /> Clinician Tasks &amp; Clinical Workflow
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Track alert reviews, follow-up evaluations, report sign-offs, and dataset quality tasks.
            </p>
          </div>
        </div>

        {/* Quick Task Creation Form */}
        <div className="bg-slate-900/90 p-4 rounded-xl border border-slate-800 flex flex-col md:flex-row items-center gap-3">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            placeholder="Add new clinician task (e.g. Review Patient CP-0002 baseline)..."
            className="flex-1 w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-amber-500"
          />

          <select
            value={newPriority}
            onChange={(e) => setNewPriority(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:border-amber-500"
          >
            <option value="low">Low Priority</option>
            <option value="medium">Medium Priority</option>
            <option value="high">High Priority</option>
            <option value="urgent">Urgent</option>
          </select>

          <button
            onClick={() => createTaskMutation.mutate()}
            disabled={!newTitle.trim() || createTaskMutation.isPending}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs flex items-center gap-1.5 transition disabled:opacity-50"
          >
            <Plus className="w-4 h-4" /> Add Task
          </button>
        </div>

        {/* Tasks List */}
        <div className="bg-slate-900/90 rounded-2xl border border-slate-800 p-6 space-y-4">
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2 border-b border-slate-800 pb-3">
            <UserCheck className="w-5 h-5 text-amber-400" /> Assigned Clinical Tasks
          </h2>

          <div className="space-y-3">
            {tasks.map((task: any) => (
              <div
                key={task.id}
                className="p-4 bg-slate-950/80 rounded-xl border border-slate-800 flex items-center justify-between gap-4"
              >
                <div className="flex items-center gap-3">
                  <button
                    onClick={() =>
                      updateTaskMutation.mutate({
                        id: task.id,
                        status: task.status === "completed" ? "pending" : "completed",
                      })
                    }
                    className={`w-5 h-5 rounded border flex items-center justify-center transition ${
                      task.status === "completed"
                        ? "bg-emerald-500 border-emerald-500 text-slate-950"
                        : "border-slate-700 hover:border-amber-500"
                    }`}
                  >
                    {task.status === "completed" && <CheckCircle2 className="w-4 h-4 stroke-[3]" />}
                  </button>

                  <div>
                    <span
                      className={`text-xs font-semibold ${
                        task.status === "completed" ? "line-through text-slate-500" : "text-slate-200"
                      }`}
                    >
                      {task.title}
                    </span>
                    <div className="flex items-center gap-2 mt-1">
                      <span
                        className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase ${
                          task.priority === "urgent" || task.priority === "high"
                            ? "bg-red-500/20 text-red-400 border border-red-500/30"
                            : "bg-amber-500/20 text-amber-400 border border-amber-500/30"
                        }`}
                      >
                        {task.priority}
                      </span>
                      <span className="text-[10px] text-slate-500 flex items-center gap-1 font-mono">
                        <Clock className="w-3 h-3" /> {task.status}
                      </span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() =>
                    updateTaskMutation.mutate({
                      id: task.id,
                      status: task.status === "completed" ? "pending" : "completed",
                    })
                  }
                  className="text-xs text-amber-400 hover:underline font-medium"
                >
                  {task.status === "completed" ? "Reopen" : "Mark Complete"}
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
};
