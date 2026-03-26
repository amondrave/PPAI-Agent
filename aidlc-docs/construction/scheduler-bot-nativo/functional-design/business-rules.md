# Reglas de Negocio — UOW-05 Scheduler Bot Nativo

## Reglas de Recordatorio Diario

### BR-SCHED-01: Ventana de tolerancia de inicio/cierre
- Los recordatorios de inicio y cierre se evalúan con tolerancia de **±7 minutos** respecto a la hora configurada.
- Si el tick del scheduler cae fuera de esta ventana, el recordatorio se omite hasta el siguiente día.
- **Máximo 1 envío por tipo por día** (controlado por idempotencia).

### BR-SCHED-02: Idempotencia de recordatorios
- Antes de enviar recordatorio de inicio, verificar que no exista evento `DAILY_START_SENT` en el `ExecutionCycle` de hoy.
- Antes de enviar recordatorio de cierre, verificar que no exista evento `DAILY_END_SENT` en el `ExecutionCycle` de hoy.
- Si el evento ya existe → skip silencioso (no error, no log adicional).

### BR-SCHED-03: Defaults de horarios
- `daily_start_time` default: `"08:00"` en timezone del usuario.
- `daily_end_time` default: `"18:00"` en timezone del usuario.
- Los defaults se activan automáticamente al registrarse. No requieren configuración explícita.

### BR-SCHED-04: Contenido del recordatorio matutino
- Incluye Top 3 actual del usuario (vía `DecisionService.get_top3`).
- Incluye mensaje motivacional configurable (`motivational_message`).
- Si Top 3 vacío → mensaje indicando que no hay tareas pendientes.

### BR-SCHED-05: Contenido del resumen de cierre
- Lista detallada de tareas completadas hoy (título).
- Lista detallada de tareas pendientes (título).
- Lista detallada de tareas pospuestas hoy (título).
- Tono neutro, nunca acusatorio.

## Reglas de Rescue Mode

### BR-SCHED-06: Condición de día caído
- "Día caído" = 0 tareas completadas hoy **Y** al menos 1 tarea pendiente o pospuesta existía hoy.
- Se evalúa como parte del cierre de día.

### BR-SCHED-07: Propuesta de rescate
- Seleccionar 1 tarea clave: la de mayor prioridad entre las pendientes.
- Generar 1 microacción concreta: "Dedícale solo 5 minutos a: {título}".
- Tono siempre empático — aplicar guardrails de BR-PUSH-10 (prohibido: "debías", "ya vas tarde", etc.).

### BR-SCHED-08: Unicidad de rescue por día
- Máximo 1 activación de rescue por día por usuario.
- Controlado por evento `RESCUE_TRIGGERED` en el ExecutionCycle.
- Si ya existe → no se vuelve a evaluar.

## Reglas de Modo Zen

### BR-SCHED-09: Activación de zen
- Solo se activa por comando explícito del usuario (`/zen` o `/zen on`).
- Al activar: `zen_active = True`, se crea `ZenSession` en memoria.
- Se registra evento `ZEN_ACTIVATED`.

### BR-SCHED-10: Desactivación de zen
- Por comando explícito (`/zen off`) o por alcanzar `zen_max_nudges`.
- Al desactivar: `zen_active = False`, se elimina `ZenSession`.
- Se registra evento `ZEN_DEACTIVATED` con conteo de nudges enviados.
- Si zen no está activo y usuario envía `/zen off` → respuesta informativa sin error.

### BR-SCHED-11: Intervalo y cap de zen
- `zen_interval_minutes` configurable: rango 5-60 min (default 15).
- `zen_max_nudges` configurable: rango 1-50 (default 10).
- Cap es **por sesión zen**, no por día. Al reiniciar bot, el conteo se resetea.

### BR-SCHED-12: Zen override de silencio
- Si `zen_active = True`, los nudges zen **ignoran** la ventana de silencio.
- Razón: el usuario activó zen explícitamente, se confía en su intención (Q8: B).
- Los recordatorios de inicio/cierre **sí** respetan silencio (no son zen).

### BR-SCHED-13: Zen vs nudges regulares
- Si `zen_active = True` → solo nudges zen. Nudges regulares no se evalúan.
- Si `zen_active = False` → **no se envían nudges intermedios**. Solo inicio/cierre programados.
- Recordatorios de inicio/cierre se evalúan **siempre**, independientemente del estado zen.

### BR-SCHED-14: Reconstrucción de zen al reinicio
- Al iniciar el bot, si `zen_active = True` en preferencias → crear `ZenSession` con `nudges_sent = 0`.
- El usuario mantiene su modo zen activo tras reinicio del contenedor.

## Reglas de Configuración

### BR-SCHED-15: Validación de `/config inicio` y `/config cierre`
- Formato requerido: `HH:MM` (24h).
- Rango válido: `00:00` a `23:59`.
- `inicio` debe ser diferente de `cierre` (no pueden ser la misma hora).
- Cambios impactan solo el siguiente tick, no retroactivos.

### BR-SCHED-16: Validación de configuración zen
- `zen_intervalo`: entero entre 5 y 60.
- `zen_max`: entero entre 1 y 50.
- `motivacion`: string no vacío, máximo 100 caracteres.
- Cambios en intervalo/cap durante una sesión zen activa: se aplican al siguiente nudge, no reinician la sesión.

### BR-SCHED-17: Display de configuración
- `/config` sin argumentos muestra todos los parámetros, incluyendo los nuevos (inicio, cierre, zen, motivación).

## Reglas de Tono

### BR-SCHED-18: Tono del recordatorio matutino
- Positivo, breve, energético.
- Incluye mensaje motivacional del usuario.
- Si no hay tareas → tono neutro, invitación a capturar.

### BR-SCHED-19: Tono del resumen de cierre
- Neutro, factual.
- Nunca acusatorio.
- Si rescue → empático, sin presión.

### BR-SCHED-20: Tono del rescue mode
- Empático, sin culpa.
- Propositivo (ofrece microacción concreta).
- Cierra con "Sin presión — mañana es otro día" o similar.
- Aplica guardrails de BR-PUSH-10: prohibido "debías", "ya vas tarde", "otra vez", "no hiciste", "fallaste".
