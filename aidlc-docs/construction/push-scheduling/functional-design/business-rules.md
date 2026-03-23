# Business Rules — UOW-03 Push & Scheduling

## BR-PUSH-01: Default Scheduling Window

- **Rule**: Si el usuario no tiene configuracion explicita, el sistema programa un
  solo nudge diario a las `09:00` hora local del usuario.
- **Trigger**: Evaluacion diaria del scheduler
- **Purpose**: Proveer un empuje inicial simple y consistente para el MVP

---

## BR-PUSH-02: Cycle Creation on Real Dispatch Opportunity

- **Rule**: `ExecutionCycle` se crea solo cuando existe una oportunidad real de push.
- **Trigger**: Ventana activa + tarea elegible + ausencia de ciclo activo
- **Action**: Crear ciclo antes de registrar el primer evento de dispatch
- **Constraint**: No crear ciclos vacios por calendario

---

## BR-PUSH-03: Cycle Closure Deferred

- **Rule**: UOW-03 no cierra el `ExecutionCycle`.
- **Trigger**: Fin de ventana o fin de dia
- **Action**: Ninguna mutacion de cierre desde esta unidad
- **Delegation**: El cierre queda para UOW-05

---

## BR-PUSH-04: Nudge Target Selection

- **Rule**: El nudge usa siempre la tarea en posicion `#1` del Top 3 vigente.
- **Trigger**: Construccion de mensaje de nudge
- **Source**: Resultado de UOW-02 Decision Core
- **Constraint**: No usar heuristicas alternativas en el MVP

---

## BR-PUSH-05: No Top 3, No Nudge

- **Rule**: Si no existe Top 3 vigente o disponible al momento de la ventana, no se
  envia nudge.
- **Trigger**: Evaluacion de ventana sin `Top3Result`
- **Action**: Omitir envio y registrar motivo operativo
- **Constraint**: No recalcular Top 3 automaticamente y no enviar mensaje generico

---

## BR-PUSH-06: Activity Silence Guard

- **Rule**: Si el usuario tuvo actividad relevante en los ultimos 60 minutos, se
  omite el nudge programado.
- **Trigger**: Evaluacion previa al envio
- **Relevant activity**: captura, presentacion de Top 3, respuesta a nudge, `done`,
  `snooze`, `clarify`
- **Event**: Registrar `NUDGE_SKIPPED_ACTIVITY`

---

## BR-PUSH-07: Daily Intensity Cap

- **Rule**: El sistema no debe enviar mas de 3 nudges automaticos por dia por usuario.
- **Trigger**: Antes de despachar un nuevo nudge
- **Constraint**: El limite es baseline del MVP
- **Future extension**: Puede existir override por usuario via `/config`

---

## BR-PUSH-08: Silence Window Enforcement

- **Rule**: Si el usuario configuro una ventana de silencio, no se envia ningun nudge
  dentro de ese rango.
- **Trigger**: Evaluacion de ventana
- **Model**: Un solo rango horario persistido por usuario que aplica a todos los dias
- **Constraint**: La unidad respeta la configuracion; la captura/edicion de esa
  preferencia puede completarse en otra historia/capa

---

## BR-PUSH-09: Nudge Message Format

- **Rule**: El nudge se presenta como un solo mensaje con:
  - titulo de la tarea prioritaria;
  - linea corta con razon de prioridad;
  - botones inline `✓ Hecho`, `⏸ Posponer`, `? Aclarar`.
- **Trigger**: Construccion del payload outbound a Telegram
- **Constraint**: La explicacion debe ser breve, legible y no tecnica

---

## BR-PUSH-10: Tone Guardrails

- **Rule**: El contenido del nudge usa tono motivacional suave, sin culpa ni
  presion artificial.
- **Trigger**: Generacion de cualquier mensaje de push o reenganche
- **Prohibited examples**: "debias", "ya vas tarde", "otra vez", "no hiciste"
- **Constraint**: No usar elogio exagerado ni framing terapeutico

---

## BR-PUSH-11: Retry Policy

- **Rule**: Ante fallo transitorio de Telegram, el sistema realiza hasta 3 intentos
  de envio dentro de la misma ventana.
- **Trigger**: Error transitorio de mensajeria
- **Expected behavior**: backoff corto y controlado
- **Constraint**: No trasladar retries a otra ventana del dia

---

## BR-PUSH-12: Final Failure Persistence

- **Rule**: Si todos los retries fallan, se persiste un evento de fallo en
  `ExecutionCycle`.
- **Trigger**: Agotamiento de intentos
- **Metadata minima**: `task_id`, timestamp, ventana usada, motivo resumido
- **Constraint**: El fallo debe ser auditable aunque el nudge no haya salido

---

## BR-PUSH-13: Task Status Transition on Successful Send

- **Rule**: Si el nudge se envia correctamente, la tarea objetivo transiciona a
  `nudged`.
- **Trigger**: Confirmacion exitosa del envio por Telegram
- **Previous state expected**: `prioritized`
- **Purpose**: Representar que la tarea ya fue empujada y esta esperando respuesta

---

## BR-PUSH-14: Dispatch Telemetry

- **Rule**: Cada decision del scheduler debe dejar trazabilidad minima en el ciclo.
- **Events mínimos**:
  - `NUDGE_SCHEDULED`
  - `NUDGE_SENT`
  - `NUDGE_SKIPPED_ACTIVITY`
  - `NUDGE_FAILED`
- **Metadata minima**: `task_id`, ventana usada, timestamp, motivo si aplica

---

## BR-PUSH-15: Low-Intensity Re-engagement

- **Rule**: Si el usuario lleva mas de 24 horas sin actividad relevante, el sistema
  envia un reenganche de baja intensidad.
- **Trigger**: Deteccion de inactividad >24h
- **Action**: Proponer retomar con una sola tarea, no con todo el backlog
- **Constraint**: Mantener botones inline y respetar los mismos guardrails de tono

---

## Rules Summary Table

| Rule ID | Nombre | Tipo | Blocking |
|---|---|---|---|
| BR-PUSH-01 | Default Scheduling Window | Scheduling | No |
| BR-PUSH-02 | Cycle Creation on Real Dispatch Opportunity | Lifecycle | No |
| BR-PUSH-03 | Cycle Closure Deferred | Lifecycle | No |
| BR-PUSH-04 | Nudge Target Selection | Selection | Yes |
| BR-PUSH-05 | No Top 3, No Nudge | Guard | Yes |
| BR-PUSH-06 | Activity Silence Guard | Guard | Yes |
| BR-PUSH-07 | Daily Intensity Cap | Guard | Yes |
| BR-PUSH-08 | Silence Window Enforcement | Guard | Yes |
| BR-PUSH-09 | Nudge Message Format | Output | No |
| BR-PUSH-10 | Tone Guardrails | Output | Yes |
| BR-PUSH-11 | Retry Policy | Reliability | No |
| BR-PUSH-12 | Final Failure Persistence | Audit | No |
| BR-PUSH-13 | Task Status Transition on Successful Send | Transition | Yes |
| BR-PUSH-14 | Dispatch Telemetry | Audit | No |
| BR-PUSH-15 | Low-Intensity Re-engagement | Output | No |
