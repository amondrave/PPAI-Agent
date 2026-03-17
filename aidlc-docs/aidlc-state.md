# AI-DLC State Tracking

## Project Information
- **Project Type**: Greenfield
- **Start Date**: 2026-03-10T21:21:54Z
- **Current Stage**: CONSTRUCTION - Code Generation In Progress (UOW-01)

## Workspace State
- **Existing Code**: Yes (Steps 1-14 completados)
- **Reverse Engineering Needed**: No
- **Workspace Root**: /Users/angelmondragon/Desktop/PPAI/ppai

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| Baseline Security Rules | Yes | Requirements Analysis |

## Stage Progress
### 🔵 INCEPTION PHASE
- [x] Workspace Detection
- [x] Reverse Engineering (SKIPPED)
- [x] Requirements Analysis
- [x] User Stories
- [x] Workflow Planning
- [x] Application Design
- [x] Units Planning
- [x] Units Generation

### 🟢 CONSTRUCTION PHASE
- [x] Functional Design (UOW-01 Capture Foundation)
- [x] NFR Requirements
- [x] NFR Design
- [x] Infrastructure Design
- [x] Code Planning
- [ ] Code Generation ← EN PROGRESO
- [ ] Build and Test

### 🟡 OPERATIONS PHASE
- [ ] Operations (PLACEHOLDER)

## Current Status
- **Lifecycle Phase**: CONSTRUCTION
- **Current Stage**: Code Generation — UOW-01 Capture Foundation
- **Last Session Date**: 2026-03-17
- **Status**: Steps 1-14 completados (14/16). Pendiente Steps 15-16 + LocalStack setup.

## Code Generation Progress (UOW-01)

| Step | Descripcion | Estado | Linear |
|------|-------------|--------|--------|
| Step 1 | Project Structure Setup | ✅ Done | PPA-6 |
| Step 2 | Domain Layer — Entities & Value Objects | ✅ Done | PPA-7 |
| Step 3 | Domain Layer — Unit Tests | ✅ Done | PPA-8 |
| Step 4 | Application Layer — Ports | ✅ Done | PPA-9 |
| Step 5 | Application Layer — Capture Service | ✅ Done | PPA-10 |
| Step 6 | Application Layer — Unit Tests | ✅ Done | PPA-11 |
| Step 7 | Infrastructure Layer — DynamoDB Repositories | ✅ Done | PPA-12 |
| Step 8 | Infrastructure Layer — Integration Tests | ✅ Done | PPA-13 |
| Step 9 | Infrastructure Layer — Telegram Adapter + Rate Limiter | ✅ Done | PPA-14 |
| Step 10 | Infrastructure Layer — Structured Logging | ✅ Done | PPA-15 |
| Step 11 | Application Entry Point — main.py | ✅ Done | PPA-16 |
| Step 12 | E2E Tests — Telegram Flow | ✅ Done | PPA-17 |
| Step 13 | Dockerfile + Container Config | ✅ Done | PPA-18 |
| Step 14 | Terraform Infrastructure | ✅ Done | PPA-19 |
| Step 15 | GitHub Actions Workflow | ⏳ Pendiente | PPA-20 |
| Step 16 | Documentation Summaries | ⏳ Pendiente | PPA-21 |
| Extra | LocalStack + docker-compose + ppai/local.py | ⏳ Pendiente | — |

## Test Coverage
- **Total tests**: 75 passing (0 failing)
- **Unit tests**: 52 (domain + service)
- **Integration tests**: 14 (DynamoDB repos con moto)
- **E2E tests**: 9 (flujo completo Telegram simulado)

## Archivos Generados (Code Generation)

### Application Code
```
ppai/
├── __init__.py
├── main.py                                    ← Entry point (webhook)
├── capture/
│   ├── domain/
│   │   ├── entities.py                        ← Intent, TaskState, CaptureEvent, DedupRecord
│   │   ├── value_objects.py                   ← TaskStatus enum, ACTIVE_STATUSES
│   │   └── exceptions.py                      ← CaptureError hierarchy
│   ├── application/
│   │   ├── ports.py                           ← Protocols: TaskStateRepo, EventRepo, DedupRepo
│   │   └── capture_service.py                 ← CaptureService (BR-CAP-01..10)
│   └── infrastructure/
│       ├── telegram_adapter.py                ← Webhook handler + error handler
│       ├── dynamodb_task_repo.py              ← DynamoDB: ppai-tasks
│       ├── dynamodb_event_repo.py             ← DynamoDB: ppai-events
│       └── dynamodb_dedup_repo.py             ← DynamoDB: ppai-dedup (TTL)
└── shared/
    ├── domain/
    │   └── base_entity.py                     ← generate_id() UUID factory
    └── infrastructure/
        ├── config.py                          ← pydantic-settings (env vars)
        ├── dynamodb_client.py                 ← boto3 factory
        ├── rate_limiter.py                    ← InMemoryRateLimiter sliding window
        └── logging.py                         ← structlog JSON config

tests/
├── conftest.py                                ← moto DynamoDB fixtures (3 tablas)
├── unit/capture/
│   ├── test_entities.py                       ← 9 tests
│   ├── test_value_objects.py                  ← 5 tests
│   └── test_capture_service.py               ← 38 tests (todas las BRs)
├── integration/capture/
│   └── test_dynamodb_repos.py                 ← 14 tests (moto)
└── e2e/
    └── test_telegram_flow.py                  ← 9 tests (flujo completo)
```

### Infrastructure
```
terraform/
├── main.tf, providers.tf, variables.tf, outputs.tf
└── modules/
    ├── networking/     ← VPC, subnets, NAT, VPC endpoints, SGs
    ├── api-gateway/    ← HTTP API, VPC Link, route, access logs
    ├── ecs/            ← Cluster, task def, service (desiredCount=1)
    ├── dynamodb/       ← 3 tablas + GSI + TTL + deletion protection
    ├── iam/            ← Task execution role + task role (least privilege)
    ├── ecr/            ← Repository + scanning + lifecycle
    └── monitoring/     ← CloudWatch log groups (90 days)
```

### Docs
```
docs/
└── setup-guide.md     ← Guia completa: Telegram setup, LocalStack, AWS deploy
```

## Proximos Pasos (siguiente sesion)

1. **LocalStack setup** — `docker-compose.yml` + `scripts/create-local-tables.py` + `ppai/local.py` (polling mode) + `.env.example`
2. **Step 15** — GitHub Actions: build, test, push ECR
3. **Step 16** — Documentation summary
4. **Prueba manual** — Levantar LocalStack + bot polling + probar desde Telegram real

## Decisiones Tecnicas Relevantes

| Decision | Razon |
|----------|-------|
| API Gateway HTTP API (no ALB) | Mas barato (~$43/mes vs ~$60+), TLS automatico |
| pyenv local 3.12.4 | Python 3.12 requerido (StrEnum), pyenv configurado |
| .venv en raiz del proyecto | Entorno aislado, ya en .gitignore |
| run_polling para local | Webhook requiere URL publica, polling es suficiente para dev |
| LocalStack pendiente | Necesario para prueba manual sin cuenta AWS |
