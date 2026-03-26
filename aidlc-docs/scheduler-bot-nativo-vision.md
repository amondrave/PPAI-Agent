# Visión: Scheduler Nativo del Bot (no Remote Trigger)

## Idea central

El scheduler de recordatorios debe vivir **dentro del bot de Telegram** (en AWS ECS), no como agente remoto de Claude. El usuario recibe mensajes directamente en Telegram sin depender de servicios externos.

## Flujo propuesto

### Recordatorio de inicio de día
- Todos los días a la **hora que el usuario configure** (ej. 8:00 AM), el bot le envía su Top 3 automáticamente por Telegram.
- No requiere que el usuario escriba `/top3` — le llega solo.
- Es un "buenos días, estas son tus prioridades de hoy".

### Recordatorio de cierre de día
- Al final del día (hora configurable, ej. 6:00 PM), el bot envía un resumen:
  - Qué completaste hoy
  - Qué quedó pendiente
  - Qué se pospuso

### Modo Zen (nudges cada 15 min)
- Los nudges cada 15 minutos **NO se activan automáticamente**.
- Solo se activan cuando el usuario **explícitamente lo pide** (ej. `/zen` o `/focus`).
- Esto indica: "estoy en modo trabajo, recuérdame mis tareas activamente".
- Cuando el usuario termina, desactiva el modo (ej. `/zen off`).

### Nudges pasivos (fuera de modo zen)
- Fuera de modo zen, el bot **no molesta** entre el recordatorio de inicio y cierre.
- Solo envía los dos mensajes programados (mañana y tarde).

## Configuración vía `/config`

Extender el comando `/config` existente:

```
/config inicio 08:00      → hora del recordatorio matutino
/config cierre 18:00      → hora del resumen de cierre
/config silencio 22:00-08:00  → ya existe
/config nudges 5          → máx nudges en modo zen
/config timezone America/Bogota  → ya existe
```

## Implementación técnica (alto nivel)

### Opción: Extender NudgeScheduler existente

El `NudgeScheduler` ya corre cada 15 min. Se puede extender para:

1. **Cada tick**, evaluar si es hora de enviar recordatorio de inicio/cierre:
   - Comparar `local_now.strftime("%H:%M")` con `prefs.inicio` y `prefs.cierre`
   - Tolerancia de ±15 min (por el intervalo del tick)

2. **Modo zen**: nuevo campo `zen_active: bool` en `UserNudgePreferences`
   - Si `zen_active = True` → nudges cada 15 min (comportamiento actual)
   - Si `zen_active = False` → solo inicio/cierre programados

### Nuevos campos en UserNudgePreferences

```python
daily_start_time: Optional[str] = None   # "HH:MM" — recordatorio matutino
daily_end_time: Optional[str] = None     # "HH:MM" — resumen de cierre
zen_active: bool = False                  # modo zen activo/inactivo
```

### Nuevos comandos

```
/zen       → activa modo zen (nudges cada 15 min)
/zen off   → desactiva modo zen
```

## Diferencia con el enfoque anterior

| Aspecto | Antes (Remote Trigger) | Ahora (Bot nativo) |
|---------|----------------------|---------------------|
| Dónde corre | Nube de Anthropic | AWS ECS (mismo contenedor del bot) |
| Output | Resultado en Claude Code | Mensaje de Telegram directo |
| Dependencias | GitHub App + Linear MCP | Solo DynamoDB (ya existe) |
| Costo adicional | Créditos Claude por ejecución | $0 (ya paga ECS) |
| Complejidad | Alta (setup externo) | Baja (extender NudgeScheduler) |

## Scope estimado

- Extender `UserNudgePreferences` con 3 campos
- Extender `/config` con `inicio` y `cierre`
- Crear `/zen` y `/zen off`
- Modificar `NudgeScheduler._tick()` para evaluar inicio/cierre
- Crear mensaje de cierre (resumen del día)
- ~15-20 tests nuevos

## Prioridad

Esto se puede implementar como parte de UOW-04 o como un UOW-05 separado, dependiendo del scope final.

---

*Capturado: 2026-03-26 — Para continuar en siguiente sesión.*
