




import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import Avatar from "../components/Avatar.jsx";
import AppointmentPanel from "../components/AppointmentPanel.jsx";
import ToolFeed from "../components/ToolFeed.jsx";
import TranscriptView from "../components/TranscriptView.jsx";
import WsCallControls from "../components/WsCallControls.jsx";
import { createWebSocketVoiceSession } from "../lib/api.js";
import { useStore } from "../lib/store.js";


let pendingWsVoiceSessionPromise = null;

export default function WsCallPage() {
  const navigate = useNavigate();
  const reset = useStore((s) => s.reset);
  const setSession = useStore((s) => s.setSession);
  const setStatus = useStore((s) => s.setStatus);
  const pushToolEvent = useStore((s) => s.pushToolEvent);
  const pushTranscript = useStore((s) => s.pushTranscript);
  const upsertTranscript = useStore((s) => s.upsertTranscript);
  const setUser = useStore((s) => s.setUser);

  const [error, setError] = useState(null);
  const [starting, setStarting] = useState(true);
  const [mediaStream, setMediaStream] = useState(null);
  const [lastReply, setLastReply] = useState("");
  const [agentSpeaking, setAgentSpeaking] = useState(false);
  const [assistantSpeechLevel, setAssistantSpeechLevel] = useState(0);
  const [inputMode, setInputMode] = useState("pcm");
  const [draftText, setDraftText] = useState("");
  const [speechSupported, setSpeechSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [speechHint, setSpeechHint] = useState("Tap Speak to start voice input.");

  const wsRef = useRef(null);
  const audioCleanupRef = useRef(null);
  const sessionIdRef = useRef(null);
  const speechRef = useRef(null);
  const speechModeRef = useRef("idle");
  const audioLevelRafRef = useRef(0);
  const commandDraftRef = useRef("");

  const sendTextPayload = useCallback(
    (text) => {
      const cleaned = String(text || "").trim();
      if (!cleaned) return false;
      try {
        wsRef.current?.send(JSON.stringify({ type: "user_text", text: cleaned }));
        setDraftText("");
        setSpeechHint("Processing your request…");
        return true;
      } catch {
        setError("Call connection error.");
        setStatus("error");
        return false;
      }
    },
    [setStatus]
  );

  const handleJson = useCallback(
    (data) => {
      if (data.type === "tool_event" && data.tool) {
        pushToolEvent({
          tool: data.tool,
          status: data.status || "loading",
          result: data.result,
          message: data.message,
          timestamp: data.timestamp
        });
        if (data.tool === "identify_user" && data.status === "success" && data.result) {
          setUser({
            phone: data.result.phone || null,
            name: data.result.name || null
          });
        }
        return;
      }
      if (data.type === "transcript_interim" && data.text) {
        upsertTranscript({
          role: "user",
          text: data.text,
          interim: true,
          timestamp: new Date().toISOString()
        });
        return;
      }
      if (data.type === "user_text" && data.text) {
        upsertTranscript({
          role: "user",
          text: data.text,
          interim: false,
          timestamp: new Date().toISOString()
        });
        return;
      }
      if (data.type === "assistant_text" && data.text) {
        setLastReply(data.text);
        pushTranscript({
          role: "assistant",
          text: data.text,
          interim: false,
          timestamp: new Date().toISOString()
        });
        return;
      }
      if (data.type === "assistant_audio_wav" && data.data) {
        const bytes = Uint8Array.from(atob(data.data), (c) => c.charCodeAt(0));
        const blob = new Blob([bytes], { type: "audio/wav" });
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.addEventListener("play", () => {
          setAgentSpeaking(true);
          setSpeechHint("Aarav is speaking…");
          cancelAnimationFrame(audioLevelRafRef.current);
          try {
            const ctx = new (window.AudioContext || window.webkitAudioContext)();
            const source = ctx.createMediaElementSource(audio);
            const analyser = ctx.createAnalyser();
            analyser.fftSize = 128;
            source.connect(analyser);
            analyser.connect(ctx.destination);
            const buf = new Uint8Array(analyser.frequencyBinCount);
            const tick = () => {
              analyser.getByteFrequencyData(buf);
              const avg = buf.reduce((a, b) => a + b, 0) / Math.max(1, buf.length);
              setAssistantSpeechLevel(Math.min(1, avg / 140));
              audioLevelRafRef.current = requestAnimationFrame(tick);
            };
            tick();
            audio.addEventListener(
              "ended",
              () => {
                try {
                  ctx.close();
                } catch {

                }
              },
              { once: true }
            );
          } catch {

          }
        });
        audio.addEventListener("ended", () => {
          setAgentSpeaking(false);
          setAssistantSpeechLevel(0);
          cancelAnimationFrame(audioLevelRafRef.current);
          URL.revokeObjectURL(url);
        });
        audio.play().catch(() => {
          setAgentSpeaking(false);
          setAssistantSpeechLevel(0);
        });
        return;
      }
      if (data.type === "call_ended") {
        setStatus("ended");
        const sid = sessionIdRef.current;
        if (sid) navigate(`/summary/${sid}`);else
        navigate("/");
      }
    },
    [
    navigate,
    pushToolEvent,
    pushTranscript,
    setStatus,
    setUser,
    upsertTranscript]

  );

  useEffect(() => {
    reset();
    setStatus("connecting");

    let ws;
    let cancelled = false;

    async function startMic(socket) {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true },
        video: false
      });
      if (cancelled) {
        stream.getTracks().forEach((t) => t.stop());
        return;
      }
      setMediaStream(stream);
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      processor.onaudioprocess = (event) => {
        if (socket.readyState !== WebSocket.OPEN) return;
        const input = event.inputBuffer.getChannelData(0);
        const pcm = new Int16Array(input.length);
        for (let i = 0; i < input.length; i += 1) {
          pcm[i] = Math.max(-32768, Math.min(32767, input[i] * 32767));
        }
        socket.send(pcm.buffer);
      };
      source.connect(processor);
      processor.connect(ctx.destination);
      audioCleanupRef.current = () => {
        try {
          processor.disconnect();
        } catch {

        }
        try {
          source.disconnect();
        } catch {

        }
        try {
          ctx.close();
        } catch {

        }
        stream.getTracks().forEach((t) => t.stop());
      };
    }

    (async () => {
      try {
        if (!pendingWsVoiceSessionPromise) {
          pendingWsVoiceSessionPromise = createWebSocketVoiceSession().finally(() => {
            pendingWsVoiceSessionPromise = null;
          });
        }
        const data = await pendingWsVoiceSessionPromise;
        if (cancelled) return;
        sessionIdRef.current = data.session_id;
        setSession({
          id: data.session_id,
          status: "connecting",
          startedAt: new Date().toISOString()
        });
        ws = new WebSocket(data.websocket_url);
        ws.binaryType = "arraybuffer";
        wsRef.current = ws;
        ws.onopen = () => {
          setStarting(false);
          setStatus("active");
        };
        ws.onmessage = (ev) => {
          if (typeof ev.data === "string") {
            try {
              const data = JSON.parse(ev.data);
              if (data?.type === "ready") {
                if (data.input_mode === "text") {
                  setInputMode("text");
                } else {
                  setInputMode("pcm");
                  startMic(ws).catch((err) => {
                    console.error(err);
                    setError("Could not access the microphone.");
                    setStatus("error");
                  });
                }
                return;
              }
              handleJson(data);
            } catch {

            }
          }
        };
        ws.onerror = () => {
          setError("Call connection error.");
          setStatus("error");
        };
        ws.onclose = () => {
          wsRef.current = null;
        };
      } catch (err) {
        const st = err?.response?.status;
        const detail = err?.response?.data?.detail;
        if (st === 429) {
          setError(
            "Too many session starts (rate limit). Wait about a minute, then reload this page."
          );
        } else {
          setError(detail || err?.message || "Could not start this call mode.");
        }
        setStatus("error");
        setStarting(false);
      }
    })();

    return () => {
      cancelled = true;
      audioCleanupRef.current?.();
      audioCleanupRef.current = null;
      try {
        ws?.close();
      } catch {

      }
      wsRef.current = null;
    };

  }, []);

  const sendTextTurn = useCallback(() => {
    const text = draftText.trim();
    if (!text) return;
    sendTextPayload(text);
  }, [draftText, sendTextPayload]);

  useEffect(() => {
    if (inputMode !== "text") return undefined;
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setSpeechSupported(false);
      return undefined;
    }

    const rec = new SR();
    rec.lang = "en-US";
    rec.continuous = false;
    rec.interimResults = true;

    rec.onstart = () => setListening(true);
    rec.onend = () => {
      setListening(false);
      if (speechModeRef.current === "command") {
        const buffered = commandDraftRef.current.trim();
        commandDraftRef.current = "";
        speechModeRef.current = "idle";
        if (buffered) {
          sendTextPayload(buffered);
          return;
        }
        setSpeechHint("Tap Speak to start voice input.");
      }
    };
    rec.onerror = () => {
      setListening(false);
      setSpeechHint("Voice input unavailable. You can still type.");
    };
    rec.onresult = (event) => {
      let text = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        text += event.results[i][0]?.transcript || "";
      }
      const cleaned = text.trim();
      if (!cleaned) return;

      const finalResult = event.results[event.results.length - 1]?.isFinal;
      if (speechModeRef.current !== "command") return;
      setDraftText(cleaned);
      commandDraftRef.current = cleaned;
      if (!finalResult) return;
      try {
        rec.stop();
      } catch {

      }
    };

    speechRef.current = rec;
    setSpeechSupported(true);

    return () => {
      try {
        speechModeRef.current = "idle";
        commandDraftRef.current = "";
        rec.stop();
      } catch {

      }
      speechRef.current = null;
      setListening(false);
      setSpeechHint("Tap Speak to start voice input.");
    };
  }, [inputMode, sendTextPayload]);

  const toggleSpeechInput = useCallback(() => {
    const rec = speechRef.current;
    if (!rec) return;
    try {
      if (listening) {
        speechModeRef.current = "idle";
        commandDraftRef.current = "";
        rec.stop();
        setSpeechHint("Tap Speak to start voice input.");
      } else {
        setDraftText("");
        commandDraftRef.current = "";
        speechModeRef.current = "command";
        setSpeechHint("Listening for your request…");
        rec.start();
      }
    } catch {

    }
  }, [listening]);

  const onEndCall = useCallback(() => {
    try {
      wsRef.current?.send(JSON.stringify({ type: "hangup" }));
    } catch {

    }
    audioCleanupRef.current?.();
    audioCleanupRef.current = null;
    const sid = sessionIdRef.current;
    setStatus("ended");
    if (sid) navigate(`/summary/${sid}`);else
    navigate("/");
  }, [navigate, setStatus]);

  if (error) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-brand-bg p-6 animate-fadeIn">
        <div className="max-w-md rounded-2xl border border-zinc-800 bg-zinc-950 p-8 text-center shadow-card">
          <h1 className="text-xl font-semibold text-zinc-100">Call mode unavailable</h1>
          <p className="mt-2 text-sm text-zinc-400">{error}</p>
          <p className="mt-3 text-xs leading-relaxed text-zinc-500">
            Copy <code className="rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5 text-zinc-200">backend/.env.example</code> to{" "}
            <code className="rounded border border-zinc-700 bg-zinc-900 px-1 py-0.5 text-zinc-200">backend/.env</code>, update the required
            call credentials, restart the API, then retry.
          </p>
          <div className="mt-6 flex flex-col items-stretch gap-3 sm:flex-row sm:justify-center">
            <button
              type="button"
              className="rounded-xl border border-zinc-600 bg-zinc-900 px-5 py-2.5 text-sm font-medium text-zinc-100 hover:bg-zinc-800"
              onClick={() => navigate("/")}>
              
              Home
            </button>
            <Link
              to="/call"
              className="rounded-xl border border-zinc-600 bg-zinc-900 px-5 py-2.5 text-center text-sm font-medium text-zinc-100 hover:bg-zinc-800">
              
              Standard call mode
            </Link>
            <button
              type="button"
              className="rounded-xl bg-brand-primary px-5 py-2.5 text-sm font-semibold text-brand-onPrimary hover:bg-brand-primaryDark"
              onClick={() => window.location.reload()}>
              
              Retry
            </button>
          </div>
        </div>
      </div>);

  }

  if (starting) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-brand-bg p-6 animate-fadeIn">
        <div className="flex flex-col items-center gap-4 text-brand-mute">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-zinc-700 border-t-zinc-100" />
          <span className="text-sm">Preparing call session…</span>
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
          <span className="text-sm font-semibold text-zinc-100">AptivCare · Voice Assistant</span>
        </div>
        <span className="rounded-full border border-zinc-600 bg-zinc-900 px-3 py-1 text-xs font-medium text-zinc-200">
          {inputMode === "text" ? "Text input mode" : "Voice input mode"}
        </span>
      </header>

      <div className="mx-auto grid max-w-7xl grid-cols-1 gap-4 px-4 py-4 md:px-6 lg:grid-cols-[320px_1fr_320px]">
        <div className="hidden lg:block">
          <TranscriptView />
        </div>

        <main className="relative flex flex-col items-center overflow-hidden rounded-2xl p-6 shadow-soft glass-panel">
          <div className="pointer-events-none absolute inset-0 bg-gradient-to-br from-white/[0.04] via-transparent to-zinc-500/[0.06]" />
          <Avatar
            audioTrack={null}
            isSpeaking={agentSpeaking}
            isThinking={false}
            speechLevel={assistantSpeechLevel} />
          
          <WsCallControls stream={mediaStream} onEndCall={onEndCall} />
          {inputMode === "text" &&
          <div className="mt-4 flex w-full max-w-xl items-center gap-2">
              {speechSupported &&
            <button
              type="button"
              onClick={toggleSpeechInput}
              className={`rounded-xl px-3 py-2 text-xs font-semibold ring-1 transition ${
              listening ?
              "bg-zinc-800 text-zinc-100 ring-zinc-600" :
              "bg-zinc-900 text-zinc-100 ring-zinc-600 hover:bg-zinc-800"}`
              }>
              
                  {listening ? "Stop" : "Speak"}
                </button>
            }
              <input
              type="text"
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") sendTextTurn();
              }}
              placeholder="Type what the patient says, then press Enter"
              className="w-full rounded-xl border border-zinc-600 bg-zinc-900 px-4 py-2 text-sm text-zinc-100 outline-none ring-zinc-500/40 focus:ring" />
            
              <button
              type="button"
              onClick={sendTextTurn}
              className="rounded-xl bg-brand-primary px-4 py-2 text-sm font-semibold text-brand-onPrimary hover:bg-brand-primaryDark">
              
                Send
              </button>
            </div>
          }
          {inputMode === "text" &&
          <p className="mt-2 text-xs text-brand-mute">{speechHint}</p>
          }
          {lastReply &&
          <p className="mt-4 max-w-lg text-center text-sm leading-relaxed text-brand-ink">{lastReply}</p>
          }
        </main>

        <div className="space-y-4">
          <ToolFeed />
          <AppointmentPanel />
        </div>
      </div>
    </div>);

}