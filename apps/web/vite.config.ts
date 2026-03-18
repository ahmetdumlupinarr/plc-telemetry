import path from "node:path";

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@contracts": path.resolve(__dirname, "../../packages/contracts/src/index.ts"),
    },
  },
  server: {
    port: 5173,
    fs: {
      allow: [path.resolve(__dirname, "../..")],
    },
    proxy: {
      "/api": "http://localhost:4000",
    },
  },
});
