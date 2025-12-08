"""Placement API routes."""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

router = APIRouter()


# =============================================================================
# Request/Response Models
# =============================================================================


class TimeRangeModel(BaseModel):
    """Time range within a video."""

    start_time: float = Field(..., ge=0, description="Start time in seconds")
    end_time: float = Field(..., gt=0, description="End time in seconds")


class PositionModel(BaseModel):
    """Position of placement on screen (normalized 0-1)."""

    x: float = Field(..., ge=0, le=1)
    y: float = Field(..., ge=0, le=1)
    width: float = Field(..., gt=0, le=1)
    height: float = Field(..., gt=0, le=1)


class CreatePlacementRequest(BaseModel):
    """Request to create a new placement."""

    video_id: UUID
    product_id: UUID
    time_range: TimeRangeModel
    description: Optional[str] = None
    position: Optional[PositionModel] = None


class UpdatePlacementRequest(BaseModel):
    """Request to update an existing placement."""

    time_range: Optional[TimeRangeModel] = None
    description: Optional[str] = None
    position: Optional[PositionModel] = None


class PlacementResponse(BaseModel):
    """Placement response model."""

    id: UUID
    video_id: UUID
    product_id: UUID
    time_range: TimeRangeModel
    description: Optional[str]
    position: Optional[PositionModel]
    status: str
    file_url: Optional[str]
    created_at: str
    updated_at: str


class PlacementListResponse(BaseModel):
    """Paginated list of placements."""

    data: list[PlacementResponse]
    meta: dict


# =============================================================================
# Routes
# =============================================================================


@router.get("", response_model=PlacementListResponse)
async def list_placements(
    video_id: Optional[UUID] = Query(None, description="Filter by video ID"),
    product_id: Optional[UUID] = Query(None, description="Filter by product ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(20, ge=1, le=100),
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
):
    """
    List placements with optional filters.

    Supports cursor-based pagination for efficient large result sets.
    """
    # TODO: Implement with repository
    return {
        "data": [],
        "meta": {
            "has_more": False,
            "next_cursor": None,
        },
    }


@router.post("", response_model=PlacementResponse, status_code=status.HTTP_201_CREATED)
async def create_placement(request: CreatePlacementRequest):
    """
    Create a new placement.

    Validates:
    - Time range is within video duration
    - Product belongs to active campaign
    - No overlapping placements for same product
    """
    # TODO: Implement with use case
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.get("/{placement_id}", response_model=PlacementResponse)
async def get_placement(placement_id: UUID):
    """Get a placement by ID."""
    # TODO: Implement with repository
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Placement {placement_id} not found",
    )


@router.put("/{placement_id}", response_model=PlacementResponse)
async def update_placement(placement_id: UUID, request: UpdatePlacementRequest):
    """
    Update an existing placement.

    Uses optimistic locking to prevent concurrent modification conflicts.
    """
    # TODO: Implement with use case
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.delete("/{placement_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_placement(placement_id: UUID):
    """
    Delete a placement (soft delete).

    The placement is marked as deleted but retained for audit purposes.
    """
    # TODO: Implement with use case
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )


@router.get("/{placement_id}/file")
async def get_placement_file(placement_id: UUID):
    """
    Get the generated placement file.

    Returns a pre-signed S3 URL for the placement data file.
    Returns 202 Accepted if file generation is still in progress.
    """
    # TODO: Implement with S3 client
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Not implemented yet",
    )
