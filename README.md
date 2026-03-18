# PLC Telemetry 2.0

`dev/2.0` greenfield branch for the Node.js/TypeScript-first replatform.

## Direction

- Backend: Node.js + TypeScript
- Frontend: React + TypeScript
- Runtime target: remote Windows 10 device with a single JavaScript runtime
- PLC transport strategy: UDP first-class, ADS behind a dedicated feasibility spike

This branch keeps the legacy Python code as a reference, but the 2.0 entrypoint is now the npm workspace under `apps/`.

## Workspace Layout

- `apps/server`: Express API for sessions, exports, transport capability reporting, and future live telemetry
- `apps/web`: React/Vite operator UI
- `packages/contracts`: shared TypeScript API contracts
- `docs/adr`: architecture decisions for the replatform

## Quick Start

```bash
npm install
npm run dev
```

Default URLs:

- Web UI: `http://localhost:5173`
- API: `http://localhost:4000`

To point the server at a different session directory:

```powershell
$env:PLC_TELEMETRY_SESSIONS_DIR='C:\telemetry\sessions'
npm run dev:server
```

## Current Coverage

- Session list API
- Session detail API
- Channel metadata API
- Capability/health API
- Sample/export routes stubbed for parity planning

## Near-Term 2.0 Goals

1. Validate ADS feasibility from Node.js on the target Windows environment.
2. Add session sample paging/downsampling for the viewer.
3. Add CSV/PNG export parity.
4. Add live telemetry and recording control after offline parity is stable.
