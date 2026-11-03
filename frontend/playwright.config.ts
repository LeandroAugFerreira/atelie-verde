import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
const dataDir = resolve("..", ".local", `e2e-${Date.now()}`);
export default defineConfig({
  testDir: "./tests",
  timeout: 60000,
  fullyParallel: false,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://127.0.0.1:5174",
    viewport: { width: 1672, height: 941 },
    deviceScaleFactor: 1,
  },
  projects: [{ name: "chromium", use: { browserName: "chromium" } }],
  webServer: [
    {
      command: `${process.platform === "win32" ? ".venv\\Scripts\\python.exe" : "python"} -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8016`,
      cwd: "..",
      url: "http://127.0.0.1:8016/api/health",
      env: {
        DATA_DIR: dataDir,
        RAFINHA_CREDENTIALS_DIR: resolve(dataDir, "credentials"),
        SEED_DEMO: "true",
        RAFINHA_PROVIDER: "catalog",
        DATABASE_URL: `sqlite:///${dataDir.replaceAll("\\", "/")}/greenscape.db`,
      },
      timeout: 60000,
    },
    {
      command: "npm run dev -- --port 5174 --strictPort",
      url: "http://127.0.0.1:5174",
      env: { GREENSCAPE_API_TARGET: "http://127.0.0.1:8016" },
      timeout: 30000,
    },
  ],
});
