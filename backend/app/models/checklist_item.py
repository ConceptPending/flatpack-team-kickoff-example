import uuid

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class ChecklistItem(Base, TimestampMixin):
    """An item within a ChecklistSection. Mirrors the Flatpack manifest's
    ChecklistItem entity.

    Same id-type note as ChecklistSection — UUID PK rather than the
    Flatpack's stable-string convention. See reference/decisions.md C.
    """

    __tablename__ = "checklist_items"

    id = uuid_pk()
    section_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_sections.id"),
        nullable=False,
        index=True,
    )
    text: Mapped[str] = mapped_column(String(500), nullable=False)
    why: Mapped[str | None] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
