













import { create } from "zustand";

const initialSession = {
  id: null,
  livekitToken: null,
  livekitUrl: null,
  room: null,
  status: "idle",
  startedAt: null
};

export const useStore = create((set, get) => ({
  session: { ...initialSession },
  toolEvents: [],
  transcript: [],
  summary: null,
  user: { phone: null, name: null },


  setSession(payload) {
    set({
      session: { ...get().session, ...payload }
    });
  },
  setStatus(status) {
    set({ session: { ...get().session, status } });
  },


  pushToolEvent(event) {
    const enriched = {
      ...event,
      timestamp: event.timestamp || new Date().toISOString(),
      id: event.id || `${event.tool}-${Date.now()}-${Math.random()}`
    };
    set({ toolEvents: [...get().toolEvents, enriched] });
  },


  pushTranscript(turn) {
    const enriched = {
      ...turn,
      timestamp: turn.timestamp || new Date().toISOString(),
      id: turn.id || `${turn.role}-${Date.now()}-${Math.random()}`
    };
    set({ transcript: [...get().transcript, enriched] });
  },

  upsertTranscript(turn) {


    const list = get().transcript;
    const lastIndex = (() => {
      for (let i = list.length - 1; i >= 0; i--) {
        if (list[i].role === turn.role && list[i].interim) return i;
      }
      return -1;
    })();
    if (lastIndex === -1) {
      set({
        transcript: [
        ...list,
        { ...turn, id: turn.id || `${turn.role}-${Date.now()}` }]

      });
      return;
    }
    const next = [...list];
    next[lastIndex] = { ...next[lastIndex], ...turn };
    set({ transcript: next });
  },


  setSummary(summary) {
    set({ summary });
  },


  setUser(user) {
    set({ user: { ...get().user, ...user } });
  },


  reset() {
    set({
      session: { ...initialSession },
      toolEvents: [],
      transcript: [],
      summary: null,
      user: { phone: null, name: null }
    });
  }
}));