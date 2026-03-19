"""
RF1 — Serviço de Integridade de Upload.

Responsabilidade: validar o payload de upload antes de qualquer
processamento fiscal, garantindo que dados corrompidos, incompletos
ou com hash divergente sejam bloqueados imediatamente.

Regras de negócio implementadas:
  - Presença de metadados obrigatórios (cycle, phase, trace_id)
  - Base64 válido em todos os documentos
  - Hash SHA-256 consistente com o conteúdo decodificado
  - Tamanho declarado igual ao tamanho real do conteúdo
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from src.tributron.domain.models import UploadErrorResponse, UploadPayload, UploadResponse

logger = logging.getLogger(__name__)

_AUDIT_LOG = Path(__file__).parent.parent.parent.parent.parent / "src" / "testes" / "rf1" / "logs" / "integrity_audit.jsonl"


def _write_audit(entry: dict[str, Any]) -> None:
    _AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with _AUDIT_LOG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")


class IntegrityService:
    """
    Valida um payload de upload de acordo com o contrato RF1.

    Retorna UploadResponse em caso de sucesso (HTTP 200) ou
    UploadErrorResponse em caso de violação (HTTP 422).
    """

    CURRENT_SCHEMA_VERSION = "1.0.0"

    def validate(self, raw: dict[str, Any]) -> UploadResponse | UploadErrorResponse:
        evaluated_at = datetime.now(tz=timezone.utc).isoformat()
        request_id = raw.get("request_id", "unknown")

        try:
            payload = UploadPayload.model_validate(raw)
        except ValidationError as exc:
            errors = [f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}" for e in exc.errors()]
            logger.warning("RF1 BLOQUEADO request_id=%s erros=%s", request_id, errors)
            _write_audit({
                "event": "UPLOAD_VALIDATION",
                "evaluated_at": evaluated_at,
                "request_id": request_id,
                "success": False,
                "errors": errors,
            })
            return UploadErrorResponse(
                request_id=request_id,
                evaluated_at=evaluated_at,
                error_count=len(errors),
                errors=errors,
            )

        logger.info("RF1 APROVADO request_id=%s documentos=%d", payload.request_id, len(payload.documents))
        _write_audit({
            "event": "UPLOAD_VALIDATION",
            "evaluated_at": evaluated_at,
            "request_id": payload.request_id,
            "success": True,
            "errors": [],
        })
        return UploadResponse(
            success=True,
            request_id=payload.request_id,
            evaluated_at=evaluated_at,
            message="Upload válido. Processamento fiscal permitido.",
        )
