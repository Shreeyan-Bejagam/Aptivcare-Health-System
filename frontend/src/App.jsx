







import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import HomePage from "./pages/HomePage.jsx";
import CallPage from "./pages/CallPage.jsx";
import WsCallPage from "./pages/WsCallPage.jsx";
import SummaryPage from "./pages/SummaryPage.jsx";
import AppointmentsPage from "./pages/AppointmentsPage.jsx";
import Toast from "./components/Toast.jsx";

export default function App() {
  return (
    <BrowserRouter
      future={{
        v7_startTransition: true,
        v7_relativeSplatPath: true
      }}>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/call" element={<CallPage />} />
        <Route path="/call-ws" element={<WsCallPage />} />
        <Route path="/summary/:sessionId" element={<SummaryPage />} />
        <Route path="/appointments" element={<AppointmentsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <Toast />
    </BrowserRouter>);

}