








import { useStore } from "../lib/store.js";
import { motion } from "framer-motion";

const DISPLAY_NAMES = {
  identify_user: "Identifying Patient",
  fetch_slots: "Fetching Available Slots",
  book_appointment: "Booking Appointment",
  retrieve_appointments: "Retrieving Your Appointments",
  cancel_appointment: "Cancelling Appointment",
  modify_appointment: "Rescheduling Appointment",
  end_conversation: "Wrapping Up Call"
};

const STATUS_COPY = {
  loading: "Checking…",
  success: "Done",
  error: "Couldn't complete"
};

function ToolIcon({ tool }) {
  const baseClass =
  "flex h-9 w-9 flex-none items-center justify-center rounded-xl border border-zinc-600 bg-zinc-900 text-zinc-200";
  const stroke = "currentColor";

  switch (tool) {
    case "identify_user":
      return (
        <span className={baseClass} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 21a8 8 0 0 1 16 0" />
          </svg>
        </span>);

    case "fetch_slots":
      return (
        <span className={baseClass} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
            <rect x="3" y="4" width="18" height="18" rx="2" />
            <line x1="16" y1="2" x2="16" y2="6" />
            <line x1="8" y1="2" x2="8" y2="6" />
            <line x1="3" y1="10" x2="21" y2="10" />
          </svg>
        </span>);

    case "book_appointment":
      return (
        <span className={baseClass} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
            <path d="M5 13l4 4L19 7" />
          </svg>
        </span>);

    case "retrieve_appointments":
      return (
        <span className={baseClass} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
            <path d="M3 6h18M3 12h18M3 18h12" />
          </svg>
        </span>);

    case "cancel_appointment":
      return (
        <span className={baseClass} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
            <line x1="6" y1="6" x2="18" y2="18" />
            <line x1="6" y1="18" x2="18" y2="6" />
          </svg>
        </span>);

    case "modify_appointment":
      return (
        <span className={baseClass} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
            <path d="M21 12a9 9 0 1 1-3-6.7" />
            <path d="M21 4v5h-5" />
          </svg>
        </span>);

    case "end_conversation":
      return (
        <span className={baseClass} aria-hidden="true">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke={stroke} strokeWidth="2">
            <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z" />
          </svg>
        </span>);

    default:
      return (
        <span className={baseClass} aria-hidden="true">
          <span className="text-sm font-bold">·</span>
        </span>);

  }
}

function StatusBadge({ status }) {
  if (status === "loading") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-600 bg-zinc-800 px-2 py-0.5 text-xs font-medium text-zinc-200">
        <span className="h-2 w-2 rounded-full bg-zinc-400 animate-pulseDot" />
        {STATUS_COPY.loading}
      </span>);

  }
  if (status === "success") {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-500 bg-zinc-800 px-2 py-0.5 text-xs font-medium text-zinc-100">
        <span aria-hidden="true">✓</span>
        {STATUS_COPY.success}
      </span>);

  }
  return (
    <span className="inline-flex items-center gap-1.5 rounded-full border border-zinc-500 bg-zinc-900 px-2 py-0.5 text-xs font-medium text-zinc-300">
      <span aria-hidden="true">×</span>
      {STATUS_COPY.error}
    </span>);

}

function summarise(event) {
  if (event.message) return event.message;
  const r = event.result;
  if (!r) return "";
  switch (event.tool) {
    case "identify_user":
      return r.is_returning ?
      `Welcome back, ${r.name || "patient"}.` :
      "New patient identified.";
    case "fetch_slots":
      return `${r.count ?? 0} open slots with ${r.doctor || "the doctor"}.`;
    case "book_appointment":
      return r.datetime ?
      `Booked ${r.datetime} with ${r.doctor}.` :
      "Booking confirmed.";
    case "retrieve_appointments":
      return `${r.count ?? 0} confirmed appointment${r.count === 1 ? "" : "s"}.`;
    case "cancel_appointment":
      return "Appointment cancelled.";
    case "modify_appointment":
      return r.new_datetime ? `Moved to ${r.new_datetime}.` : "Rescheduled.";
    case "end_conversation":
      return "Saving the call summary…";
    default:
      return "";
  }
}

export default function ToolFeed() {
  const events = useStore((s) => s.toolEvents);
  const recent = events.slice(-10).reverse();

  return (
    <aside
      className="flex h-full flex-col rounded-2xl p-4 shadow-soft glass-panel"
      aria-live="polite">
      
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-brand-ink">Task timeline</h3>
        <span className="text-xs text-brand-mute">
          {events.length} event{events.length === 1 ? "" : "s"}
        </span>
      </header>

      <div className="soft-scrollbar flex-1 space-y-2 overflow-y-auto pr-1">
        {recent.length === 0 &&
        <p className="rounded-xl bg-brand-bg px-4 py-6 text-center text-sm text-brand-mute">
            Aarav's tool calls will show up here as the conversation progresses.
          </p>
        }
        {recent.map((event) => {
          const loading = event.status === "loading";
          const success = event.status === "success";
          return (
            <motion.div
              key={event.id}
              initial={{ x: 20, opacity: 0 }}
              animate={{ x: 0, opacity: 1 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              className={`flex items-start gap-3 rounded-2xl border border-zinc-700 bg-zinc-950/90 p-3 transition hover:shadow-soft ${
              success ?
              "border-l-4 border-l-zinc-200" :
              event.status === "error" ?
              "border-l-4 border-l-zinc-500" :
              "border-l-4 border-l-zinc-600"}`
              }>
              
            <ToolIcon tool={event.tool} />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-sm font-medium text-brand-ink">
                  {DISPLAY_NAMES[event.tool] || event.tool}
                </span>
                <StatusBadge status={event.status} />
              </div>
              <p className="mt-0.5 truncate text-xs text-brand-mute">
                {summarise(event)}
              </p>
              {loading &&
                <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-slate-100">
                  <div className="h-full w-2/3 rounded-full shimmer" />
                </div>
                }
            </div>
          </motion.div>);
        })}
      </div>
    </aside>);

}