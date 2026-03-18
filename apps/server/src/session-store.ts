import fs from "node:fs/promises";
import path from "node:path";

import type { ChannelSummary, SessionDetail, SessionListItem, SessionStatus } from "../../../packages/contracts/src/index.js";

interface SessionManifest {
  session_id: string;
  project_name?: string;
  transport?: string;
  status?: string;
  start_time?: string | null;
  end_time?: string | null;
  storage_path?: string;
  stats?: {
    sample_count?: number;
  };
}

interface SignalDefinition {
  channel_id: number;
  name: string;
  path: string;
  value_type?: string;
  unit?: string | null;
  group?: string | null;
}

const MANIFEST_FILE = "session.json";
const CHANNELS_FILE = "channels.json";

function normalizeStatus(value: string | undefined): SessionStatus {
  const normalized = String(value ?? "unknown").toLowerCase();
  if (
    normalized === "completed" ||
    normalized === "running" ||
    normalized === "failed" ||
    normalized === "aborted"
  ) {
    return normalized;
  }
  return "unknown";
}

function toSessionListItem(sessionPath: string, manifest: SessionManifest): SessionListItem {
  return {
    id: manifest.session_id || path.basename(sessionPath),
    projectName: manifest.project_name ?? "Unknown project",
    transport: String(manifest.transport ?? "unknown").toUpperCase(),
    status: normalizeStatus(manifest.status),
    startedAt: manifest.start_time ?? null,
    endedAt: manifest.end_time ?? null,
    sampleCount: Number(manifest.stats?.sample_count ?? 0),
  };
}

function toChannelSummary(channel: SignalDefinition): ChannelSummary {
  return {
    channelId: channel.channel_id,
    name: channel.name,
    path: channel.path,
    valueType: String(channel.value_type ?? "unknown"),
    unit: channel.unit ?? null,
    group: channel.group ?? null,
  };
}

export class SessionStore {
  constructor(private readonly sessionRoot: string) {}

  async listSessions(): Promise<SessionListItem[]> {
    try {
      const entries = await fs.readdir(this.sessionRoot, { withFileTypes: true });
      const items = await Promise.all(
        entries
          .filter((entry) => entry.isDirectory())
          .map(async (entry) => {
            const sessionPath = path.join(this.sessionRoot, entry.name);
            try {
              const manifest = await this.readManifest(sessionPath);
              return toSessionListItem(sessionPath, manifest);
            } catch {
              return null;
            }
          }),
      );

      return items
        .filter((item): item is SessionListItem => item !== null)
        .sort((left, right) => (right.startedAt ?? "").localeCompare(left.startedAt ?? ""));
    } catch {
      return [];
    }
  }

  async getSession(sessionId: string): Promise<SessionDetail | null> {
    const sessionPath = path.join(this.sessionRoot, sessionId);
    try {
      const manifest = await this.readManifest(sessionPath);
      const channels = await this.readChannels(sessionPath);

      return {
        ...toSessionListItem(sessionPath, manifest),
        storagePath: manifest.storage_path ?? sessionPath,
        channels: channels.map(toChannelSummary),
      };
    } catch {
      return null;
    }
  }

  async getChannels(sessionId: string): Promise<ChannelSummary[] | null> {
    const sessionPath = path.join(this.sessionRoot, sessionId);
    try {
      const channels = await this.readChannels(sessionPath);
      return channels.map(toChannelSummary);
    } catch {
      return null;
    }
  }

  private async readManifest(sessionPath: string): Promise<SessionManifest> {
    const raw = await fs.readFile(path.join(sessionPath, MANIFEST_FILE), "utf8");
    return JSON.parse(raw) as SessionManifest;
  }

  private async readChannels(sessionPath: string): Promise<SignalDefinition[]> {
    const raw = await fs.readFile(path.join(sessionPath, CHANNELS_FILE), "utf8");
    return JSON.parse(raw) as SignalDefinition[];
  }
}
