# Code Generation Plan — UOW-04 Respond & State Transition

## Contexto de la unidad

| Campo | Valor |
|---|---|
| Unidad | UOW-04 Respond & State Transition |
| Workspace root | `/Users/angelmondragon/Desktop/PPAI/ppai` |
| Paquete principal | `ppai/respond/` (nuevo) |
| Tests | `tests/unit/respond/`, `tests/integration/respond/`, `tests/e2e/` |
| Infra | `terraform/modules/dynamodb/` (solo TTL en events) |

## Stories cubiertas

| Story | Descripción |
|---|---|
| US-07 | Cierre de estado por respuesta (done/snooze/clarify con transiciones reales) |
| US-08 | Registro de eventos del loop (InteractionEvents en ppai-events + ppai-cycles) |

## Dependencias hacia unidades anteriores

| Recurso | Unidad origen | Uso |
|---|---|---|
| `TaskState`, `TaskStatus` | UOW-01 | Entidad a transicionar, campos nuevos `snoozed_until`, `completed_at` |
| `DynamoDBTaskStateRepository` | UOW-01 | Leer/guardar tareas con nuevos campos |
| `DynamoDBEventRepository` | UOW-01 | Registrar InteractionEvents en `ppai-events` |
| `ExecutionCycle`, `CycleRepository` | UOW-02 | Correlación de ciclo diario |
| `DecisionService.invalidate_cache()` | UOW-02 | Invalidar Top 3 tras callback |
| `CycleEventRepository` | UOW-03 | Registrar eventos de interacción en `ppai-cycles` |
| `UserRegistry` | v0.7.0 | Registrar user_id en callbacks |
| `structlog`, `config.py` | Shared | Logging y settings |

## Gap Analysis — qué existe vs qué falta

### Ya existe (en UOW-02 DecisionTelegramAdapter):
- Callback handler parsea `done:{task_id}`, `snooze:{task_id}`, `clarify:{task_id}`
- ACK messages + keyboard removal
- `clarify` llama `DecisionService.clarify()` (transición básica)
- Cache invalidation on done/snooze callbacks
- `TaskStatus` enum tiene DONE, SNOOZED, NEEDS_CLARIFICATION

### Falta (scope de UOW-04):
- `done` callback: no transiciona a DONE (solo muestra ACK)
- `snooze` callback: no transiciona a SNOOZED ni incrementa `snooze_count`
- No hay confirmación de Done (2 steps)
- No hay límite de snooze ni auto-clarify
- No hay detección de clarify response por texto libre
- No hay InteractionEvents registrados
- No hay idempotency guard
- No hay authorization guard
- Campos `snoozed_until` y `completed_at` no existen en TaskState
- `list_pending` no filtra por `snoozed_until`

---

## Pasos de generación

### Step 1 — Domain Layer: Extender TaskState + nuevos Value Objects
- [ ] Modify `ppai/capture/domain/entities.py`:
  - Agregar campos `snoozed_until: datetime | None = None` y `completed_at: datetime | None = None`
  - Agregar métodos `transition_to_done(now)`, `transition_to_snoozed(now, cooldown)`, `transition_to_needs_clarification(now)`, `resolve_clarification(text, now)`, `is_snooze_limit_reached()`
- [ ] Create `ppai/respond/__init__.py`
- [ ] Create `ppai/respond/domain/__init__.py`
- [ ] Create `ppai/respond/domain/value_objects.py`:
  - `ResponseAction` (StrEnum): DONE, SNOOZE, CLARIFY
  - Constantes: `MAX_SNOOZE_COUNT = 3`, `SNOOZE_COOLDOWN = timedelta(hours=1)`
- [ ] Create `ppai/respond/domain/entities.py`:
  - `InteractionEvent`: event_id, user_id, task_id, event_type, correlation_id, metadata, timestamp
  - `TransitionResult`: success, task_id, action, message, requires_confirmation, previous_status, new_status
- [ ] Create `ppai/respond/domain/exceptions.py`:
  - `RespondError`, `InvalidTransitionError`, `UnauthorizedCallbackError`
- **Stories**: US-07

### Step 2 — Domain Layer: Unit Tests
- [ ] Create `tests/unit/respond/__init__.py`
- [ ] Create `tests/unit/respond/test_domain.py`:
  - `TaskState.transition_to_done`: estado válido → DONE + completed_at
  - `TaskState.transition_to_done`: estado inválido → raise
  - `TaskState.transition_to_snoozed`: incrementa snooze_count, setea snoozed_until
  - `TaskState.transition_to_snoozed`: snooze_count >= 3 → raise
  - `TaskState.resolve_clarification`: actualiza texto, reset snooze_count, status=PENDING
  - `TaskState.is_snooze_limit_reached`: true/false
  - `InteractionEvent`: construcción, campos obligatorios
  - `TransitionResult`: con y sin confirmación
- **Stories**: US-07

### Step 3 — BDD Scenarios: /story-to-bdd para US-07, US-08
- [ ] Create `tests/features/e4/us07.feature`: done con confirmación, snooze con cooldown, snooze limit, clarify + response
- [ ] Create `tests/features/e4/us08.feature`: eventos registrados por acción, best-effort en fallo
- [ ] Create `tests/unit/e4/__init__.py`
- [ ] Create `tests/unit/e4/test_us07.py`: skeleton pytest en RED
- [ ] Create `tests/unit/e4/test_us08.py`: skeleton pytest en RED
- **Stories**: US-07, US-08

### Step 4 — Application Layer: Ports
- [ ] Create `ppai/respond/application/__init__.py`
- [ ] Create `ppai/respond/application/ports.py`:
  - `InteractionEventRepository` (Protocol): `append(event: InteractionEvent) -> None`
  - Reutiliza: `TaskStateRepository`, `CycleEventRepository`, `CycleRepository` de UOW-01/02/03
- **Stories**: US-07, US-08

### Step 5 — Application Layer: ResponseService
- [ ] Create `ppai/respond/application/response_service.py`:
  - `__init__(task_repo, event_repo, cycle_event_repo, cycle_repo, decision_service)`
  - `handle_done(user_id, task_id) → TransitionResult` (BR-RSP-01, BR-RSP-06, BR-RSP-07)
  - `confirm_done(user_id, task_id) → TransitionResult` (BR-RSP-01, BR-RSP-08)
  - `handle_snooze(user_id, task_id) → TransitionResult` (BR-RSP-02, BR-RSP-03, BR-RSP-06, BR-RSP-07)
  - `handle_clarify(user_id, task_id) → TransitionResult` (BR-RSP-04, BR-RSP-06, BR-RSP-07)
  - `handle_clarify_response(user_id, text) → TransitionResult` (BR-RSP-05)
  - `_authorize(callback_user_id, task) → bool` (BR-RSP-07)
  - `_record_event(...)` con try/except best-effort (BR-RSP-09)
- **Stories**: US-07, US-08

### Step 6 — Application Layer: Unit Tests (ResponseService)
- [ ] Create `tests/unit/respond/test_response_service.py`:
  - handle_done: happy path → requires_confirmation=True
  - confirm_done: happy path → status=DONE, event recorded, cache invalidated
  - confirm_done: idempotent (already DONE) → message informativo
  - handle_snooze: happy path → SNOOZED, snooze_count++, snoozed_until
  - handle_snooze: limit reached → auto-clarify
  - handle_snooze: idempotent (already SNOOZED) → message informativo
  - handle_clarify: happy path → NEEDS_CLARIFICATION
  - handle_clarify_response: happy path → PENDING, texto actualizado, snooze_count=0
  - handle_clarify_response: no task in NEEDS_CLARIFICATION → message
  - authorization: mismatch → rejected
  - event recording failure → transition not reverted
- **Stories**: US-07, US-08

### Step 7 — Modify list_pending: Snooze Cooldown Filter
- [ ] Modify `ppai/decision/application/decision_service.py`:
  - `get_top3` filtra tareas con `snoozed_until > now` (cooldown pasivo)
- [ ] Modify `ppai/capture/infrastructure/dynamodb_task_repo.py`:
  - `_to_entity` y `_to_item` manejan `snoozedUntil` y `completedAt`
- [ ] Update tests unitarios de DecisionService si se ven afectados
- **Stories**: US-07

### Step 8 — Infrastructure Layer: InteractionEvent en ppai-events
- [ ] Modify `ppai/capture/infrastructure/dynamodb_event_repo.py`:
  - Agregar método `append_interaction(event: InteractionEvent)` con campo `ttl`
  - TTL = `int(event.timestamp.timestamp()) + 7_776_000` (90 días)
- [ ] Modify Terraform `terraform/modules/dynamodb/main.tf`:
  - Agregar bloque `ttl { attribute_name = "ttl"; enabled = true }` a tabla events
- **Stories**: US-08

### Step 9 — Infrastructure Layer: ResponseTelegramAdapter
- [ ] Create `ppai/respond/infrastructure/__init__.py`
- [ ] Create `ppai/respond/infrastructure/response_telegram_adapter.py`:
  - Reemplaza callback handling de `DecisionTelegramAdapter`
  - Callback patterns: `done:`, `confirm_done:`, `cancel_done:`, `snooze:`, `clarify:`
  - `MessageHandler` para clarify response (texto libre cuando user tiene task NEEDS_CLARIFICATION)
  - Botones de confirmación Done: `[Sí] [No]` via `edit_message_reply_markup`
- **Stories**: US-07

### Step 10 — Infrastructure Layer: Integration Tests
- [ ] Create `tests/integration/respond/__init__.py`
- [ ] Create `tests/integration/respond/test_dynamodb_interaction_events.py` (moto):
  - append_interaction: evento con TTL persiste y se lee
  - TTL attribute tiene valor correcto (timestamp + 90 días)
  - InteractionEvent y CaptureEvent coexisten en misma tabla
- **Stories**: US-08

### Step 11 — Infrastructure Layer: Adapter Tests
- [ ] Create `tests/unit/respond/test_response_telegram_adapter.py`:
  - done callback → muestra botones [Sí] [No]
  - confirm_done callback → ACK + transición
  - cancel_done callback → restaura keyboard
  - snooze callback → ACK + snooze_count en mensaje
  - snooze limit → auto-clarify message
  - clarify callback → pregunta de aclaración
  - texto libre con task en NEEDS_CLARIFICATION → resolve
  - authorization failure → mensaje genérico
  - idempotent callback → mensaje informativo
- **Stories**: US-07

### Step 12 — Wiring en main.py + Refactor callbacks
- [ ] Modify `ppai/main.py`:
  - Instanciar `ResponseService` con repos existentes
  - Instanciar `ResponseTelegramAdapter`
  - Reemplazar `CallbackQueryHandler` pattern para incluir `confirm_done:` y `cancel_done:`
  - Agregar `MessageHandler` para clarify response (con filtro de prioridad menor que /top3 y /config)
  - Remover callback handling de `DecisionTelegramAdapter` (mover a ResponseTelegramAdapter)
- **Stories**: US-07, US-08

### Step 13 — E2E Tests
- [ ] Create/extend `tests/e2e/test_respond_flow.py` (moto + mock Telegram):
  - Flujo completo done: press → confirm → DONE, evento registrado
  - Flujo completo snooze: press → SNOOZED → cooldown → disponible en next /top3
  - Flujo completo snooze limit: 3 snoozes → auto-clarify
  - Flujo completo clarify: press → question → text response → PENDING
  - Idempotent: double-press done → segundo callback informativo
  - Authorization: otro user_id → rechazado
- **Stories**: US-07, US-08

### Step 14 — BDD Tests: Turn Green
- [ ] Implement `tests/unit/e4/test_us07.py`: todos los escenarios pasan
- [ ] Implement `tests/unit/e4/test_us08.py`: todos los escenarios pasan
- **Stories**: US-07, US-08

### Step 15 — Documentation Summary
- [ ] Create `aidlc-docs/construction/respond-state-transition/code/code-generation-summary.md`:
  - Inventario de archivos generados/modificados
  - Cobertura de stories US-07, US-08
  - Test coverage (unit + integration + e2e + BDD)
- [ ] Update `aidlc-docs/aidlc-state.md`: Code Generation UOW-04 → ✅
- **Stories**: US-07, US-08 traceability

---

## Resumen del plan

| Categoría | Steps | Archivos nuevos | Archivos modificados |
|-----------|-------|-----------------|---------------------|
| Domain | 1-2 | 5 | 1 (`entities.py` UOW-01) |
| BDD | 3, 14 | 5 | 0 |
| Application | 4-6 | 3 | 0 |
| Cooldown filter | 7 | 0 | 3 |
| Infrastructure | 8-11 | 4 | 3 |
| Wiring | 12 | 0 | 1 (`main.py`) |
| E2E | 13 | 1 | 0 |
| Docs | 15 | 1 | 1 |
| **Total** | **15 steps** | **~19 archivos** | **~9 archivos** |

## Estimación de tests nuevos

| Tipo | Tests estimados |
|------|----------------|
| Unit (domain + service + adapter) | ~35 |
| BDD acceptance | ~10 |
| Integration (DynamoDB) | ~5 |
| E2E | ~6 |
| **Total** | **~56 tests** |

## Linear Issues

Cada step se puede mapear a un issue hijo de PPA-54 o crear un issue padre UOW-04 Code Generation con sub-issues por step.
