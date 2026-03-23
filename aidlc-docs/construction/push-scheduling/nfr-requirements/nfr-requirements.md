# NFR Requirements — UOW-03 Push & Scheduling

> La base no funcional se hereda de UOW-01 y UOW-02. Este documento registra
> solo los delta que introduce UOW-03.

---

## NFR-PUSH-01: Scalability

### Scheduler Scope (Q1 = A)
- El scheduler corre **in-process** dentro del mismo contenedor del bot.
- No se introduce worker separado, cola dedicada ni servicio administrado en esta fase.
- El objetivo sigue siendo MVP personal / bajo volumen.

### Tick Frequency (Q2 = C)
- El scheduler evalua ventanas cada **15 minutos**.
- Esta frecuencia reduce costo cognitivo y operacional, y es consistente con un MVP
  que usa una sola ventana default diaria.

### Escala objetivo
- Volumen esperado: 1-5 usuarios concurrentes, 1-3 nudges diarios por usuario.
- DynamoDB on-demand sigue siendo suficiente sin ajustes especiales de capacidad.

---

## NFR-PUSH-02: Performance

### Dispatch Trigger Latency (Q5 = A)
- Una vez detectada una ventana valida, el envio del nudge es **mejor esfuerzo dentro
  del mismo minuto**.
- Dado que el tick corre cada 15 minutos, el sistema prioriza simplicidad sobre
  puntualidad exacta al segundo.

### Callback Responsiveness (Q6 = C)
- No se define un target formal estricto para callbacks en MVP.
- Se asume mejor esfuerzo operacional.
- Aun asi, la experiencia deseada es que responder un boton inline se sienta inmediata
  para el usuario final siempre que Telegram y el contenedor esten sanos.

### Scheduler Overhead
- El tick del scheduler no debe degradar la captura ni `/top3`.
- La evaluacion por usuario es liviana: revisar ventana, actividad reciente, preferencia
  y presencia de Top 3.

---

## NFR-PUSH-03: Availability

### Runtime Model
- UOW-03 hereda la disponibilidad base de ECS Fargate con `desiredCount=1`.
- Como el scheduler corre dentro del mismo proceso, la disponibilidad del push depende
  de la salud del contenedor principal.

### Tradeoff aceptado
- Si el contenedor cae, se afecta tanto la experiencia reactiva como la proactiva.
- Este riesgo es aceptable para el MVP personal por mantener stack simple.

---

## NFR-PUSH-04: Reliability

### Retry Reliability
- La politica funcional de 3 intentos se mantiene.
- La proteccion contra duplicados se limita **al mismo proceso** (Q7 = C).
- No se exige idempotencia fuerte frente a reinicios del contenedor entre intentos.

### Lost Window Policy (Q8 = A)
- Si el contenedor cae durante una ventana de envio, la ventana perdida **no se recupera**.
- El sistema sigue con la siguiente ventana.
- No se introduce backlog persistente de ventanas pendientes en esta unidad.

### Failure Boundaries
- El dispatch debe ser tolerante a fallos transitorios de Telegram.
- Los fallos definitivos deben quedar registrados en `ExecutionCycle` / event log.
- No se permite que un fallo de push rompa otras capacidades del bot.

---

## NFR-PUSH-05: Security

### Callback Ownership Validation (Q9 = B)
- A diferencia de UOW-02, en UOW-03 sí se debe validar:

```text
callback.from_user.id == resource.user_id
```

- Esto aplica a respuestas sobre nudges y reduce riesgo de uso indebido si el mensaje
  se comparte, reenvia o si el bot termina en un contexto no estrictamente privado.

### Preference Data Protection
- `UserNudgePreferences` no contiene secretos, pero sí preferencias personales de uso.
- Debe heredarse el baseline de:
  - encryption at rest de DynamoDB;
  - logging sin PII sensible innecesaria;
  - least privilege IAM.

### Scope of `/config` (Q10 = A)
- `/config` se reconoce como interfaz futura prevista.
- No es obligatoria en esta unidad, pero la arquitectura no debe bloquear su posterior
  incorporación.

---

## NFR-PUSH-06: Maintainability

### Lean Architecture Mandate (Q12 = A)
- Se evita nueva infraestructura pesada en esta unidad:
  - sin Redis;
  - sin colas dedicadas;
  - sin worker separado;
  - sin scheduler externo administrado.

### Consecuencia positiva
- Menor carga operativa y menor fricción para iterar.

### Consecuencia negativa aceptada
- Menor robustez frente a reinicios y ventanas perdidas.
- Estas limitaciones quedan registradas como deuda técnica controlada, no como bug.

---

## NFR-PUSH-07: Observability

### Logging Granularity (Q11 = A)
- En producción se loggean solo decisiones relevantes:
  - `NUDGE_SENT`
  - `NUDGE_SKIPPED_ACTIVITY`
  - `NUDGE_FAILED`
  - opcionalmente `NUDGE_SCHEDULED` si aporta trazabilidad sin ruido excesivo

- No se loggea cada tick del scheduler en prod.

### Metrics/Tracing Intent
- La observabilidad debe permitir responder:
  - cuántos nudges se intentaron;
  - cuántos se enviaron;
  - cuántos se omitieron por actividad;
  - cuántos fallaron.

### Metadata minima
- `user_id`
- `cycle_id`
- `task_id` si aplica
- ventana usada
- motivo de skip/fallo

---

## NFR-PUSH-08: Data Persistence

### Preferences Persistence (Q3 = A)
- `UserNudgePreferences` se persiste en **nueva tabla DynamoDB dedicada**.
- Justificación:
  - mantiene separacion clara de responsabilidades;
  - evita sobrecargar tablas existentes con items heterogéneos;
  - prepara futuras opciones de configuracion.

### Dispatch Trace Persistence (Q4 = A)
- `NudgeDispatch` no requiere tabla propia en MVP.
- Su trazabilidad se persiste como:
  - eventos y metadata dentro de `ExecutionCycle`;
  - event log existente.

### Resultado
- Nueva tabla solo donde agrega valor funcional claro: preferencias.
- Reuso de mecanismos ya existentes para eventos de dispatch.

---

## NFR-PUSH-09: Infrastructure as Code

- Toda persistencia nueva de UOW-03 debe entrar por Terraform.
- Delta esperado:
  - tabla nueva para preferencias;
  - permisos IAM adicionales para leer/escribir esa tabla;
  - sin nuevos componentes de red;
  - sin nuevos servicios administrados de scheduling.

---

## Security Compliance Summary (Baseline Extension — delta UOW-03)

| Rule | Status | Notas |
|---|---|---|
| SECURITY-01 Encryption | Compliant (heredado) | Nueva tabla DynamoDB debe ir cifrada |
| SECURITY-03 App Logging | Compliant | Solo logs relevantes, sin payload sensible innecesario |
| SECURITY-05 Input Validation | Compliant | Validar payload de callbacks y comandos de preferencias |
| SECURITY-06 Least Privilege | Compliant | IAM delta limitado a tabla de preferencias y updates necesarias |
| SECURITY-08 App Access Control | Compliant | Se exige validacion de owner en callbacks |
| SECURITY-11 Secure Design | Compliant | Scheduler lean, retries controlados, sin dependencias pesadas |

---

## Deuda Técnica Registrada

| ID | Descripción | Condición de resolución |
|---|---|---|
| TD-PUSH-01 | Scheduler in-process depende del mismo contenedor del bot | Revisar al crecer usuarios o criticidad del push |
| TD-PUSH-02 | Ventanas perdidas no se recuperan tras reinicio | Resolver si el push se vuelve parte critica del SLA |
| TD-PUSH-03 | Callback response sin target formal | Definir SLO cuando exista volumen real |
