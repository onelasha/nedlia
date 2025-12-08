# Nedlia JavaScript SDK

SDK for integrating Nedlia product placement validation into streaming video players.

## Installation

```bash
npm install @nedlia/sdk
# or
pnpm add @nedlia/sdk
```

## Usage

```typescript
import { NedliaPlayer } from '@nedlia/sdk';

const nedlia = new NedliaPlayer({
  apiKey: 'your-api-key',
  videoId: 'video-123',
});

// Attach to video element
nedlia.attach(videoElement);

// Listen for placement events
nedlia.on('placement:show', placement => {
  console.log('Showing placement:', placement.productName);
});

nedlia.on('placement:hide', placement => {
  console.log('Hiding placement:', placement.productName);
});
```

## Features

| Feature               | Description                                |
| --------------------- | ------------------------------------------ |
| Time-based validation | Validate placements at specific timestamps |
| Overlay management    | Show/hide product overlays                 |
| Analytics             | Track placement impressions                |
| Offline support       | Cache placements for offline playback      |

## Supported Players

- HTML5 Video
- Video.js
- HLS.js
- Dash.js
