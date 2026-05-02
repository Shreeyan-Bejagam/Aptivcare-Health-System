


















import { useEffect, useMemo, useRef, useState } from "react";
import { motion } from "framer-motion";

const BAR_COUNT = 8;
const SIMLI_API_KEY = import.meta.env.VITE_SIMLI_API_KEY || "";
const SIMLI_FACE_ID = import.meta.env.VITE_SIMLI_FACE_ID || "";
const TAVUS_EMBED_URL = import.meta.env.VITE_TAVUS_EMBED_URL || "";
const BEYOND_PRESENCE_EMBED_URL = import.meta.env.VITE_BEYOND_PRESENCE_EMBED_URL || "";

function useAudioAnalyser(audioTrack) {
  const [bars, setBars] = useState(() => Array(BAR_COUNT).fill(0.2));
  const rafRef = useRef(0);
  const ctxRef = useRef(null);
  const analyserRef = useRef(null);

  useEffect(() => {
    if (!audioTrack) return undefined;

    const mediaStreamTrack =
    audioTrack.mediaStreamTrack || audioTrack._mediaStreamTrack;
    if (!mediaStreamTrack) return undefined;

    let ctx;
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)();
    } catch (err) {
      console.warn("Web Audio not available", err);
      return undefined;
    }
    ctxRef.current = ctx;

    const source = ctx.createMediaStreamSource(new MediaStream([mediaStreamTrack]));
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 128;
    analyser.smoothingTimeConstant = 0.7;
    source.connect(analyser);
    analyserRef.current = analyser;

    const buf = new Uint8Array(analyser.frequencyBinCount);

    function tick() {
      if (!analyserRef.current) return;
      analyserRef.current.getByteFrequencyData(buf);
      const slice = Math.floor(buf.length / BAR_COUNT);
      const next = Array(BAR_COUNT).
      fill(0).
      map((_, i) => {
        let sum = 0;
        for (let j = 0; j < slice; j++) sum += buf[i * slice + j];
        return Math.min(1, sum / slice / 180);
      });
      setBars(next);
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(rafRef.current);
      analyserRef.current = null;
      try {
        source.disconnect();
        ctx.close();
      } catch {

      }
      ctxRef.current = null;
    };
  }, [audioTrack]);

  return bars;
}

function ProviderIframeAvatar({ url, label }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative h-56 w-full max-w-sm overflow-hidden rounded-2xl bg-slate-100 shadow-card ring-1 ring-slate-200">
        <iframe title={label} src={url} className="h-full w-full border-0" allow="camera; microphone" />
      </div>
      <div className="text-sm font-medium text-brand-ink">
        Aarav
        <span className="ml-2 text-brand-mute">· {label}</span>
      </div>
    </div>);

}

function SvgFallback({ audioTrack, isSpeaking, isThinking, speechLevel = 0 }) {
  const bars = useAudioAnalyser(audioTrack);
  const ringColor = isThinking ?
  "from-zinc-500 via-zinc-300 to-zinc-600" :
  "from-zinc-400 via-zinc-200 to-zinc-500";
  const mouthOpen = Math.max(0.08, Math.min(0.72, speechLevel * 1.8 + (isSpeaking ? 0.2 : 0.08)));
  const lipCenterY = 58;
  const upperLipClip = `ellipse(11.6% 2.8% at 50% ${lipCenterY - 0.9}%)`;
  const lowerLipClip = `ellipse(12.6% 4.8% at 50% ${lipCenterY + 0.7}%)`;
  const innerMouthClip = `ellipse(9.6% 3.2% at 50% ${lipCenterY + 1.5}%)`;

  return (
    <div className="flex flex-col items-center gap-6">
      <motion.div
        animate={{
          scale: isSpeaking ? [1, 1.04, 1] : [1, 1.015, 1]
        }}
        transition={{ duration: 1.8, repeat: Infinity, ease: "easeInOut" }}
        className={`relative flex h-44 w-44 items-center justify-center rounded-full text-white shadow-soft md:h-56 md:w-56 ${
        isSpeaking ? "animate-speakingGlow" : ""}`
        }>
        
        <div
          className={`absolute inset-0 rounded-full bg-gradient-to-tr ${ringColor} ${
          isThinking ? "animate-spin [animation-duration:3.5s]" : ""}`
          } />
        
        <div className="absolute inset-[3px] rounded-full bg-[#f6efe7]" />
        <motion.div
          className="absolute inset-[8px] z-10 overflow-hidden rounded-full bg-[#eef1f5]"
          animate={{ rotate: isThinking ? [0, -1, 1, 0] : 0 }}
          transition={{ duration: 1.4, repeat: Infinity, ease: "easeInOut" }}>
          
          <img
            src="/avatar.png"
            alt="Aarav avatar"
            className="h-full w-full object-cover"
            draggable={false} />
          
          {}
          <motion.img
            src="/avatar.png"
            alt=""
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 h-full w-full object-cover"
            style={{
              clipPath: upperLipClip
            }}
            animate={{
              opacity: isSpeaking ? [0.98, 1, 0.98] : 0.98
            }}
            transition={{ duration: 0.22, repeat: Infinity, ease: "easeInOut" }} />
          
          <motion.img
            src="/avatar.png"
            alt=""
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 h-full w-full object-cover"
            style={{
              clipPath: lowerLipClip,
              transformOrigin: `50% ${lipCenterY - 0.8}%`
            }}
            animate={{
              y: isSpeaking ? [0, 0.8 + mouthOpen * 1.7, 0] : [0, 0.1, 0],
              scaleY: isSpeaking ? [1, 1 + mouthOpen * 0.12, 1] : [1, 1.005, 1]
            }}
            transition={{ duration: 0.21, repeat: Infinity, ease: "easeInOut" }} />
          
          <motion.div
            className="pointer-events-none absolute inset-0"
            style={{
              clipPath: innerMouthClip,
              background:
              "radial-gradient(ellipse at 50% 50%, rgba(34,16,18,0.62) 0%, rgba(34,16,18,0.24) 45%, rgba(34,16,18,0) 85%)"
            }}
            animate={{
              opacity: isSpeaking ? [0.02, 0.2 + mouthOpen * 0.3, 0.02] : [0, 0.02, 0],
              scaleY: isSpeaking ? [0.85, 1 + mouthOpen * 0.35, 0.85] : [0.85, 0.9, 0.85]
            }}
            transformTemplate={({ scaleY }) => `translateZ(0) scaleY(${scaleY})`}
            transition={{ duration: 0.24, repeat: Infinity, ease: "easeInOut" }} />
          
        </motion.div>
        <div className="absolute inset-0 rounded-full ring-4 ring-white/30" />
      </motion.div>

      <div className="flex h-16 items-end gap-1.5" aria-hidden="true">
        {bars.map((value, i) =>
        <motion.div
          key={i}
          className="w-2 rounded-full bg-zinc-300 transition-[height] duration-75"
          style={{
            height: `${Math.max(8, value * 64)}px`,
            opacity: isSpeaking ? 0.95 : 0.45
          }}
          animate={{ scaleY: isSpeaking ? [1, 1.1, 1] : [1, 1.02, 1] }}
          transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.05 }} />

        )}
      </div>

      <div className="text-sm font-medium text-brand-ink">
        Aarav
        <span className="ml-2 text-brand-mute">
          · {isThinking ? "Thinking" : isSpeaking ? "Speaking" : "Listening"}
        </span>
      </div>
    </div>);

}

function SimliAvatar({ audioTrack, isSpeaking, onFailed }) {
  const containerRef = useRef(null);
  const clientRef = useRef(null);
  const [ready, setReady] = useState(false);
  const [errored, setErrored] = useState(false);

  useEffect(() => {
    let cancelled = false;
    let client = null;

    async function bootstrap() {
      try {
        const mod = await import("simli-client");
        const SimliClient = mod.SimliClient || mod.default;
        if (!SimliClient || cancelled) return;

        client = new SimliClient();
        clientRef.current = client;

        client.Initialize({
          apiKey: SIMLI_API_KEY,
          faceID: SIMLI_FACE_ID,
          handleSilence: true,
          videoRef: containerRef.current,
          audioRef: null
        });

        await client.start();
        if (cancelled) return;
        setReady(true);
      } catch (err) {
        console.warn("Simli avatar failed to initialise; falling back.", err);
        setErrored(true);
        if (onFailed) onFailed(err);
      }
    }
    bootstrap();

    return () => {
      cancelled = true;
      try {
        client?.close?.();
      } catch {

      }
      clientRef.current = null;
    };

  }, []);


  useEffect(() => {
    if (!ready || !clientRef.current || !audioTrack) return undefined;

    const mediaStreamTrack =
    audioTrack.mediaStreamTrack || audioTrack._mediaStreamTrack;
    if (!mediaStreamTrack) return undefined;

    let ctx;
    try {
      ctx = new (window.AudioContext || window.webkitAudioContext)({
        sampleRate: 16000
      });
    } catch (err) {
      console.warn("Could not open AudioContext for Simli stream", err);
      return undefined;
    }

    const source = ctx.createMediaStreamSource(new MediaStream([mediaStreamTrack]));
    const processor = ctx.createScriptProcessor(2048, 1, 1);
    source.connect(processor);
    processor.connect(ctx.destination);

    processor.onaudioprocess = (event) => {
      const data = event.inputBuffer.getChannelData(0);
      const pcm = new Int16Array(data.length);
      for (let i = 0; i < data.length; i++) {
        pcm[i] = Math.max(-32768, Math.min(32767, data[i] * 32767));
      }
      try {
        clientRef.current?.sendAudioData?.(new Uint8Array(pcm.buffer));
      } catch {

      }
    };

    return () => {
      try {
        processor.disconnect();
        source.disconnect();
        ctx.close();
      } catch {

      }
    };
  }, [ready, audioTrack]);

  if (errored) return null;

  return (
    <div className="flex flex-col items-center gap-3">
      <div
        className={`relative h-56 w-56 overflow-hidden rounded-full bg-slate-100 shadow-card ${
        isSpeaking ? "animate-speakingGlow" : ""}`
        }>
        
        <video
          ref={containerRef}
          autoPlay
          playsInline
          muted
          className="h-full w-full object-cover" />
        
        {!ready &&
        <div className="absolute inset-0 flex items-center justify-center text-sm text-brand-mute">
            Loading avatar…
          </div>
        }
      </div>
      <div className="text-sm font-medium text-brand-ink">
        Aarav
        <span className="ml-2 text-brand-mute">
          · {isSpeaking ? "Speaking" : "Listening"}
        </span>
      </div>
    </div>);

}

export default function Avatar({ audioTrack, isSpeaking, isThinking = false, speechLevel = 0 }) {
  if (TAVUS_EMBED_URL) {
    return <ProviderIframeAvatar url={TAVUS_EMBED_URL} label="Tavus" />;
  }
  if (BEYOND_PRESENCE_EMBED_URL) {
    return <ProviderIframeAvatar url={BEYOND_PRESENCE_EMBED_URL} label="Beyond Presence" />;
  }

  const useSimli = useMemo(
    () => Boolean(SIMLI_API_KEY && SIMLI_FACE_ID),
    []
  );
  const [simliFailed, setSimliFailed] = useState(false);

  if (useSimli && !simliFailed) {
    return (
      <SimliAvatar
        audioTrack={audioTrack}
        isSpeaking={isSpeaking}
        onFailed={() => setSimliFailed(true)} />);


  }
  return (
    <SvgFallback
      audioTrack={audioTrack}
      isSpeaking={isSpeaking}
      isThinking={isThinking}
      speechLevel={speechLevel} />);


}