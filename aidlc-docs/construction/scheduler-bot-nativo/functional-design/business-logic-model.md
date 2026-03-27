# Modelo de Lógica de Negocio — UOW-05 Scheduler Bot Nativo

## Flujo General

El NudgeScheduler existente (tick cada 15 min) se extiende con tres nuevas responsabilidades evaluadas en cada tick:

```
Tick del Scheduler (cada 15 min)
  |
  +-- Para cada usuario registrado:
  |     |
  |     +-- 1. Evaluar recordatorio de INICIO de día
  |     |     (si está en ventana ±7 min de daily_start_time)
  |     |
  |     +-- 2. Evaluar resumen de CIERRE de día
  |     |     (si está en ventana ±7 min de daily_end_time)
  |     |
  |     +-- 3. Evaluar nudge zen
  |     |     (si zen_active y no alcanzó zen_max_nudges)
  |     |
  |     +-- 4. Nudge regular (lógica existente — SOLO si NO zen_active)
```

## Flujo 1: Recordatorio de Inicio de Día

### Precondiciones
- `daily_start_time` configurado (default: `"08:00"`)
- Hora local del usuario dentro de ventana ±7 min de `daily_start_time`
- No existe evento `DAILY_START_SENT` en el ExecutionCycle de hoy

### Lógica
1. Convertir `now` UTC a hora local del usuario (usando `timezone`)
2. Verificar ventana: `|local_now - daily_start_time| <= 7 min`
3. Verificar idempotencia: consultar si existe `DAILY_START_SENT` en ciclo de hoy
4. Si ya enviado hoy → skip
5. Resolver Top 3 vía `DecisionService.get_top3(user_id, now)`
6. Construir mensaje: Top 3 + mensaje motivacional (`motivational_message`)
7. Enviar vía `TelegramPushPort`
8. Registrar evento `DAILY_START_SENT` en ExecutionCycle

### Output del mensaje
```
Buenos días! {motivational_message}

Tu Top 3 para hoy:
1. {task_1_title} — {reason_1}
2. {task_2_title} — {reason_2}
3. {task_3_title} — {reason_3}
```

Si Top 3 vacío:
```
Buenos días! {motivational_message}

No tienes tareas pendientes por ahora. Puedes capturar nuevas con un mensaje de texto.
```

## Flujo 2: Resumen de Cierre de Día

### Precondiciones
- `daily_end_time` configurado (default: `"18:00"`)
- Hora local del usuario dentro de ventana ±7 min de `daily_end_time`
- No existe evento `DAILY_END_SENT` en el ExecutionCycle de hoy

### Lógica
1. Convertir `now` UTC a hora local del usuario
2. Verificar ventana: `|local_now - daily_end_time| <= 7 min`
3. Verificar idempotencia: consultar si existe `DAILY_END_SENT` en ciclo de hoy
4. Si ya enviado hoy → skip
5. Generar `DailySummary`:
   - Consultar tareas del usuario con estado `completed` cuyo `completedAt` sea hoy
   - Consultar tareas con estado `pending` (activas, no completadas)
   - Consultar tareas con estado `snoozed` cuyo último snooze sea hoy
6. Evaluar rescue mode (ver Flujo 2b)
7. Construir mensaje detallado con listas
8. Enviar vía `TelegramPushPort`
9. Registrar evento `DAILY_END_SENT` en ExecutionCycle

### Output del mensaje
```
Resumen del día:

Completadas ({count}):
  - {title_1}
  - {title_2}

Pendientes ({count}):
  - {title_3}
  - {title_4}

Pospuestas ({count}):
  - {title_5}

Descansa bien!
```

## Flujo 2b: Rescue Mode (US-10)

### Condición de activación
"Día caído" se detecta cuando:
- 0 tareas completadas hoy **Y** al menos 1 tarea estaba pendiente al inicio del día

### Lógica
1. Si `completed_tasks` es vacío Y `pending_tasks + snoozed_tasks > 0`:
   - Seleccionar `key_task`: la tarea de mayor prioridad entre las pendientes (primera del Top 3 si disponible)
   - Generar `micro_action`: "Dedícale solo 5 minutos a: {key_task.title}"
   - Crear `RescueSuggestion` con tono empático
2. Agregar al mensaje de cierre
3. Registrar evento `RESCUE_TRIGGERED`
4. Evitar múltiples activaciones: máx 1 rescue por día (controlado por el evento en el ciclo)

### Output adicional en mensaje de cierre (si rescue)
```
Hoy fue un día difícil, y eso está bien.

Si quieres retomar con algo pequeño:
  - {key_task.title}
  - Microacción: {micro_action}

Sin presión — mañana es otro día.
```

### Tono guardrails (heredado de BR-PUSH-10)
Prohibido en rescue: "debías", "ya vas tarde", "otra vez", "no hiciste", "fallaste".

## Flujo 3: Modo Zen

### Activación (`/zen` o `/zen on`)
1. Cargar preferencias del usuario
2. Setear `zen_active = True` en preferencias
3. Persistir en DynamoDB
4. Crear `ZenSession` en memoria con `nudges_sent = 0`
5. Registrar evento `ZEN_ACTIVATED` en ExecutionCycle
6. Responder al usuario: "Modo zen activado. Recibirás nudges cada {zen_interval_minutes} min (máx {zen_max_nudges})."

### Desactivación (`/zen off`)
1. Cargar preferencias del usuario
2. Si `zen_active` es False → responder "El modo zen no está activo."
3. Setear `zen_active = False` en preferencias
4. Persistir en DynamoDB
5. Registrar evento `ZEN_DEACTIVATED` con `nudges_sent` de la sesión
6. Eliminar `ZenSession` de memoria
7. Responder: "Modo zen desactivado. Enviaste {nudges_sent} nudges en esta sesión."

### Evaluación en tick (si zen_active)
1. Verificar `zen_active == True` en preferencias
2. **Zen override de silencio**: NO verificar ventana de silencio (Q8: B)
3. Verificar `ZenSession.nudges_sent < zen_max_nudges`
4. Verificar intervalo: `now - last_zen_nudge >= zen_interval_minutes`
5. Si cumple todas → ejecutar nudge normal (resolve Top 3, build message, send)
6. Incrementar `ZenSession.nudges_sent`
7. Si `nudges_sent >= zen_max_nudges`:
   - Auto-desactivar zen
   - Setear `zen_active = False`
   - Notificar: "Modo zen completado. Alcanzaste el máximo de {zen_max_nudges} nudges."

### Interacción zen + nudges regulares
- Si `zen_active = True` → **solo** nudges zen. No se evalúan nudges regulares.
- Si `zen_active = False` → nudges regulares NO se envían (ya no hay nudges entre inicio/cierre fuera de zen).
- Los recordatorios de inicio/cierre **siempre** se evalúan independientemente del estado zen.

## Flujo 4: Extensión de `/config`

### Nuevos subcomandos

| Comando | Validación | Efecto |
|---------|-----------|--------|
| `/config inicio HH:MM` | Formato HH:MM, 00:00-23:59 | Actualiza `daily_start_time` |
| `/config cierre HH:MM` | Formato HH:MM, 00:00-23:59 | Actualiza `daily_end_time` |
| `/config zen_intervalo N` | Entero 5-60 | Actualiza `zen_interval_minutes` |
| `/config zen_max N` | Entero 1-50 | Actualiza `zen_max_nudges` |
| `/config motivacion TEXTO` | String no vacío, máx 100 chars | Actualiza `motivational_message` |

### `/config` sin argumentos (actualizar display)
Agregar al display existente:
```
Recordatorio inicio: 08:00
Recordatorio cierre: 18:00
Modo zen: inactivo
  Intervalo: 15 min
  Máx nudges: 10
Mensaje motivacional: A darle con todo hoy
```

## Flujo 5: Reconstrucción de ZenSession al reinicio

1. Al iniciar el bot, para cada usuario con `zen_active = True`:
   - Crear `ZenSession` con `nudges_sent = 0` y `started_at = now`
   - El conteo se resetea (aceptable — el cap es por sesión zen, no acumulativo)
2. Esto permite que zen sobreviva reinicios del contenedor ECS
