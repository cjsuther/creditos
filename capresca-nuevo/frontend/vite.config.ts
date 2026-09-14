import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El backend se expone en :8000. En dev se hace proxy de /api hacia el backend.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
