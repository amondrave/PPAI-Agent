# NFR Design Patterns — UOW-05 Scheduler Bot Nativo

> Patrones base de UOW-01/02/03/04 se heredan íntegramente.
> Este documento define los patrones delta nuevos de UOW-05.

---

## DP-SCHED-01: Dynamic Interval Scheduler Pattern

### Pattern
El `NudgeScheduler` ajusta su intervalo de tick **dinámicamente** según el estado de zen de los usuarios registrados.

### Design
```text
Al final de cada ciclo de tick:
1. Consultar zen_interval_minutes de todos los usuarios con zen_active = True
2. Si hay al menos uno activo → intervalo = min(zen_interval_minutes) (floor: 5 min)
3. Si ninguno activo → intervalo = 15 min (base)
4. Aplicar nuevo intervalo al siguiente sleep del scheduler thread
```

### Implementation
- `NudgeScheduler` recibe un `interval_provider: Callable[[], int]` que calcula el intervalo dinámico.
- El provider consulta `PreferencesRepository` para obtener zen states.
- El `threading.Event.wait(timeout)` ya soporta timeout dinámico — no requiere cambio de mecanismo.

### Benefits
- Nudges zen con precisión real (no redondeados a 15 min).
- Sin overhead cuando zen está inactivo (vuelve a 15 min).
- Sin dependencias externas ni timers adicionales.

### Constraint
- Floor de 5 minutos: `max(calculated_interval, 5 * 60)`.
- Evita ticks excesivamente frecuentes por configuración errónea.

---

## DP-SCHED-02: Daily Event Idempotency Pattern

### Pattern
Los recordatorios de inicio/cierre usan **eventos en ExecutionCycle** como guard de idempotencia. Antes de enviar, se verifica si el evento ya fue registrado hoy.

### Design
```text
Para DAILY_START_SENT / DAILY_END_SENT:
1. get_active(user_id, today) → cycle
2. Si cycle tiene evento del tipo buscado → skip
3. Si no existe → enviar mensaje → record_nudge_event(cycle_id, event_type, metadata)
```

### Benefits
- Reutiliza infraestructura existente (`CycleEventRepository`).
- Sobrevive reinicios del contenedor (persistido en DynamoDB).
- Consistente con DP-PUSH-02 (Persisted Dispatch Marker).

### Diferencia vs DP-PUSH-02
- DP-PUSH-02 marca `NUDGE_SCHEDULED` antes de enviar (optimista).
- DP-SCHED-02 verifica existencia del evento como guard (pesimista) — más apropiado porque los recordatorios diarios son exactly-once por día, no best-effort.

---

## DP-SCHED-03: Tolerance Window Matching Pattern

### Pattern
Los recordatorios programados (inicio/cierre) se evalúan con una **ventana de tolerancia de ±7 minutos** respecto a la hora configurada.

### Design
```text
target_time = parse(daily_start_time)  # ej. 08:00
local_now = now.astimezone(user_timezone)
delta = abs(local_now.hour*60 + local_now.minute - target_time.hour*60 - target_time.minute)
if delta <= 7:
    # dentro de ventana → evaluar envío
```

### Edge cases
- Cross-midnight: si `target_time = 23:55` y `local_now = 00:02`, delta = 7 min → dentro de ventana. Requiere wrap-around de 1440 minutos.
- Tolerancia asimétrica NO necesaria: ±7 min con ticks de 15 min garantiza que al menos 1 tick cae en ventana.

### Benefits
- Simple y determinístico.
- Garantiza máximo 1 envío por ventana por día (combinado con DP-SCHED-02).

---

## DP-SCHED-04: Zen Session Lifecycle Pattern

### Pattern
La sesión zen tiene un **ciclo de vida explícito** con estados: creación, ejecución, finalización (manual o auto).

### Design
```text
Activación (/zen):
  1. zen_active = True en DynamoDB
  2. ZenSession creada en memoria (nudges_sent=0)
  3. Evento ZEN_ACTIVATED en ExecutionCycle

Tick zen (cada zen_interval_minutes):
  4. Si nudges_sent < zen_max_nudges → enviar nudge
  5. Incrementar nudges_sent
  6. Si nudges_sent >= zen_max_nudges → auto-desactivar

Desactivación (/zen off o auto):
  7. zen_active = False en DynamoDB
  8. Evento ZEN_DEACTIVATED con nudges_sent
  9. ZenSession eliminada de memoria

Reconstrucción (reinicio del bot):
  10. Para cada user con zen_active=True → crear ZenSession(nudges_sent=0)
```

### State ownership
- `zen_active` → DynamoDB (sobrevive reinicios)
- `ZenSession` (nudges_sent, started_at) → memoria (se resetea al reiniciar — TD-SCHED-01)

### Benefits
- Desactivación automática al alcanzar cap → no se olvida activo.
- Flag persistido permite reconstrucción tras reinicio.
- Separación clara entre estado durable (flag) y estado efímero (conteo).

---

## DP-SCHED-05: Zen Silence Override Pattern

### Pattern
Cuando zen está activo, los nudges zen **ignoran** la ventana de silencio del usuario.

### Design
```text
if zen_active:
    # skip silence window check
    # proceed with zen nudge evaluation
else:
    # apply silence window check (comportamiento existente)
```

### Rationale
- El usuario activó zen explícitamente → se confía en su intención (Q8: B).
- Los recordatorios de inicio/cierre **sí** respetan silencio (son automáticos, no explícitos).

### Implementation note
- En `NudgeService.run_tick()` o equivalente, el check de silencio se condiciona al flag `zen_active`.

---

## DP-SCHED-06: Rescue Detection Pattern

### Pattern
Al generar el resumen de cierre, el sistema evalúa si el día fue un "día caído" y propone rescue.

### Design
```text
1. Generar DailySummary con tareas del día
2. Si completed_tasks == 0 AND (pending_tasks + snoozed_tasks) > 0:
   → Día caído detectado
3. Verificar que no exista RESCUE_TRIGGERED hoy (idempotencia)
4. Si no existe:
   a. Seleccionar key_task = primera tarea del Top 3 (o primera pendiente si no hay Top 3)
   b. Generar micro_action = "Dedícale solo 5 minutos a: {title}"
   c. Crear RescueSuggestion
   d. Registrar RESCUE_TRIGGERED
   e. Agregar al mensaje de cierre
```

### Tone guardrails
- Aplica BR-PUSH-10: prohibido "debías", "ya vas tarde", "otra vez", "no hiciste", "fallaste".
- Mensaje empático: "Hoy fue un día difícil, y eso está bien."
- Cierra con: "Sin presión — mañana es otro día."

### Benefits
- Detección automática sin configuración del usuario.
- Propuesta concreta y de baja fricción (microacción de 5 min).
- Máx 1 rescue por día (idempotente).

---

## DP-SCHED-07: Input Sanitization Pattern

### Pattern
El campo `motivational_message` configurable por el usuario se sanitiza antes de persistir.

### Design
```text
def sanitize_motivational(text: str) -> str:
    text = text.strip()
    text = re.sub(r'<[^>]+>', '', text)        # strip HTML tags
    if re.search(r'https?://', text):
        raise ValueError("URLs no permitidas")
    if len(text) == 0:
        raise ValueError("Mensaje vacío")
    if len(text) > 100:
        raise ValueError("Máximo 100 caracteres")
    return text
```

### Applied to
- `/config motivacion TEXTO` — validar antes de `prefs_repo.save()`.

### Benefits
- Previene inyección de HTML/scripts en mensajes de Telegram.
- Previene uso del bot como relay de URLs.
- Límite de largo razonable.

---

## Security Compliance Summary (delta UOW-05)

| Rule | Status | Notas |
|---|---|---|
| SECURITY-01 Encryption | Compliant (heredado) | GSI hereda cifrado de tabla |
| SECURITY-03 App Logging | Compliant | Eventos sin PII, correlación por cycle_id |
| SECURITY-05 Input Validation | Compliant | DP-SCHED-07 sanitización de motivational_message |
| SECURITY-06 Least Privilege | Compliant | IAM delta acotado a Query en GSI |
| SECURITY-08 App Access Control | N/A | No nuevos endpoints ni auth flows |
| SECURITY-11 Secure Design | Compliant | Floor de 5 min en scheduler, idempotencia en recordatorios |
| SECURITY-15 Exception Handling | Compliant | Fail-soft en todos los flujos (heredado DP-PUSH-06) |
