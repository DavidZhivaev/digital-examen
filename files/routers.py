import os
import uuid
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path

from core.permissions import min_perms
from users.models import User
from files.models import UploadedFile
from files.schemas import UploadFileResponse

router = APIRouter()

STORAGE_DIR = Path("storage/uploads")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload", response_model=UploadFileResponse)
@min_perms(2)
async def upload_file(current_user: User, file: UploadFile = File(...)):
    file_id = uuid.uuid4()
    extension = Path(file.filename).suffix
    
    saved_filename = f"{file_id}{extension}"
    target_path = STORAGE_DIR / saved_filename

    try:
        with target_path.open("wb") as buffer:
            while chunk := await file.read(1024 * 1024):
                buffer.write(chunk)
    except Exception as e:
        raise HTTPException(500, f"Ошибка при сохранении файла на диск: {str(e)}")

    db_file = await UploadedFile.create(
        id=file_id,
        original_name=file.filename,
        file_path=str(target_path),
        mime_type=file.content_type,
        uploaded_by=current_user
    )

    return db_file


@router.get("/{file_id}")
async def download_file(file_id: uuid.UUID):
    db_file = await UploadedFile.get_or_none(id=file_id)
    if not db_file:
        raise HTTPException(404, "Файл с таким ID не найден в системе")

    if not os.path.exists(db_file.file_path):
        raise HTTPException(404, "Файл физически отсутствует на сервере")

    return FileResponse(
        path=db_file.file_path,
        filename=db_file.original_name,
        media_type=db_file.mime_type
    )