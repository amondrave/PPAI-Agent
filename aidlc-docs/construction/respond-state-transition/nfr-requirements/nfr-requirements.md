# NFR Requirements — UOW-04 Respond & State Transition

> La mayoria de NFRs se heredan de UOW-01/02/03. Este documento registra solo los deltas.

---

## NFR-RSP-01: Escalabilidad (heredado UOW-01)

Igual que NFR-CAP-01. MVP personal, 1-5 usuarios concurrentes.
DynamoDB on-demand capacity cubre el volumen sin configuracion adicional.

**Delta UOW-04:** Sin cambios. No se crean tablas nuevas ni GSIs. Se reutilizan `ppai-tasks`, `ppai-events` y `ppai-cycles`.

---

## NFR-RSP-02: Performance

### Latencia de callbacks (Q1 = A)
- **Target**: < 500ms desde que el usuario presiona boton hasta recibir respuesta.
- **Desglose estimado**:
  - Telegram callback ACK: ~50ms
  - DynamoDB get_by_id (task): ~50-100ms
  - DynamoDB put_item (save task): ~50-100ms
  - DynamoDB put_item (evento, best-effort): ~50-100ms
  - Telegram reply: ~50-100ms
- **Total estimado**: 250-450ms — dentro del target.
- **Optimizacion**: El evento se graba en best-effort (no bloquea la respuesta al usuario si falla).

### Confirmacion de Done
- La confirmacion "Si/No" agrega un round-trip adicional de Telegram.
- Latencia total del flujo done: ~800ms (2 callbacks). Aceptable dado que el usuario inicia el segundo click.

### Cooldown de snooze (Q2 = A)
- Precision en minutos es suficiente para cooldown de 1 hora.
- Implementacion pasiva: filtro en aplicacion al momento de `list_pending`.
- Sin scheduler ni job de fondo para recuperar tareas snoozed.

---

## NFR-RSP-03: Disponibilidad (heredado UOW-01)

Igual que NFR-CAP-03. ECS Fargate desiredCount=1, restart on failure, ~99% uptime objetivo.

**Delta UOW-04:** Si el contenedor reinicia, las tareas en `SNOOZED` con `snoozed_until` persisten en DynamoDB. Al volver, el cooldown se respeta correctamente porque la logica es pasiva (comparacion de timestamps).

---

## NFR-RSP-04: Seguridad

### Autorizacion de callbacks (delta vs UOW-02)
- **Cambio**: En UOW-02 se decidio YAGNI para validacion de `callback.from_user.id`. En UOW-04 se activa (BR-RSP-07).
- **Implementacion**: Antes de cualquier transicion, validar `str(callback.from_user.id) == task.user_id`.
- **En caso de mismatch**: Log `callback.unauthorized` + respuesta generica sin revelar datos del task.

### Datos sensibles en eventos
- Los InteractionEvents NO almacenan texto de tareas ni datos personales.
- Solo: `event_type`, `task_id`, `user_id`, `timestamp`, `correlation_id`, metadata operativa (`snooze_count`, `action`).
- Cumple SECURITY-03 (no sensitive data in logs/events).

---

## NFR-RSP-05: Confiabilidad e Idempotencia

### Idempotencia de callbacks
- Callbacks duplicados (usuario presiona boton 2 veces rapido) no corrompen el estado.
- Implementacion: leer estado actual del task antes de transicionar. Si ya esta en estado terminal, responder con mensaje informativo sin cambio.
- Patron: read-then-write con DynamoDB `put_item` (eventual consistency aceptable para MVP single-user).

### Eventos best-effort
- Si el registro de InteractionEvent falla, la transicion de estado NO se revierte.
- Log warning + continuar. Mismo patron que UOW-02 (cycle updates) y UOW-03 (nudge events).

---

## NFR-RSP-06: Observabilidad

### Eventos de interaccion (US-08)
- **Destino dual**: `ppai-events` (audit trail) + `ppai-cycles` (agregacion diaria).
- **Retencion ppai-events** (Q3 = B): TTL de 90 dias. Items se auto-eliminan despues de 90 dias.
  - Requiere atributo `ttl` (epoch seconds) en el item de DynamoDB.
  - Configurar TTL en la tabla `ppai-events` si no esta habilitado.
- **Retencion ppai-cycles**: Sin TTL (ciclos diarios son ligeros y utiles para reportes UOW-05).

### Logging estructurado
- Heredado de UOW-01. Usar `structlog` con campos: `user_id`, `task_id`, `action`, `from_status`, `to_status`.
- No loguear contenido de tareas ni texto del usuario.

---

## NFR-RSP-07: Mantenibilidad

- Modulo `ppai/respond/` sigue la misma estructura que `ppai/push/` (domain, application, infrastructure).
- Tests unitarios para ResponseService con fakes in-memory (mismo patron que DecisionService tests).
- Tests de integracion con moto para validar escritura de eventos en DynamoDB.
