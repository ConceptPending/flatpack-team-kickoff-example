from uuid import UUID

from pydantic import BaseModel, Field


class ChecklistItemDraft(BaseModel):
    text: str = Field(..., min_length=1, max_length=500)
    why: str | None = None
    position: int = Field(..., ge=0)


class ChecklistSectionDraft(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    position: int = Field(..., ge=0)
    items: list[ChecklistItemDraft] = Field(default_factory=list)


class TemplateCreate(BaseModel):
    """POST payload for a new template (or a new version of an existing one)."""

    name: str = Field(..., min_length=1, max_length=255)
    sections: list[ChecklistSectionDraft] = Field(default_factory=list)


class TemplateResponse(BaseModel):
    id: UUID
    name: str
    version: int = Field(..., ge=1)
    is_active: bool
    created_by_id: UUID

    model_config = {"from_attributes": True}


class SectionResponse(BaseModel):
    id: UUID
    title: str
    position: int

    model_config = {"from_attributes": True}


class ItemResponse(BaseModel):
    id: UUID
    section_id: UUID
    text: str
    why: str | None
    position: int

    model_config = {"from_attributes": True}


class TemplateDetailResponse(TemplateResponse):
    sections: list["SectionWithItems"] = Field(default_factory=list)


class SectionWithItems(SectionResponse):
    items: list[ItemResponse] = Field(default_factory=list)


TemplateDetailResponse.model_rebuild()
