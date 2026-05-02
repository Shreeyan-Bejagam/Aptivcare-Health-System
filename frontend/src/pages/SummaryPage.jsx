








import { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import SummaryCard from "../components/SummaryCard.jsx";
import { getSummary } from "../lib/api.js";

const POLL_INTERVAL_MS = 2000;
const MAX_POLL_ATTEMPTS = 30;

function SkeletonRow() {
  return (
    <div className="rounded-2xl border border-zinc-800 bg-zinc-950/90 p-6 shadow-soft">
      <div className="mb-3 h-3 w-24 animate-pulse rounded bg-zinc-700" />
      <div className="space-y-2">
        <div className="h-3 w-full animate-pulse rounded bg-zinc-800" />
        <div className="h-3 w-5/6 animate-pulse rounded bg-zinc-800" />
        <div className="h-3 w-3/4 animate-pulse rounded bg-zinc-800" />
      </div>
    </div>);

}

export default function SummaryPage() {
  const { sessionId } = useParams();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [summaryPending, setSummaryPending] = useState(false);
  const attemptsRef = useRef(0);

  useEffect(() => {
    if (!sessionId) return undefined;
    setData(null);
    setError(null);
    setSummaryPending(false);
    attemptsRef.current = 0;

    let stopped = false;
    let timer = null;

    async function pollOnce() {
      if (stopped) return;
      attemptsRef.current += 1;
      try {
        const resp = await getSummary(sessionId);
        if (resp?.status === "ready") {
          setData(resp);
          return;
        }
        if (resp?.status === "pending") {
          setSummaryPending(true);
        }
        if (attemptsRef.current >= MAX_POLL_ATTEMPTS) {
          setError(
            "It's taking longer than expected to finalise the summary. Please refresh in a minute."
          );
          return;
        }
        timer = setTimeout(pollOnce, POLL_INTERVAL_MS);
      } catch (err) {
        if (err?.response?.status === 404) {
          setError("We couldn't find that session.");
          return;
        }
        if (attemptsRef.current >= MAX_POLL_ATTEMPTS) {
          setError("Could not load the summary. Please try refreshing.");
          return;
        }
        timer = setTimeout(pollOnce, POLL_INTERVAL_MS);
      }
    }

    pollOnce();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
    };
  }, [sessionId]);

  return (
    <div className="min-h-screen bg-brand-bg animate-fadeIn">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-zinc-800/80 bg-zinc-950/90 px-6 py-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-zinc-100 hover:bg-zinc-800">
            
            Back
          </button>
          <Link to="/" className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-primary text-brand-onPrimary font-bold">
              A
            </div>
            <span className="text-sm font-semibold text-zinc-100">
              AptivCare Assistant
            </span>
          </Link>
        </div>
        <Link
          to="/call-ws"
          className="rounded-2xl bg-brand-primary px-4 py-2 text-sm font-semibold text-brand-onPrimary shadow-soft transition hover:bg-brand-primaryDark">
          
          Start new call
        </Link>
      </header>

      <main className="mx-auto max-w-7xl p-6">
        <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-zinc-800 bg-zinc-950/90 p-4 shadow-soft">
          <div className="min-w-0">
          <h1 className="text-2xl font-semibold tracking-tight text-zinc-50">Call Summary</h1>
          <p className="truncate text-sm text-zinc-500">
            Session{" "}
            <span className="font-mono text-zinc-200">{sessionId}</span>
          </p>
          </div>
          <button
            type="button"
            onClick={() => window.print()}
            className="rounded-2xl border border-zinc-600 bg-zinc-900 px-4 py-2 text-sm font-medium text-zinc-100 transition hover:-translate-y-0.5 hover:bg-zinc-800">
            
            Print summary
          </button>
        </div>

        {error &&
        <div className="mb-6 rounded-2xl border border-zinc-600 bg-zinc-900 p-6 text-sm text-zinc-200">
            {error}
          </div>
        }

        {!data && !error && summaryPending &&
        <div className="mb-6 rounded-2xl border border-zinc-600 bg-zinc-900 p-5 text-sm text-zinc-200">
            <p className="font-medium text-zinc-100">Summary not ready yet</p>
            <p className="mt-2 leading-relaxed text-zinc-400">
              We poll the server every few seconds. If the call never connected, the assistant may not write a
              summary—this page will stop waiting after about a minute.
              You can also try{" "}
              <Link to="/call-ws" className="font-semibold text-zinc-100 underline underline-offset-2">
                alternate call mode
              </Link>{" "}
              or update your call credentials and start a new call.
            </p>
          </div>
        }

        {!data && !error &&
        <div className="grid gap-4 lg:grid-cols-3">
            <SkeletonRow />
            <SkeletonRow />
            <SkeletonRow />
            <div className="lg:col-span-3">
              <SkeletonRow />
            </div>
          </div>
        }

        {data &&
        <SummaryCard
          summary={data.summary}
          costBreakdown={data.cost_breakdown}
          transcript={data.transcript}
          startedAt={data.started_at}
          endedAt={data.ended_at} />

        }
      </main>
    </div>);

}