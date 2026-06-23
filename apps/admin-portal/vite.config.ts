import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/api/customers": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/api/tasks": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/api/geo": {
        target: "http://127.0.0.1:8002",
        changeOrigin: true,
      },
      "/api/v1/geo-tracking": {
        target: "http://127.0.0.1:8002",
        changeOrigin: true,
      },
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/health": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
