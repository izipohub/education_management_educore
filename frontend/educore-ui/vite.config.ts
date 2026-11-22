import { fileURLToPath, URL } from "node:url";
import tailwindcss from "@tailwindcss/vite";
import vue from "@vitejs/plugin-vue";
import { defineConfig, loadEnv } from "vite";

// In development the browser talks only to Vite (one origin), and Vite forwards Frappe's paths to the
// bench. So Frappe's session cookie and CSRF checks work as they will behind the production proxy.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const frappe = env.FRAPPE_URL || "http://educore-frappe:8000";
  const realtime = env.FRAPPE_REALTIME_URL || "http://educore-frappe:9000";
  const site = env.FRAPPE_SITE || "educore.localhost";
  // Frappe picks the site from this header before the Host header
  const toFrappe = { target: frappe, headers: { "X-Frappe-Site-Name": site } };

  return {
    plugins: [vue(), tailwindcss()],
    resolve: {
      alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
    },
    server: {
      host: "0.0.0.0",
      port: 5173,
      strictPort: true,
      allowedHosts: [env.APP_HOST || "app.educore.localhost", "localhost"],
      // Playwright writes here while tests run (dot-files too, which globs skip); a reload mid-test breaks them
      watch: { ignored: [/[\\/]e2e[\\/]results[\\/]/, /[\\/]playwright-report[\\/]/] },
      proxy: {
        "/api": toFrappe,
        "/assets": toFrappe,
        "/files": toFrappe,
        "/private": toFrappe,
        "/socket.io": { ...toFrappe, target: realtime, ws: true },
      },
    },
  };
});
