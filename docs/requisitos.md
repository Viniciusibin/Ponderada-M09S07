# Documento de Requisitos como Ativo de Software
## ASIS TaxTech — Ponderada M09S07

---

## 1. Empresa selecionada e contexto

**ASIS TaxTech** é uma empresa de tecnologia fiscal que oferece uma plataforma API-First para processamento de obrigações acessórias (SPED, DCTF, NFSe). Clientes de grande porte submetem seus arquivos fiscais via API e recebem relatórios de auditoria tributária automatizados.

O problema central que motiva estes requisitos é o **"Dia 20 de cada mês"**: dezenas de empresas enviam simultaneamente seus arquivos antes do prazo da Receita Federal. Nesse pico, dois riscos são críticos:

1. **Dados corrompidos entrando no pipeline fiscal** — um upload com hash adulterado ou metadados ausentes pode gerar cálculos incorretos que se propagam silenciosamente.
2. **Imprecisão monetária em cálculos tributários** — usar aritmética de ponto flutuante ou regras expiradas gera subfaturamento fiscal com risco de autuação.

Este documento implementa e afere esses dois riscos como **código executável e auditável**.

---

## 2. RF1 — Integridade de Upload

### 2.1 Requisito

> **RF1**: O sistema deve validar automaticamente todo payload de upload recebido antes de permitir qualquer processamento fiscal. Cada upload deve conter metadados obrigatórios (`cycle`, `phase`, `trace_id`), documentos com base64 válido, hash SHA-256 consistente com o conteúdo e tamanho declarado igual ao tamanho real. Qualquer violação bloqueia o upload imediatamente.

### 2.2 Critério de aceitação (CA1)

| # | Regra verificada | Resultado esperado |
|---|---|---|
| 1 | Payload com todos os campos válidos | HTTP 200 — processamento permitido |
| 2 | Hash SHA-256 adulterado ou tamanho divergente | HTTP 422 — bloqueado com mensagem de erro |
| 3 | Campo `metadata` ausente | HTTP 422 — bloqueado com mensagem de erro |
| 4 | `trace_id` vazio | HTTP 422 — bloqueado com mensagem de erro |
| 5 | Base64 inválido | HTTP 422 — bloqueado com mensagem de erro |

### 2.3 Implementação em código

| Artefato | Responsabilidade |
|---|---|
| `src/tributron/domain/models.py` → `UploadPayload` | Schema Pydantic com validações: base64, SHA-256, tamanho, metadados obrigatórios |
| `src/tributron/domain/services/integrity_service.py` → `IntegrityService` | Orquestra validação e grava trilha auditável em `logs/integrity_audit.jsonl` |
| `src/tributron/api/routes/upload.py` | Endpoint `POST /v1/upload/validate` que retorna 200 ou 422 |
| `src/testes/rf1/samples/` | 3 payloads de amostra: válido, corrompido (hash errado + tamanho errado), metadados ausentes |
| `src/testes/rf1/runner.py` | Runner que executa os 3 cenários e gera `logs/integrity_report.json` |

### 2.4 Fluxo de validação

```
UploadPayload recebido
        │
        ▼
  [Pydantic parse]
        │
  ┌─────┴──────────────────────────┐
  │  metadata.trace_id presente?   │
  │  base64 decodificável?         │
  │  sha256 == hash(decodificado)? │
  │  size_bytes == len(raw)?       │
  └─────────────────────────────────
        │                    │
       SIM                  NÃO
        │                    │
     HTTP 200            HTTP 422
   (processamento      (bloqueado +
    permitido)          log auditável)
```

### 2.5 Execução

```bash
python -m src.testes.rf1.runner
```

**Saída esperada:**
```
✓  [PASS]  valid_upload.json
✓  [PASS]  corrupted_upload.json
✓  [PASS]  missing_metadata_upload.json
Resultado: 3/3 PASS
```

### 2.6 Artefatos gerados

| Arquivo | Conteúdo |
|---|---|
| `src/testes/rf1/logs/integrity_report.json` | Status de cada amostra: `expected_valid`, `got_valid`, `status`, `errors` |
| `src/testes/rf1/logs/integrity_audit.jsonl` | Uma linha JSON por validação: evento, timestamp, request_id, resultado |

---

## 3. RNF1 — Precisão Tributária Determinística

### 3.1 Requisito

> **RNF1**: O sistema deve calcular ICMS, ISS, PIS e COFINS com aritmética `Decimal` e arredondamento `ROUND_HALF_UP`, garantindo precisão exata ao centavo. Requisições que referenciem versões de regras expiradas devem ser bloqueadas com erro antes de qualquer cálculo. O resultado deve ser idêntico ao esperado em 100% dos casos, sem divergência de um único centavo.

### 3.2 Por que este RNF é crítico

Com regras **v1.0.0** (expiradas em jan/2026) sobre R$ 50.000,00 em SP:
- ICMS 12% → R$ 6.000,00
- ISS 2% → R$ 1.000,00
- PIS 1,65% → R$ 825,00
- COFINS 3% → R$ 1.500,00
- **Total: R$ 9.325,00**

Com regras **v2.0.0** (vigentes):
- ICMS 18% → R$ 9.000,00
- ISS 2,5% → R$ 1.250,00
- PIS 1,65% → R$ 825,00
- COFINS 7,6% → R$ 3.800,00
- **Total: R$ 14.875,00**

**Diferença: R$ 5.550,00 de subfaturamento fiscal** — configura autuação pela Receita Federal.

### 3.3 Critério de aceitação (CA2)

| # | Regra verificada | Resultado esperado |
|---|---|---|
| 1 | Cálculo padrão com regras v2.0.0 | Valores idênticos ao esperado ao centavo |
| 2 | Arredondamento em valores com casas infinitas | `ROUND_HALF_UP` sem divergência |
| 3 | Regras expiradas (v1.0.0) | `ExpiredRulesError` — bloqueado antes do cálculo |
| 4 | Versão inexistente (v9.9.9) | `UnknownRulesVersionError` — bloqueado antes do cálculo |
| 5 | Tipo dos campos monetários | Sempre `Decimal`, nunca `float` |

### 3.4 Implementação em código

| Artefato | Responsabilidade |
|---|---|
| `src/tributron/domain/models.py` → `TaxRequest / TaxBreakdown` | Contrato tipado com `Decimal` nos campos monetários |
| `src/tributron/domain/services/tax_service.py` → `TaxService` | Cálculo com `ROUND_HALF_UP`, regras versionadas, rejeição de versões expiradas |
| `src/tributron/api/routes/calculos.py` | Endpoint `POST /v1/calculos/tributos` |
| `src/testes/rnf1/cases/precision_cases.json` | 4 casos: cálculo padrão, borda de arredondamento, regras expiradas, versão inválida |
| `src/testes/rnf1/validator.py` | Validator que executa os 4 casos e gera `logs/precision_metrics.json` |

### 3.5 Execução

```bash
python -m src.testes.rnf1.validator
```

**Saída esperada:**
```
✓  [PASS]  TC-P-01 — Cálculo padrão SP R$ 15.750,99 com regras v2.0.0
✓  [PASS]  TC-P-02 — Caso de borda RJ ROUND_HALF_UP em R$ 33.333,33
✓  [PASS]  TC-P-03 — Regras expiradas v1.0.0 → ExpiredRulesError
✓  [PASS]  TC-P-04 — Versão inexistente → UnknownRulesVersionError
Resultado: 4/4 PASS
```

### 3.6 Artefatos gerados

| Arquivo | Conteúdo |
|---|---|
| `src/testes/rnf1/logs/precision_metrics.json` | Resumo por caso: status, valores calculados vs esperados |

---

## 4. Rastreabilidade RF × RNF

| ID | Tipo | Risco mitigado | Como é verificado em código |
|---|---|---|---|
| RF1 | Funcional | Dados corrompidos no pipeline fiscal | `UploadPayload` (Pydantic) + `IntegrityService.validate()` |
| RNF1 | Não-funcional | Imprecisão monetária / regras expiradas | `TaxService.calculate()` com `Decimal` + `ExpiredRulesError` |

Ambos os requisitos geram **artefatos auditáveis** por execução (JSON de relatório/métricas), permitindo integração com CI/CD: se qualquer cenário falhar, o runner retorna código de saída `1` e o pipeline é bloqueado.
