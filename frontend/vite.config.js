/**
 * Vite configuration.
 *
 * - Uses the official React plugin (Babel pipeline, fast refresh).
 * - Dev server binds to 5173 to match the backend's CORS allowlist default.
 */

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
  },
  preview: {
    port: 5173,
  },
  build: {
    sourcemap: true,
    target: "es2020",
  },
});
