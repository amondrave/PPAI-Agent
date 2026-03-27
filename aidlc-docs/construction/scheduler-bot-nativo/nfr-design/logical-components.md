# Logical Components — UOW-05 Scheduler Bot Nativo

> Componentes base de UOW-01/02/03/04 se heredan. Este documento define solo los
> componentes nuevos o modificados por UOW-05.

---

## Componentes Modificados

### NudgeScheduler (modificado)

**Cambio**: Acepta intervalo dinámico en lugar de fijo.

| Aspecto | Antes (UOW-03) | Después (UOW-05) |
|---------|----------------|-------------------|
| Intervalo | Fijo 15 min | Dinámico: min(zen_intervals) o 15 min |
| Input | `nudge_service`, `user_ids_provider` | + `interval_provider: Callable[[], int]` |
| Tick logic | Solo nudges regulares | + evaluar inicio/cierre/zen |

**Responsabilidades nuevas**:
- Recalcular intervalo al final de cada tick.
- Delegar evaluación de inicio/cierre/zen al servicio.

### NudgeService (modificado)

**Cambio**: Método `run_tick()` se extiende para evaluar los 3 nuevos flujos.

**Nuevos métodos internos**:

```text
_evaluate_daily_start(user_id, prefs, now) -> Optional[DispatchOutcome]
    Evalúa si enviar recordatorio matutino.

_evaluate_daily_end(user_id, prefs, now) -> Optional[DispatchOutcome]
    Evalúa si enviar resumen de cierre + rescue.

_evaluate_zen_nudge(user_id, prefs, zen_session, now) -> Optional[DispatchOutcome]
    Evalúa si enviar nudge zen.

_build_daily_summary(user_id, today) -> DailySummary
    Consulta tareas del día y genera resumen.

_evaluate_rescue(summary) -> Optional[RescueSuggestion]
    Evalúa condición de día caído y genera propuesta.

_build_start_message(top3, motivational_message) -> str
    Construye mensaje de recordatorio matutino.

_build_end_message(summary) -> str
    Construye mensaje de resumen de cierre.
```

**Flujo actualizado de `run_tick()`**:
```text
Para cada user_id:
  1. Cargar preferences
  2. Convertir now a local_now
  3. _evaluate_daily_start(...)
  4. _evaluate_daily_end(...)
  5. Si zen_active → _evaluate_zen_nudge(...)
  6. Si NO zen_active → skip nudges regulares
  7. Agregar outcome al resultado
```

### UserNudgePreferences (modificado)

**Campos nuevos**: `daily_start_time`, `daily_end_time`, `zen_active`, `zen_interval_minutes`, `zen_max_nudges`, `motivational_message`.

**Métodos nuevos**: `is_within_start_window()`, `is_within_end_window()`, `should_zen_override_silence()`.

### DynamoDBPreferencesRepository (modificado)

**Cambio**: Serializar/deserializar los 6 campos nuevos con camelCase mapping.

### ConfigTelegramAdapter (modificado)

**Nuevos subcomandos**: `inicio`, `cierre`, `zen_intervalo`, `zen_max`, `motivacion`.

**Display actualizado**: Incluye nuevos campos en `/config` sin argumentos.

### TelegramPushAdapter (sin cambios)

Reutiliza `send_message()` existente para recordatorios y resumen. No requiere cambios.

---

## Componentes Nuevos

### ZenSessionManager

**Responsabilidad**: Gestionar las sesiones zen activas en memoria.

```text
class ZenSessionManager:
    _sessions: dict[str, ZenSession]

    activate(user_id, zen_max_nudges, zen_interval_minutes) -> ZenSession
        Crea sesión zen. Si ya existe, retorna la existente.

    deactivate(user_id) -> Optional[ZenSession]
        Elimina sesión y retorna la sesión con stats. None si no existía.

    get(user_id) -> Optional[ZenSession]
        Retorna sesión activa o None.

    record_nudge(user_id) -> bool
        Incrementa nudges_sent. Retorna False si alcanzó cap.

    reconstruct_from_prefs(prefs_list: list[UserNudgePreferences])
        Al inicio del bot, reconstruye sesiones para users con zen_active=True.

    get_min_interval() -> Optional[int]
        Retorna el menor zen_interval_minutes entre sesiones activas. None si no hay.
```

**Ubicación**: `ppai/push/application/zen_session_manager.py`

### DailySummaryBuilder

**Responsabilidad**: Construir `DailySummary` consultando tareas del día.

```text
class DailySummaryBuilder:
    __init__(task_repo: TaskStateRepository)

    build(user_id, for_date) -> DailySummary
        Consulta GSI userId-status-index para obtener:
        - completed: status=completed con completedAt de hoy
        - pending: status=pending
        - snoozed: status=snoozed
        Retorna DailySummary con las listas.
```

**Ubicación**: `ppai/push/application/daily_summary_builder.py`

### RescueEvaluator

**Responsabilidad**: Evaluar condición de día caído y generar propuesta de rescate.

```text
class RescueEvaluator:
    evaluate(summary: DailySummary, top3: list) -> Optional[RescueSuggestion]
        Si completed_tasks vacío Y (pending + snoozed) > 0:
            key_task = top3[0] si disponible, sino pending[0]
            micro_action = "Dedícale solo 5 minutos a: {key_task.title}"
            return RescueSuggestion(key_task, micro_action, tone="empathetic")
        return None
```

**Ubicación**: `ppai/push/application/rescue_evaluator.py`

### ZenTelegramAdapter

**Responsabilidad**: Manejar comandos `/zen` y `/zen off`.

```text
class ZenTelegramAdapter:
    __init__(prefs_repo, zen_manager, cycle_event_repo)

    zen_handler(update, context)
        Parsea argumentos: sin args → activar, "off" → desactivar.
        Activa/desactiva zen, persiste, registra eventos, responde al usuario.
```

**Ubicación**: `ppai/push/infrastructure/zen_telegram_adapter.py`

---

## Wiring en main.py (delta)

```text
# Nuevos componentes
zen_manager = ZenSessionManager()
daily_summary_builder = DailySummaryBuilder(task_repo=task_repo)
rescue_evaluator = RescueEvaluator()

# NudgeService recibe nuevas dependencias
nudge_service = NudgeService(
    ...,  # existentes
    zen_manager=zen_manager,
    daily_summary_builder=daily_summary_builder,
    rescue_evaluator=rescue_evaluator,
)

# NudgeScheduler con interval_provider
nudge_scheduler = NudgeScheduler(
    nudge_service=nudge_service,
    user_ids_provider=user_registry.get_all,
    interval_provider=lambda: zen_manager.get_min_interval() or 900,
)

# Reconstruir zen sessions al inicio
all_prefs = prefs_repo.get_all()
zen_manager.reconstruct_from_prefs(all_prefs)

# Registrar /zen command
zen_adapter = ZenTelegramAdapter(prefs_repo, zen_manager, cycle_event_repo)
app.add_handler(CommandHandler("zen", zen_adapter.zen_handler))
```

---

## Infraestructura Delta

| Componente | Cambio | Terraform |
|------------|--------|-----------|
| `ppai-tasks` | Agregar GSI `userId-status-index` | Sí — módulo `dynamodb` |
| `ppai-preferences` | 6 atributos nuevos (no schema change en DynamoDB) | No |
| `ppai-cycles` | Nuevos tipos de evento (no schema change) | No |
| IAM Task Role | Agregar permiso Query en GSI | Sí — módulo `iam` |
| ECS / VPC / API Gateway | Sin cambios | No |
