






import { Link } from "react-router-dom";
import HeroAgentCard from "../components/HeroAgentCard.jsx";

const steps = [
{
  title: "Connect",
  body: "Click 'Talk to Aarav' and grant microphone access — no account needed."
},
{
  title: "Talk naturally",
  body: "Tell Aarav your phone number and what you need; he handles the rest."
},
{
  title: "Get confirmed",
  body: "Your appointment is booked, rescheduled, or cancelled in seconds."
}];


function StepCard({ index, title, body }) {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/80 p-6 shadow-soft transition hover:-translate-y-0.5 hover:border-zinc-700 hover:shadow-card">
      <div className="mb-3 inline-flex h-9 w-9 items-center justify-center rounded-full bg-zinc-800 text-sm font-semibold text-zinc-100 ring-1 ring-zinc-600">
        {index + 1}
      </div>
      <h3 className="mb-1 text-lg font-semibold text-zinc-100">{title}</h3>
      <p className="text-sm leading-relaxed text-zinc-400">{body}</p>
    </div>);

}

export default function HomePage() {
  return (
    <div className="min-h-screen bg-brand-bg text-zinc-100 animate-fadeIn">
      <header className="sticky top-0 z-20 border-b border-zinc-800/80 bg-zinc-950/95 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-2">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand-primary text-brand-onPrimary font-bold">
            A
          </div>
          <span className="text-base font-semibold text-zinc-100">
            AptivCare
          </span>
        </div>
        <nav className="flex flex-wrap items-center justify-end gap-x-4 gap-y-1 text-xs font-medium text-zinc-400 sm:gap-x-6 sm:text-sm">
          <Link to="/appointments" className="transition hover:text-zinc-100">
            Appointments
          </Link>
          <a href="#how" className="transition hover:text-zinc-100">
            How it works
          </a>
          <a href="#contact" className="transition hover:text-zinc-100">
            Contact
          </a>
        </nav>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6">
        <section className="grid gap-10 py-14 md:grid-cols-2 md:py-20">
          <div className="flex flex-col justify-center">
            <span className="mb-4 inline-flex w-fit items-center gap-2 rounded-full border border-zinc-700 bg-zinc-900 px-3 py-1 text-xs font-semibold text-zinc-200">
              <span className="h-2 w-2 rounded-full bg-zinc-300 animate-pulseDot" />
              Live voice agent
            </span>
            <h1 className="text-balance text-4xl font-semibold tracking-tight text-zinc-50 md:text-5xl">
              Your 24/7 Clinic Concierge
            </h1>
            <p className="mt-4 max-w-md text-lg leading-relaxed text-zinc-400">
              Talk naturally to book, manage, or cancel appointments with
              AptivCare. No menus, no forms — just a quick conversation with Aarav.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                to="/call-ws"
                className="inline-flex items-center gap-2 rounded-2xl bg-brand-primary px-6 py-3 text-base font-semibold text-brand-onPrimary shadow-soft transition hover:-translate-y-0.5 hover:bg-brand-primaryDark">
                
                Start conversation
                <svg
                  className="h-4 w-4"
                  viewBox="0 0 20 20"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  aria-hidden="true">
                  
                  <path d="M5 10h10M11 6l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              </Link>
              <a
                href="#how"
                className="inline-flex items-center rounded-xl border border-zinc-700 bg-transparent px-6 py-3 text-base font-medium text-zinc-200 transition hover:border-zinc-500 hover:bg-zinc-900/50">
                
                How it works
              </a>
            </div>
            <div className="mt-8 grid max-w-md grid-cols-3 gap-3 text-center text-xs">
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-3 shadow-soft">
                <p className="text-lg font-semibold text-zinc-100">&lt; 60s</p>
                <p className="text-zinc-500">Avg booking time</p>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-3 shadow-soft">
                <p className="text-lg font-semibold text-zinc-100">24/7</p>
                <p className="text-zinc-500">Always available</p>
              </div>
              <div className="rounded-xl border border-zinc-800 bg-zinc-950/80 p-3 shadow-soft">
                <p className="text-lg font-semibold text-zinc-100">AA</p>
                <p className="text-zinc-500">Accessible UI</p>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-center md:justify-end">
            <HeroAgentCard />
          </div>
        </section>

        <section
          id="appointments"
          className="rounded-2xl border border-zinc-800 bg-zinc-950/60 px-6 py-8 md:flex md:items-center md:justify-between md:gap-8 md:px-10 md:py-10"
        >
          <div className="max-w-lg">
            <h2 className="text-lg font-semibold text-zinc-100">Already a patient?</h2>
            <p className="mt-2 text-sm leading-relaxed text-zinc-500">
              Look up confirmed and cancelled visits by phone — same records Aarav references on a live call.
            </p>
          </div>
          <Link
            to="/appointments"
            className="mt-5 inline-flex items-center justify-center rounded-xl border border-zinc-600 bg-zinc-900 px-5 py-2.5 text-sm font-semibold text-zinc-100 transition hover:border-zinc-500 hover:bg-zinc-800 md:mt-0 md:shrink-0"
          >
            View appointment history
          </Link>
        </section>

        <section id="how" className="py-10">
          <h2 className="mb-6 text-2xl font-semibold text-zinc-100">
            How it works
          </h2>
          <div className="grid gap-6 md:grid-cols-3">
            {steps.map((step, index) =>
            <StepCard key={step.title} index={index} {...step} />
            )}
          </div>
        </section>

        <section className="my-14 rounded-2xl border border-zinc-800 bg-zinc-950/80 p-8 shadow-soft md:p-10">
          <h2 className="text-xl font-semibold text-zinc-100">
            What Aarav can do
          </h2>
          <ul className="mt-4 grid gap-3 text-sm text-zinc-300 md:grid-cols-2">
            <li className="flex items-start gap-3">
              <span className="mt-1 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full border border-zinc-600 bg-zinc-900 text-zinc-200">
                ✓
              </span>
              Identify you by phone number
            </li>
            <li className="flex items-start gap-3">
              <span className="mt-1 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full border border-zinc-600 bg-zinc-900 text-zinc-200">
                ✓
              </span>
              List available slots and book one for you
            </li>
            <li className="flex items-start gap-3">
              <span className="mt-1 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full border border-zinc-600 bg-zinc-900 text-zinc-200">
                ✓
              </span>
              Pull up your existing appointments on demand
            </li>
            <li className="flex items-start gap-3">
              <span className="mt-1 inline-flex h-5 w-5 flex-none items-center justify-center rounded-full border border-zinc-600 bg-zinc-900 text-zinc-200">
                ✓
              </span>
              Reschedule or cancel without filling out a single form
            </li>
          </ul>
        </section>
      </main>

      <footer
        id="contact"
        className="border-t border-zinc-800/80 bg-zinc-950/80 py-6 text-center text-xs text-zinc-500">
        
        AptivCare &middot; Mon–Sat 9am–6pm &middot; This is a demo of a voice
        AI front desk.
      </footer>
    </div>);

}