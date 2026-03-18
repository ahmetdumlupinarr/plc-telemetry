# ADR 0001: Node.js/TypeScript-first 2.0 greenfield replatform

## Status

Accepted on March 18, 2026.

## Context

The legacy PLC Telemetry MVP is Python-first and includes a PySide6 desktop viewer. That stack works, but the 2.0 target environment is a remote Windows 10 device with limited storage and a strong preference for a single runtime with predictable install size.

The design goals for 2.0 are:

- browser-accessible UI on the local network
- one primary runtime for deployment and maintenance
- explicit gating of ADS support behind a feasibility spike
- preservation of the legacy session format as a migration bridge

## Decision

2.0 will start as a greenfield Node.js/TypeScript workspace:

- `apps/server` owns HTTP APIs, future transport adapters, and file access
- `apps/web` owns the operator UI
- `packages/contracts` defines shared API shapes

The browser never talks to PLC hardware directly. UDP and ADS concerns remain on the backend.

## Consequences

### Positive

- Deployment is simplified to a single JavaScript runtime on the target machine.
- The new UI can be accessed from multiple devices on the same network.
- The frontend can evolve independently from Beckhoff-specific transport work.

### Negative

- ADS support is no longer inherited from the mature Python stack and must be validated with a dedicated spike.
- Export and sample paging parity must be rebuilt.

## Follow-up

1. Complete the ADS feasibility spike on the target Windows 10 environment.
2. Implement sample paging and downsampling for the viewer.
3. Add CSV/PNG export parity.
4. Reassess whether any native bridge is needed for ADS if the Node path underperforms.
