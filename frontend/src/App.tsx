import React, { useEffect, lazy, Suspense } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "./store/auth";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { ErrorBoundary } from "./components/ErrorBoundary";

// Lazy load secondary routes for code splitting
const PatientsPage = lazy(() => import("./pages/Patients").then(m => ({ default: m.PatientsPage })));
const PatientDetail = lazy(() => import("./pages/PatientDetail").then(m => ({ default: m.PatientDetail })));
const LiveMonitoringPage = lazy(() => import("./pages/LiveMonitoring").then(m => ({ default: m.LiveMonitoringPage })));
const AlertsPage = lazy(() => import("./pages/Alerts").then(m => ({ default: m.AlertsPage })));
const AnalyticsPage = lazy(() => import("./pages/Analytics").then(m => ({ default: m.AnalyticsPage })));
const TrendsPage = lazy(() => import("./pages/Trends").then(m => ({ default: m.TrendsPage })));
const DataPipelinePage = lazy(() => import("./pages/DataPipeline").then(m => ({ default: m.DataPipelinePage })));
const DatasetExplorer = lazy(() => import("./pages/DatasetExplorer").then(m => ({ default: m.DatasetExplorer })));
const DatasetQuality = lazy(() => import("./pages/DatasetQuality").then(m => ({ default: m.DatasetQuality })));
const DatasetManagement = lazy(() => import("./pages/DatasetManagement").then(m => ({ default: m.DatasetManagement })));
const HealthAssistant = lazy(() => import("./pages/HealthAssistant").then(m => ({ default: m.HealthAssistant })));
const ReportsPage = lazy(() => import("./pages/Reports").then(m => ({ default: m.ReportsPage })));
const TasksPage = lazy(() => import("./pages/TasksPage").then(m => ({ default: m.TasksPage })));
const NotificationsPage = lazy(() => import("./pages/NotificationsPage").then(m => ({ default: m.NotificationsPage })));
const AuditLogsPage = lazy(() => import("./pages/AuditLogsPage").then(m => ({ default: m.AuditLogsPage })));
const AdminDashboard = lazy(() => import("./pages/AdminDashboard").then(m => ({ default: m.AdminDashboard })));
const SettingsPage = lazy(() => import("./pages/SettingsPage").then(m => ({ default: m.SettingsPage })));

const PageLoader: React.FC = () => (
  <div className="min-h-screen bg-slate-950 flex items-center justify-center">
    <div className="flex flex-col items-center gap-3">
      <div className="w-8 h-8 border-2 border-amber-400 border-t-transparent rounded-full animate-spin" />
      <span className="text-xs font-mono text-amber-400/80">Loading CarePulse Module...</span>
    </div>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 10000,
      gcTime: 300000,
    },
  },
});


const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isAuthenticated, restore } = useAuthStore();

  useEffect(() => {
    restore();
  }, [restore]);

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
};

export const App: React.FC = () => {
  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <Suspense fallback={<PageLoader />}>
            <Routes>
              <Route path="/login" element={<Login />} />

            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <Dashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/patients"
              element={
                <ProtectedRoute>
                  <PatientsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/patients/:id"
              element={
                <ProtectedRoute>
                  <PatientDetail />
                </ProtectedRoute>
              }
            />
            <Route
              path="/live-monitoring"
              element={
                <ProtectedRoute>
                  <LiveMonitoringPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/alerts"
              element={
                <ProtectedRoute>
                  <AlertsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/analytics"
              element={
                <ProtectedRoute>
                  <AnalyticsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/trends"
              element={
                <ProtectedRoute>
                  <TrendsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/data-pipeline"
              element={
                <ProtectedRoute>
                  <DataPipelinePage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dataset-explorer"
              element={
                <ProtectedRoute>
                  <DatasetExplorer />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dataset-quality"
              element={
                <ProtectedRoute>
                  <DatasetQuality />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dataset-management"
              element={
                <ProtectedRoute>
                  <DatasetManagement />
                </ProtectedRoute>
              }
            />
            <Route
              path="/health-assistant"
              element={
                <ProtectedRoute>
                  <HealthAssistant />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute>
                  <ReportsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/tasks"
              element={
                <ProtectedRoute>
                  <TasksPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/notifications"
              element={
                <ProtectedRoute>
                  <NotificationsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/audit-logs"
              element={
                <ProtectedRoute>
                  <AuditLogsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/admin"
              element={
                <ProtectedRoute>
                  <AdminDashboard />
                </ProtectedRoute>
              }
            />
            <Route
              path="/settings"
              element={
                <ProtectedRoute>
                  <SettingsPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>

      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default App;
