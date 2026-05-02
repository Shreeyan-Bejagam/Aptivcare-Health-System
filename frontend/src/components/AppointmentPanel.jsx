



import { useCallback, useEffect, useState } from "react";
import { deleteAppointment, listAppointments, patchAppointment } from "../lib/api.js";
import { useStore } from "../lib/store.js";

export default function AppointmentPanel() {
  const phone = useStore((s) => s.user.phone);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const refresh = useCallback(async () => {
    if (!phone) {
      setRows([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await listAppointments(phone);
      setRows(data);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Could not load appointments.");
    } finally {
      setLoading(false);
    }
  }, [phone]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const onModify = async (row) => {
    const next = window.prompt(
      "New date & time (YYYY-MM-DD HH:MM, 24h)",
      row.appointment_datetime
    );
    if (!next) return;
    try {
      await patchAppointment(row.id, { appointment_datetime: next });
      await refresh();
    } catch (e) {
      window.alert(e?.response?.data?.detail || e?.message || "Could not reschedule.");
    }
  };

  const onCancel = async (row) => {
    if (!window.confirm("Cancel this appointment?")) return;
    try {
      await deleteAppointment(row.id);
      await refresh();
    } catch (e) {
      window.alert(e?.response?.data?.detail || e?.message || "Could not cancel.");
    }
  };

  if (!phone) {
    return (
      <div className="rounded-2xl border border-dashed border-zinc-700 bg-zinc-950/60 p-4 text-sm text-zinc-500">
        Appointments appear here after Aarav identifies your phone number.
      </div>);

  }

  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/90 p-4 shadow-soft">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-brand-ink">Your appointments</h3>
        <button
          type="button"
          onClick={() => refresh()}
          className="text-xs font-medium text-zinc-300 underline-offset-2 hover:text-white hover:underline">
          
          Refresh
        </button>
      </div>
      {loading && <p className="text-xs text-brand-mute">Loading…</p>}
      {error && <p className="text-xs text-zinc-400">{error}</p>}
      {!loading && rows.length === 0 &&
      <p className="text-xs text-brand-mute">No upcoming confirmed bookings.</p>
      }
      <ul className="mt-2 space-y-2">
        {rows.map((row) =>
        <li
          key={row.id}
          className="flex flex-col gap-2 rounded-xl border border-zinc-700 bg-zinc-900/80 p-3 text-xs text-zinc-100 md:flex-row md:items-center md:justify-between">
          
            <div>
              <p className="font-medium">{row.appointment_datetime}</p>
              <p className="text-brand-mute">{row.doctor_name}</p>
            </div>
            <div className="flex gap-2">
              <button
              type="button"
              onClick={() => onModify(row)}
              className="rounded-lg border border-zinc-600 bg-zinc-800 px-3 py-1.5 text-xs font-medium text-zinc-100 hover:bg-zinc-700">
              
                Modify
              </button>
              <button
              type="button"
              onClick={() => onCancel(row)}
              className="rounded-lg border border-zinc-500 bg-zinc-100 px-3 py-1.5 text-xs font-medium text-zinc-900 hover:bg-white">
              
                Cancel
              </button>
            </div>
          </li>
        )}
      </ul>
    </div>);

}