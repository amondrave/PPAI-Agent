# Entidades de Dominio — UOW-05 Scheduler Bot Nativo

## Entidades modificadas

### UserNudgePreferences (extendida)

Campos nuevos sobre la entidad existente (`ppai/push/domain/entities.py`):

| Campo | Tipo | Default | Descripción |
|-------|------|---------|-------------|
| `daily_start_time` | `str` | `"08:00"` | Hora local del recordatorio matutino (HH:MM) |
| `daily_end_time` | `str` | `"18:00"` | Hora local del resumen de cierre (HH:MM) |
| `zen_active` | `bool` | `False` | Modo zen activo/inactivo |
| `zen_interval_minutes` | `int` | `15` | Intervalo entre nudges en modo zen (min) |
| `zen_max_nudges` | `int` | `10` | Cap de nudges mientras zen esté activo (por sesión zen) |
| `motivational_message` | `str` | `"A darle con todo hoy"` | Mensaje motivacional para recordatorio matutino |

**Campos existentes que no cambian**: `user_id`, `timezone`, `max_nudges_per_day`, `silence_start`, `silence_end`, `updated_at`.

**Nota**: `daily_start_time` y `daily_end_time` tienen defaults (`08:00` / `18:00`) — se activan automáticamente al registrarse (Q7: B).

### Métodos nuevos en UserNudgePreferences

```
is_within_start_window(local_now: datetime, tolerance_minutes: int = 7) -> bool
    Retorna True si local_now está dentro de [daily_start_time - tolerance, daily_start_time + tolerance].

is_within_end_window(local_now: datetime, tolerance_minutes: int = 7) -> bool
    Retorna True si local_now está dentro de [daily_end_time - tolerance, daily_end_time + tolerance].

should_zen_override_silence() -> bool
    Retorna True si zen_active es True (Q8: B — zen override de silencio).
```

## Entidades nuevas

### DailySummary (value object)

Resumen generado al cierre del día. No se persiste como entidad — se genera on-the-fly.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user_id` | `str` | ID del usuario |
| `date` | `date` | Fecha del resumen |
| `completed_tasks` | `list[TaskSummaryItem]` | Tareas completadas hoy |
| `pending_tasks` | `list[TaskSummaryItem]` | Tareas que quedaron pendientes |
| `snoozed_tasks` | `list[TaskSummaryItem]` | Tareas pospuestas hoy |
| `rescue_triggered` | `bool` | Si se activó rescue mode |
| `rescue_suggestion` | `Optional[RescueSuggestion]` | Propuesta de rescate si aplica |

### TaskSummaryItem (value object)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `task_id` | `str` | ID de la tarea |
| `title` | `str` | Título de la tarea |
| `status` | `str` | Estado actual (completed/pending/snoozed) |

### RescueSuggestion (value object)

Propuesta de rescate cuando se detecta "día caído" (US-10).

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `key_task` | `TaskSummaryItem` | 1 tarea clave para retomar |
| `micro_action` | `str` | 1 microacción concreta (ej. "revisa los primeros 5 minutos de esta tarea") |
| `tone` | `str` | Siempre `"empathetic"` — sin tono acusatorio |

### ZenSession (value object, en memoria)

Tracking de la sesión zen activa del usuario. Se usa para controlar el cap de nudges zen.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `user_id` | `str` | ID del usuario |
| `started_at` | `datetime` | Timestamp de activación |
| `nudges_sent` | `int` | Nudges enviados en esta sesión zen |
| `max_nudges` | `int` | Cap configurado (de `zen_max_nudges`) |
| `interval_minutes` | `int` | Intervalo configurado (de `zen_interval_minutes`) |

**Nota**: `ZenSession` vive en memoria del proceso. Al reiniciar, se reconstruye leyendo `zen_active` de preferencias. El conteo de `nudges_sent` se resetea al reiniciar (aceptable — el cap es por sesión, no por día).

## Eventos nuevos (en ExecutionCycle)

Eventos registrados via `CycleEventRepository.record_nudge_event()`:

| Tipo de evento | Metadata | Descripción |
|----------------|----------|-------------|
| `DAILY_START_SENT` | `{"sent_at": "ISO8601"}` | Recordatorio matutino enviado — idempotencia (Q6: C) |
| `DAILY_END_SENT` | `{"sent_at": "ISO8601"}` | Resumen de cierre enviado — idempotencia (Q6: C) |
| `ZEN_ACTIVATED` | `{"activated_at": "ISO8601"}` | Modo zen activado por usuario |
| `ZEN_DEACTIVATED` | `{"deactivated_at": "ISO8601", "nudges_sent": N}` | Modo zen desactivado |
| `RESCUE_TRIGGERED` | `{"task_id": "...", "micro_action": "..."}` | Rescue mode activado al cierre |

## Persistencia en DynamoDB

### Tabla `ppai-preferences` (campos nuevos)

| Atributo DynamoDB | Campo | Tipo |
|-------------------|-------|------|
| `dailyStartTime` | `daily_start_time` | `S` |
| `dailyEndTime` | `daily_end_time` | `S` |
| `zenActive` | `zen_active` | `BOOL` |
| `zenIntervalMinutes` | `zen_interval_minutes` | `N` |
| `zenMaxNudges` | `zen_max_nudges` | `N` |
| `motivationalMessage` | `motivational_message` | `S` |

### Tabla `ppai-cycles` (sin cambios de schema)

Los nuevos eventos (`DAILY_START_SENT`, `DAILY_END_SENT`, etc.) se almacenan en la lista `nudgeEvents` existente. No requieren cambios de schema.
