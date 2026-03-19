"""
RNF1 — Serviço de Cálculo Tributário com Precisão Determinística.

Responsabilidade: calcular ICMS, ISS, PIS e COFINS com aritmética
Decimal + ROUND_HALF_UP, garantindo precisão ao centavo e rejeição
de regras tributárias expiradas.

Alíquotas vigentes (versão 2.0.0, em vigor desde jan/2026):
  ICMS: variável por UF (SP=18%, RJ=20%, MG=18%, outros=17%)
  ISS:  variável por tipo de serviço (consultoria=2,5%, outros=5%)
  PIS:  1,65% (regime não-cumulativo)
  COFINS: 7,60% (regime não-cumulativo)

Versão expirada (1.0.0): ICMS SP=12%, ISS=2%, PIS=1,65%, COFINS=3%
— uso da versão expirada geraria subfaturamento fiscal e
  representa risco de autuação pela Receita Federal.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from datetime import datetime, timezone
from typing import Any

from src.tributron.domain.models import TaxBreakdown, TaxRequest, TaxResponse

_CENT = Decimal("0.01")

_RULES: dict[str, dict[str, Any]] = {
    "2.0.0": {
        "valid": True,
        "icms_by_state": {"SP": Decimal("0.18"), "RJ": Decimal("0.20"), "MG": Decimal("0.18")},
        "icms_default": Decimal("0.17"),
        "iss_by_service": {"consultoria": Decimal("0.025"), "auditoria": Decimal("0.025")},
        "iss_default": Decimal("0.05"),
        "pis": Decimal("0.0165"),
        "cofins": Decimal("0.0760"),
    },
    "1.0.0": {
        "valid": False,
        "expired_since": "2026-01-01",
        "icms_by_state": {"SP": Decimal("0.12"), "RJ": Decimal("0.17"), "MG": Decimal("0.15")},
        "icms_default": Decimal("0.12"),
        "iss_by_service": {},
        "iss_default": Decimal("0.02"),
        "pis": Decimal("0.0165"),
        "cofins": Decimal("0.03"),
    },
}

CURRENT_VERSION = "2.0.0"


class ExpiredRulesError(ValueError):
    def __init__(self, version: str, expired_since: str) -> None:
        super().__init__(
            f"Regras versão '{version}' expiraram em {expired_since}. "
            f"Use a versão vigente '{CURRENT_VERSION}'."
        )
        self.version = version
        self.expired_since = expired_since


class UnknownRulesVersionError(ValueError):
    pass


def _round(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


class TaxService:
    """
    Calcula tributos sobre o valor base de uma nota fiscal.

    Lança ExpiredRulesError se a versão solicitada estiver expirada,
    impedindo que cálculos com alíquotas defasadas contaminem o sistema.
    """

    def calculate(self, req: TaxRequest) -> TaxResponse:
        rules = _RULES.get(req.rules_version)
        if rules is None:
            raise UnknownRulesVersionError(f"Versão '{req.rules_version}' desconhecida.")

        if not rules["valid"]:
            raise ExpiredRulesError(req.rules_version, rules["expired_since"])

        base = req.base_value

        icms_rate = rules["icms_by_state"].get(req.state.upper(), rules["icms_default"])
        iss_rate = rules["iss_by_service"].get(req.service_type, rules["iss_default"])
        pis_rate: Decimal = rules["pis"]
        cofins_rate: Decimal = rules["cofins"]

        icms = _round(base * icms_rate)
        iss = _round(base * iss_rate)
        pis = _round(base * pis_rate)
        cofins = _round(base * cofins_rate)
        total_tax = _round(icms + iss + pis + cofins)
        net_value = _round(base - total_tax)

        return TaxResponse(
            success=True,
            request_id=req.request_id,
            rules_version=req.rules_version,
            calculated_at=datetime.now(tz=timezone.utc).isoformat(),
            breakdown=TaxBreakdown(
                icms=icms,
                iss=iss,
                pis=pis,
                cofins=cofins,
                total_tax=total_tax,
                net_value=net_value,
            ),
        )
