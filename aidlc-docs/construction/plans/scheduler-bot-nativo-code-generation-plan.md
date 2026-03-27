# Code Generation Plan — UOW-05 Scheduler Bot Nativo

## Contexto

**Stories**: US-09 (reporte diario), US-10 (rescue mode), parcialmente US-06 (control intensidad).
**Dependencias**: UOW-01 (TaskStateRepository), UOW-02 (DecisionService, ExecutionCycle), UOW-03 (NudgeScheduler, NudgeService, PreferencesRepository, ConfigTelegramAdapter), UOW-04 (ResponseService).
**Workspace root**: `/Users/angelmondragon/Desktop/PPAI/ppai`
**Rama**: `feature/uow-05-scheduler-bot-nativo` (crear desde main)

## Hallazgo importante

El GSI `userId-status-index` **ya existe** en `ppai-tasks` con `projection_type = "ALL"`, y el IAM ya tiene `dynamodb:Query` sobre `${var.tasks_table_arn}/index/*`. **No hay delta de Terraform**. Además, `DynamoDBTaskStateRepository` ya tiene `list_by_status()` que usa este GSI. `DailySummaryBuilder` puede reutilizar directamente.

## Plan de generación

### Step 1: Domain — Extender UserNudgePreferences + nuevos value objects ✅
- [x] Modificar `ppai/push/domain/entities.py`
- [x] Modificar `ppai/push/domain/value_objects.py`
- [x] Tests unitarios: `tests/unit/push/test_entities_uow05.py` (23 tests passing)
  - Test defaults de nuevos campos
  - Test `is_within_start_window` / `is_within_end_window` con ±7 min
  - Test cross-midnight tolerance
  - Test `should_zen_override_silence()`
  - Test ZenSession cap y reset

### Step 2: Application — ZenSessionManager ✅
- [x] Crear `ppai/push/application/zen_session_manager.py`
- [x] Tests unitarios: `tests/unit/push/test_zen_session_manager.py` (13 tests passing)
  - Test activate/deactivate lifecycle
  - Test record_nudge con cap
  - Test auto-deactivation al alcanzar cap
  - Test get_min_interval con múltiples usuarios
  - Test reconstruct_from_prefs
  - Test activate cuando ya existe sesión

### Step 3: Application — DailySummaryBuilder ✅
- [x] Crear `ppai/push/application/daily_summary_builder.py`
- [x] Tests unitarios: `tests/unit/push/test_daily_summary_builder.py` (6 tests passing)
  - Test con tareas completadas/pendientes/pospuestas
  - Test con cero tareas
  - Test filtrado por fecha (completedAt de hoy vs ayer)

### Step 4: Application — RescueEvaluator ✅
- [x] Crear `ppai/push/application/rescue_evaluator.py`
- [x] Tests unitarios: `tests/unit/push/test_rescue_evaluator.py` (5 tests passing)
  - Test día caído → rescue suggestion
  - Test día productivo → None
  - Test sin tareas → None
  - Test microacción generada correctamente
  - Test tone guardrails en micro_action

### Step 5: Application — Extender NudgeService ✅
- [x] Modificar `ppai/push/application/nudge_service.py`:
  - Agregar dependencias: `zen_manager`, `daily_summary_builder`, `rescue_evaluator`
  - Agregar `_evaluate_daily_start()`, `_evaluate_daily_end()`, `_evaluate_zen_nudge()`
  - Agregar `_build_start_message()`, `_build_end_message()`
  - Modificar `run_tick()` para evaluar inicio/cierre/zen antes de nudges regulares
  - Cuando `zen_active=False`: no evaluar nudges regulares (solo inicio/cierre)
  - Cuando `zen_active=True`: evaluar nudges zen con override de silencio
  - Fix: `_evaluate_user(skip_silence=True)` para zen override (BR-SCHED-12)
- [x] Tests unitarios: `tests/unit/push/test_nudge_service_uow05.py` (19 tests passing)
  - Test recordatorio matutino enviado en ventana
  - Test recordatorio matutino skip por idempotencia
  - Test recordatorio matutino no enviado fuera de ventana
  - Test mensaje con Top 3
  - Test mensaje con Top 3 vacío
  - Test mensaje con motivational personalizado
  - Test fallo de envío matutino
  - Test resumen de cierre enviado en ventana
  - Test resumen de cierre con lista detallada
  - Test cierre skip por idempotencia
  - Test cierre con rescue mode activado
  - Test cierre sin rescue (día productivo)
  - Test cierre sin summary builder
  - Test zen nudge enviado
  - Test zen nudge skip por cap alcanzado
  - Test zen override de silencio
  - Test zen no activo → no nudges regulares
  - Test zen sin sesión activa
  - Test error handling
- [x] Actualizar tests UOW-03 (`test_nudge_service.py`) — 20 tests passing con nuevo routing

### Step 6: Application — NudgeScheduler dinámico ✅
- [x] Modificar `ppai/push/application/nudge_scheduler.py`:
  - Agregar `interval_provider: Callable[[], int] | None` al constructor
  - Agregar `_recalculate_interval()` llamado al final de cada tick
  - Floor de 5 minutos (`_MIN_INTERVAL_MINUTES`)
- [x] Tests unitarios: `tests/unit/push/test_nudge_scheduler_uow05.py` (5 tests passing)
  - Test intervalo dinámico cambia con zen activo
  - Test restaura 15 min sin zen
  - Test floor de 5 minutos
  - Test backward compatible (sin interval_provider)
  - Test error en provider mantiene intervalo actual

### Step 7: Application — Extender ports ✅
- [x] Modificar `ppai/push/application/ports.py`:
  - Agregar `get_all() -> list[UserNudgePreferences]` a `PreferencesRepository`
  - Agregar `has_event_today(cycle_id, event_type) -> bool` a `CycleEventRepository`
  - Agregar `send_message(chat_id, text) -> bool` a `TelegramPushPort`

### Step 8: Infrastructure — Extender DynamoDBPreferencesRepository ✅
- [x] Modificar `ppai/push/infrastructure/dynamodb_preferences_repo.py`:
  - Serializar/deserializar 6 campos nuevos (camelCase mapping)
  - Implementar `get_all()` vía Scan
- [x] Tests integración en `tests/integration/push/test_dynamodb_push_repos.py` (3 tests adding)
  - Test save/get con campos nuevos UOW-05
  - Test get_all retorna todos los usuarios
  - Test defaults para datos legacy sin campos UOW-05

### Step 9: Infrastructure — Extender CycleEventRepository ✅
- [x] Modificar `ppai/push/infrastructure/cycle_event_repo.py`:
  - Implementar `has_event_today(cycle_id, event_type)` — buscar en `nudgeEvents` list
- [x] Tests integración en `tests/integration/push/test_dynamodb_push_repos.py` (3 tests adding)
  - Test has_event_today True
  - Test has_event_today False
  - Test con múltiples eventos distintos

### Step 10: Infrastructure — ZenTelegramAdapter ✅
- [x] Crear `ppai/push/infrastructure/zen_telegram_adapter.py`:
  - `zen_handler(update, context)`: parsear args, activar/desactivar zen
  - Persistir `zen_active` en preferencias
  - Registrar eventos `ZEN_ACTIVATED` / `ZEN_DEACTIVATED`
  - Respuestas en español
- [x] Tests unitarios: `tests/unit/push/test_zen_telegram_adapter.py` (6 tests passing)
  - Test `/zen` activa modo zen
  - Test `/zen` cuando ya activo
  - Test `/zen` registra evento de activación
  - Test `/zen off` desactiva
  - Test `/zen off` cuando no está activo
  - Test respuestas en español

### Step 11: Infrastructure — Extender ConfigTelegramAdapter ✅
- [x] Modificar `ppai/push/infrastructure/config_telegram_adapter.py`:
  - Agregar subcomandos: `inicio`, `cierre`, `zen_intervalo`, `zen_max`, `motivacion`
  - Agregar sanitización de motivational_message (DP-SCHED-07)
  - Actualizar display de `/config` sin args
  - Actualizar `_HELP_TEXT`
- [x] Tests unitarios: `tests/unit/push/test_config_adapter_uow05.py` (14 tests passing)
  - Test `/config inicio 09:00` + formato inválido
  - Test `/config cierre 18:00` + formato inválido
  - Test `/config zen_intervalo 10` (rango 5-60) + fuera de rango
  - Test `/config zen_max 20` (rango 1-50) + fuera de rango
  - Test `/config motivacion texto válido`
  - Test sanitización: strip HTML, reject URLs, reject too long
  - Test display muestra campos nuevos UOW-05

### Step 12: Wiring — Actualizar main.py ✅
- [x] Modificar `ppai/main.py`:
  - Instanciar `ZenSessionManager`, `DailySummaryBuilder`, `RescueEvaluator`
  - Pasar nuevas dependencias a `NudgeService`
  - Pasar `interval_provider` a `NudgeScheduler`
  - Reconstruir zen sessions al inicio (`reconstruct_from_prefs`)
  - Registrar `/zen` command handler

### Step 13: E2E Tests
- [x] Crear `tests/e2e/test_scheduler_bot_nativo_flow.py` (8 tests)
  - Test recordatorio matutino: simular tick en ventana → mensaje enviado con Top 3
  - Test resumen de cierre: simular tick en ventana → mensaje con lista detallada
  - Test rescue mode: simular día caído → mensaje empático con microacción
  - Test zen activate/deactivate: `/zen` → nudges zen → `/zen off`
  - Test zen auto-deactivate al alcanzar cap
  - Test idempotencia: dos ticks en misma ventana → solo 1 envío
  - Test config inicio/cierre: `/config inicio 09:00` → persistido
  - Test config motivacion con sanitización

### Step 14: BDD Acceptance Tests
- [x] Crear `tests/features/e5/us09.feature`, `tests/features/e5/us10.feature`
- [x] Crear `tests/unit/e5/test_us09.py`, `tests/unit/e5/test_us10.py` (6 tests)
  - Scenario: "Como usuario, recibo mi Top 3 automáticamente cada mañana" (US-09)
  - Scenario: "Como usuario, recibo resumen de cierre con tareas del día" (US-09)
  - Scenario: "Como usuario, recibo propuesta de rescate en día caído" (US-10)
  - Scenario: "Como usuario, activo modo zen y recibo nudges frecuentes" (US-10 / ext US-06)
  - Scenario: "Como usuario, el modo zen ignora mi ventana de silencio"
  - Scenario: "Como usuario, configuro horarios de inicio y cierre"

### Step 15: Code Summary Documentation
- [x] Crear `aidlc-docs/construction/scheduler-bot-nativo/code/code-summary.md`
  - Resumen de archivos creados/modificados
  - Story traceability
  - Test coverage summary

## Resumen

| Tipo | Archivos | Tests estimados |
|------|----------|-----------------|
| Domain (entities + value objects) | 2 modificados | ~12 unit |
| Application (zen, summary, rescue, service, scheduler, ports) | 3 nuevos + 3 modificados | ~41 unit |
| Infrastructure (prefs repo, cycle repo, zen adapter, config adapter) | 2 nuevos + 2 modificados | ~21 (unit + integration) |
| Wiring (main.py) | 1 modificado | — |
| E2E + BDD | 2 nuevos | ~14 |
| Documentation | 1 nuevo | — |
| **Total** | **8 nuevos + 8 modificados** | **~88 tests** |

**Terraform**: Sin cambios (GSI y IAM ya existen).
