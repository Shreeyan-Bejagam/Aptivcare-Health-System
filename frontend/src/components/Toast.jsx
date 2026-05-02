







import { useEffect, useState } from "react";

const TYPE_STYLES = {
  info: "border-zinc-600 bg-zinc-900 text-zinc-100",
  warn: "border-zinc-500 bg-zinc-800 text-zinc-200",
  error: "border-zinc-500 bg-zinc-950 text-zinc-300",
  success: "border-zinc-400 bg-zinc-800 text-zinc-100"
};

export default function Toast() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    function onToast(event) {
      const detail = event.detail || {};
      const id = `${Date.now()}-${Math.random()}`;
      const item = {
        id,
        type: detail.type || "info",
        message: detail.message || ""
      };
      setItems((prev) => [...prev, item].slice(-3));
      setTimeout(() => {
        setItems((prev) => prev.filter((i) => i.id !== id));
      }, 4000);
    }
    window.addEventListener("app:toast", onToast);
    return () => window.removeEventListener("app:toast", onToast);
  }, []);

  if (!items.length) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2">
      {items.map((it) =>
      <div
        key={it.id}
        className={`max-w-sm rounded-xl border px-4 py-3 text-sm shadow-card animate-slideIn ${
        TYPE_STYLES[it.type] || TYPE_STYLES.info}`
        }>
        
          {it.message}
        </div>
      )}
    </div>);

}