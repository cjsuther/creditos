import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Portal público del ciudadano. Puerto 5174 (el backoffice usa 5173).
// En dev se hace proxy de /api hacia el backend (mismo backend que el sistema interno).
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5174,
    proxy: {
      "/api": {
        target: process.env.VITE_API_TARGET || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
