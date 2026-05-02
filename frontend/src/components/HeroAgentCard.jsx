import { useState } from "react";
import { Link } from "react-router-dom";

export default function HeroAgentCard() {
  const [avatarFailed, setAvatarFailed] = useState(false);

  return (
    <div className="group relative w-full max-w-md overflow-hidden rounded-3xl border border-zinc-700/80 bg-zinc-950 shadow-card">
      <div
        className="pointer-events-none absolute inset-0 opacity-[0.2] bg-[linear-gradient(rgba(255,255,255,0.04)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.04)_1px,transparent_1px)] bg-[length:28px_28px]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute inset-0 bg-gradient-to-br from-zinc-800/50 via-transparent to-black/60"
        aria-hidden
      />
      <div className="pointer-events-none absolute -right-16 top-1/2 h-48 w-48 -translate-y-1/2 rounded-full bg-white/[0.04] blur-3xl" aria-hidden />

      <div className="relative z-10 flex min-h-[20rem] flex-col p-8 md:min-h-[22rem] md:p-10">
        <div className="flex items-start justify-between gap-4">
          <div className="relative shrink-0">
            <div className="h-24 w-24 overflow-hidden rounded-2xl bg-zinc-800 ring-2 ring-zinc-600 shadow-lg md:h-28 md:w-28">
              {!avatarFailed ? (
                <img
                  src="/avatar.png"
                  alt="Aarav"
                  className="h-full w-full object-cover"
                  onError={() => setAvatarFailed(true)}
                />
              ) : (
                <div className="flex h-full w-full items-center justify-center bg-gradient-to-br from-zinc-700 to-zinc-900 text-3xl font-semibold tracking-tight text-zinc-200">
                  A
                </div>
              )}
            </div>
            <span
              className="absolute -bottom-1 -right-1 flex items-center gap-1 rounded-full border border-zinc-600 bg-zinc-950 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide text-zinc-300 shadow-md"
              title="Agent ready for new sessions"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-zinc-200 animate-pulseDot" />
              Live
            </span>
          </div>

          <div className="min-w-0 flex-1 space-y-2 pt-1 text-right">
            <p className="text-xs font-medium uppercase tracking-[0.2em] text-zinc-500">Voice concierge</p>
            <p className="text-xl font-semibold tracking-tight text-zinc-50 md:text-2xl">Aarav</p>
            <p className="text-sm text-zinc-400">AptivCare Assistant</p>
          </div>
        </div>

        <div className="mt-8 grid grid-cols-3 gap-2 border-t border-zinc-800/80 pt-6">
          {[
            { label: "Avg. booking", value: "< 60s" },
            { label: "Availability", value: "24/7" },
            { label: "Channel", value: "Secure" }
          ].map((s) => (
            <div
              key={s.label}
              className="rounded-xl border border-zinc-800/90 bg-black/30 px-2 py-2.5 text-center md:px-1"
            >
              <p className="text-[11px] font-medium uppercase tracking-wide text-zinc-500">{s.label}</p>
              <p className="mt-0.5 text-sm font-semibold text-zinc-100">{s.value}</p>
            </div>
          ))}
        </div>

        <div className="mt-auto flex flex-col gap-3 pt-8">
          <div className="rounded-2xl border border-zinc-700/90 bg-zinc-950/90 px-4 py-3 backdrop-blur-sm">
            <p className="text-sm font-medium text-zinc-100">Aarav is live</p>
            <p className="mt-0.5 text-xs leading-relaxed text-zinc-500">
              Ready to book, reschedule, or cancel — by voice or text.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              to="/call-ws"
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-brand-primary px-4 py-2.5 text-center text-sm font-semibold text-brand-onPrimary transition hover:bg-brand-primaryDark md:flex-none md:px-5"
            >
              Start conversation
            </Link>
            <Link
              to="/appointments"
              className="inline-flex flex-1 items-center justify-center rounded-xl border border-zinc-600 bg-zinc-900/80 px-4 py-2.5 text-sm font-semibold text-zinc-200 transition hover:border-zinc-500 hover:bg-zinc-800 md:flex-none md:px-5"
            >
              My appointments
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
