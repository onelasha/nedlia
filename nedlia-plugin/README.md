# Nedlia Plugins

Video editing platform plugins for adding product placements.

## Available Plugins

| Plugin        | Platform         | Status  |
| ------------- | ---------------- | ------- |
| `finalcut/`   | Final Cut Pro    | Planned |
| `davinci/`    | DaVinci Resolve  | Planned |
| `lumafusion/` | LumaFusion (iOS) | Planned |

## Common Features

All plugins provide:

- **Time Marking**: Add product placements with time ranges
- **Control Panel**: User-friendly interface for managing placements
- **Server Integration**: Sync placements to Nedlia server
- **File Generation**: Export placement data files

## Architecture

Plugins share a common Swift core with platform-specific UI:

```
shared/           # Shared Swift code (planned)
  NedliaCore/     # Core logic
  NedliaAPI/      # API client

finalcut/         # Final Cut Pro specific
davinci/          # DaVinci Resolve specific
lumafusion/       # LumaFusion specific
```
