






function fmt(value, fallback = "—") {
  if (value === null || value === undefined || value === "") return fallback;
  return value;
}

function fmtDuration(seconds) {
  if (!seconds && seconds !== 0) return "—";
  const total = Math.round(Number(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  if (m === 0) return `${s}s`;
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function Section({ title, children }) {
  return (
    <section className="rounded-2xl border border-zinc-800 bg-zinc-950/90 p-6 shadow-soft">
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-brand-mute">
        {title}
      </h3>
      {children}
    </section>);

}

export default function SummaryCard({
  summary,
  transcript,
  startedAt,
  endedAt
}) {
  const booked = summary?.appointments_booked || [];
  const cancelled = summary?.appointments_cancelled || [];
  const modified = summary?.appointments_modified || [];
  const preferences = summary?.preferences || [];
  const keyMoments = summary?.key_moments || [];
  const reportDoctor = summary?.doctor_name || booked?.[0]?.doctor || null;
  const doctorFeeMap = {
    "Dr. Priya Sharma": "INR 700",
    "Dr. Rohan Mehta": "INR 1200",
    "Dr. Neha Kapoor": "INR 900",
    "Dr. Arjun Iyer": "INR 1400",
    "Dr. Kavita Rao": "INR 1000"
  };
  const appointmentFee = reportDoctor ? doctorFeeMap[reportDoctor] || "INR 900" : "—";

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Section title="Patient">
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-brand-mute">Name</span>
            <span className="font-medium text-brand-ink">
              {fmt(summary?.name)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Phone</span>
            <span className="font-medium text-brand-ink">
              {fmt(summary?.phone)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Duration</span>
            <span className="font-medium text-brand-ink">
              {fmtDuration(summary?.duration_seconds)}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Turns</span>
            <span className="font-medium text-brand-ink">
              {fmt(summary?.turn_count)}
            </span>
          </div>
        </div>
      </Section>

      <Section title="Appointment report">
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-brand-mute">Name</span>
            <span className="font-medium text-brand-ink">{fmt(summary?.name)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Phone number</span>
            <span className="font-medium text-brand-ink">{fmt(summary?.phone)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Date</span>
            <span className="font-medium text-brand-ink">{fmt(summary?.appointment_date)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Time</span>
            <span className="font-medium text-brand-ink">{fmt(summary?.appointment_time)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Doctor</span>
            <span className="font-medium text-brand-ink">{fmt(summary?.doctor_name)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Appointment fee</span>
            <span className="font-medium text-brand-ink">{appointmentFee}</span>
          </div>
        </div>
      </Section>

      <Section title="Why they called">
        <p className="text-sm leading-relaxed text-brand-ink">
          {fmt(summary?.intent, "No intent captured.")}
        </p>
      </Section>

      <div className="lg:col-span-3">
        <Section title="Appointments">
          {booked.length + cancelled.length + modified.length === 0 ?
          <p className="text-sm text-brand-mute">
              No appointment changes during this call.
            </p> :

          <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-zinc-800 text-xs uppercase tracking-wide text-zinc-500">
                    <th className="py-2">Action</th>
                    <th className="py-2">Date / Time</th>
                    <th className="py-2">Doctor</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-800">
                  {booked.map((row, idx) =>
                <tr key={`b-${idx}`}>
                      <td className="py-2">
                        <span className="rounded-full border border-zinc-600 bg-zinc-800 px-2 py-0.5 text-xs font-medium text-zinc-200">
                          Booked
                        </span>
                      </td>
                      <td className="py-2 text-brand-ink">{fmt(row.datetime)}</td>
                      <td className="py-2 text-brand-mute">{fmt(row.doctor)}</td>
                    </tr>
                )}
                  {modified.map((row, idx) =>
                <tr key={`m-${idx}`}>
                      <td className="py-2">
                        <span className="rounded-full border border-zinc-500 bg-zinc-700 px-2 py-0.5 text-xs font-medium text-zinc-100">
                          Rescheduled
                        </span>
                      </td>
                      <td className="py-2 text-brand-ink">
                        {fmt(row.from_datetime)} → {fmt(row.to_datetime)}
                      </td>
                      <td className="py-2 text-brand-mute">{fmt(row.doctor)}</td>
                    </tr>
                )}
                  {cancelled.map((row, idx) =>
                <tr key={`c-${idx}`}>
                      <td className="py-2">
                        <span className="rounded-full border border-zinc-500 bg-zinc-200 px-2 py-0.5 text-xs font-medium text-zinc-900">
                          Cancelled
                        </span>
                      </td>
                      <td className="py-2 text-brand-ink">{fmt(row.datetime)}</td>
                      <td className="py-2 text-brand-mute">{fmt(row.doctor)}</td>
                    </tr>
                )}
                </tbody>
              </table>
            </div>
          }
        </Section>
      </div>

      <Section title="Preferences captured">
        {preferences.length === 0 ?
        <p className="text-sm text-brand-mute">None captured.</p> :

        <ul className="list-disc space-y-1 pl-5 text-sm text-brand-ink">
            {preferences.map((p, idx) =>
          <li key={idx}>{p}</li>
          )}
          </ul>
        }
      </Section>

      <Section title="Key moments">
        {keyMoments.length === 0 ?
        <p className="text-sm text-brand-mute">None captured.</p> :

        <ul className="list-disc space-y-1 pl-5 text-sm text-brand-ink">
            {keyMoments.map((m, idx) =>
          <li key={idx}>{m}</li>
          )}
          </ul>
        }
      </Section>

      <Section title="Timing">
        <div className="space-y-1 text-sm">
          <div className="flex justify-between">
            <span className="text-brand-mute">Started</span>
            <span className="font-medium text-brand-ink">{fmt(startedAt)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Ended</span>
            <span className="font-medium text-brand-ink">{fmt(endedAt)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-brand-mute">Transcript turns</span>
            <span className="font-medium text-brand-ink">
              {transcript?.length ?? 0}
            </span>
          </div>
        </div>
      </Section>
    </div>);

}