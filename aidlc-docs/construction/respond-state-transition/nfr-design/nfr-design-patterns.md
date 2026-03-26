# Patrones de Diseno NFR — UOW-04 Respond & State Transition

> Todos los patrones son heredados de UOW-01/02/03. No se introducen patrones nuevos.

---

## Patron 1: Read-Then-Write para Idempotencia (heredado UOW-02)

**Aplicacion en UOW-04**: Antes de transicionar un task, se lee su estado actual de DynamoDB.
Si ya esta en estado terminal (DONE, SNOOZED, NEEDS_CLARIFICATION), se responde con mensaje informativo sin escribir.

```
callback(action, task_id)
  → get_by_id(user_id, task_id)
  → if task.status in estados_validos: transicionar + save
  → else: respuesta idempotente
```

**Limitacion aceptada**: Sin conditional writes (ConditionExpression). En MVP single-user, la probabilidad de race condition es despreciable. Si dos callbacks llegan simultaneos, el segundo lee el estado actualizado por el primero.

---

## Patron 2: Best-Effort Event Recording (heredado UOW-02/03)

**Aplicacion en UOW-04**: Los InteractionEvents se graban despues de la transicion de estado exitosa. Si el registro falla:
- Se loguea warning con structlog
- La transicion NO se revierte
- El usuario recibe su respuesta normalmente

```
task.transition_to_done(now)
task_repo.save(task)
try:
    event_repo.append(interaction_event)
    cycle_event_repo.record_interaction_event(...)
except Exception:
    logger.warning("event.recording_failed", ...)
```

**Justificacion**: La transicion de estado es la operacion critica. Los eventos son secundarios para auditoria.

---

## Patron 3: Filtro Pasivo de Cooldown (nuevo, simple)

**Aplicacion**: El cooldown de snooze se implementa sin scheduler ni jobs de fondo.

```
# Al hacer snooze:
task.snoozed_until = now + timedelta(hours=1)
task.status = SNOOZED
task_repo.save(task)

# Al consultar /top3 (en list_pending o en aplicacion):
# Filtrar tasks donde snoozed_until > now
pending = [t for t in tasks if t.snoozed_until is None or t.snoozed_until <= now]
```

**Ventaja**: Zero overhead operativo. No hay procesos que monitorear o que puedan fallar.
**Precision**: En minutos (verificado al momento del query, no al segundo exacto). Suficiente para cooldown de 1h.

---

## Patron 4: Autorizacion en Capa de Servicio (nuevo, simple)

**Aplicacion**: La validacion de `callback.from_user.id == task.user_id` se hace en ResponseService, no en el adapter.

```
def _authorize(self, callback_user_id: str, task: TaskState) -> bool:
    if callback_user_id != task.user_id:
        logger.warning("callback.unauthorized", ...)
        return False
    return True
```

**Justificacion**: Centraliza la logica de autorizacion en un punto. El adapter solo pasa el user_id del callback.
**En caso de fallo**: Respuesta generica "No tienes permiso para esta accion." sin revelar datos del task.

---

## Patron 5: Confirmacion con Inline Keyboard Dinamico (nuevo, UX)

**Aplicacion**: El boton [Done] no transiciona directamente. Reemplaza el keyboard con botones [Si] [No].

```
# Primer callback: done:{task_id}
→ edit_message_reply_markup con botones [Si] [No]
  - Si → confirm_done:{task_id} → transicion DONE
  - No → cancel_done:{task_id} → restaurar keyboard original o cerrar
```

**Patron Telegram**: `edit_message_reply_markup` para reemplazar botones in-place sin enviar mensaje nuevo.
