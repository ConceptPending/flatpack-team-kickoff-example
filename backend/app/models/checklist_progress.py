import datetime as dt
import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class ChecklistProgress(Base, TimestampMixin):
    """One (run, item) pair's state: ticked / not, plus optional note.

    The Flatpack's `state.progress[item_id] = { done, note }` becomes a
    real row with attribution and timestamps. `done_by_id` and `done_at`
    are nullable because un-ticked rows haven't been touched.

    Lifecycle: created when ChecklistRun is started, one row per
    ChecklistItem in the snapshotted template version. See
    reference/decisions.md item A.
    """

    __tablename__ = "checklist_progress"
    __table_args__ = (
        UniqueConstraint("run_id", "item_id", name="uq_progress_run_item"),
    )

    id = uuid_pk()
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_runs.id"),
        nullable=False,
        index=True,
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_items.id"),
        nullable=False,
        index=True,
    )
    done: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    done_by_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    done_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
