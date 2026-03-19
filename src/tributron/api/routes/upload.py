"""Rota RF1 — validação de upload antes do processamento fiscal."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from src.tributron.domain.models import UploadErrorResponse, UploadPayload, UploadResponse
from src.tributron.domain.services.integrity_service import IntegrityService

router = APIRouter(prefix="/v1/upload", tags=["RF1 – Integridade de Upload"])
_svc = IntegrityService()


@router.post(
    "/validate",
    summary="RF1 — Valida integridade do payload antes do processamento fiscal",
    responses={
        200: {"model": UploadResponse, "description": "Upload válido — processamento permitido"},
        422: {"model": UploadErrorResponse, "description": "Payload inválido — processamento bloqueado"},
    },
)
def validate_upload(body: dict) -> JSONResponse:
    result = _svc.validate(body)
    if isinstance(result, UploadErrorResponse):
        return JSONResponse(status_code=422, content=result.model_dump())
    return JSONResponse(status_code=200, content=result.model_dump())
