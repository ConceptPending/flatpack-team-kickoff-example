import uuid

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class ChecklistSection(Base, TimestampMixin):
    """A section within a ChecklistTemplate. Mirrors the Flatpack
    manifest's ChecklistSection entity.

    Note: the Flatpack manifest declares `id` as `string`. The Baseplate
    version uses a UUID primary key (Baseplate convention). This is a
    deliberate convention shift documented in reference/decisions.md
    item C — the verifier honestly WARNs on the type mismatch.
    """

    __tablename__ = "checklist_sections"

    id = uuid_pk()
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("checklist_templates.id"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
