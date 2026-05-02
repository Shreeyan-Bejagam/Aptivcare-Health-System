








import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL,
  timeout: 15000,
  headers: { "Content-Type": "application/json" }
});

function pushToast(detail) {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new CustomEvent("app:toast", { detail }));
}

function formatErrorDetail(error) {
  const d = error?.response?.data?.detail;
  if (typeof d === "string" && d.trim()) return d;
  if (Array.isArray(d) && d.length) {
    try {
      return d.map((x) => x?.msg || JSON.stringify(x)).join(" · ");
    } catch {
      return null;
    }
  }
  return null;
}

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 429) {
      pushToast({ type: "warn", message: "Too many requests — please slow down." });
    } else if (status === 503) {

    } else if (status >= 500) {
      const detail = formatErrorDetail(error);
      pushToast({
        type: "error",
        message: detail || "Server error — please retry in a moment."
      });
    } else if (error.code === "ECONNABORTED") {
      pushToast({ type: "error", message: "Network timeout — check your connection." });
    } else if (!error.response) {
      pushToast({
        type: "error",
        message: "Could not reach the server. Is the backend running?"
      });
    }
    return Promise.reject(error);
  }
);


export async function createSession() {
  const { data } = await api.post("/api/sessions");
  return data;
}


export async function createWebSocketVoiceSession() {
  const { data } = await api.post("/api/sessions/websocket-voice");
  return data;
}


export async function getSummary(sessionId) {
  const { data } = await api.get(`/api/sessions/${encodeURIComponent(sessionId)}/summary`);
  return data;
}


export async function listAppointments(phone, { includeCancelled = false } = {}) {
  const { data } = await api.get("/api/appointments", {
    params: { phone, include_cancelled: includeCancelled }
  });
  return data;
}

export async function patchAppointment(appointmentId, body) {
  const { data } = await api.patch(
    `/api/appointments/${encodeURIComponent(appointmentId)}`,
    body
  );
  return data;
}

export async function deleteAppointment(appointmentId) {
  const { data } = await api.delete(`/api/appointments/${encodeURIComponent(appointmentId)}`);
  return data;
}


export async function getHealth() {
  const { data } = await api.get("/api/health");
  return data;
}