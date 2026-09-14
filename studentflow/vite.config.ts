import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { defineConfig, type Plugin } from "vite";

const clientRoot = path.resolve(import.meta.dirname, "client");
const documentInputs = [
  "index.html",
  "login/index.html",
  "tasks/index.html",
  "tasks/detail.html",
  "community/index.html",
  "proposals/index.html",
  "proposals/detail.html",
  "events/detail.html",
  "announcements/index.html",
  "announcements/detail.html",
  "calendar/index.html",
  "teams/index.html",
  "notifications/index.html",
  "users/index.html",
  "event-create/index.html",
  "tutorial/index.html",
].map(document => path.resolve(clientRoot, document));

const staticDocuments = new Map([
  ["/login", "/login/index.html"],
  ["/tasks", "/tasks/index.html"],
  ["/community", "/community/index.html"],
  ["/proposals", "/proposals/index.html"],
  ["/announcements", "/announcements/index.html"],
  ["/calendar", "/calendar/index.html"],
  ["/teams", "/teams/index.html"],
  ["/notifications", "/notifications/index.html"],
  ["/users", "/users/index.html"],
  ["/event-create", "/event-create/index.html"],
  ["/tutorial", "/tutorial/index.html"],
]);

function mpaDevelopmentRoutes(): Plugin {
  return {
    name: "studentflow-mpa-development-routes",
    configureServer(server) {
      server.middlewares.use((request, _response, next) => {
        if (!request.url) return next();
        const url = new URL(request.url, "http://studentflow.local");
        const pathName = url.pathname.replace(/\/+$/, "") || "/";
        const staticDocument = staticDocuments.get(pathName);
        const detailDocument = /^\/tasks\/[^/]+$/.test(pathName)
          ? "/tasks/detail.html"
          : /^\/proposals\/[^/]+$/.test(pathName)
            ? "/proposals/detail.html"
          : /^\/announcements\/[^/]+$/.test(pathName)
            ? "/announcements/detail.html"
            : /^\/events\/[^/]+$/.test(pathName)
              ? "/events/detail.html"
              : undefined;
        const document = staticDocument ?? detailDocument;
        if (document) request.url = `${document}${url.search}`;
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [mpaDevelopmentRoutes(), react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "client", "src"),
      "@shared": path.resolve(import.meta.dirname, "shared"),
      "@assets": path.resolve(import.meta.dirname, "attached_assets"),
    },
  },
  envDir: path.resolve(import.meta.dirname),
  root: clientRoot,
  build: {
    outDir: path.resolve(import.meta.dirname, "dist/public"),
    emptyOutDir: true,
    rollupOptions: {
      input: documentInputs,
    },
  },
  server: {
    host: true,
    port: 3000,
    proxy: {
      "/api": "http://localhost:8000",
    },
  },
});
