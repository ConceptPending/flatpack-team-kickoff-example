from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.checklist_item import ChecklistItem
from app.models.checklist_section import ChecklistSection
from app.models.checklist_template import ChecklistTemplate
from app.schemas.checklist_template import ChecklistSectionDraft


class ChecklistTemplateService:
    """Template-level operations.

    Versioning contract (see reference/decisions.md item 2):
    - A new POST creates a new ChecklistTemplate row with version = max(
      previous version, 0) + 1.
    - Activating a new version deactivates the prior active one for the
      same name.
    - In-progress runs are NOT migrated. ChecklistRun.template_version is
      snapshotted at run-start.
    """

    @staticmethod
    async def list_all(db: AsyncSession) -> list[ChecklistTemplate]:
        result = await db.execute(
            select(ChecklistTemplate).order_by(
                ChecklistTemplate.name, ChecklistTemplate.version.desc()
            )
        )
        return list(result.scalars().all())

    @staticmethod
    async def get(db: AsyncSession, template_id: UUID) -> ChecklistTemplate | None:
        return await db.get(ChecklistTemplate, template_id)

    @staticmethod
    async def get_active(db: AsyncSession, name: str) -> ChecklistTemplate | None:
        result = await db.execute(
            select(ChecklistTemplate).where(
                ChecklistTemplate.name == name,
                ChecklistTemplate.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def next_version_for(db: AsyncSession, name: str) -> int:
        result = await db.execute(
            select(ChecklistTemplate.version)
            .where(ChecklistTemplate.name == name)
            .order_by(ChecklistTemplate.version.desc())
            .limit(1)
        )
        prior = result.scalar_one_or_none()
        return (prior or 0) + 1

    @staticmethod
    async def create_version(
        db: AsyncSession,
        *,
        name: str,
        sections: list[ChecklistSectionDraft],
        created_by_id: UUID,
        activate: bool = True,
    ) -> ChecklistTemplate:
        # Deactivate the prior active version, if any.
        if activate:
            prior_active = await ChecklistTemplateService.get_active(db, name)
            if prior_active is not None:
                prior_active.is_active = False

        version = await ChecklistTemplateService.next_version_for(db, name)
        template = ChecklistTemplate(
            name=name,
            version=version,
            is_active=activate,
            created_by_id=created_by_id,
        )
        db.add(template)
        await db.flush()  # need template.id for FKs

        # Materialise sections + items.
        for sd in sections:
            section = ChecklistSection(
                template_id=template.id,
                title=sd.title,
                position=sd.position,
            )
            db.add(section)
            await db.flush()
            for it in sd.items:
                item = ChecklistItem(
                    section_id=section.id,
                    text=it.text,
                    why=it.why,
                    position=it.position,
                )
                db.add(item)
        await db.commit()
        await db.refresh(template)
        # TODO(audit-log-recipe): emit template.created event.
        return template

    @staticmethod
    async def sections_with_items(
        db: AsyncSession, template_id: UUID
    ) -> list[tuple[ChecklistSection, list[ChecklistItem]]]:
        sections_result = await db.execute(
            select(ChecklistSection)
            .where(ChecklistSection.template_id == template_id)
            .order_by(ChecklistSection.position)
        )
        sections = list(sections_result.scalars().all())
        if not sections:
            return []
        items_result = await db.execute(
            select(ChecklistItem)
            .where(ChecklistItem.section_id.in_([s.id for s in sections]))
            .order_by(ChecklistItem.position)
        )
        items = list(items_result.scalars().all())
        by_section: dict[UUID, list[ChecklistItem]] = {s.id: [] for s in sections}
        for item in items:
            by_section[item.section_id].append(item)
        return [(s, by_section[s.id]) for s in sections]
