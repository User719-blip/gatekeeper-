from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from db.deps import get_db
from repo.auth_dependency import require_admin, require_superadmin
from repo.service import ApplicationStore
from schema.schema import Application, ApplicationCreate

router = APIRouter()
store = ApplicationStore()

@router.post("/apply", response_model=Application, status_code=status.HTTP_201_CREATED)
async def apply(payload: ApplicationCreate, db: Session = Depends(get_db)) -> Application:
    return store.create(payload, db)

@router.get("/applications", response_model=list[Application])
async def get_applications(_: dict = Depends(require_admin), db: Session = Depends(get_db)) -> list[Application]:
    return store.list_all(db)

@router.patch("/approve/{application_id}", response_model=Application)
async def approve_application(
    application_id: UUID,
    _: dict = Depends(require_admin),
    db: Session = Depends(get_db),
) -> Application:
    app_item = store.approve(application_id, db)
    if app_item is None:
        raise HTTPException(status_code=404, detail={"message": "Application not found"})
    return app_item

@router.delete("/delete/{application_id}")
async def delete_application(
    application_id: UUID,
    _: dict = Depends(require_superadmin),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    app_item = store.delete(application_id, db)
    if app_item is None:
        raise HTTPException(status_code=404, detail={"message": "Application not found"})
    return {"message": f"Application {app_item.name} deleted successfully"}


