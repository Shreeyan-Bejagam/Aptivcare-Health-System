







import { useEffect, useRef } from "react";
import { useStore } from "../lib/store.js";

function timeLabel(iso) {
  if (!iso) return "";
  try {
    const d = new Date(iso);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

export default function TranscriptView() {
  const transcript = useStore((s) => s.transcript);
  const endRef = useRef(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [transcript.length]);

  return (
    <aside
      className="flex h-full flex-col rounded-2xl p-4 shadow-soft glass-panel"
      aria-live="polite">
      
      <header className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-brand-ink">Conversation</h3>
        <span className="text-xs text-brand-mute">
          {transcript.length} turn{transcript.length === 1 ? "" : "s"}
        </span>
      </header>

      <div className="soft-scrollbar flex-1 space-y-3 overflow-y-auto pr-1">
        {transcript.length === 0 &&
        <p className="rounded-xl bg-brand-bg px-4 py-6 text-center text-sm text-brand-mute">
            Waiting for call to begin...
          </p>
        }

        {transcript.map((turn) => {
          const isUser = turn.role === "user";
          return (
            <div
              key={turn.id}
              className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
              
              <div
                className={`max-w-[85%] rounded-2xl px-3 py-2 text-sm ${
                isUser ?
                "bg-zinc-100 text-zinc-900 ring-1 ring-zinc-400" :
                "bg-zinc-900 text-zinc-100 ring-1 ring-zinc-700"} ${
                turn.interim ? "opacity-70" : ""}`}>
                
                <div
                  className={`mb-0.5 text-[10px] uppercase tracking-wide ${
                  isUser ? "text-zinc-600" : "text-zinc-400"}`
                  }>
                  
                  {isUser ? "You" : "Aarav"} · {timeLabel(turn.timestamp)}
                </div>
                <div className="leading-relaxed">{turn.text || turn.content}</div>
              </div>
            </div>);

        })}
        <div ref={endRef} />
      </div>
    </aside>);

}