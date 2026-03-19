"""
RF1 Runner — Aferição de Integridade de Upload (ASIS TaxTech).

Lê os payloads de amostra em samples/, chama o IntegrityService
diretamente (sem servidor HTTP) e gera o relatório em
logs/integrity_report.json.

Uso:
    python -m src.testes.rf1.runner
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Garante que o pacote raiz está no path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from src.tributron.domain.models import UploadErrorResponse
from src.tributron.domain.services.integrity_service import IntegrityService

SAMPLES_DIR = Path(__file__).parent / "samples"
LOGS_DIR = Path(__file__).parent / "logs"
REPORT_FILE = LOGS_DIR / "integrity_report.json"

_EXPECTED: dict[str, bool] = {
    "valid_upload.json": True,
    "corrupted_upload.json": False,
    "missing_metadata_upload.json": False,
}


def _banner(text: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {text}")
    print("=" * 60)


def run() -> int:
    svc = IntegrityService()
    results: list[dict] = []
    passed = failed = 0

    _banner("RF1 — Runner de Integridade de Upload")
    print(f"  Empresa: ASIS TaxTech")
    print(f"  Data   : {datetime.now(tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"  Amostras em: {SAMPLES_DIR}\n")

    for filename, expect_valid in _EXPECTED.items():
        path = SAMPLES_DIR / filename
        raw = json.loads(path.read_text(encoding="utf-8"))
        # Remove chave de descrição antes de validar
        raw.pop("_description", None)

        result = svc.validate(raw)
        got_valid = not isinstance(result, UploadErrorResponse)
        ok = got_valid == expect_valid

        status = "PASS" if ok else "FAIL"
        if ok:
            passed += 1
        else:
            failed += 1

        detail: dict = {
            "sample": filename,
            "expected_valid": expect_valid,
            "got_valid": got_valid,
            "status": status,
        }
        if not got_valid:
            detail["errors"] = result.errors  # type: ignore[union-attr]

        results.append(detail)
        icon = "✓" if ok else "✗"
        print(f"  {icon}  [{status}]  {filename}")
        if not got_valid and not ok:
            for err in result.errors:  # type: ignore[union-attr]
                print(f"         Erro: {err}")

    # Relatório JSON
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    report = {
        "generated_at": datetime.now(tz=timezone.utc).isoformat(),
        "total": passed + failed,
        "passed": passed,
        "failed": failed,
        "samples_evaluated": results,
    }
    REPORT_FILE.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    _banner(f"Resultado: {passed}/{passed + failed} PASS  —  relatório em {REPORT_FILE.relative_to(Path.cwd())}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run())
