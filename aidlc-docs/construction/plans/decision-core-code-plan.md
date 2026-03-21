# Code Plan — UOW-02 Decision Core

**Fecha**: 2026-03-21
**Estado**: En progreso
**Rama**: `feature/uow-02-decision-core` (sugerida)

---

## Resumen de cambios

| Área | Tipo | Descripción |
|---|---|---|
| `ppai/decision/` | Nuevo módulo | Domain, Application, Infrastructure |
| `ppai/capture/domain/entities.py` | Modificación | Añadir `snooze_count` a TaskState |
| `ppai/main.py` | Modificación | Wiring de DecisionService + handlers /top3 + callbacks |
| `terraform/modules/dynamodb/` | Modificación | Tabla `ppai-cycles` + GSI |
| `terraform/modules/iam/` | Modificación | Permisos sobre `ppai-cycles` |
| `tests/` | Nuevos | Unit, integration, e2e para decision core |

---

## Steps

### Step 1 — Domain Layer: Entities, Value Objects y Scoring Rules

**Archivos a crear:**
```
ppai/decision/__init__.py
ppai/decision/domain/__init__.py
ppai/decision/domain/value_objects.py        ← CycleStatus enum
ppai/decision/domain/entities.py             ← ExecutionCycle, PriorityScore, Top3Result
ppai/decision/domain/exceptions.py           ← DecisionError hierarchy
ppai/decision/domain/scoring_rules.py        ← Constantes del algoritmo v1.0
```

**Archivos a modificar:**
```
ppai/capture/domain/entities.py              ← Añadir snooze_count: int = 0 a TaskState
```

**Detalles:**
- `CycleStatus`: StrEnum con `active`, `closed`
- `ExecutionCycle`: dataclass con `cycle_id`, `user_id`, `date` (str YYYY-MM-DD),
  `status`, `top3_task_ids`, `manual_reorders`, `created_at`, `closed_at`
- `PriorityScore`: dataclass (value object, no entity) con `task_id`, `urgency_score`,
  `age_score`, `snooze_score`, `total_score`, `explanation`
- `Top3Result`: dataclass con `cycle_id`, `user_id`, `ranked_scores`, `generated_at`
- `scoring_rules.py`: constantes `URGENCY_SCORE_24H=10`, `URGENCY_SCORE_72H=7`,
  `URGENCY_SCORE_FAR=4`, `URGENCY_SCORE_NONE=3`, `AGE_SCORE_MAX_DAYS=7`,
  `SNOOZE_SCORE_MULTIPLIER=2`, `SNOOZE_SCORE_MAX=10`, `TOP3_CACHE_TTL_SECONDS=60`
- `snooze_count: int = 0` en TaskState (backward compatible — tareas existentes tratadas como 0)

**Linear**: PPA-22

---

### Step 2 — Domain Layer: ScoringEngine (puro, sin I/O)

**Archivos a crear:**
```
ppai/decision/domain/scoring_engine.py       ← ScoringEngine
```

**Detalles:**
- Clase `ScoringEngine` sin estado, sin efectos secundarios
- Método `score(task: TaskState, now: datetime) -> PriorityScore`
- Métodos privados: `_urgency_score`, `_age_score`, `_snooze_score`, `_build_explanation`
- `_urgency_score`: usa `task.deadline` vs `now` + umbrales 24h/72h (BR-DEC-02)
- `_age_score`: `min(days_since_pending, 7)` donde `days_since_pending = (now - task.updated_at).days`
- `_snooze_score`: `min(task.snooze_count * 2, 10)`
- `_build_explanation`: genera texto en español combinando factores con valor > 0
  - Ejemplos: `"deadline hoy + 3 días pendiente"`, `"sin deadline + pospuesta 2 veces"`
- `now` como parámetro explícito (determinismo en tests sin monkey-patching)

**Linear**: PPA-23

---

### Step 3 — Domain Layer: Unit Tests (entities + scoring engine)

**Archivos a crear:**
```
tests/unit/decision/__init__.py
tests/unit/decision/test_entities.py         ← ExecutionCycle invariantes
tests/unit/decision/test_scoring_engine.py   ← BR-DEC-02, BR-DEC-03, BR-DEC-05
```

**Cobertura mínima (test_scoring_engine.py):**
- `test_urgency_deadline_within_24h` → urgencyScore=10
- `test_urgency_deadline_within_72h` → urgencyScore=7
- `test_urgency_deadline_far` → urgencyScore=4
- `test_urgency_no_deadline` → urgencyScore=3
- `test_age_score_zero_days` → ageScore=0
- `test_age_score_capped_at_7` → 10 días → ageScore=7
- `test_snooze_score_zero` → snoozeCount=0 → snoozeScore=0
- `test_snooze_score_capped_at_10` → snoozeCount=6 → snoozeScore=10
- `test_total_score_sum` → urgency+age+snooze
- `test_explanation_combined` → texto legible en español
- `test_determinism` → mismo input, mismo resultado con diferentes instancias

**Linear**: PPA-24

---

### Step 4 — Application Layer: Ports

**Archivos a crear:**
```
ppai/decision/application/__init__.py
ppai/decision/application/ports.py          ← Protocols: CycleRepository
```

**Detalles:**
- `CycleRepository(Protocol)`:
  - `get_active(user_id: str, date: str) -> ExecutionCycle | None`
  - `save(cycle: ExecutionCycle) -> None`
  - `update_top3(cycle_id: str, top3_task_ids: list[str]) -> None`
  - `increment_reorders(cycle_id: str) -> None`

**Linear**: PPA-25

---

### Step 5 — Application Layer: DecisionService

**Archivos a crear:**
```
ppai/decision/application/decision_service.py
```

**Detalles:**
- Constructor: `task_repo` (TaskStateRepository de UOW-01), `cycle_repo` (CycleRepository),
  `event_repo` (EventRepository de UOW-01), `scoring_engine: ScoringEngine`
- Cache in-memory: `dict[str, CacheEntry]` con `result` y `expires_at` (DP-10)
- Métodos públicos:
  - `get_top3(user_id: str) -> Top3Result` — flujo completo BR-DEC-01..08
  - `clarify(task_id: str, user_id: str) -> str` — retorna pregunta de aclaración (BR-DEC-10)
  - `reorder(user_id: str, task_id: str) -> Top3Result` — mueve tarea a pos #1 (BR-DEC-09)
  - `invalidate_cache(user_id: str) -> None` — para llamar desde UOW-01 al capturar
- Método privado `_get_or_create_cycle` — fallback creation (DP-13, BR-DEC-08)
- `get_top3` actualiza `task.status = prioritized` para las tareas seleccionadas (BR-DEC-04)
- Registro de evento `TOP3_PRESENTED` con best-effort (no falla si registro falla)
- Tie-breaking: `sorted(scores, key=lambda s: (-s.total_score, deadline_key(task), task.created_at))`

**Linear**: PPA-26

---

### Step 6 — Application Layer: Unit Tests para DecisionService

**Archivos a crear:**
```
tests/unit/decision/test_decision_service.py
```

**Cobertura mínima:**
- `test_get_top3_empty_returns_empty_result` (BR-DEC-01, BR-DEC-07)
- `test_get_top3_filters_non_pending` (BR-DEC-01)
- `test_get_top3_scores_and_selects_top3` (BR-DEC-02, BR-DEC-04)
- `test_get_top3_with_only_1_task` (BR-DEC-07)
- `test_get_top3_tie_breaking_by_deadline` (BR-DEC-03)
- `test_get_top3_tie_breaking_by_created_at` (BR-DEC-03)
- `test_get_top3_transitions_status_to_prioritized` (BR-DEC-04)
- `test_get_top3_cache_hit_returns_cached` (DP-10)
- `test_get_top3_cache_expired_recomputes` (DP-10)
- `test_invalidate_cache_clears_entry` (DP-10)
- `test_clarify_transitions_to_needs_clarification` (BR-DEC-10)
- `test_reorder_moves_task_to_position_1` (BR-DEC-09)
- `test_reorder_increments_manual_reorders` (BR-DEC-09)
- `test_cycle_fallback_created_if_not_exists` (DP-13, BR-DEC-08)
- Usar repos fake (in-memory) — sin mocks de biblioteca

**Linear**: PPA-27

---

### Step 7 — Infrastructure Layer: DynamoDB CycleRepository

**Archivos a crear:**
```
ppai/decision/infrastructure/__init__.py
ppai/decision/infrastructure/dynamodb_cycle_repo.py
```

**Detalles:**
- `DynamoDBCycleRepository` implementa `CycleRepository`
- `get_active`: query sobre `userId-date-index` con FilterExpression `status=active`
- `save`: `put_item` con `ConditionExpression=attribute_not_exists(cycleId)` (evita duplicados en race condition)
- `update_top3`: `update_item` sobre `cycle_id`, set `top3TaskIds` y añade evento `TOP3_PRESENTED`
- `increment_reorders`: `update_item` con `ADD manualReorders :one`
- Serialización/deserialización: snake_case Python ↔ camelCase DynamoDB (mismo patrón que UOW-01)
- `snooze_count` en DynamoDB: campo `snoozeCount`, ausente → default 0 en `DynamoDBTaskStateRepository`
  (modificar `dynamodb_task_repo.py` para manejar campo opcional)

**Linear**: PPA-28

---

### Step 8 — Infrastructure Layer: Integration Tests

**Archivos a crear:**
```
tests/integration/decision/__init__.py
tests/integration/decision/test_dynamodb_cycle_repo.py
```

**Detalles (moto para mock DynamoDB):**
- Fixture: crear tabla `ppai-cycles` con GSI `userId-date-index`
- `test_save_and_get_active_cycle`
- `test_get_active_returns_none_if_not_exists`
- `test_save_prevents_duplicate_cycle` (ConditionExpression)
- `test_update_top3_sets_task_ids`
- `test_increment_reorders`

**Linear**: PPA-29

---

### Step 9 — Telegram Adapter: /top3 command + inline keyboard callbacks

**Archivos a crear:**
```
ppai/decision/infrastructure/decision_telegram_adapter.py
```

**Detalles:**
- `DecisionTelegramAdapter(decision_service: DecisionService)`
- `top3_handler(update, context)` — handler para CommandHandler("top3")
  - Llama `decision_service.get_top3(user_id)`
  - Envía 1 mensaje por tarea con `InlineKeyboardMarkup` (DP-11)
  - Formato: `"{N}. {task.normalized_text}"` + botones `[✓ Hecho][⏸ Posponer][? Aclarar]`
  - Maneja Top3Result vacío (BR-DEC-07): `"Tu bandeja está vacía..."`
  - Maneja 1-2 tareas: mensajes disponibles + mensaje motivacional
- `callback_handler(update, context)` — handler para `CallbackQueryHandler`
  - Parsea `callback_data`: `"{action}:{task_id}"`
  - `done` → responde "Marcado como hecho" (UOW-04 lo implementará completamente)
  - `snooze` → responde "Pospuesto" (UOW-04)
  - `clarify` → llama `decision_service.clarify(task_id, user_id)` → envía pregunta
  - Llama `callback_query.answer()` en todos los casos (ACK al botón)
  - Invalida cache tras cualquier callback

**Linear**: PPA-30

---

### Step 10 — E2E Tests: flujo /top3 completo

**Archivos a crear:**
```
tests/e2e/test_top3_flow.py
```

**Cobertura:**
- `test_top3_command_empty_inbox` — usuario sin tareas → mensaje bandeja vacía
- `test_top3_command_with_tasks` — 5 tareas pending → top 3 con botones
- `test_top3_callback_clarify` → tarea entra en needs_clarification, pregunta enviada
- `test_top3_partial_inbox_2_tasks` → 2 tareas + mensaje motivacional
- Usar Application de python-telegram-bot en modo test (sin conexión real)

**Linear**: PPA-31

---

### Step 11 — Terraform: tabla ppai-cycles + IAM

**Archivos a modificar:**
```
terraform/modules/dynamodb/main.tf           ← Nuevo resource ppai-cycles + GSI
terraform/modules/dynamodb/outputs.tf        ← Output ARN ppai-cycles
terraform/modules/iam/main.tf                ← Permisos sobre ppai-cycles
```

**Detalles:**
- Resource `aws_dynamodb_table.cycles`:
  - `name = "${var.table_prefix}-cycles"`
  - PK: `cycleId (S)`, GSI: `userId-date-index` (PK=userId, SK=date), `ALL` projection
  - `billing_mode = "PAY_PER_REQUEST"`, `deletion_protection_enabled = true`
  - `server_side_encryption { enabled = true }`
- IAM policy inline en task role:
  - `PutItem, GetItem, UpdateItem, Query` sobre `ppai-cycles` y `ppai-cycles/index/*`

**Linear**: PPA-32

---

### Step 12 — main.py: wiring UOW-02

**Archivos a modificar:**
```
ppai/main.py                                 ← Wire DecisionService + handlers
```

**Detalles:**
- Crear `cycles_table` con `dynamodb.Table(table_name(prefix, "cycles"))`
- Instanciar `DynamoDBCycleRepository(cycles_table)`
- Instanciar `ScoringEngine()`
- Instanciar `DecisionService(task_repo, cycle_repo, event_repo, scoring_engine)`
- Instanciar `DecisionTelegramAdapter(decision_service)`
- Registrar handlers:
  ```python
  application.add_handler(CommandHandler("top3", decision_adapter.top3_handler))
  application.add_handler(
      CallbackQueryHandler(decision_adapter.callback_handler, pattern=r"^(done|snooze|clarify):.+$")
  )
  ```
- `CaptureService` llama `decision_service.invalidate_cache(user_id)` al finalizar captura exitosa

**Linear**: PPA-33

---

## Recomendaciones para GitHub Actions + Variables de entorno (Prod)

> Comentario proactivo antes de empezar a codear.

### Estrategia recomendada: GitHub Actions + AWS OIDC (sin credenciales hardcodeadas)

En lugar de guardar `AWS_ACCESS_KEY_ID` y `AWS_SECRET_ACCESS_KEY` como secrets de GitHub,
la práctica recomendada es **OIDC (OpenID Connect)**:

```
GitHub Actions → asume IAM Role via OIDC → sin credenciales de larga duración
```

**Variables de entorno por ambiente (GitHub Environments):**

| Variable | Dónde | Tipo |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | GitHub Secret (env: prod) | Secret |
| `AWS_REGION` | GitHub Variable (env: prod) | Plain |
| `DYNAMODB_TABLE_PREFIX` | GitHub Variable (env: prod) | Plain |
| `ACTIVE_TASK_LIMIT` | GitHub Variable (env: prod) | Plain |
| `RATE_LIMIT_PER_MINUTE` | GitHub Variable (env: prod) | Plain |

**Pipeline sugerido (`.github/workflows/deploy.yml`):**
```
push to main
  → test (pytest, all envs mocked)
  → build Docker image
  → push a ECR (via OIDC, sin secrets hardcodeados)
  → terraform apply (solo cambios)
  → ECS force-new-deployment
  → health check (curl /health endpoint)
```

**Configuración OIDC** → Step 15 (UOW-01 pendiente) lo implementa.
Para MVP con credenciales actuales, podemos usar secrets de GitHub temporalmente
y migrar a OIDC en Step 15.

---

## Orden de ejecución recomendado

```
Step 1 → Step 2 → Step 3   (Domain puro — testeable sin infra)
Step 4 → Step 5 → Step 6   (Application — testeable con fakes)
Step 7 → Step 8            (Infrastructure DynamoDB)
Step 9 → Step 10           (Telegram adapter + E2E)
Step 11                    (Terraform — infra)
Step 12                    (Wiring final main.py)
```

## Tabla de Linear Issues

| Step | Descripción | Linear ID |
|---|---|---|
| Step 1 | Domain entities + scoring rules | PPA-22 |
| Step 2 | ScoringEngine | PPA-23 |
| Step 3 | Unit tests domain | PPA-24 |
| Step 4 | Application ports | PPA-25 |
| Step 5 | DecisionService | PPA-26 |
| Step 6 | Unit tests service | PPA-27 |
| Step 7 | DynamoDB CycleRepo | PPA-28 |
| Step 8 | Integration tests | PPA-29 |
| Step 9 | Telegram adapter | PPA-30 |
| Step 10 | E2E tests | PPA-31 |
| Step 11 | Terraform | PPA-32 |
| Step 12 | main.py wiring | PPA-33 |
