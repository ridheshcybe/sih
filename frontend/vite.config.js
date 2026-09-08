import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// The dev server proxies API + WebSocket traffic to the FastAPI backend so
// the frontend can use same-origin URLs and no CORS configuration is needed
// in the browser.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});