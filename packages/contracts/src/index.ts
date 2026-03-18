export type SessionStatus = "completed" | "running" | "failed" | "aborted" | "unknown";

export interface CapabilityFlag {
  name: string;
  status: "available" | "planned" | "spike";
  detail: string;
}

export interface HealthResponse {
  service: string;
  version: string;
  sessionRoot: string;
  capabilities: CapabilityFlag[];
}

export interface SessionListItem {
  id: string;
  projectName: string;
  transport: string;
  status: SessionStatus;
  startedAt: string | null;
  endedAt: string | null;
  sampleCount: number;
}

export interface ChannelSummary {
  channelId: number;
  name: string;
  path: string;
  valueType: string;
  unit: string | null;
  group: string | null;
}

export interface SessionDetail extends SessionListItem {
  storagePath: string;
  channels: ChannelSummary[];
}

export interface ApiMessage {
  message: string;
}
