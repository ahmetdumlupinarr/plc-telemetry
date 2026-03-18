import cors from "cors";
import express from "express";

import type { ApiMessage, CapabilityFlag, HealthResponse } from "../../../packages/contracts/src/index.js";
import { SERVER_PORT, SESSION_ROOT } from "./config.js";
import { SessionStore } from "./session-store.js";

const app = express();
const store = new SessionStore(SESSION_ROOT);

const capabilities: CapabilityFlag[] = [
  {
    name: "udp",
    status: "available",
    detail: "Node.js backend will own UDP communication directly.",
  },
  {
    name: "ads",
    status: "spike",
    detail: "ADS support is gated behind the 2.0 feasibility spike on the target Win10 device.",
  },
  {
    name: "samples",
    status: "planned",
    detail: "Parquet sample paging/downsampling is the next API milestone.",
  },
  {
    name: "exports",
    status: "planned",
    detail: "CSV/PNG parity will be implemented after sample access lands.",
  },
];

app.use(cors());
app.use(express.json());

app.get("/api/health", (_request, response) => {
  const payload: HealthResponse = {
    service: "plc-telemetry-server",
    version: "2.0.0-dev",
    sessionRoot: SESSION_ROOT,
    capabilities,
  };
  response.json(payload);
});

app.get("/api/sessions", async (_request, response) => {
  response.json(await store.listSessions());
});

app.get("/api/sessions/:sessionId", async (request, response) => {
  const session = await store.getSession(request.params.sessionId);
  if (!session) {
    response.status(404).json({ message: "Session not found" } satisfies ApiMessage);
    return;
  }
  response.json(session);
});

app.get("/api/sessions/:sessionId/channels", async (request, response) => {
  const channels = await store.getChannels(request.params.sessionId);
  if (!channels) {
    response.status(404).json({ message: "Session not found" } satisfies ApiMessage);
    return;
  }
  response.json(channels);
});

app.get("/api/sessions/:sessionId/samples", (_request, response) => {
  response.status(501).json({
    message: "Sample paging is planned for the next 2.0 milestone.",
  } satisfies ApiMessage);
});

app.post("/api/exports/:format", (request, response) => {
  response.status(501).json({
    message: `Export route '${request.params.format}' is reserved for parity work.`,
  } satisfies ApiMessage);
});

app.listen(SERVER_PORT, () => {
  console.log(`PLC Telemetry server listening on http://localhost:${SERVER_PORT}`);
});
