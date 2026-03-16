# PLC Telemetry Platform MVP

Python-first telemetry/logger MVP for Beckhoff/TwinCAT-oriented PLC workflows.

## Scope

- ADS-based headless data acquisition
- Session-oriented Parquet recording
- Session metadata and channel metadata storage
- Offline viewer for recorded sessions
- CSV and PNG export

## Quick Start

1. Install the package and dependencies.
2. Update `examples/ads_config.yaml` with your ADS target.
3. Record a session:

```bash
plc-telemetry record --config examples/ads_config.yaml
```

4. List sessions:

```bash
plc-telemetry sessions list
```

5. Open a recorded session:

```bash
plc-telemetry view sessions/<timestamp>_<name>
```
