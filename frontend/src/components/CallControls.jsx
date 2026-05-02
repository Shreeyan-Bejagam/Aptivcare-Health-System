








import { useLocalParticipant } from "@livekit/components-react";
import { useEffect, useState } from "react";

function MicIcon({ muted }) {
  return muted ?
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true">
    
      <line x1="3" y1="3" x2="21" y2="21" />
      <path d="M9 9v3a3 3 0 0 0 5.12 2.12L9 9z" />
      <path d="M12 1a3 3 0 0 0-3 3v6l6 6V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-.11 1.23" />
      <line x1="12" y1="19" x2="12" y2="23" />
    </svg> :

  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true">
    
      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
      <line x1="12" y1="19" x2="12" y2="23" />
    </svg>;

}

function PhoneOffIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true">
      
      <path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92V20a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-3.61-2.65" />
      <line x1="23" y1="1" x2="1" y2="23" />
    </svg>);

}

export default function CallControls({ onEndCall }) {
  const { localParticipant } = useLocalParticipant();
  const [muted, setMuted] = useState(false);

  useEffect(() => {
    if (!localParticipant) return;
    setMuted(!localParticipant.isMicrophoneEnabled);
  }, [localParticipant]);

  async function toggleMute() {
    if (!localParticipant) return;
    const next = !muted;
    try {
      await localParticipant.setMicrophoneEnabled(!next);
      setMuted(next);
    } catch (err) {
      console.error("Mic toggle failed", err);
    }
  }

  return (
    <div className="mt-6 flex items-center justify-center gap-4 rounded-full border border-zinc-800 bg-zinc-950/90 px-4 py-3 shadow-soft backdrop-blur-sm">
      <button
        type="button"
        onClick={toggleMute}
        aria-label={muted ? "Unmute microphone" : "Mute microphone"}
        className={`flex h-12 w-12 items-center justify-center rounded-full transition ${
        muted ?
        "bg-zinc-800 text-zinc-200 ring-1 ring-zinc-600 hover:bg-zinc-700" :
        "bg-brand-elevated text-brand-ink ring-1 ring-zinc-600 hover:bg-zinc-800"}`
        }>
        
        <MicIcon muted={muted} />
      </button>

      <button
        type="button"
        onClick={onEndCall}
        aria-label="End call"
        className="flex h-12 items-center gap-2 rounded-full border border-zinc-400 bg-zinc-100 px-5 text-sm font-semibold text-zinc-900 shadow-soft transition hover:bg-white">
        
        <PhoneOffIcon />
        End call
      </button>
    </div>);

}