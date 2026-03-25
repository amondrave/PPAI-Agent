# AI-DLC State Tracking

## Project Information
- **Project Type**: Greenfield
- **Start Date**: 2026-03-10T21:21:54Z
- **Current Stage**: CONSTRUCTION - Code Generation COMPLETO (UOW-01 + UOW-02 + UOW-03)

## Workspace State
- **Existing Code**: Yes (UOW-01 + UOW-02 completos, CI/CD verde)
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

#### UOW-01 Capture Foundation — ✅ COMPLETO
- [x] Functional Design
- [x] NFR Requirements
- [x] NFR Design
- [x] Infrastructure Design
- [x] Code Planning
- [x] Code Generation ✅ (Steps 1–16 completos)
- [x] Build and Test ✅ 2026-03-21 — LocalStack + CI verde + prueba manual Telegram OK

#### UOW-02 Decision Core — ✅ COMPLETO
- [x] Functional Design ✅ 2026-03-18
- [x] NFR Requirements ✅ 2026-03-18
- [x] NFR Design ✅ 2026-03-18
- [x] Infrastructure Design ✅ 2026-03-18
- [x] Code Planning ✅ 2026-03-21
- [x] Code Generation ✅ 2026-03-21 (Steps 1–12, 168 tests passing)
- [x] Build and Test ✅ 2026-03-21 — CI verde (168/168), prueba LocalStack OK

#### UOW-03 Push & Scheduling — ✅ COMPLETO
- [x] Functional Design ✅ 2026-03-23
- [x] NFR Requirements ✅ 2026-03-23
- [x] NFR Design ✅ 2026-03-23
- [x] Infrastructure Design ✅ 2026-03-25
- [x] Code Planning ✅ 2026-03-25
- [x] Code Generation ✅ 2026-03-25 (Steps 1–16, 94 tests UOW-03)
- [x] Build and Test ✅ 2026-03-25 — 262/262 tests, LocalStack OK, prueba manual Telegram OK, PR #6 mergeado, deploy prod en curso

### 🟡 OPERATIONS PHASE
- [ ] Operations (PLACEHOLDER)

## Current Status
- **Lifecycle Phase**: CONSTRUCTION → OPERATIONS
- **Current Stage**: UOW-03 COMPLETO. Deploy prod en curso (PR #6 mergeado → pipeline CI/CD activo).
- **Last Session Date**: 2026-03-25
- **Next**: 1) Confirmar deploy prod exitoso + prod-snapshot. 2) Iniciar OPERATIONS phase.

## Test Coverage (total acumulado)
- **Total tests**: 262 passing (0 failing)
- **UOW-01**: 75 tests (52 unit, 14 integration, 9 e2e)
- **UOW-02**: 93 tests (65 unit, 14 integration, 14 e2e)
- **UOW-03**: 94 tests (71 unit, 14 integration, 9 e2e) — incluye 11 BDD acceptance tests

## CI/CD Pipeline (operativo)
- **Branch**: main
- **Jobs**: test → build-push (ECR) → terraform apply → ECS deploy
- **Auth**: OIDC (sin credenciales de larga duración en Secrets)
- **Secrets requeridos en GitHub**: `AWS_DEPLOY_ROLE_ARN`, `TELEGRAM_BOT_TOKEN`

## Fixes aplicados en Build and Test
| Fix | Descripción |
|-----|-------------|
| `config.py extra="ignore"` | pydantic-settings rechazaba `AWS_*` vars del `.env` |
| `requirements-dev.txt` | pytest/moto/pytest-asyncio faltaban en CI |
| `get_top3(now=)` inyectable | tests de ciclos fallaban por desface UTC vs local |
| `datetime.now(timezone.utc)` en e2e | `date.today()` usaba timezone local, ciclo usa UTC |

## Decisiones Tecnicas Relevantes

| Decision | Razon |
|----------|-------|
| API Gateway HTTP API (no ALB) | Mas barato (~$43/mes vs ~$60+), TLS automatico |
| pyenv local 3.12.4 | Python 3.12 requerido (StrEnum), pyenv configurado |
| .venv en raiz del proyecto | Entorno aislado, ya en .gitignore |
| run_polling para local | Webhook requiere URL publica, polling es suficiente para dev |
| LocalStack 3.4 via docker-compose | Prueba local completa sin cuenta AWS |
| OIDC para GitHub Actions | Sin credenciales de larga duración en Secrets |
| `extra="ignore"` en pydantic-settings | AWS_* vars en .env no declaradas en Settings |
| `now` inyectable en get_top3 | Determinismo en tests sin depender del reloj del sistema |

## Proximos Pasos (siguiente sesion)

1. **Confirmar deploy prod** — verificar ECS task estable con UOW-03 activo (nudge scheduler corriendo)
2. **prod-snapshot** — ejecutar skill para documentar estado AWS actualizado
3. **OPERATIONS phase** — iniciar según AI-DLC workflow
