import datetime as dt
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class RunStatus(str, enum.Enum):
    in_progress = "in_progress"
    completed = "completed"
    abandoned = "abandoned"


class ChecklistRun(Base, TimestampMixin):
    """One walk-through of a ChecklistTemplate by a User, for a project.

    The Flatpack's whole `state.progress` map (one walk-through, ephemeral
    in localStorage) becomes this entity plus its child ChecklistProgress
    rows.

    `template_version` is snapshotted at run-start (see
    reference/decisions.md item 2). Subsequent template-version activations
    don't migrate this run.
    """

    __tablename__ = "checklist_runs"

    id = uuid_pk()
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_templates.id"),
        nullable=False,
        index=True,
    )
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    project_handle: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status"),
        default=RunStatus.in_progress,
        nullable=False,
        index=True,
    )
    started_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
