# Code Generation Plan — UOW-03 Push & Scheduling

## Contexto de la unidad

| Campo | Valor |
|---|---|
| Unidad | UOW-03 Push & Scheduling |
| Workspace root | `/Users/angelmondragon/Desktop/PPAI/ppai` |
| Paquete principal | `ppai/push/` |
| Tests | `tests/unit/push/`, `tests/integration/push/`, `tests/e2e/` |
| Infra | `terraform/modules/dynamodb/`, `terraform/modules/iam/` |

## Stories cubiertas

| Story | Descripción |
|---|---|
| US-05 | Nudge accionable en Telegram (dispatch, retry, botones inline) |
| US-06 | Control de intensidad y ventana de empuje (preferencias, silencio, límite diario) |

## Dependencias hacia unidades anteriores

| Recurso | Unidad origen | Uso |
|---|---|---|
| `TaskState`, `TaskStatus` | UOW-01 | Tarea objetivo, transición `prioritized → nudged` |
| `DynamoDBTaskStateRepository` | UOW-01 | Update status a `nudged` |
| `ExecutionCycle`, `CycleRepository` | UOW-02 | Ciclo activo del día, registro de eventos |
| `DecisionService.get_top3()` | UOW-02 | Obtener Top 3 vigente para tarea #1 |
| `structlog`, `config.py` | Shared | Logging estructurado y settings |

---

## Pasos de generación

### Step 1 — Domain Layer: Entities, Value Objects & Exceptions ✅
- [x] Create `ppai/push/__init__.py`
- [x] Create `ppai/push/domain/__init__.py`
- [x] Create `ppai/push/domain/value_objects.py`
  - `NudgeDispatchStatus` (StrEnum): scheduled | sent | skipped_activity | skipped_no_top3 | failed
  - `WindowEvaluation` (dataclass): window_start, window_end, is_silence_window, recent_activity
  - `DispatchOutcome` (dataclass): status, task_id, cycle_id, sent_at, reason
- [ ] Create `ppai/push/domain/entities.py`
  - `UserNudgePreferences`: userId, timezone (default=America/Bogota), maxNudgesPerDay=3, silenceStart, silenceEnd, updatedAt
  - `NudgeMessage` (VO): taskTitle, priorityReason, toneProfile, buttons
- [ ] Create `ppai/push/domain/exceptions.py`
  - `PushError`, `NoTop3AvailableError`, `SilenceWindowActiveError`, `DailyCapReachedError`, `NudgeDispatchFailedError`
- **Stories**: US-05, US-06

### Step 2 — Domain Layer: Unit Tests ✅
- [x] Create `tests/unit/push/__init__.py`
- [ ] Create `tests/unit/push/test_domain.py`
  - `UserNudgePreferences`: defaults correctos, timezone fallback America/Bogota
  - `WindowEvaluation`: ventana normal, ventana que cruza medianoche (DP-PUSH-04)
  - `NudgeDispatchStatus`: todos los valores del StrEnum
  - `NudgeMessage`: construcción con campos obligatorios
- **Stories**: US-05, US-06

### Step 3 — BDD Scenarios: /story-to-bdd para US-05, US-06 ✅
- [x] Create `tests/features/e3/us05.feature`: nudge accionable, retry controlado, bandeja sin Top 3
- [ ] Create `tests/features/e3/us06.feature`: ventana de silencio, límite diario, actividad reciente
- [ ] Create `tests/unit/e3/__init__.py`
- [ ] Create `tests/unit/e3/test_us05.py`: skeleton pytest en RED (pytest.fail)
- [ ] Create `tests/unit/e3/test_us06.py`: skeleton pytest en RED (pytest.fail)
- **Stories**: US-05, US-06

### Step 4 — Application Layer: Ports (Repository Interfaces) ✅
- [x] Create `ppai/push/application/__init__.py`
- [ ] Create `ppai/push/application/ports.py`
  - `PreferencesRepository` (Protocol): `get(user_id) → UserNudgePreferences | None`, `save(prefs)`
  - `CycleEventRepository` (Protocol): `get_active(user_id, date) → ExecutionCycle | None`, `create(cycle)`, `record_nudge_event(cycle_id, event_type, metadata)`, `get_nudge_count(cycle_id) → int`, `get_last_activity_at(user_id) → datetime | None`
  - `TelegramPushPort` (Protocol): `send_nudge(chat_id, message) → bool`
- **Stories**: US-05, US-06

### Step 5 — Application Layer: NudgeService ✅
- [x] Create `ppai/push/application/nudge_service.py`
  - `NudgeService.__init__(prefs_repo, cycle_event_repo, task_repo, telegram_port, decision_service)`
  - `run_tick(user_ids: list[str]) → list[DispatchOutcome]`: entrada principal del scheduler
  - `_evaluate_user(user_id, now) → DispatchOutcome`: evaluación completa por usuario
    - cargar preferencias (fallback defaults)
    - resolver timezone operativa
    - verificar ventana de silencio (BR-PUSH-08, DP-PUSH-04)
    - verificar actividad reciente <60 min (BR-PUSH-06)
    - verificar límite diario ≤3 nudges (BR-PUSH-07)
    - obtener Top 3 vigente via DecisionService (BR-PUSH-04, BR-PUSH-05)
    - tomar tarea #1
    - obtener/crear ExecutionCycle (BR-PUSH-02)
    - registrar NUDGE_SCHEDULED (DP-PUSH-02)
    - despachar con retry (BR-PUSH-11, DP-PUSH-05)
    - actualizar tarea → nudged (BR-PUSH-13)
    - registrar NUDGE_SENT | NUDGE_FAILED (BR-PUSH-12, BR-PUSH-14)
  - `_send_with_retry(nudge_msg, chat_id) → bool`: 3 intentos, backoff fijo +30s (DP-PUSH-05)
  - `_build_nudge_message(task, prefs) → NudgeMessage`: tono motivacional suave (BR-PUSH-09, BR-PUSH-10)
  - `_check_re_engagement(user_id, now) → bool`: inactividad >24h (BR-PUSH-15)
- **Stories**: US-05, US-06

### Step 6 — Application Layer: Unit Tests (NudgeService) ✅
- [x] Create `tests/unit/push/test_nudge_service.py`
  - `evaluate_user`: happy path dispatch exitoso
  - `evaluate_user`: skip por ventana de silencio activa
  - `evaluate_user`: skip por actividad reciente (<60 min)
  - `evaluate_user`: skip por límite diario alcanzado (3 nudges)
  - `evaluate_user`: skip por sin Top 3 vigente
  - `_send_with_retry`: éxito en primer intento
  - `_send_with_retry`: éxito en segundo intento (primero falla)
  - `_send_with_retry`: fallo total después de 3 intentos → NUDGE_FAILED
  - `_build_nudge_message`: tono correcto, sin palabras prohibidas
  - `_check_re_engagement`: >24h sin actividad → True
  - `_check_re_engagement`: <24h con actividad → False
- **Stories**: US-05, US-06

### Step 7 — Application Layer: NudgeScheduler ✅
- [x] Create `ppai/push/application/nudge_scheduler.py`
  - `NudgeScheduler.__init__(nudge_service, user_ids_provider, tick_interval_minutes=15)`
  - `start() → None`: inicia el loop asíncrono de ticks (usando `asyncio` o `threading`)
  - `stop() → None`: detiene el scheduler limpiamente
  - `_tick() → None`: llama a `nudge_service.run_tick(user_ids)` cada `tick_interval_minutes`
  - Fail-soft: excepciones del tick se loggean y no rompen el loop (DP-PUSH-06)
  - Log minimal por tick relevante (NUDGE_SENT / SKIPPED / FAILED), no por tick vacío (NFR observability)
- **Stories**: US-05, US-06

### Step 8 — Application Layer: Unit Tests (NudgeScheduler) ✅
- [x] Create `tests/unit/push/test_nudge_scheduler.py`
  - Tick invoca `run_tick` con user_ids correctos
  - Excepción en `run_tick` no propaga → loop sigue (fail-soft)
  - `stop()` detiene el scheduler sin error
- **Stories**: US-05, US-06

### Step 9 — Infrastructure Layer: DynamoDBPreferencesRepository ✅
- [x] Create `ppai/push/infrastructure/__init__.py`
- [ ] Create `ppai/push/infrastructure/dynamodb_preferences_repo.py`
  - `DynamoDBPreferencesRepository(table_name, dynamodb_client)`
  - `get(user_id) → UserNudgePreferences | None`: GetItem; None si no existe
  - `save(prefs: UserNudgePreferences) → None`: PutItem; serializa/deserializa campos
  - Mapeo DynamoDB ↔ `UserNudgePreferences`
- **Stories**: US-06

### Step 10 — Infrastructure Layer: CycleEventRepository ✅
- [x] Create `ppai/push/infrastructure/cycle_event_repo.py`
  - `DynamoDBCycleEventRepository(cycles_table_name, dynamodb_client)`
  - `get_active(user_id, date) → ExecutionCycle | None`: reutiliza lógica de UOW-02
  - `create(cycle: ExecutionCycle) → None`: PutItem con ConditionExpression
  - `record_nudge_event(cycle_id, event_type, metadata: dict) → None`: UpdateItem append a events list
  - `get_nudge_count(cycle_id) → int`: cuántos NUDGE_SENT tiene el ciclo hoy
  - `get_last_activity_at(user_id) → datetime | None`: query sobre events para timestamp más reciente
- **Stories**: US-05

### Step 11 — Infrastructure Layer: Integration Tests (DynamoDB) ✅
- [x] Create `tests/integration/push/__init__.py`
- [x] Create `tests/integration/push/test_dynamodb_push_repos.py` (moto)
  - `DynamoDBPreferencesRepository.get`: retorna None si no existe, prefs si existe
  - `DynamoDBPreferencesRepository.save`: crea y actualiza preferencias
  - `DynamoDBPreferencesRepository`: defaults aplicados correctamente
  - `DynamoDBCycleEventRepository.get_active`: ciclo activo del día
  - `DynamoDBCycleEventRepository.create`: crea ciclo, falla si ya existe
  - `DynamoDBCycleEventRepository.record_nudge_event`: NUDGE_SCHEDULED, NUDGE_SENT, NUDGE_FAILED
  - `DynamoDBCycleEventRepository.get_nudge_count`: cuenta solo NUDGE_SENT
  - `DynamoDBCycleEventRepository.get_last_activity_at`: timestamp correcto
- Extender `conftest.py` con fixture para tabla `ppai-preferences`
- **Stories**: US-05, US-06

### Step 12 — Infrastructure Layer: TelegramPushAdapter ✅
- [x] Create `ppai/push/infrastructure/telegram_push_adapter.py`
  - `TelegramPushAdapter(bot_token)`
  - `send_nudge(chat_id, message: NudgeMessage) → bool`
    - Construye payload: texto con título + razón + botones inline (✓ Hecho / ⏸ Posponer / ? Aclarar)
    - Callback data: `done:{task_id}` / `snooze:{task_id}` / `clarify:{task_id}`
    - Retorna True en éxito, False en fallo
  - `CallbackAuthorizationGuard`: validación `from_user.id == userId` (DP-PUSH-07)
  - Unit tests del adapter: construcción de payload, botones correctos, callback data
- **Stories**: US-05

### Step 13 — Infrastructure Layer: Adapter Tests + main.py wiring ✅
- [x] Create `tests/unit/push/test_telegram_push_adapter.py`
  - Payload tiene título + razón de prioridad
  - Botones inline: ✓ Hecho / ⏸ Posponer / ? Aclarar
  - Callback data correctos: `done:{task_id}`, `snooze:{task_id}`, `clarify:{task_id}`
  - `CallbackAuthorizationGuard`: acepta callback del owner, rechaza de otro user
- [x] Update `ppai/main.py`
  - Wiring: `DynamoDBPreferencesRepository`, `DynamoDBCycleEventRepository`, `TelegramPushAdapter`
  - Instanciar `NudgeService` con dependencias
  - Instanciar `NudgeScheduler` y llamar `scheduler.start()` al arrancar el bot
- **Stories**: US-05, US-06

### Step 14 — Terraform: ppai-preferences table + IAM update ✅
- [x] Update `terraform/modules/dynamodb/main.tf`
  - Agregar `resource "aws_dynamodb_table" "preferences"`: PK=userId, SSE, deletion_protection, PAY_PER_REQUEST
- [x] Update `terraform/modules/dynamodb/outputs.tf`
  - Agregar `output "preferences_table_arn"`
- [x] Update `terraform/modules/iam/variables.tf`
  - Agregar `variable "preferences_table_arn"`
- [x] Update `terraform/modules/iam/main.tf`
  - Agregar statement `GetItem / PutItem / UpdateItem` para `ppai-preferences`
- [x] Update `terraform/main.tf`
  - Pasar `preferences_table_arn = module.dynamodb.preferences_table_arn` al módulo iam
- **Stories**: US-06 (infraestructura soporte)

### Step 15 — E2E Tests: scheduler tick flow ✅
- [x] Create `tests/e2e/test_push_flow.py` (moto + mock Telegram API)
  - Tick con usuario sin Top 3 → NUDGE_SKIPPED (sin mensaje)
  - [x] Tick con Top 3 vigente → NUDGE_SENT, tarea → nudged
  - [x] Tick con ventana de silencio activa → NUDGE_SKIPPED
  - [x] Tick con actividad reciente (<60 min) → NUDGE_SKIPPED
  - [x] Tick con límite diario alcanzado → NUDGE_SKIPPED
  - [x] Reenganche: >24h sin actividad → mensaje de baja intensidad enviado
  - [x] Retry: primer intento falla, segundo OK → NUDGE_SENT
  - [x] Fallo total (3 retries) → NUDGE_FAILED registrado
- **Stories**: US-05, US-06

### Step 16 — Documentation Summary ✅
- [x] Create `aidlc-docs/construction/push-scheduling/code/code-generation-summary.md`
  - Inventario de archivos generados
  - Cobertura de stories US-05, US-06
  - Test coverage (unit + integration + e2e + BDD)
- [x] Update `aidlc-docs/aidlc-state.md`: Code Generation UOW-03 → ✅
- **Stories**: US-05, US-06 traceability

---

## Resumen del plan

| Categoría | Archivos |
|---|---|
| Domain | `value_objects.py`, `entities.py`, `exceptions.py` |
| Application | `ports.py`, `nudge_service.py`, `nudge_scheduler.py` |
| Infrastructure | `dynamodb_preferences_repo.py`, `cycle_event_repo.py`, `telegram_push_adapter.py` |
| Main wiring | `ppai/main.py` (update) |
| Terraform | `dynamodb/main.tf`, `dynamodb/outputs.tf`, `iam/variables.tf`, `iam/main.tf`, `main.tf` |
| Unit tests | `test_domain.py`, `test_nudge_service.py`, `test_nudge_scheduler.py`, `test_telegram_push_adapter.py` |
| Integration tests | `test_dynamodb_push_repos.py` |
| E2E tests | `test_push_flow.py` |
| BDD | `us05.feature`, `us06.feature`, `test_us05.py`, `test_us06.py` |
| Docs | `code-generation-summary.md` |

**Total: 16 steps**
