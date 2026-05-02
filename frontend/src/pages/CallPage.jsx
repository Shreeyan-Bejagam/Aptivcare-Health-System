







import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useDataChannel,
  useRoomContext,
  useTracks,
  useTranscriptions,
  useVoiceAssistant } from
"@livekit/components-react";
import { Track } from "livekit-client";
import "@livekit/components-styles";
import { AnimatePresence, motion } from "framer-motion";

import Avatar from "../components/Avatar.jsx";
import AppointmentPanel from "../components/AppointmentPanel.jsx";
import CallControls from "../components/CallControls.jsx";
import ToolFeed from "../components/ToolFeed.jsx";
import TranscriptView from "../components/TranscriptView.jsx";
import { useStore } from "../lib/store.js";
import { createSession } from "../lib/api.js";


let pendingCreateSessionPromise = null;

function CallStage({ onEndCall }) {
  const room = useRoomContext();
  const pushToolEvent = useStore((s) => s.pushToolEvent);
  const setUser = useStore((s) => s.setUser);
  const upsertTranscript = useStore((s) => s.upsertTranscript);
  const setStatus = useStore((s) => s.setStatus);
  const sessionStatus = useStore((s) => s.session.status);
  const toolEvents = useStore((s) => s.toolEvents);
  const [mobileTab, setMobileTab] = useState("transcript");


  useDataChannel("tool_event", (msg) => {
    try {
      const text = new TextDecoder().decode(msg.payload);
      const payload = JSON.parse(text);
      if (payload?.type === "tool_event" && payload.tool) {
        pushToolEvent({
          tool: payload.tool,
          status: payload.status || "loading",
          result: payload.result,
          message: payload.message,
          timestamp: payload.timestamp
        });
      }
    } catch (err) {
      console.warn("Bad tool_event payload", err);
    }
  });


  const transcriptions = useTranscriptions();
  useEffect(() => {
    if (!transcriptions || transcriptions.length === 0) return;
    const latest = transcriptions[transcriptions.length - 1];
    if (!latest) return;

    const isLocal =
    latest.participantInfo?.identity === room?.localParticipant?.identity;

    const turn = {
      id: latest.id || `${isLocal ? "user" : "assistant"}-${latest.firstReceivedTime}`,
      role: isLocal ? "user" : "assistant",
      text: latest.text || "",
      interim: !latest.final,
      timestamp: new Date(latest.firstReceivedTime || Date.now()).toISOString()
    };
    if (latest.final) {

      upsertTranscript({ ...turn, interim: false });
    } else {
      upsertTranscript(turn);
    }
  }, [transcriptions, room, upsertTranscript]);


  const trackRefs = useTracks([Track.Source.Microphone], {
    onlySubscribed: true
  });

  const agentAudioTrack = useMemo(() => {
    const remote = trackRefs.find(
      (ref) =>
      ref.publication?.track && !ref.participant?.isLocal && ref.publication.track.kind === "audio"
    );
    return remote?.publication?.track;
  }, [trackRefs]);


  const { state: assistantState } = useVoiceAssistant();
  const isAgentSpeaking = assistantState === "speaking";
  const isThinking = toolEvents.some((event) => event.status === "loading");

  useEffect(() => {
    const lastIdentify = [...toolEvents].reverse().find((e) => e.tool === "identify_user" && e.status === "success");
    if (lastIdentify?.result?.phone) {
      setUser({
        phone: lastIdentify.result.phone,
        name: lastIdentify.result.name || null
      });
    }
  }, [toolEvents, setUser]);

  useEffect(() => {
    setStatus("active");
  }, [setStatus]);

  const statusPill = (() => {
    if (sessionStatus === "connecting") {
      return { label: "Connecting...", classes: "bg-zinc-800 text-zinc-200 ring-1 ring-zinc-700" };
    }
    if (sessionStatus === "ended") {
      return { label: "Ending...", classes: "bg-zinc-700 text-zinc-200 ring-1 ring-zinc-600" };
    }
    return { label: "Live with Aarav", classes: "bg-zinc-100 text-zinc-900 ring-1 ring-zinc-300" };
  })();

  return (
    <div className="mx-auto grid h-[calc(100vh-72px)] max-w-7xl grid-cols-1 gap-4 px-4 py-4 md:px-6 md:grid-cols-[1fr_340px] lg:grid-cols-[320px_1fr_340px]">
      <div className="hidden lg:block">
        <TranscriptView />
      </div>

      <main className="relative flex flex-col items-center justify-center overflow-hidden rounded-2xl p-6 shadow-soft glass-panel">
        <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.04] via-transparent to-zinc-500/[0.06]" />
        <span className={`absolute top-4 inline-flex items-center gap-2 rounded-full px-3 py-1 text-xs font-medium ${statusPill.classes}`}>
          <span className="h-2 w-2 rounded-full bg-current animate-pulseDot" />
          {statusPill.label}
        </span>
        <Avatar
          audioTrack={agentAudioTrack}
          isSpeaking={isAgentSpeaking}
          isThinking={isThinking} />
        
        <CallControls onEndCall={onEndCall} />
        <p className="mt-6 max-w-sm text-balance text-center text-sm leading-relaxed text-brand-mute">
          Talk naturally. Aarav will identify you, check slots, and confirm every
          booking step clearly.
        </p>
        <div className="mt-5 flex flex-wrap justify-center gap-2 text-xs">
          <span className="rounded-full border border-zinc-700 bg-zinc-900/90 px-3 py-1 text-zinc-400">
            Real-time transcript
          </span>
          <span className="rounded-full border border-zinc-700 bg-zinc-900/90 px-3 py-1 text-zinc-400">
            Secure booking tools
          </span>
          <span className="rounded-full border border-zinc-700 bg-zinc-900/90 px-3 py-1 text-zinc-400">
            Instant summary
          </span>
        </div>
      </main>

      <div className="hidden max-h-[calc(100vh-120px)] space-y-4 overflow-y-auto md:block">
        <ToolFeed />
        <AppointmentPanel />
      </div>

      <section className="mt-2 rounded-2xl p-2 glass-panel md:hidden">
        <div className="mb-2 grid grid-cols-2 rounded-full border border-zinc-800 bg-zinc-950 p-1 text-sm">
          <button
            type="button"
            onClick={() => setMobileTab("transcript")}
            className={`rounded-full px-3 py-1.5 ${
            mobileTab === "transcript" ?
            "bg-zinc-800 font-medium text-zinc-100 shadow-sm" :
            "text-zinc-500"}`
            }>
            
            Transcript
          </button>
          <button
            type="button"
            onClick={() => setMobileTab("actions")}
            className={`rounded-full px-3 py-1.5 ${
            mobileTab === "actions" ?
            "bg-zinc-800 font-medium text-zinc-100 shadow-sm" :
            "text-zinc-500"}`
            }>
            
            Actions
          </button>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={mobileTab}
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -6 }}
            transition={{ duration: 0.2 }}
            className="h-[34vh]">
            
            {mobileTab === "transcript" ?
            <TranscriptView /> :

            <div className="flex flex-col gap-3 overflow-y-auto">
                <ToolFeed />
                <AppointmentPanel />
              </div>
            }
          </motion.div>
        </AnimatePresence>
      </section>
    </div>);

}

export default function CallPage() {
  const navigate = useNavigate();
  const setSession = useStore((s) => s.setSession);
  const setStatus = useStore((s) => s.setStatus);
  const reset = useStore((s) => s.reset);

  const [credentials, setCredentials] = useState(null);
  const [error, setError] = useState(null);
  const sessionIdRef = useRef(null);

  useEffect(() => {
    let cancelled = false;
    reset();
    setStatus("connecting");

    (async () => {
      try {
        if (!pendingCreateSessionPromise) {
          pendingCreateSessionPromise = createSession().finally(() => {
            pendingCreateSessionPromise = null;
          });
        }
        const data = await pendingCreateSessionPromise;
        if (cancelled) return;
        sessionIdRef.current = data.session_id;
        setSession({
          id: data.session_id,
          livekitToken: data.livekit_token,
          livekitUrl: data.livekit_url,
          room: data.room,
          status: "connecting",
          startedAt: new Date().toISOString()
        });
        setCredentials(data);
      } catch (err) {
        if (cancelled) return;
        const status = err?.response?.status;
        const rawDetail = err?.response?.data?.detail;
        const detail =
          typeof rawDetail === "string"
            ? rawDetail
            : Array.isArray(rawDetail)
              ? rawDetail.map((x) => (x && typeof x === "object" ? x.msg || JSON.stringify(x) : String(x))).join(" ")
              : rawDetail != null
                ? String(rawDetail)
                : "";
        if (status === 503) {
          const d = detail.toLowerCase();
          if (d.includes("livekit")) {
            navigate("/call-ws", { replace: true });
            return;
          }
          setError(detail || "Voice calls are not configured yet. Please set up API keys in backend/.env.");
        } else if (status === 429) {
          setError(
            "Too many session starts from this network. Wait about a minute, then try again—or use the alternate call mode."
          );
        } else {
          setError(detail || err?.message || "Could not start the call.");
        }
        setStatus("error");
      }
    })();

    return () => {
      cancelled = true;
    };

  }, []);

  const handleEndCall = useCallback(() => {
    const sessionId = sessionIdRef.current;
    setStatus("ended");
    if (sessionId) {
      navigate(`/summary/${sessionId}`);
    } else {
      navigate("/");
    }
  }, [navigate, setStatus]);

  const handleDisconnected = useCallback(() => {
    if (sessionIdRef.current) {
      setStatus("ended");
      navigate(`/summary/${sessionIdRef.current}`);
    }
  }, [navigate, setStatus]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-brand-bg p-6 animate-fadeIn">
        <div className="max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-8 text-center shadow-card">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-zinc-200 ring-1 ring-zinc-400">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#171717" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <circle cx="12" cy="12" r="10" />
              <line x1="12" y1="8" x2="12" y2="12" />
              <line x1="12" y1="16" x2="12.01" y2="16" />
            </svg>
          </div>
          <h1 className="text-xl font-semibold text-brand-ink">
            We couldn't start the call
          </h1>
          <p className="mt-2 text-sm leading-relaxed text-brand-mute">{error}</p>
          <div className="mt-6 flex flex-col items-stretch gap-3 sm:flex-row sm:justify-center">
            <button
              type="button"
              className="rounded-xl border border-zinc-600 bg-zinc-900 px-5 py-2.5 text-sm font-medium text-zinc-100 hover:bg-zinc-800"
              onClick={() => navigate("/")}>
              
              Back to home
            </button>
            <Link
              to="/call-ws"
              className="rounded-xl border border-zinc-300 bg-zinc-100 px-5 py-2.5 text-center text-sm font-semibold text-zinc-900 hover:bg-zinc-200">
              
              Try alternate call mode
            </Link>
            <button
              type="button"
              className="rounded-xl bg-brand-primary px-5 py-2.5 text-sm font-semibold text-brand-onPrimary hover:bg-brand-primaryDark"
              onClick={() => window.location.reload()}>
              
              Try again
            </button>
          </div>
        </div>
      </div>);

  }

  if (!credentials) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-brand-bg p-6 animate-fadeIn">
        <div className="flex flex-col items-center gap-4 text-brand-mute">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-zinc-700 border-t-zinc-100" />
          <span className="text-sm">Connecting you to Aarav…</span>
        </div>
      </div>);

  }

  return (
    <div className="min-h-screen bg-brand-bg animate-fadeIn">
      <header className="sticky top-0 z-10 flex items-center justify-between border-b border-zinc-800/80 bg-zinc-950/90 px-6 py-4 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => navigate(-1)}
            className="rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-1.5 text-xs font-semibold text-zinc-100 hover:bg-zinc-800">
            
            Back
          </button>
          <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-brand-primary text-brand-onPrimary font-bold">
            A
          </div>
          <span className="text-sm font-semibold text-brand-ink">
            AptivCare Assistant
          </span>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full bg-zinc-100 px-3 py-1 text-xs font-medium text-zinc-800 ring-1 ring-zinc-300">
          <span className="h-2 w-2 rounded-full bg-zinc-600 animate-pulseDot" />
          Live
        </span>
      </header>

      <LiveKitRoom
        serverUrl={credentials.livekit_url}
        token={credentials.livekit_token}
        connect={true}
        audio={true}
        video={false}
        onDisconnected={handleDisconnected}
        onError={(err) => {
          console.error("LiveKit error", err);
          const msg = err?.message || "Voice connection failed.";
          const lower = String(msg).toLowerCase();
          if (
          lower.includes("invalid token") ||
          lower.includes("unauthorized") ||
          lower.includes("could not establish signal"))
          {
            setError(
              "Voice service connection failed. Please check backend call credentials in backend/.env and restart the server."
            );
          } else {
            setError(msg);
          }
        }}>
        
        <RoomAudioRenderer />
        <CallStage onEndCall={handleEndCall} />
      </LiveKitRoom>
    </div>);

}