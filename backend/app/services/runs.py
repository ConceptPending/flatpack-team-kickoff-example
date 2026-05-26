"""Run + Progress orchestration.

The Flatpack's computeProgress() and toMarkdown() are carried over here
as pure helpers and exposed via methods on RunService.
"""

from __future__ import annotations

import datetime as dt
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist_item import ChecklistItem
from app.models.checklist_progress import ChecklistProgress
from app.models.checklist_run import ChecklistRun, RunStatus
from app.models.checklist_section import ChecklistSection
from app.models.checklist_template import ChecklistTemplate
from app.services.checklist_templates import ChecklistTemplateService


class RunService:
    @staticmethod
    async def start(
        db: AsyncSession,
        *,
        template_id: UUID,
        owner_id: UUID,
        project_handle: str,
    ) -> ChecklistRun:
        """Start a new run. Snapshots the template's current version into
        the run, then materialises one ChecklistProgress per item in that
        version. See reference/decisions.md item A.
        """
        template = await ChecklistTemplateService.get(db, template_id)
        if template is None:
            raise ValueError(f"Template {template_id} not found")

        run = ChecklistRun(
            template_id=template.id,
            template_version=template.version,
            owner_id=owner_id,
            project_handle=project_handle,
            status=RunStatus.in_progress,
            started_at=dt.datetime.now(dt.timezone.utc),
        )
        db.add(run)
        await db.flush()

        # One Progress row per item in the snapshotted template version.
        sections = await ChecklistTemplateService.sections_with_items(db, template_id)
        for _section, items in sections:
            for item in items:
                progress = ChecklistProgress(
                    run_id=run.id,
                    item_id=item.id,
                    done=False,
                )
                db.add(progress)

        await db.commit()
        await db.refresh(run)
        # TODO(audit-log-recipe): emit run.started event.
        return run

    @staticmethod
    async def list_all(db: AsyncSession, limit: int = 50) -> list[ChecklistRun]:
        result = await db.execute(
            select(ChecklistRun).order_by(ChecklistRun.started_at.desc()).limit(limit)
        )
        return list(result.scalars().all())

    @staticmethod
    async def get(db: AsyncSession, run_id: UUID) -> ChecklistRun | None:
        return await db.get(ChecklistRun, run_id)

    @staticmethod
    async def set_status(
        db: AsyncSession, run: ChecklistRun, status: RunStatus
    ) -> ChecklistRun:
        run.status = status
        if status == RunStatus.completed and run.completed_at is None:
            run.completed_at = dt.datetime.now(dt.timezone.utc)
        await db.commit()
        await db.refresh(run)
        # TODO(audit-log-recipe): emit run.status_changed event.
        return run

    @staticmethod
    async def progress_for(db: AsyncSession, run_id: UUID) -> list[ChecklistProgress]:
        result = await db.execute(
            select(ChecklistProgress)
            .where(ChecklistProgress.run_id == run_id)
            .order_by(ChecklistProgress.created_at)
        )
        return list(result.scalars().all())

    @staticmethod
    async def compute_progress(db: AsyncSession, run_id: UUID) -> dict[str, int]:
        """Carries over the Flatpack's computeProgress() function as a pure
        DB query. Returns {"done": int, "total": int, "pct": int}."""
        total_result = await db.execute(
            select(func.count(ChecklistProgress.id)).where(
                ChecklistProgress.run_id == run_id
            )
        )
        total = int(total_result.scalar_one())

        done_result = await db.execute(
            select(func.count(ChecklistProgress.id)).where(
                ChecklistProgress.run_id == run_id,
                ChecklistProgress.done.is_(True),
            )
        )
        done = int(done_result.scalar_one())

        pct = 0 if total == 0 else round((done / total) * 100)
        return {"done": done, "total": total, "pct": pct}

    @staticmethod
    async def to_markdown(db: AsyncSession, run_id: UUID) -> str:
        """Carries over the Flatpack's toMarkdown() function.

        Renders the run as a Markdown summary with one ## section per
        ChecklistSection and `- [x] / - [ ]` lines per item.
        """
        run = await RunService.get(db, run_id)
        if run is None:
            raise ValueError(f"Run {run_id} not found")

        template = await ChecklistTemplateService.get(db, run.template_id)
        if template is None:
            raise ValueError(f"Template {run.template_id} not found")

        progress = await RunService.progress_for(db, run_id)
        progress_by_item = {p.item_id: p for p in progress}

        counts = await RunService.compute_progress(db, run_id)

        lines: list[str] = []
        lines.append(f"# {template.name} (v{run.template_version}) — {run.project_handle}")
        lines.append(
            f"_{run.started_at.isoformat()} · "
            f"{counts['done']}/{counts['total']} ({counts['pct']}%)_"
        )
        lines.append("")

        sections = await ChecklistTemplateService.sections_with_items(
            db, run.template_id
        )
        for section, items in sections:
            lines.append(f"## {section.title}")
            for item in items:
                p = progress_by_item.get(item.id)
                checked = "x" if (p and p.done) else " "
                lines.append(f"- [{checked}] {item.text}")
                if p and p.note and p.note.strip():
                    lines.append(f"  - {p.note.replace(chr(10), ' ')}")
            lines.append("")
        return "\n".join(lines)


class ProgressService:
    @staticmethod
    async def get(
        db: AsyncSession, run_id: UUID, item_id: UUID
    ) -> ChecklistProgress | None:
        result = await db.execute(
            select(ChecklistProgress).where(
                ChecklistProgress.run_id == run_id,
                ChecklistProgress.item_id == item_id,
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def update(
        db: AsyncSession,
        *,
        progress: ChecklistProgress,
        user_id: UUID,
        done: bool | None = None,
        note: str | None = None,
    ) -> ChecklistProgress:
        """Apply a partial update. Tick attribution + timestamps are
        managed here, not at the route layer. See decisions.md item 3
        for the tick/untick lifecycle.
        """
        if done is not None:
            was_done = progress.done
            progress.done = done
            if done and not was_done:
                progress.done_by_id = user_id
                progress.done_at = dt.datetime.now(dt.timezone.utc)
                # TODO(audit-log-recipe): emit progress.ticked event.
            elif not done and was_done:
                progress.done_by_id = None
                progress.done_at = None
                # TODO(audit-log-recipe): emit progress.unticked event.

        if note is not None:
            progress.note = note
            # TODO(audit-log-recipe): emit progress.note_edited event.

        await db.commit()
        await db.refresh(progress)
        return progress
