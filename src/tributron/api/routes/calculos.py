"""Rota RNF1 — cálculo tributário com precisão determinística."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.tributron.domain.models import TaxRequest, TaxResponse
from src.tributron.domain.services.tax_service import (
    ExpiredRulesError,
    TaxService,
    UnknownRulesVersionError,
)

router = APIRouter(prefix="/v1/calculos", tags=["RNF1 – Precisão Tributária"])
_svc = TaxService()


@router.post(
    "/tributos",
    summary="RNF1 — Calcula tributos com precisão Decimal ao centavo",
    responses={
        200: {"model": TaxResponse, "description": "Cálculo realizado com sucesso"},
        422: {"description": "Regras expiradas ou versão desconhecida"},
    },
)
def calcular_tributos(body: TaxRequest) -> JSONResponse:
    try:
        result = _svc.calculate(body)
        return JSONResponse(status_code=200, content=result.model_dump(mode="json"))
    except ExpiredRulesError as exc:
        return JSONResponse(
            status_code=422,
            content={"success": False, "error": "REGRAS_EXPIRADAS", "detail": str(exc)},
        )
    except UnknownRulesVersionError as exc:
        return JSONResponse(
            status_code=422,
            content={"success": False, "error": "VERSAO_DESCONHECIDA", "detail": str(exc)},
        )
