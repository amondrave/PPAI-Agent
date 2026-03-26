# NFR Requirements — UOW-05 Scheduler Bot Nativo

> La base no funcional se hereda de UOW-01/02/03/04. Este documento registra
> solo los delta que introduce UOW-05.

---

## NFR-SCHED-01: Scheduler Dinámico (Q1 = B)

### Tick dedicado para zen
- Cuando `zen_active = True` para al menos un usuario, el scheduler **baja su intervalo** al `zen_interval_minutes` más bajo entre los usuarios activos en zen.
- Cuando ningún usuario tiene zen activo, el scheduler **restaura** el intervalo base de 15 minutos.
- Implementación: el `NudgeScheduler` acepta un intervalo dinámico que se recalcula en cada ciclo.

### Impacto
- Mayor precisión para nudges zen (ej. cada 10 min exactos vs ~15 min).
- Mayor frecuencia de ticks cuando zen está activo — aceptable dado el bajo volumen (1-5 usuarios).
- Sin impacto cuando zen está inactivo (vuelve a 15 min).

### Constraint
- El intervalo mínimo permitido para zen es 5 minutos (BR-SCHED-16).
- El scheduler nunca debe correr más frecuente que cada 5 minutos.

---

## NFR-SCHED-02: Consulta de Tareas por Estado (Q2 = B)

### GSI en ppai-tasks
- Crear GSI `userId-status-index` en tabla `ppai-tasks`:
  - **Partition key**: `userId` (String)
  - **Sort key**: `status` (String)
- Permite consulta eficiente de tareas por usuario y estado (completed/pending/snoozed).

### Justificación
- El resumen de cierre necesita consultar tareas por estado para un usuario.
- Sin GSI, requeriría scan + filter — ineficiente incluso para bajo volumen.
- El GSI prepara para observabilidad futura (US-12).

### Proyección
- `KEYS_ONLY` o `INCLUDE` con atributos: `title`, `completedAt`, `snoozedUntil`.
- Evitar `ALL` para no duplicar datos innecesariamente.

---

## NFR-SCHED-03: ZenSession en Memoria (Q3 = A)

### Decisión
- `ZenSession` (conteo de nudges, timestamps) vive **solo en memoria** del proceso.
- Al reiniciar el contenedor, el conteo se resetea a 0.
- El flag `zen_active` sí se persiste en DynamoDB (en `UserNudgePreferences`).

### Tradeoff aceptado
- Un reinicio durante zen resetea el cap de nudges → el usuario podría recibir más nudges de lo configurado ese día.
- Aceptable para MVP: los reinicios son infrecuentes y el impacto es menor (nudges adicionales, no pérdida de datos).

### Deuda técnica
- Si zen se vuelve crítico, migrar `nudges_sent` a DynamoDB con update atómico.

---

## NFR-SCHED-04: Observabilidad de Rescue (Q4 = A)

### Logging mínimo
- Rescue mode registra solo `RESCUE_TRIGGERED` como evento en `ExecutionCycle`.
- Metadata del evento: `task_id` seleccionada, `micro_action` generada.
- No se introduce log estructurado adicional más allá del evento.

### Consistencia
- Sigue el patrón establecido en UOW-03/04: eventos como fuente de verdad, logs solo para decisiones de dispatch.

---

## NFR-SCHED-05: Sanitización de Input (Q5 = A)

### Validación del mensaje motivacional
- Máximo 100 caracteres.
- Strip de tags HTML (`<script>`, `<b>`, etc.) — solo texto plano.
- Rechazar si vacío o solo whitespace.
- No permitir URLs (regex simple para filtrar `http://` / `https://`).

### Alcance
- Solo aplica a `/config motivacion TEXTO`.
- Los demás inputs de `/config` ya tienen validación de formato (HH:MM, enteros con rango).

---

## NFR-SCHED-06: Performance del Resumen de Cierre

### Consulta de DailySummary
- El resumen consulta el GSI `userId-status-index` para obtener tareas por estado.
- Query DynamoDB por usuario + status: máx 3 queries (completed, pending, snoozed).
- Para MVP con <50 tareas por usuario, la latencia es despreciable.

### Target
- Generación del resumen + envío: < 2 segundos end-to-end.
- Si el envío a Telegram falla → retry con política existente (3 intentos, 30s backoff).

---

## NFR-SCHED-07: Disponibilidad del Scheduler Dinámico

### Resiliencia
- Hereda el modelo de UOW-03: scheduler in-process, `desiredCount=1` ECS.
- Si el contenedor cae:
  - Recordatorios de inicio/cierre perdidos → no se recuperan (consistente con TD-PUSH-02).
  - Zen sessions se reconstruyen al reiniciar (zen_active en DynamoDB).

### Fail-soft
- Excepciones en evaluación de inicio/cierre/zen → catch + log, nunca propagan.
- Un fallo en el resumen de cierre de un usuario no bloquea los demás.

---

## Security Compliance Summary (delta UOW-05)

| Rule | Status | Notas |
|---|---|---|
| SECURITY-01 Encryption | Compliant (heredado) | GSI en ppai-tasks hereda cifrado de la tabla |
| SECURITY-03 App Logging | Compliant | Rescue event sin PII, solo task_id |
| SECURITY-05 Input Validation | Compliant | Sanitización de motivational_message (max 100, strip HTML, no URLs) |
| SECURITY-06 Least Privilege | Compliant | IAM delta: Query en GSI nuevo |
| SECURITY-08 App Access Control | N/A | No nuevos endpoints ni auth flows; zen/config usan mismo patrón |
| SECURITY-11 Secure Design | Compliant | Scheduler dinámico con floor de 5 min, rescue con guardrails de tono |

---

## Deuda Técnica Registrada (delta UOW-05)

| ID | Descripción | Condición de resolución |
|---|---|---|
| TD-SCHED-01 | ZenSession en memoria, cap se resetea al reiniciar | Migrar a DynamoDB si zen se vuelve crítico |
| TD-SCHED-02 | Recordatorios perdidos no se recuperan tras reinicio | Consistente con TD-PUSH-02, resolver si push es parte del SLA |
