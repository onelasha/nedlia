# Nedlia Swift SDK

Swift SDK for iOS/macOS video player integration.

## Installation

### Swift Package Manager

```swift
dependencies: [
    .package(url: "https://github.com/onelasha/nedlia-swift-sdk", from: "1.0.0")
]
```

## Usage

```swift
import NedliaSDK

let nedlia = NedliaPlayer(
    apiKey: "your-api-key",
    videoId: "video-123"
)

// Attach to AVPlayer
nedlia.attach(to: avPlayer)

// Listen for placement events
nedlia.onPlacementShow = { placement in
    print("Showing: \(placement.productName)")
}

nedlia.onPlacementHide = { placement in
    print("Hiding: \(placement.productName)")
}
```

## Features

| Feature               | Description                       |
| --------------------- | --------------------------------- |
| AVPlayer integration  | Native iOS/macOS player support   |
| Time-based validation | Validate placements at timestamps |
| Overlay views         | SwiftUI/UIKit overlay components  |
| Offline caching       | Cache placements for offline use  |

## Requirements

- iOS 15.0+ / macOS 12.0+
- Swift 5.9+
