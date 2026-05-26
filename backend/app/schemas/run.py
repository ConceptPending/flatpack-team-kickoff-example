from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.checklist_run import RunStatus


class RunStart(BaseModel):
    template_id: UUID
    project_handle: str = Field(..., min_length=1, max_length=255)


class RunStatusUpdate(BaseModel):
    status: RunStatus


class RunResponse(BaseModel):
    id: UUID
    template_id: UUID
    template_version: int = Field(..., ge=1)
    owner_id: UUID
    project_handle: str
    status: RunStatus
    started_at: datetime
    completed_at: datetime | None

    model_config = {"from_attributes": True}


class ProgressUpdate(BaseModel):
    """PATCH payload for a single progress row. Either field is optional —
    the route applies whichever is supplied."""

    done: bool | None = None
    note: str | None = None


class ProgressResponse(BaseModel):
    id: UUID
    run_id: UUID
    item_id: UUID
    done: bool
    note: str | None
    done_by_id: UUID | None
    done_at: datetime | None

    model_config = {"from_attributes": True}


class RunProgressSummary(BaseModel):
    """Returned from GET /api/admin/runs/{id}/progress — the equivalent of
    the Flatpack's computeProgress() output."""

    done: int = Field(..., ge=0)
    total: int = Field(..., ge=0)
    pct: int = Field(..., ge=0, le=100)
