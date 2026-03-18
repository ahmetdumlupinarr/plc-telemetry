import path from "node:path";

export const SERVER_PORT = Number(process.env.PORT ?? 4000);

export const SESSION_ROOT = path.resolve(
  process.env.PLC_TELEMETRY_SESSIONS_DIR ?? path.join(process.cwd(), "sessions"),
);
