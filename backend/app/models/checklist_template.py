import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class ChecklistTemplate(Base, TimestampMixin):
    """A versioned checklist definition. The Flatpack's hard-coded
    `checklist` array becomes editable, versioned database data.

    See reference/promotion-plan.md "ChecklistTemplate **CODE-INFERRED**"
    and reference/decisions.md item 2 for the immutability contract.
    """

    __tablename__ = "checklist_templates"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_template_name_version"),
    )

    id = uuid_pk()
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
