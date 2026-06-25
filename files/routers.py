import io
import json
import os
import uuid
import zipfile
from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pathlib import Path

from core.config import settings
from core.permissions import min_perms
from users.models import User
from files.models import UploadedFile, WorkScan
from files.schemas import UploadFileResponse, WorkUploadResponse

router = APIRouter()

STORAGE_DIR = Path("storage/uploads")
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

WORKS_BASE_DIR = Path("storage/works")


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


@router.post("/upload/work/{work_id}", response_model=WorkUploadResponse)
@min_perms(settings.OPERATOR_ROLE)
async def upload_work_scans(work_id: uuid.UUID, current_user: User, file: UploadFile = File(...)):
    work_dir = WORKS_BASE_DIR / str(work_id)
    if not work_dir.exists() or not work_dir.is_dir():
        raise HTTPException(404, f"Папка для работы {work_id} не найдена в системе. Проверьте UUID.")

    if not file.filename.lower().endswith('.zip'):
        raise HTTPException(400, "Разрешены только архивы формата .zip")

    try:
        zip_content = await file.read()
        zip_buffer = io.BytesIO(zip_content)
        
        with zipfile.ZipFile(zip_buffer) as z:
            namelist = z.namelist()
            
            results_file = next((f for f in namelist if f.endswith('results.json')), None)
            results_data = {}
            
            if results_file:
                with z.open(results_file) as rf:
                    results_data = json.load(rf)

            scans_processed = 0

            for filename in namelist:
                if filename.endswith('/') or filename.endswith('results.json'):
                    continue
                
                path_obj = Path(filename)
                if path_obj.suffix.lower() == '.pdf':
                    try:
                        work_number = int(path_obj.stem)
                    except ValueError:
                        continue
                    
                    pdf_data = z.read(filename)
                    target_pdf_path = work_dir / f"{work_number}.pdf"
                    
                    with open(target_pdf_path, "wb") as pdf_out:
                        pdf_out.write(pdf_data)
                    
                    scan_results = results_data.get(str(work_number)) or {}

                    await WorkScan.update_or_create(
                        work_id=work_id,
                        work_number=work_number,
                        defaults={"results": scan_results}
                    )
                    scans_processed += 1

        return WorkUploadResponse(
            work_id=work_id,
            scans_processed=scans_processed,
            status="success"
        )

    except zipfile.BadZipFile:
        raise HTTPException(400, "Передан некорректный или поврежденный ZIP-архив")
    except Exception as e:
        raise HTTPException(500, f"Внутренняя ошибка при обработке архива: {str(e)}")


@router.get("/work/{work_id}/scan/{scan_id}")
async def download_work_scan(work_id: uuid.UUID, scan_id: uuid.UUID):
    scan = await WorkScan.get_or_none(id=scan_id, work_id=work_id)
    if not scan:
        raise HTTPException(404, "Скан не найден или не принадлежит указанной работе")

    file_path = WORKS_BASE_DIR / str(work_id) / f"{scan.work_number}.pdf"

    if not file_path.exists():
        raise HTTPException(404, "Файл скана физически отсутствует на сервере")

    return FileResponse(
        path=str(file_path),
        filename=f"{scan.work_number}.pdf",
        media_type="application/pdf"
    )
