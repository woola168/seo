import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      "/api/v1/customers": {
        target: "http://127.0.0.1:8001",
        changeOrigin: true,
      },
      "/api/v1/tasks": {
        target: "http://127.0.0.1:8001",
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
