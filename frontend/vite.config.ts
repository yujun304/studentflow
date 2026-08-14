import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: { proxy: { "/api": { target: "http://localhost:8000", changeOrigin: true } } },
  build: {
    rollupOptions: {
      input: {
        dashboard: "index.html",
        login: "login/index.html",
        events: "events/index.html",
        tasks: "tasks/index.html",
        taskEditor: "tasks/editor/index.html",
        notices: "notices/index.html",
        noticeEditor: "notices/editor/index.html",
        reviews: "reviews/index.html",
        more: "more/index.html",
        admin: "admin/index.html",
      },
    },
  },
});
