import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useAuthStore } from "./store/auth";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { PatientsPage } from "./pages/Patients";
import { LiveMonitoringPage } from "./pages/LiveMonitoring";
import { PatientDetail } from "./pages/PatientDetail";
import { AlertsPage } from "./pages/Alerts";
import { AnalyticsPage } from "./pages/Analytics";
import { TrendsPage } from "./pages/Trends";
import { DataPipelinePage } from "./pages/DataPipeline";
import { DatasetExplorer } from "./pages/DatasetExplorer";
import { DatasetQuality } from "./pages/DatasetQuality";
import { DatasetManagement } from "./pages/DatasetManagement";
import { HealthAssistant } from "./pages/HealthAssistant";
import { ReportsPage } from "./pages/Reports";
import { TasksPage } from "./pages/TasksPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { AuditLogsPage } from "./pages/AuditLogsPage";
import { AdminDashboard } from "./pages/AdminDashboard";
import { SettingsPage } from "./pages/SettingsPage";
import { ErrorBoundary } from "./components/ErrorBoundary";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
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
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  );
};

export default App;
