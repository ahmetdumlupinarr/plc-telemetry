import { startTransition, useDeferredValue, useEffect, useState } from "react";

import type { HealthResponse, SessionDetail, SessionListItem, SessionStatus } from "@contracts";

function formatTimestamp(value: string | null): string {
  if (!value) {
    return "N/A";
  }

  return new Date(value).toLocaleString();
}

function statusTone(status: SessionStatus): string {
  switch (status) {
    case "completed":
      return "ok";
    case "running":
      return "warn";
    case "failed":
    case "aborted":
      return "bad";
    default:
      return "muted";
  }
}

async function readJson<T>(input: RequestInfo): Promise<T> {
  const response = await fetch(input);
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return (await response.json()) as T;
}

export function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [selectedSession, setSelectedSession] = useState<SessionDetail | null>(null);
  const [filter, setFilter] = useState("");
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const deferredFilter = useDeferredValue(filter);

  useEffect(() => {
    void Promise.all([
      readJson<HealthResponse>("/api/health"),
      readJson<SessionListItem[]>("/api/sessions"),
    ])
      .then(([healthPayload, sessionsPayload]) => {
        setHealth(healthPayload);
        setSessions(sessionsPayload);
        setSelectedSessionId(sessionsPayload[0]?.id ?? null);
      })
      .catch((reason: Error) => {
        setError(reason.message);
      });
  }, []);

  useEffect(() => {
    if (!selectedSessionId) {
      setSelectedSession(null);
      return;
    }

    setLoadingDetail(true);
    void readJson<SessionDetail>(`/api/sessions/${selectedSessionId}`)
      .then((payload) => {
        startTransition(() => {
          setSelectedSession(payload);
          setLoadingDetail(false);
        });
      })
      .catch((reason: Error) => {
        setError(reason.message);
        setLoadingDetail(false);
      });
  }, [selectedSessionId]);

  const query = deferredFilter.trim().toLowerCase();
  const filteredSessions = !query
    ? sessions
    : sessions.filter((session) => {
        return (
          session.id.toLowerCase().includes(query) ||
          session.projectName.toLowerCase().includes(query) ||
          session.transport.toLowerCase().includes(query)
        );
      });

  return (
    <div className="shell">
      <header className="hero">
        <div>
          <p className="eyebrow">PLC Telemetry 2.0</p>
          <h1>Node/TypeScript-first control room for offline telemetry</h1>
          <p className="lede">
            This branch repositions the product around a single JavaScript runtime for remote Win10 installs.
            UDP is ready, ADS is explicitly gated behind the 2.0 feasibility spike.
          </p>
        </div>
        <div className="capabilityCard">
          <p className="sectionLabel">Server</p>
          <h2>{health?.service ?? "Loading service metadata"}</h2>
          <p>{health?.sessionRoot ?? "Waiting for API..."}</p>
        </div>
      </header>

      {error ? <div className="errorBanner">{error}</div> : null}

      <main className="grid">
        <section className="panel">
          <div className="panelHeader">
            <div>
              <p className="sectionLabel">Sessions</p>
              <h2>Recorded runs</h2>
            </div>
            <input
              className="filterInput"
              placeholder="Filter by session, project, transport"
              value={filter}
              onChange={(event) => setFilter(event.target.value)}
            />
          </div>

          <div className="sessionList">
            {filteredSessions.map((session) => (
              <button
                key={session.id}
                type="button"
                className={`sessionCard ${session.id === selectedSessionId ? "selected" : ""}`}
                onClick={() => {
                  startTransition(() => {
                    setSelectedSessionId(session.id);
                  });
                }}
              >
                <div className="sessionCardTop">
                  <strong>{session.id}</strong>
                  <span className={`status status-${statusTone(session.status)}`}>{session.status}</span>
                </div>
                <p>{session.projectName}</p>
                <div className="metaRow">
                  <span>{session.transport}</span>
                  <span>{session.sampleCount.toLocaleString()} samples</span>
                </div>
              </button>
            ))}

            {filteredSessions.length === 0 ? <p className="emptyState">No sessions match the current filter.</p> : null}
          </div>
        </section>

        <section className="panel detailPanel">
          <div className="panelHeader">
            <div>
              <p className="sectionLabel">Detail</p>
              <h2>{selectedSession?.id ?? "Select a session"}</h2>
            </div>
            <span className={`status status-${statusTone(selectedSession?.status ?? "unknown")}`}>
              {selectedSession?.status ?? "unknown"}
            </span>
          </div>

          {loadingDetail ? <p className="emptyState">Loading session detail...</p> : null}

          {selectedSession ? (
            <>
              <div className="metrics">
                <article>
                  <span>Project</span>
                  <strong>{selectedSession.projectName}</strong>
                </article>
                <article>
                  <span>Transport</span>
                  <strong>{selectedSession.transport}</strong>
                </article>
                <article>
                  <span>Started</span>
                  <strong>{formatTimestamp(selectedSession.startedAt)}</strong>
                </article>
                <article>
                  <span>Ended</span>
                  <strong>{formatTimestamp(selectedSession.endedAt)}</strong>
                </article>
              </div>

              <div className="channelPanel">
                <div className="channelPanelHeader">
                  <div>
                    <p className="sectionLabel">Channels</p>
                    <h3>{selectedSession.channels.length} loaded</h3>
                  </div>
                  <span className="chip">Samples API pending</span>
                </div>

                <div className="tableFrame">
                  <table>
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Type</th>
                        <th>Unit</th>
                        <th>Path</th>
                      </tr>
                    </thead>
                    <tbody>
                      {selectedSession.channels.map((channel) => (
                        <tr key={channel.channelId}>
                          <td>{channel.name}</td>
                          <td>{channel.valueType}</td>
                          <td>{channel.unit ?? "-"}</td>
                          <td>{channel.path}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          ) : (
            <p className="emptyState">Pick a session to inspect metadata and channels.</p>
          )}
        </section>

        <section className="panel capabilityPanel">
          <div className="panelHeader">
            <div>
              <p className="sectionLabel">2.0 Gates</p>
              <h2>Execution constraints</h2>
            </div>
          </div>

          <div className="capabilityGrid">
            {health?.capabilities.map((capability) => (
              <article key={capability.name} className="capabilityTile">
                <div className="sessionCardTop">
                  <strong>{capability.name}</strong>
                  <span className={`status status-${capability.status === "available" ? "ok" : capability.status === "spike" ? "warn" : "muted"}`}>
                    {capability.status}
                  </span>
                </div>
                <p>{capability.detail}</p>
              </article>
            ))}
          </div>
        </section>
      </main>
    </div>
  );
}
