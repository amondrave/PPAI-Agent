# Code Generation Summary — UOW-01 + UOW-02

**Fecha de cierre:** 2026-03-21
**Tests totales:** 168 passing (0 failing)
**Rama de referencia:** `feature/uow-02-decision-core` → PR #1

---

## UOW-01 — Capture Foundation

**Objetivo:** El bot recibe texto libre de Telegram y lo convierte en tareas estructuradas persistidas en DynamoDB.

### Reglas de negocio implementadas (BR-CAP-01..10)
| ID | Regla |
|---|---|
| BR-CAP-01 | Validación de input (texto no vacío, con caracteres alfanuméricos) |
| BR-CAP-02 | Normalización de texto (limpieza, capitalización) |
| BR-CAP-03 | Extracción de tags (`#trabajo`, `#personal`, etc.) |
| BR-CAP-04 | Extracción de deadlines relativos (`mañana`, `hoy`, `urgente`, fechas ISO) |
| BR-CAP-05 | Soporte multiline — un mensaje puede crear N tareas |
| BR-CAP-06 | Deduplicación por ventana de tiempo configurable |
| BR-CAP-07 | Límite de tareas activas por usuario (default: 50) |
| BR-CAP-08 | Rate limiting por usuario (sliding window, default: 10/min) |
| BR-CAP-09 | Transición automática `captured → pending` al guardar |
| BR-CAP-10 | Evento `INTENT_CAPTURED` registrado por cada tarea creada |

### Estructura de archivos
```
ppai/
├── capture/
│   ├── domain/
│   │   ├── entities.py          — Intent, TaskState, CaptureEvent, DedupRecord
│   │   ├── value_objects.py     — TaskStatus (8 estados), ACTIVE_STATUSES
│   │   └── exceptions.py        — CaptureError hierarchy
│   ├── application/
│   │   ├── ports.py             — Protocols: TaskStateRepository, EventRepository, DedupRepository
│   │   └── capture_service.py   — CaptureService + hook on_task_captured
│   └── infrastructure/
│       ├── telegram_adapter.py  — Webhook handler + error handler
│       ├── dynamodb_task_repo.py — ppai-tasks + list_pending() + snooze_count
│       ├── dynamodb_event_repo.py — ppai-events
│       └── dynamodb_dedup_repo.py — ppai-dedup (TTL configurable)
└── shared/
    ├── domain/base_entity.py    — generate_id() UUID factory
    └── infrastructure/
        ├── config.py            — pydantic-settings + .env support + dynamodb_endpoint_url
        ├── dynamodb_client.py   — boto3 factory con soporte endpoint_url (LocalStack)
        ├── rate_limiter.py      — InMemoryRateLimiter sliding window
        └── logging.py           — structlog JSON config
```

### Tests UOW-01
| Tipo | Archivo | Tests |
|---|---|---|
| Unit | `tests/unit/capture/test_entities.py` | 9 |
| Unit | `tests/unit/capture/test_value_objects.py` | 5 |
| Unit | `tests/unit/capture/test_capture_service.py` | 38 |
| Integration | `tests/integration/capture/test_dynamodb_repos.py` | 14 |
| E2E | `tests/e2e/test_telegram_flow.py` | 9 |
| **Total** | | **75** |

### Infraestructura UOW-01 (Terraform)
| Módulo | Recursos |
|---|---|
| `networking/` | VPC `10.0.0.0/16`, 2 subnets privadas, NAT Gateway, VPC Endpoint DynamoDB |
| `ecr/` | Repository `ppai-bot`, scanning habilitado, lifecycle policy |
| `dynamodb/` | `ppai-tasks` (GSI `userId-status-index`), `ppai-events`, `ppai-dedup` (TTL) |
| `iam/` | Task Execution Role + Task Role (least privilege) |
| `ecs/` | Cluster, Task Definition (256 CPU / 512MB), Service (desiredCount=1), circuit breaker |
| `api-gateway/` | HTTP API, VPC Link, ruta `/webhook` |
| `monitoring/` | Log groups `/ppai/bot` y `/ppai/apigw` (retención 90 días) |

---

## UOW-02 — Decision Core

**Objetivo:** Priorizar las tareas pendientes con un algoritmo determinístico y presentar el Top 3 al usuario vía Telegram con botones de acción inline.

### Reglas de negocio implementadas (BR-DEC-01..10)
| ID | Regla |
|---|---|
| BR-DEC-01 | Solo tareas con status `pending` son elegibles para el Top 3 |
| BR-DEC-02 | Scoring determinístico: `totalScore = urgencyScore + ageScore + snoozeScore` (max 27) |
| BR-DEC-03 | Tie-breaking: deadline ASC (null al final) → createdAt ASC (FIFO) |
| BR-DEC-04 | Selección top `min(3, elegibles)` → transición `pending → prioritized` |
| BR-DEC-05 | Explicación legible en español por cada score (para auditoría, no se muestra al usuario) |
| BR-DEC-06 | Presentación con botones inline: `[✓ Hecho] [⏸ Posponer] [? Aclarar]` |
| BR-DEC-07 | Bandeja vacía → mensaje invitación. 1-2 tareas → mostrar + mensaje motivacional |
| BR-DEC-08 | Registro `TOP3_PRESENTED` en `ExecutionCycle` activo (best effort) |
| BR-DEC-09 | Reordenamiento manual sin cambiar scores — solo reordena presentación |
| BR-DEC-10 | Inicio de aclaración vía botón — transición `prioritized → needs_clarification` |

### Algoritmo de scoring v1.0
```
urgencyScore:  deadline ≤24h → 10 | ≤72h → 7 | >72h → 4 | sin deadline → 3
ageScore:      min(días_en_pending, 7)          — 1 pt/día, techo en 7
snoozeScore:   min(snoozeCount × 2, 10)        — más posposiciones = más urgente
```

### Estructura de archivos
```
ppai/
└── decision/
    ├── domain/
    │   ├── entities.py          — ExecutionCycle, PriorityScore (frozen), Top3Result (frozen)
    │   ├── value_objects.py     — CycleStatus (active, closed)
    │   ├── exceptions.py        — DecisionError, CycleConflictError, TaskNotInTop3Error
    │   ├── scoring_engine.py    — ScoringEngine (puro, sin I/O, now como parámetro)
    │   └── scoring_rules.py     — Constantes v1.0 (cambio = nueva versión)
    ├── application/
    │   ├── ports.py             — Protocols: TaskStateQueryRepository, CycleRepository
    │   └── decision_service.py  — get_top3, clarify, reorder + cache TTL 60s
    └── infrastructure/
        ├── dynamodb_cycle_repo.py         — ppai-cycles + GSI userId-date-index
        └── decision_telegram_adapter.py   — /top3 handler + CallbackQueryHandler
```

### Tests UOW-02
| Tipo | Archivo | Tests |
|---|---|---|
| Unit | `tests/unit/decision/test_entities.py` | 10 |
| Unit | `tests/unit/decision/test_scoring_engine.py` | 30 |
| Unit | `tests/unit/decision/test_decision_service.py` | 25 |
| Integration | `tests/integration/decision/test_dynamodb_repos.py` | 14 |
| E2E | `tests/e2e/test_top3_flow.py` | 14 |
| **Total** | | **93** |

### Infraestructura delta UOW-02 (Terraform)
| Módulo | Cambio |
|---|---|
| `dynamodb/` | Nueva tabla `ppai-cycles` + GSI `userId-date-index`, encryption, deletion protection |
| `iam/` | Permisos `PutItem/GetItem/UpdateItem/Query` sobre `ppai-cycles` y su índice |
| `iam/github-oidc.tf` | OIDC provider + deploy role para GitHub Actions (sin credenciales de larga duración) |

**Costo delta:** ~$0.15/mes

---

## Resumen global

| Métrica | Valor |
|---|---|
| Tests totales | 168 passing |
| Cobertura UOW-01 | 75 tests |
| Cobertura UOW-02 | 93 tests |
| Reglas de negocio | 20 (BR-CAP-01..10 + BR-DEC-01..10) |
| Módulos Python | 2 (capture, decision) + shared |
| Módulos Terraform | 7 (networking, ecr, dynamodb, iam, ecs, api-gateway, monitoring) |
| Costo AWS estimado | ~$43.15/mes |

---

## Infraestructura local (LocalStack)

Para desarrollo sin cuenta AWS:

```bash
# 1. Levantar LocalStack + crear tablas
docker-compose up -d

# 2. Copiar y configurar variables
cp .env.example .env
# Editar .env: agregar TELEGRAM_BOT_TOKEN y descomentar DYNAMODB_ENDPOINT_URL

# 3. Activar venv y correr en modo polling
source .venv/bin/activate
python -m ppai.local
```

---

## CI/CD (GitHub Actions)

Pipeline en `.github/workflows/deploy.yml`:

```
push a main
  → [test]          pytest — todas las UOWs
  → [build-push]    docker build + push a ECR (tag = git SHA)
  → [terraform]     terraform plan + apply (delta únicamente)
  → [deploy]        ECS force-new-deployment + wait stable + health check
```

**Credenciales:** GitHub Actions asume `ppai-github-deploy-role` vía OIDC — sin `AWS_ACCESS_KEY_ID` en secrets.

**GitHub Secrets requeridos:**
| Secret | Valor |
|---|---|
| `AWS_DEPLOY_ROLE_ARN` | ARN del role OIDC (output de `terraform output github_deploy_role_arn`) |
| `TELEGRAM_BOT_TOKEN` | Token del bot de @BotFather |

**GitHub Variables (no sensibles):**
| Variable | Valor |
|---|---|
| `AWS_REGION` | `us-east-1` |
