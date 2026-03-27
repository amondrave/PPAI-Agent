# Plan NFR Requirements — UOW-05 Scheduler Bot Nativo

## Contexto

UOW-05 hereda la base NFR completa de UOW-01/02/03/04. Este documento captura solo los **deltas** que introduce UOW-05: scheduler de recordatorios diarios, zen mode con intervalo/cap propio, y rescue mode.

## Plan

- [x] Step 1: Analizar functional design de UOW-05
- [x] Step 2: Identificar deltas NFR vs base heredada
- [x] Step 3: Recoger respuestas del usuario
- [x] Step 4: Generar artefactos NFR
- [x] Step 5: Presentar para aprobación

## Preguntas Delta

### Q1: Zen session — precisión del intervalo
El zen tiene intervalo configurable (5-60 min) pero el scheduler corre cada 15 min. Para intervalos menores a 15 min (ej. 10 min):

A) Aceptar imprecisión — el tick del scheduler es cada 15 min, zen evalúa en cada tick y envía si el intervalo ya pasó. Un intervalo de 10 min se comportará como ~15 min en la práctica.
B) Tick dedicado para zen — cuando zen está activo, bajar el intervalo del scheduler al `zen_interval_minutes` del usuario. Restaurar al desactivar.

[Answer]: B

### Q2: Daily summary — consulta de tareas del día
Para generar el resumen de cierre, se necesita consultar tareas completadas/pendientes/pospuestas hoy. ¿Cómo?

A) Reusar `TaskStateRepository` existente + filtrar por fecha en código — simple, sin índice nuevo.
B) Crear GSI `userId-status-index` en `ppai-tasks` para consulta eficiente por estado — más escalable pero más infra.

[Answer]: B

### Q3: ZenSession — persistencia del conteo
El conteo de nudges zen (`nudges_sent`) vive en memoria y se resetea al reiniciar. ¿Es aceptable?

A) Sí, aceptable para MVP — el cap es por sesión, un reinicio resetea naturalmente.
B) Persistir `nudges_sent` en DynamoDB para sobrevivir reinicios — más robusto pero más escrituras.

[Answer]: A

### Q4: Rescue mode — observabilidad
Cuando se activa rescue mode, ¿qué nivel de logging?

A) Solo evento `RESCUE_TRIGGERED` en ExecutionCycle — mínimo, consistente con el approach actual.
B) Evento en ExecutionCycle + log estructurado con user_id, task_id seleccionada y razón — para análisis posterior.

[Answer]: A

### Q5: Motivational message — seguridad del input
El usuario puede configurar `motivational_message` vía `/config motivacion TEXTO`. ¿Cómo sanitizar?

A) Validación básica: max 100 chars, strip de HTML/markdown peligroso, solo texto plano.
B) Sin sanitización especial — Telegram escapa HTML por defecto en `parse_mode=None`. Solo limitar largo.

[Answer]: A
