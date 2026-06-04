from fastapi import APIRouter, Depends, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.shelf_service import ShelfService
from app.schemas.shelf import ShelfCreate, ShelfUpdate, ShelfOut
import io

router = APIRouter(prefix="/api/shelves", tags=["shelves"])


def get_shelf_service(db: Session = Depends(get_db)):
    return ShelfService(db)


@router.get("", response_model=list[ShelfOut])
def list_shelves(
    svc: ShelfService = Depends(get_shelf_service),
):
    return svc.list_shelves()


@router.get("/export")
def export_shelves(svc: ShelfService = Depends(get_shelf_service)):
    csv_content = svc.export_csv()
    return StreamingResponse(
        io.BytesIO(csv_content.encode("utf-8-sig")),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=shelves.csv"},
    )


@router.get("/{shelf_id}", response_model=ShelfOut)
def get_shelf(shelf_id: int, svc: ShelfService = Depends(get_shelf_service)):
    return svc.get_shelf(shelf_id)


@router.post("", response_model=ShelfOut, status_code=201)
def create_shelf(data: ShelfCreate, svc: ShelfService = Depends(get_shelf_service)):
    return svc.create_shelf(data)


@router.put("/{shelf_id}", response_model=ShelfOut)
def update_shelf(shelf_id: int, data: ShelfUpdate, svc: ShelfService = Depends(get_shelf_service)):
    return svc.update_shelf(shelf_id, data)


@router.delete("/{shelf_id}", status_code=204)
def delete_shelf(shelf_id: int, svc: ShelfService = Depends(get_shelf_service)):
    svc.delete_shelf(shelf_id)


@router.post("/import")
async def import_shelves(file: UploadFile = File(...), svc: ShelfService = Depends(get_shelf_service)):
    content = await file.read()
    return svc.import_preview(content)


@router.post("/import/confirm")
def confirm_import(data: dict, svc: ShelfService = Depends(get_shelf_service)):
    return svc.import_confirm(data.get("rows", []))
