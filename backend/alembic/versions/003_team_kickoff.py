"""Drop items, add checklist tables + audit_log stub

Revision ID: 003
Revises: 002
Create Date: 2026-05-26 00:00:00.000000

Promotion from the Flatpack at
github.com/ConceptPending/flatpack/templates/checklist.html v0.1.0.

Five entities (the two manifest-asserted ones — ChecklistSection,
ChecklistItem — plus three promoted ones — ChecklistTemplate,
ChecklistRun, ChecklistProgress) and the audit_log stub.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the example Item table.
    op.drop_table("items")

    # ChecklistTemplate: versioned definition.
    op.create_table(
        "checklist_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column(
            "created_by_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("name", "version", name="uq_template_name_version"),
    )
    op.create_index(
        "ix_checklist_templates_created_by_id",
        "checklist_templates",
        ["created_by_id"],
    )

    # ChecklistSection: per-template-version section.
    op.create_table(
        "checklist_sections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("checklist_templates.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_checklist_sections_template_id",
        "checklist_sections",
        ["template_id"],
    )

    # ChecklistItem: per-section item.
    op.create_table(
        "checklist_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "section_id",
            UUID(as_uuid=True),
            sa.ForeignKey("checklist_sections.id"),
            nullable=False,
        ),
        sa.Column("text", sa.String(500), nullable=False),
        sa.Column("why", sa.Text, nullable=True),
        sa.Column("position", sa.Integer, nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_checklist_items_section_id", "checklist_items", ["section_id"]
    )

    # ChecklistRun: one walk-through.
    run_status = sa.Enum(
        "in_progress", "completed", "abandoned", name="run_status"
    )
    op.create_table(
        "checklist_runs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "template_id",
            UUID(as_uuid=True),
            sa.ForeignKey("checklist_templates.id"),
            nullable=False,
        ),
        sa.Column("template_version", sa.Integer, nullable=False),
        sa.Column(
            "owner_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("project_handle", sa.String(255), nullable=False),
        sa.Column(
            "status", run_status, nullable=False, server_default="in_progress"
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index(
        "ix_checklist_runs_template_id", "checklist_runs", ["template_id"]
    )
    op.create_index("ix_checklist_runs_owner_id", "checklist_runs", ["owner_id"])
    op.create_index("ix_checklist_runs_status", "checklist_runs", ["status"])

    # ChecklistProgress: per-(run, item) state.
    op.create_table(
        "checklist_progress",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "run_id",
            UUID(as_uuid=True),
            sa.ForeignKey("checklist_runs.id"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("checklist_items.id"),
            nullable=False,
        ),
        sa.Column("done", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "done_by_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("done_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.UniqueConstraint("run_id", "item_id", name="uq_progress_run_item"),
    )
    op.create_index(
        "ix_checklist_progress_run_id", "checklist_progress", ["run_id"]
    )
    op.create_index(
        "ix_checklist_progress_item_id", "checklist_progress", ["item_id"]
    )

    # Audit log — table only; hooks are TODO markers in the route code.
    op.create_table(
        "audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("resource_type", sa.String(64), nullable=False),
        sa.Column("resource_id", sa.String(64), nullable=True),
        sa.Column("extra", sa.JSON, nullable=False, server_default="{}"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_action", "audit_log", ["action"])
    op.create_index("ix_audit_log_resource_type", "audit_log", ["resource_type"])


def downgrade() -> None:
    op.drop_index("ix_audit_log_resource_type", table_name="audit_log")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_index("ix_audit_log_user_id", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_checklist_progress_item_id", table_name="checklist_progress")
    op.drop_index("ix_checklist_progress_run_id", table_name="checklist_progress")
    op.drop_table("checklist_progress")

    op.drop_index("ix_checklist_runs_status", table_name="checklist_runs")
    op.drop_index("ix_checklist_runs_owner_id", table_name="checklist_runs")
    op.drop_index("ix_checklist_runs_template_id", table_name="checklist_runs")
    op.drop_table("checklist_runs")
    op.execute("DROP TYPE IF EXISTS run_status")

    op.drop_index("ix_checklist_items_section_id", table_name="checklist_items")
    op.drop_table("checklist_items")

    op.drop_index("ix_checklist_sections_template_id", table_name="checklist_sections")
    op.drop_table("checklist_sections")

    op.drop_index(
        "ix_checklist_templates_created_by_id", table_name="checklist_templates"
    )
    op.drop_table("checklist_templates")

    # Recreate items.
    op.create_table(
        "items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "is_active", sa.Boolean, nullable=False, server_default="true"
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
    )
