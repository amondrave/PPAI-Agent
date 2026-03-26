# Plan NFR Requirements — UOW-04 Respond & State Transition

## Contexto
UOW-04 hereda la mayoria de NFRs de UOW-01/02/03. Este plan identifica solo los **deltas** relevantes para el modulo de respuesta y transicion de estados.

## Pasos

- [ ] Paso 1: Confirmar herencia de NFRs existentes (scalability, availability, performance base)
- [ ] Paso 2: Definir NFR de latencia para callbacks (done/snooze/clarify)
- [ ] Paso 3: Definir NFR de idempotencia y consistencia de estado
- [ ] Paso 4: Definir NFR de seguridad (callback authorization — delta vs UOW-02)
- [ ] Paso 5: Definir NFR de observabilidad (eventos de interaccion)
- [ ] Paso 6: Confirmar tech stack (sin cambios esperados)
- [ ] Paso 7: Generar artefactos

## Preguntas

### Q1: Latencia de callbacks
Cuando el usuario presiona un boton ([Done], [Snooze], [Clarify]), cual es el tiempo de respuesta aceptable?

Opciones:
A) < 500ms (mismo target que /top3 con cache miss)
B) < 1s (aceptable porque el usuario espera feedback)
C) < 2s (relajado, el callback no es critico)

[Answer]: A

### Q2: Consistencia en snooze cooldown
El cooldown de 1h del snooze se implementa de forma pasiva (filtro en list_pending). Esto significa que si el usuario hace /top3 a los 59 minutos, la tarea no aparece; a los 61 minutos si. Es aceptable esta precision?

Opciones:
A) Si, precision de minutos es suficiente para un cooldown de 1h
B) No, necesito precision al segundo (requiere logica adicional)

[Answer]: A

### Q3: Eventos de interaccion — retencion
Los InteractionEvents se guardan en ppai-events. Deben tener TTL (auto-delete) o retencion indefinida?

Opciones:
A) Sin TTL — retener indefinidamente para auditoria
B) TTL de 90 dias (igual que logs de CloudWatch)
C) TTL de 30 dias

[Answer]: B
