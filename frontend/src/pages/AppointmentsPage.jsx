import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listAppointments } from "../lib/api.js";

const PHONE_KEY = "aptivcare_last_phone";

function statusLabel(status) {
  if (status === "confirmed") return "Confirmed";
  if (status === "cancelled") return "Cancelled";
  return status || "—";
}

export default function AppointmentsPage() {
  const navigate = useNavigate();
  const [phone, setPhone] = useState("");
  const [includeCancelled, setIncludeCancelled] = useState(true);
  const [rows, setRows] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    try {
      const last = sessionStorage.getItem(PHONE_KEY);
      if (last) setPhone(last);
    } catch {
      /* ignore */
    }
  }, []);

  const onLookup = useCallback(async () => {
    const trimmed = phone.replace(/\D/g, "");
    if (trimmed.length < 10) {
      setError("Enter a valid 10-digit phone number.");
      setRows(null);
      return;
    }
    setLoading(true);
    setError(null);
    setRows(null);
    try {
      const data = await listAppointments(phone, { includeCancelled });
      setRows(data);
      try {
        sessionStorage.setItem(PHONE_KEY, phone);
      } catch {
        /* ignore */
      }
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : e?.message || "Could not load appointments.");
      setRows(null);
    } finally {
      setLoading(false);
    }
  }, [phone, includeCancelled]);

  return (
    <div className="min-h-screen bg-brand-bg text-zinc-100 animate-fadeIn">
      <header className="sticky top-0 z-10 border-b border-zinc-800/80 bg-zinc-950/95 px-6 py-4 backdrop-blur-md">
        <div className="mx-auto flex max-w-3xl items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={() => navigate(-1)}
              className="rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-zinc-100 hover:bg-zinc-800"
            >
              Back
            </button>
            <Link to="/" className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-primary text-brand-onPrimary text-sm font-bold">
                A
              </div>
              <span className="hidden text-sm font-semibold sm:inline">AptivCare</span>
            </Link>
          </div>
          <Link
            to="/call-ws"
            className="rounded-xl bg-brand-primary px-3 py-2 text-xs font-semibold text-brand-onPrimary hover:bg-brand-primaryDark sm:text-sm sm:px-4"
          >
            Talk to Aarav
          </Link>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-10">
        <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">Previous appointments</h1>
        <p className="mt-2 max-w-xl text-sm leading-relaxed text-zinc-500">
          Enter the phone number you use with AptivCare. We show upcoming and past bookings stored for this demo
          clinic (same data Aarav uses during a call).
        </p>

        <div className="mt-8 rounded-2xl border border-zinc-800 bg-zinc-950/90 p-6 shadow-soft">
          <label className="block text-xs font-medium uppercase tracking-wide text-zinc-500" htmlFor="phone">
            Phone number
          </label>
          <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-end">
            <input
              id="phone"
              type="tel"
              autoComplete="tel"
              placeholder="e.g. 9876543210"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && onLookup()}
              className="w-full flex-1 rounded-xl border border-zinc-600 bg-zinc-900 px-4 py-2.5 text-sm text-zinc-100 outline-none ring-zinc-500/30 focus:ring-2"
            />
            <button
              type="button"
              onClick={onLookup}
              disabled={loading}
              className="rounded-xl bg-brand-primary px-5 py-2.5 text-sm font-semibold text-brand-onPrimary transition hover:bg-brand-primaryDark disabled:opacity-60"
            >
              {loading ? "Loading…" : "Look up"}
            </button>
          </div>
          <label className="mt-4 flex cursor-pointer items-center gap-2 text-sm text-zinc-400">
            <input
              type="checkbox"
              checked={includeCancelled}
              onChange={(e) => setIncludeCancelled(e.target.checked)}
              className="h-4 w-4 rounded border-zinc-600 bg-zinc-900 text-zinc-100"
            />
            Include cancelled appointments
          </label>
        </div>

        {error && (
          <div className="mt-6 rounded-xl border border-zinc-600 bg-zinc-900 px-4 py-3 text-sm text-zinc-300">
            {error}
          </div>
        )}

        {rows && (
          <div className="mt-8">
            <div className="mb-3 flex items-baseline justify-between gap-2">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-zinc-500">Results</h2>
              <span className="text-xs text-zinc-500">{rows.length} record{rows.length === 1 ? "" : "s"}</span>
            </div>
            {rows.length === 0 ? (
              <p className="rounded-2xl border border-dashed border-zinc-700 bg-zinc-950/60 px-4 py-10 text-center text-sm text-zinc-500">
                No appointments found for this number. Start a call with Aarav to book your first visit.
              </p>
            ) : (
              <ul className="space-y-2">
                {rows.map((row) => (
                  <li
                    key={row.id}
                    className="rounded-2xl border border-zinc-800 bg-zinc-950/80 px-4 py-4 shadow-soft"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div>
                        <p className="text-sm font-semibold text-zinc-100">{row.appointment_datetime}</p>
                        <p className="mt-0.5 text-xs text-zinc-500">{row.doctor_name}</p>
                      </div>
                      <span
                        className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium ${
                          row.status === "cancelled"
                            ? "border-zinc-500 bg-zinc-800 text-zinc-300"
                            : "border-zinc-400 bg-zinc-200 text-zinc-900"
                        }`}
                      >
                        {statusLabel(row.status)}
                      </span>
                    </div>
                    <p className="mt-2 font-mono text-[10px] text-zinc-600">ID {row.id}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
