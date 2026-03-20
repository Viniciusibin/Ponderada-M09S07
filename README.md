# Ponderada M09S07 — ASIS TaxTech

Implementação da atividade ponderada: requisitos como ativo de software para a empresa digital ASIS TaxTech.

---

## Empresa selecionada

ASIS TaxTech — plataforma API-First de auditoria fiscal. Processa arquivos SPED, DCTF e NFSe de grandes empresas com prazo crítico no dia 20 de cada mês.

O aspecto não-funcional central é a confiabilidade dos dados fiscais: uploads corrompidos e imprecisão monetária são riscos que se propagam silenciosamente e geram autuações da Receita Federal.

---

## O que foi implementado


## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

---

## Execução dos testes

### RF1 — Integridade de Upload (Funcional)

```bash
python -m src.testes.rf1.runner
```

Valida 3 cenários: payload válido, corrompido (hash + tamanho errado) e metadados ausentes.  
Gera: `src/testes/rf1/logs/integrity_report.json`

**Saída esperada:**
```
✓  [PASS]  valid_upload.json
✓  [PASS]  corrupted_upload.json
✓  [PASS]  missing_metadata_upload.json
Resultado: 3/3 PASS
```

---

### RNF1 — Precisão Tributária (Não-funcional)

```bash
python -m src.testes.rnf1.validator
```

Verifica que ICMS, ISS, PIS e COFINS são calculados ao centavo com `Decimal + ROUND_HALF_UP` e que regras expiradas são bloqueadas antes de qualquer cálculo.  
Gera: `src/testes/rnf1/logs/precision_metrics.json`

**Saída esperada:**
```
✓  [PASS]  TC-P-01 — Cálculo padrão SP R$ 15.750,99
✓  [PASS]  TC-P-02 — Caso de borda RJ R$ 33.333,33
✓  [PASS]  TC-P-03 — Regras expiradas v1.0.0 → ExpiredRulesError
✓  [PASS]  TC-P-04 — Versão inexistente → UnknownRulesVersionError
Resultado: 4/4 PASS
```

---

## API (opcional)

Para explorar os endpoints via Swagger:

```bash
uvicorn src.tributron.main:app --reload
# Acesse: http://localhost:8000/docs
```

| Endpoint | Tipo | Descrição |
|---|---|---|
| `POST /v1/upload/validate` | RF1 | Valida integridade do payload de upload |
| `POST /v1/calculos/tributos` | RNF1 | Calcula tributos com precisão Decimal |

---

## Estrutura do projeto

```
src/
  tributron/
    domain/
      models.py                  ← Modelos Pydantic (RF1 + RNF1)
      services/
        integrity_service.py     ← Serviço RF1 (integridade de upload)
        tax_service.py           ← Serviço RNF1 (cálculo tributário)
    api/
      routes/
        upload.py                ← Endpoint RF1
        calculos.py              ← Endpoint RNF1
    main.py                      ← Aplicação FastAPI
  testes/
    rf1/
      runner.py                  ← Runner RF1
      samples/                   ← Payloads de amostra (válido, corrompido, sem metadados)
      logs/                      ← Relatórios gerados
    rnf1/
      validator.py               ← Validator RNF1
      cases/                     ← Casos de precisão tributária
      logs/                      ← Métricas geradas
docs/
  requisitos.md                  ← Documentação completa RF1 + RNF1
```
