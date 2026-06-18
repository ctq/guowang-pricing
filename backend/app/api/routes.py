import os
from datetime import datetime
from pathlib import Path

from app.utils import now
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import decode_token
from app.db.session import get_db
from app.schemas.calculation import CalculateRequest, CalculateResponse, ImportResponse, MultiCalculateRequest, MultiCalculateResponse, MultiSheetImportResponse
from app.schemas.mappers import request_to_engine, result_to_response
from app.services.excel import export_result, import_bids_from_xlsx, import_bids_from_xlsx_multi, calculate_multi_sheets
from app.services.records import save_calculation_log, save_summary
from pricing_engine.registry import calculate, list_methods

router = APIRouter(prefix="/api", tags=["pricing"])
DbDep = Annotated[AsyncSession, Depends(get_db)]


def _get_openid_from_request(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        payload = decode_token(auth[7:])
        if payload:
            return payload.get("openid")
    return None

FILES_ROOT = Path(os.environ.get("FILES_ROOT", "../")).resolve()


class FileInfo(BaseModel):
    name: str
    size: int
    mtime: str


class FileContent(BaseModel):
    content: str


class RenamePayload(BaseModel):
    new_name: str


class CreateFilePayload(BaseModel):
    name: str


def _resolve_path(filename: str) -> Path:
    root = FILES_ROOT.resolve()
    path = (root / filename).resolve()
    try:
        path.relative_to(root)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="非法路径") from None
    return path


@router.get("/files")
async def list_files() -> list[FileInfo]:
    files: list[FileInfo] = []
    for p in sorted(FILES_ROOT.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if p.is_file() and p.suffix.lower() == ".md":
            st = p.stat()
            files.append(FileInfo(
                name=p.name,
                size=st.st_size,
                mtime=datetime.fromtimestamp(st.st_mtime).isoformat(),
            ))
    return files


@router.get("/files/{filename}")
async def read_file(filename: str) -> FileContent:
    path = _resolve_path(filename)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    return FileContent(content=path.read_text(encoding="utf-8"))


@router.put("/files/{filename}")
async def write_file(filename: str, payload: FileContent) -> dict[str, str]:
    path = _resolve_path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload.content, encoding="utf-8")
    return {"status": "ok"}


@router.post("/files/{filename}/rename")
async def rename_file(filename: str, payload: RenamePayload) -> dict[str, str]:
    src = _resolve_path(filename)
    dst = _resolve_path(payload.new_name)
    if not src.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    if dst.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="目标文件已存在")
    if dst.suffix.lower() != ".md":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .md 文件")
    src.rename(dst)
    return {"status": "ok"}


@router.post("/files")
async def create_file(payload: CreateFilePayload) -> dict[str, str]:
    name = payload.name.strip()
    if not name.lower().endswith(".md"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .md 文件")
    path = _resolve_path(name)
    if path.exists():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="文件已存在")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"# {name.replace('.md', '')}\n", encoding="utf-8")
    return {"status": "ok"}


@router.delete("/files/{filename}")
async def delete_file(filename: str) -> dict[str, str]:
    path = _resolve_path(filename)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")
    path.unlink()
    return {"status": "ok"}


@router.get("/methods")
async def methods() -> list[dict[str, object]]:
    return list_methods()


@router.post("/calculate", response_model=CalculateResponse)
async def calculate_price(payload: CalculateRequest, request: Request, db: DbDep) -> CalculateResponse:
    openid = _get_openid_from_request(request)
    try:
        result = calculate(request_to_engine(payload))
    except ValueError as exc:
        await save_calculation_log(db, payload, "error", openid=openid, error_message=str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    await save_summary(db, payload, result, openid=openid)
    await save_calculation_log(db, payload, "success", openid=openid, result=result)
    return result_to_response(result)


@router.post("/import-xlsx", response_model=ImportResponse)
async def import_xlsx(file: Annotated[UploadFile, File(...)]) -> ImportResponse:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .xlsx 文件")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件不能超过 10MB")
    try:
        return import_bids_from_xlsx(content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/import-xlsx-multi", response_model=MultiSheetImportResponse)
async def import_xlsx_multi(file: Annotated[UploadFile, File(...)]) -> MultiSheetImportResponse:
    if not file.filename or not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持 .xlsx 文件")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件不能超过 10MB")
    try:
        return import_bids_from_xlsx_multi(content)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/calculate-multi", response_model=MultiCalculateResponse)
async def calculate_multi(payload: MultiCalculateRequest) -> MultiCalculateResponse:
    try:
        return calculate_multi_sheets(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.post("/export-xlsx")
async def export_xlsx(payload: CalculateRequest) -> Response:
    try:
        result = result_to_response(calculate(request_to_engine(payload))).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    content = export_result(payload, result)
    timestamp = now().strftime("%Y%m%d%H%M%S")
    filename = f"国网价格分测算_{payload.project.tender_no}_{payload.project.section_no}_{payload.project.package_no}_{timestamp}.xlsx"
    encoded_filename = quote(filename)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
