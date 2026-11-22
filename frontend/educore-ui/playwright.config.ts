import { defineConfig } from "@playwright/test";

/**
 * Browser tests against the running development stack (docker/frappe + docker/frontend) and its demo data.
 * They read the demo data and do not change it.
 *
 *   npm run e2e
 *
 * E2E_BASE_URL defaults to http://app.educore.localhost (the NPM proxy host). Without that proxy host,
 * point Chrome straight at the Vite container: E2E_HOST_RULES="MAP app.educore.localhost:80 <ip>:5173".
 * Uses the installed Google Chrome (no Playwright browser download).
 */
const hostRules = process.env.E2E_HOST_RULES;

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/results",
  timeout: 30_000,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://app.educore.localhost",
    channel: "chrome",
    screenshot: "only-on-failure",
    launchOptions: { args: hostRules ? [`--host-rules=${hostRules}`] : [] },
  },
});
