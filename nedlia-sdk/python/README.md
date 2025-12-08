# Nedlia Python SDK

Python SDK for server-side Nedlia API integration.

## Installation

```bash
pip install nedlia
# or
uv add nedlia
```

## Usage

```python
from nedlia import NedliaClient

client = NedliaClient(api_key="your-api-key")

# Create a placement
placement = client.placements.create(
    video_id="video-123",
    product_id="product-456",
    start_time=30.5,
    end_time=45.0,
    description="Product visible on table",
)

# Validate placements for a video
validation = client.videos.validate("video-123")
print(f"Valid: {validation.is_valid}")

# Generate placement file
file_url = client.videos.generate_placement_file("video-123")
```

## Features

| Feature             | Description                             |
| ------------------- | --------------------------------------- |
| Placement CRUD      | Create, read, update, delete placements |
| Validation          | Validate placements server-side         |
| File generation     | Generate placement data files           |
| Campaign management | Manage advertiser campaigns             |
