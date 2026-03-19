"""
Aplicação FastAPI — ASIS TaxTech (Ponderada M09S07).

Expõe dois grupos de endpoints:
  /v1/upload/validate  → RF1  (Integridade de Upload)
  /v1/calculos/tributos → RNF1 (Precisão Tributária)
"""

from fastapi import FastAPI

from src.tributron.api.routes.calculos import router as calculos_router
from src.tributron.api.routes.upload import router as upload_router

app = FastAPI(
    title="ASIS TaxTech — Ponderada M09S07",
    description=(
        "API de validação fiscal que implementa RF1 (Integridade de Upload) "
        "e RNF1 (Precisão Tributária Determinística)."
    ),
    version="1.0.0",
)

app.include_router(upload_router)
app.include_router(calculos_router)


@app.get("/health", tags=["Infra"])
def health() -> dict:
    return {"status": "ok"}
