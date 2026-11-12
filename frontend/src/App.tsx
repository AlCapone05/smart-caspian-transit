import { Navigate, Route, Routes } from "react-router-dom";
import { AlternativesPage } from "./pages/AlternativesPage";
import { AnalyticsPage } from "./pages/AnalyticsPage";
import { ComparePage } from "./pages/ComparePage";
import { DocumentsPage } from "./pages/DocumentsPage";
import { OverviewPage } from "./pages/OverviewPage";
import { SettingsPage } from "./pages/SettingsPage";
import { ShipmentDetailPage } from "./pages/ShipmentDetailPage";
import { ShipmentsPage } from "./pages/ShipmentsPage";
export default function App() {
  return (
    <Routes>
      <Route path="/" element={<OverviewPage />} />
      <Route path="/shipments" element={<ShipmentsPage />} />
      <Route path="/shipments/:id" element={<ShipmentDetailPage />} />
      <Route path="/shipments/:id/alternatives" element={<AlternativesPage />} />
      <Route path="/compare" element={<ComparePage />} />
      <Route path="/documents" element={<DocumentsPage />} />
      <Route path="/tracker" element={<Navigate to="/" replace />} />
      <Route path="/analytics" element={<AnalyticsPage />} />
      <Route path="/settings" element={<SettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
