from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_admin
from app.models.user import User
from app.schemas.run import (
    ProgressResponse,
    ProgressUpdate,
    RunProgressSummary,
    RunResponse,
    RunStart,
    RunStatusUpdate,
)
from app.services.runs import ProgressService, RunService

router = APIRouter(
    prefix="/api/admin/runs",
    tags=["runs"],
    dependencies=[Depends(get_current_admin)],
)


@router.post("", response_model=RunResponse, status_code=201)
async def start_run(
    body: RunStart,
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    try:
        run = await RunService.start(
            db,
            template_id=body.template_id,
            owner_id=user.id,
            project_handle=body.project_handle,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return run


@router.get("", response_model=list[RunResponse])
async def list_runs(db: AsyncSession = Depends(get_db)):
    return await RunService.list_all(db)


@router.get("/{run_id}", response_model=RunResponse)
async def get_run(run_id: UUID, db: AsyncSession = Depends(get_db)):
    run = await RunService.get(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.patch("/{run_id}/status", response_model=RunResponse)
async def set_run_status(
    run_id: UUID,
    body: RunStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    run = await RunService.get(db, run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return await RunService.set_status(db, run, body.status)


@router.get("/{run_id}/progress", response_model=list[ProgressResponse])
async def list_progress(run_id: UUID, db: AsyncSession = Depends(get_db)):
    return await RunService.progress_for(db, run_id)


@router.get("/{run_id}/summary", response_model=RunProgressSummary)
async def progress_summary(run_id: UUID, db: AsyncSession = Depends(get_db)):
    counts = await RunService.compute_progress(db, run_id)
    return RunProgressSummary(**counts)


@router.patch(
    "/{run_id}/progress/{item_id}", response_model=ProgressResponse
)
async def update_progress(
    run_id: UUID,
    item_id: UUID,
    body: ProgressUpdate,
    user: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    progress = await ProgressService.get(db, run_id, item_id)
    if progress is None:
        raise HTTPException(status_code=404, detail="Progress row not found")
    if body.done is None and body.note is None:
        raise HTTPException(
            status_code=400, detail="Provide at least one of `done` or `note`"
        )
    return await ProgressService.update(
        db,
        progress=progress,
        user_id=user.id,
        done=body.done,
        note=body.note,
    )


@router.get("/{run_id}/markdown")
async def export_markdown(run_id: UUID, db: AsyncSession = Depends(get_db)):
    """Mirrors the Flatpack's `markdown` export."""
    try:
        text = await RunService.to_markdown(db, run_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return PlainTextResponse(
        text,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="run-{run_id}.md"'},
    )
