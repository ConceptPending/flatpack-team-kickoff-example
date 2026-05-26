from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_admin
from app.models.user import User
from app.schemas.checklist_template import (
    SectionWithItems,
    TemplateCreate,
    TemplateDetailResponse,
    TemplateResponse,
)
from app.services.checklist_templates import ChecklistTemplateService

router = APIRouter(
    prefix="/api/admin/checklist-templates",
    tags=["checklist-templates"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("", response_model=list[TemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    return await ChecklistTemplateService.list_all(db)


@router.post("", response_model=TemplateResponse, status_code=201)
async def create_template(
    body: TemplateCreate,
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    """Create a new template OR a new version of an existing template
    (same `name` → next version, activated by default; prior active
    version is deactivated)."""
    if not user.is_admin:
        raise HTTPException(
            status_code=403, detail="Only admins can create templates"
        )
    template = await ChecklistTemplateService.create_version(
        db,
        name=body.name,
        sections=body.sections,
        created_by_id=user.id,
        activate=True,
    )
    return template


@router.get("/{template_id}", response_model=TemplateDetailResponse)
async def get_template(template_id: UUID, db: AsyncSession = Depends(get_db)):
    template = await ChecklistTemplateService.get(db, template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    sections_with_items = await ChecklistTemplateService.sections_with_items(
        db, template_id
    )
    sections_payload = [
        SectionWithItems(
            id=section.id,
            title=section.title,
            position=section.position,
            items=[
                {
                    "id": item.id,
                    "section_id": item.section_id,
                    "text": item.text,
                    "why": item.why,
                    "position": item.position,
                }
                for item in items
            ],
        )
        for section, items in sections_with_items
    ]
    return TemplateDetailResponse(
        id=template.id,
        name=template.name,
        version=template.version,
        is_active=template.is_active,
        created_by_id=template.created_by_id,
        sections=sections_payload,
    )
