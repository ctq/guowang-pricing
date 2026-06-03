from datetime import datetime
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.calculation import CalculateRequest, CalculateResponse, ImportResponse
from app.schemas.mappers import request_to_engine, result_to_response
from app.services.excel import export_result, import_bids_from_xlsx
from app.services.records import save_calculation_log, save_summary
from pricing_engine.registry import calculate, list_methods

router = APIRouter(prefix="/api", tags=["pricing"])
DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/methods")
async def methods() -> list[dict[str, object]]:
    return list_methods()


@router.post("/calculate", response_model=CalculateResponse)
async def calculate_price(payload: CalculateRequest, db: DbDep) -> CalculateResponse:
    try:
        result = calculate(request_to_engine(payload))
    except ValueError as exc:
        await save_calculation_log(db, payload, "error", error_message=str(exc))
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    await save_summary(db, payload, result)
    await save_calculation_log(db, payload, "success", result=result)
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


@router.post("/export-xlsx")
async def export_xlsx(payload: CalculateRequest) -> Response:
    try:
        result = result_to_response(calculate(request_to_engine(payload))).model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
    content = export_result(payload, result)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    filename = f"国网价格分测算_{payload.project.tender_no}_{payload.project.section_no}_{payload.project.package_no}_{timestamp}.xlsx"
    encoded_filename = quote(filename)
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"},
    )
