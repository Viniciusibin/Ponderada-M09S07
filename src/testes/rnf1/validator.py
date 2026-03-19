"""
RNF1 Validator — Aferição de Precisão Tributária (ASIS TaxTech).

Verifica que o TaxService produz valores idênticos aos esperados,
centavo a centavo, e que regras expiradas são rejeitadas antes de
qualquer cálculo.

Critérios de aceite avaliados:
  1. Valores calculados idênticos aos esperados (sem divergência de centavo)
  2. Regras expiradas bloqueadas com ExpiredRulesError
  3. Versões desconhecidas bloqueadas com UnknownRulesVersionError
  4. Aritmética Decimal — nenhum caso produz resultado de ponto flutuante

Uso:
    python -m src.testes.rnf1.validator
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.tributron.domain.models import TaxRequest
from src.tributron.domain.services.tax_service import (
    ExpiredRulesError,
    TaxService,
    UnknownRulesVersionError,
)

CASES_FILE = Path(__file__).parent / "cases" / "precision_cases.json"
LOGS_DIR = Path(__file__).parent / "logs"
METRICS_FILE = LOGS_DIR / "precision_metrics.json"

_ERROR_MAP = {
    "ExpiredRulesError": ExpiredRulesError,
    "UnknownRulesVersionError": UnknownRulesVersionError,
}


def _banner(text: str) -> None:
    print(f"\n{'=' * 65}")
    print(f"  {text}")
    print("=" * 65)


def _check_decimal_fields(breakdown) -> list[str]:
    """Garante que todos os campos monetários são Decimal, não float."""
    issues = []
    for field in ("icms", "iss", "pis", "cofins", "total_tax", "net_value"):
        val = getattr(breakdown, field)
        if not isinstance(val, Decimal):
            issues.append(f"{field} é {type(val).__name__}, esperado Decimal")
    return issues


def run() -> int:
    svc = TaxService()
    cases = json.loads(CASES_FILE.read_text(encoding="utf-8"))
    results: list[dict] = []
    passed = failed = 0

    _banner("RNF1 — Validator de Precisão Tributária (ASIS TaxTech)")
    print(f"  Empresa: ASIS TaxTech")
    print(f"  Data   : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Casos  : {CASES_FILE}\n")

    for case in cases:
        tc_id = case["id"]
        desc = case["description"]
        req_data = case["request"]
        expect_error = case.get("expect_error", False)

        req = TaxRequest(**req_data)
        errors: list[str] = []
        ok = True

        if expect_error:
            expected_exc = _ERROR_MAP.get(case.get("expected_error_type", ""))
            try:
                svc.calculate(req)
                ok = False
                errors.append(f"Esperava {case.get('expected_error_type')} mas nenhuma exceção foi lançada")
            except Exception as exc:
                if expected_exc and not isinstance(exc, expected_exc):
                    ok = False
                    errors.append(f"Exceção errada: esperava {expected_exc.__name__}, recebeu {type(exc).__name__}: {exc}")
        else:
            try:
                response = svc.calculate(req)
                exp = case["expected"]
                bd = response.breakdown

                # Verifica tipos Decimal
                type_issues = _check_decimal_fields(bd)
                if type_issues:
                    ok = False
                    errors.extend(type_issues)

                # Verifica valores ao centavo
                for field in ("icms", "iss", "pis", "cofins", "total_tax", "net_value"):
                    got = getattr(bd, field)
                    expected_val = Decimal(exp[field])
                    if got != expected_val:
                        ok = False
                        errors.append(f"{field}: esperado {expected_val}, calculado {got}")

            except Exception as exc:
                ok = False
                errors.append(f"Exceção inesperada: {type(exc).__name__}: {exc}")

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        icon = "✓" if ok else "✗"
        print(f"  {icon}  [{status}]  {tc_id} — {desc}")
        for err in errors:
            print(f"           ✗ {err}")

        results.append({"id": tc_id, "description": desc, "status": status, "errors": errors})

    # Métricas
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    metrics = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "sla": {"precision": "ao centavo (Decimal + ROUND_HALF_UP)", "max_divergence_cents": 0},
        "total": passed + failed,
        "passed": passed,
        "failed": failed,
        "cases": results,
    }
    METRICS_FILE.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")

    _banner(f"Resultado: {passed}/{passed + failed} PASS  —  métricas em {METRICS_FILE.relative_to(Path.cwd())}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
