# Changelog — PPAI (Personal Productivity AI)

Formato: [Keep a Changelog](https://keepachangelog.com/es/1.0.0/)
Versionado: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

> Cambios en progreso que aún no tienen versión asignada.

---

## [v0.4.0] — 2026-03-21

### ✨ Added

- Entorno de desarrollo local completo con LocalStack 3.4 via `docker-compose up -d` — permite probar captura y Top 3 sin cuenta AWS.
- Script `scripts/create-local-tables.py` que crea las 4 tablas DynamoDB (`ppai-tasks`, `ppai-events`, `ppai-dedup`, `ppai-cycles`) con sus GSIs en LocalStack al iniciar.
- Entry point `ppai/local.py` en modo polling para desarrollo local — sin necesidad de URL pública ni webhook.
- Archivo `.env.example` documentado con todos los parámetros de configuración por ambiente (local vs prod).

### ⚙️ Infra

- Pipeline CI/CD completo en GitHub Actions (`.github/workflows/deploy.yml`) con 4 jobs: `test → build-push → terraform → deploy`. Solo despliega en push a `main`.
- OIDC provider IAM + `ppai-github-deploy-role` en Terraform (`iam/github-oidc.tf`) — GitHub Actions asume el role sin credenciales de larga duración en Secrets.
- Permisos mínimos para el deploy role: ECR, ECS, S3 (state), DynamoDB (lock), IAM, CloudWatch Logs.

### 🐛 Fixed

- Corregido error de arranque del bot al leer `.env` con variables `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` — pydantic-settings configurado con `extra="ignore"` para ignorar variables no declaradas en el modelo.

---

## [v0.3.0] — 2026-03-21

### ✨ Added — UOW-02 Decision Core

- Implementado motor de priorización Top 3 determinístico (`ScoringEngine`) con tres factores: urgencia por deadline, antigüedad en pending y conteo de posposiciones. Score máximo posible: 27 puntos.
- Agregada entidad `ExecutionCycle` para agrupar eventos de decisión por usuario por día, con soporte de fallback si el scheduler (UOW-03) aún no existe.
- Agregados value objects `PriorityScore` y `Top3Result` — computados en memoria, nunca persistidos directamente.
- Implementado `DecisionService` con los flujos principales: `get_top3`, `clarify` y `reorder`. Cache in-process con TTL de 60 segundos para evitar queries repetidos a DynamoDB.
- Implementado handler `/top3` en Telegram con presentación por mensaje individual por tarea + botones inline `[✓ Hecho] [⏸ Posponer] [? Aclarar]`.
- Implementado `CallbackQueryHandler` para acciones sobre tareas del Top 3 vía botones inline — formato `{action}:{task_id}`.
- Agregado repositorio DynamoDB `DynamoDBCycleRepository` para tabla `ppai-cycles` con GSI `userId-date-index`.
- Conectados UOW-01 y UOW-02: al capturar una tarea nueva, se invalida automáticamente el cache del Top 3 del usuario.
- Agregado campo `snooze_count` (default 0) en la entidad `TaskState` — backward compatible con tareas existentes.
- Agregado status `NEEDS_CLARIFICATION` al enum `TaskStatus`.
- Agregado método `list_pending` en `DynamoDBTaskStateRepository` usando el GSI `userId-status-index` existente.
- 93 tests nuevos: 65 unitarios, 14 de integración (moto), 14 e2e.

### ⚙️ Infra

- Agregada tabla DynamoDB `ppai-cycles` en Terraform con GSI `userId-date-index`, encryption habilitado y deletion protection.
- Extendido IAM Task Role con permisos `PutItem`, `GetItem`, `UpdateItem`, `Query` sobre `ppai-cycles` y su índice (least privilege).
- Actualizado `main.tf` raíz para pasar `cycles_table_arn` al módulo IAM.

### 📝 Docs

- Generado Code Plan UOW-02 (`aidlc-docs/construction/plans/decision-core-code-plan.md`) con 12 steps, tabla de Linear Issues y estrategia de GitHub Actions + OIDC para prod.
- Actualizado `aidlc-state.md` con progreso UOW-02 completo y próximos pasos.

---

## [v0.2.0] — 2026-03-17

### ✨ Added — UOW-01 Capture Foundation

- Implementada capa de dominio completa: entidades `Intent`, `TaskState`, `CaptureEvent`, `DedupRecord`; enum `TaskStatus` con 7 estados; jerarquía de excepciones `CaptureError`.
- Implementada capa de aplicación: puertos (`TaskStateRepository`, `EventRepository`, `DedupRepository`), `CaptureService` con 10 reglas de negocio (BR-CAP-01..10) — normalización, extracción de tags, deadlines relativos, deduplicación, límite de tareas activas.
- Implementada capa de infraestructura: `DynamoDBTaskStateRepository`, `DynamoDBEventRepository`, `DynamoDBDedupRepository` (con TTL configurable), adapter de Telegram para captura de texto libre, rate limiter in-memory con ventana deslizante, logging estructurado con structlog.
- Implementado entry point `main.py` en modo webhook (puerto 8443).
- Infraestructura completa en Terraform (7 módulos): VPC, ECS Fargate, ECR, DynamoDB (3 tablas + GSIs), IAM con least privilege, API Gateway HTTP, CloudWatch Log Groups.
- Dockerfile multi-stage optimizado para producción en ECS Fargate.
- 75 tests: 52 unitarios (domain + service), 14 de integración (DynamoDB con moto), 9 e2e (flujo Telegram simulado).

### ⚙️ Infra

- Módulos Terraform: `networking`, `dynamodb`, `ecr`, `iam`, `ecs`, `api-gateway`, `monitoring`.
- Tablas DynamoDB con billing On-Demand, deletion protection, GSI `userId-status-index` en `ppai-tasks`.
- VPC endpoints para DynamoDB (tráfico interno, sin NAT para DB calls).

### 📝 Docs

- Workflow AI-DLC documentado en `AI_DLC_WORKFLOW.md` con fases Inception, Construction y Operations.
- Documentación de diseño UOW-01: functional design, NFR requirements, NFR design, infrastructure design.
- Guía de setup completa (`docs/setup-guide.md`): configuración Telegram, LocalStack, deploy AWS.

---

## [v0.1.0] — 2026-03-09

### ✨ Added — Fundación del proyecto

- PRD v1.0 consolidado (`specs/prd.md`) con visión del producto, user stories y criterios de aceptación.
- Backlog inicial generado desde PRD con épicas y stories priorizadas.
- MCPs configurados en `.mcp.json`: `filesystem`, `github`, `sqlite`, `linear`.

### ⚙️ Infra

- Skills disponibles: `prd-to-backlog`, `story-to-bdd`, `changelog`, `aidlc-to-linear`.
- Workflow AI-DLC (AI-Driven Development Lifecycle) definido como metodología del proyecto.
- Estructura de carpetas del repositorio: `specs/`, `aidlc-docs/`, `ppai/`, `terraform/`, `tests/`, `docs/`.

### 📝 Docs

- `CLAUDE.md` con instrucciones del proyecto para Claude Code.
- Documentación de fases Inception completas: Requirements Analysis, User Stories, Workflow Planning, Application Design, Units Planning.

---

[Unreleased]: https://github.com/amondrave/PPAI-Agent/compare/v0.4.0...HEAD
[v0.4.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.3.0...v0.4.0
[v0.3.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.2.0...v0.3.0
[v0.2.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/amondrave/PPAI-Agent/releases/tag/v0.1.0
