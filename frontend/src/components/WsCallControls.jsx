import { useCallback, useEffect, useRef, useState } from "react";

function MicIcon({ muted }) {
  return muted ?
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <line x1="3" y1="3" x2="21" y2="21" />
      <path d="M9 9v3a3 3 0 0 0 5.12 2.12L9 9z" />
      <path d="M12 1a3 3 0 0 0-3 3v6l6 6V4a3 3 0 0 0-3-3z" />
    </svg> :

  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
    </svg>;

}

export default function WsCallControls({ stream, onEndCall }) {
  const [muted, setMuted] = useState(false);
  const streamRef = useRef(stream);

  useEffect(() => {
    streamRef.current = stream;
  }, [stream]);

  const toggleMute = useCallback(() => {
    const s = streamRef.current;
    if (!s) return;
    const next = !muted;
    s.getAudioTracks().forEach((t) => {
      t.enabled = !next;
    });
    setMuted(next);
  }, [muted]);

  return (
    <div className="mt-6 flex items-center justify-center gap-4 rounded-full border border-zinc-800 bg-zinc-950/90 px-4 py-3 shadow-soft backdrop-blur-sm">
      <button
        type="button"
        onClick={toggleMute}
        aria-label={muted ? "Unmute microphone" : "Mute microphone"}
        className={`flex h-12 w-12 items-center justify-center rounded-full transition ${
        muted ? "bg-zinc-800 text-zinc-200 ring-1 ring-zinc-600 hover:bg-zinc-700" : "bg-zinc-900 text-zinc-100 ring-1 ring-zinc-600 hover:bg-zinc-800"}`
        }>
        
        <MicIcon muted={muted} />
      </button>
      <button
        type="button"
        onClick={onEndCall}
        className="flex h-12 items-center gap-2 rounded-full border border-zinc-400 bg-zinc-100 px-5 text-sm font-semibold text-zinc-900 shadow-soft transition hover:bg-white">
        
        End call
      </button>
    </div>);

}