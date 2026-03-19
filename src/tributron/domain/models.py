"""
Modelos de domínio da ASIS TaxTech.

RF1 — UploadPayload: contrato de upload com metadados obrigatórios,
      documentos com hash SHA-256 e codificação base64 válida.

RNF1 — TaxRequest / TaxResult: contrato de cálculo tributário com
       aritmética Decimal para garantir precisão ao centavo.
"""

from __future__ import annotations

import base64
import hashlib
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


# ─── RF1 — Modelos de Upload ────────────────────────────────────────────────

class UploadMetadata(BaseModel):
    cycle: str = Field(..., description="Ciclo fiscal, ex: '2026-03'")
    phase: Literal["upload", "validation", "processing"] = Field(
        ..., description="Fase do fluxo fiscal"
    )
    trace_id: str = Field(..., min_length=1, description="ID de rastreio da operação")


class UploadDocument(BaseModel):
    doc_type: Literal["sped", "dctf", "nfse"] = Field(..., description="Tipo do documento fiscal")
    filename: str = Field(..., min_length=1)
    content_base64: str = Field(..., description="Conteúdo do documento em base64")
    sha256: str = Field(..., min_length=64, max_length=64, description="Hash SHA-256 do conteúdo decodificado")
    size_bytes: int = Field(..., gt=0, description="Tamanho em bytes do conteúdo decodificado")

    @field_validator("content_base64")
    @classmethod
    def must_be_valid_base64(cls, v: str) -> str:
        try:
            base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("content_base64 não é um base64 válido")
        return v

    @model_validator(mode="after")
    def validate_hash_and_size(self) -> "UploadDocument":
        raw = base64.b64decode(self.content_base64)
        computed_hash = hashlib.sha256(raw).hexdigest()
        if computed_hash != self.sha256:
            raise ValueError(
                f"Hash SHA-256 inválido: esperado '{computed_hash}', recebido '{self.sha256}'"
            )
        if len(raw) != self.size_bytes:
            raise ValueError(
                f"Tamanho inconsistente: esperado {len(raw)} bytes, declarado {self.size_bytes}"
            )
        return self


class UploadPayload(BaseModel):
    request_id: str = Field(..., min_length=1, description="UUID único da requisição")
    timestamp: str = Field(..., description="Timestamp UTC ISO 8601 do envio")
    metadata: UploadMetadata
    documents: list[UploadDocument] = Field(..., min_length=1, description="Mínimo de 1 documento")


class UploadResponse(BaseModel):
    success: bool
    request_id: str
    evaluated_at: str
    message: str


class UploadErrorResponse(BaseModel):
    success: bool = False
    request_id: str
    evaluated_at: str
    error_count: int
    errors: list[str]


# ─── RNF1 — Modelos de Cálculo Tributário ───────────────────────────────────

class TaxRequest(BaseModel):
    request_id: str = Field(..., min_length=1)
    rules_version: str = Field(..., description="Versão das regras tributárias")
    base_value: Decimal = Field(..., gt=Decimal("0"), description="Valor base da NF em R$")
    state: str = Field(..., min_length=2, max_length=2, description="UF de origem, ex: 'SP'")
    service_type: Literal["consultoria", "desenvolvimento", "auditoria"] = Field(
        ..., description="Tipo de serviço para alíquota de ISS"
    )


class TaxBreakdown(BaseModel):
    icms: Decimal
    iss: Decimal
    pis: Decimal
    cofins: Decimal
    total_tax: Decimal
    net_value: Decimal


class TaxResponse(BaseModel):
    success: bool
    request_id: str
    rules_version: str
    calculated_at: str
    breakdown: TaxBreakdown
