"""Stub of the audit-log recipe's model.

Same pattern as flatpack-invoice-review-example: the table is created
to match the audit-log recipe's contract, but the hook sites are
marked TODO. Full recipe walk is a follow-up.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_log"

    id = uuid_pk()
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(64), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
