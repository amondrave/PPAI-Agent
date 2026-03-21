# Business Rules — UOW-02 Decision Core

## BR-DEC-01: Task Eligibility

- **Rule**: Solo tareas con status `pending` son elegibles para el Top 3.
- **Trigger**: Inicio de evaluación get_top3
- **Condition**: task.status == 'pending' AND task.userId == user_id
- **Excluded statuses**: captured, prioritized, nudged, done, snoozed, clarifying, needs_clarification
- **Priority**: Blocking (inelegibles se ignoran completamente)

---

## BR-DEC-02: Priority Scoring

- **Rule**: Cada tarea elegible recibe un PriorityScore determinístico.
- **Trigger**: Por cada tarea que pasa BR-DEC-01
- **Formula**: `totalScore = urgencyScore + ageScore + snoozeScore`
- **urgencyScore**:
  - deadline ≤ 24h desde ahora → 10
  - deadline ≤ 72h desde ahora → 7
  - deadline > 72h → 4
  - deadline = null → 3
- **ageScore**: `min(days_since_pending, 7)` donde `days_since_pending` = días desde que el status cambió a `pending`
- **snoozeScore**: `min(task.snoozeCount * 2, 10)`
- **Constraint**: El score es reproducible — misma entrada, mismo resultado siempre.

---

## BR-DEC-03: Tie-Breaking

- **Rule**: Empates en totalScore se resuelven de forma determinística.
- **Trigger**: Ordenamiento del ranking cuando totalScore es igual
- **Orden de desempate**:
  1. Deadline más próximo (ASC — null va al final)
  2. createdAt más antiguo (ASC — FIFO)
- **Constraint**: Nunca aleatorio. El orden debe ser reproducible con los mismos datos.

---

## BR-DEC-04: Top 3 Selection

- **Rule**: Se seleccionan las N tareas con mayor score, máximo 3.
- **Trigger**: Post-scoring y post-ordenamiento
- **N**: `min(3, len(eligible_tasks))`
- **Action**: Actualizar status de las tareas seleccionadas: `pending → prioritized`
- **Constraint**: Si 0 tareas elegibles, retornar lista vacía (no es un error).

---

## BR-DEC-05: Score Explanation

- **Rule**: Cada PriorityScore debe incluir una explicación legible en español.
- **Trigger**: Creación de cada PriorityScore
- **Format**: Texto corto que combine los factores con valor > 0
- **Examples**:
  - `"deadline hoy + 5 días pendiente + pospuesta 3 veces"`
  - `"sin deadline + 1 día pendiente"`
  - `"deadline en 2 días + sin posposiciones"`
- **Purpose**: Auditabilidad interna y base para UOW-05 (aprendizaje + reporte)
- **Constraint**: La explicación no se muestra al usuario en UOW-02. Solo se loggea y persiste en evento.

---

## BR-DEC-06: Top3 Presentation Format (Q6 = B)

- **Rule**: El Top 3 se presenta como un mensaje por tarea con botones inline.
- **Trigger**: Retorno de Top3Result al adaptador de Telegram
- **Format por tarea**:
  ```
  {N}. {task.normalizedText}
  [✓ Hecho] [⏸ Posponer] [? Aclarar]
  ```
- **N**: Posición en el ranking (1, 2, 3)
- **Constraint**: Los botones son InlineKeyboardButton con callback_data que incluye task_id y action.
- **Tone**: Sin lenguaje de presión, culpa ni urgencia artificial en el mensaje contenedor.

---

## BR-DEC-07: Empty or Partial Top 3 (Q7 = B)

- **Rule**: Si hay 0 tareas elegibles, mostrar mensaje de bandeja vacía. Si hay 1–2, mostrar las disponibles más mensaje motivacional.
- **Trigger**: Top3Result con rankedScores.len() < 3
- **Messages**:
  - 0 tareas: `"Tu bandeja está vacía. Envíame lo que tienes en mente para empezar."`
  - 1–2 tareas: Mostrar las disponibles + `"¿Tienes más pendientes? Captúralos y los agrego al mix."`
- **Tone**: Invitación, no presión. Sin mencionar que "faltan" tareas como algo negativo.

---

## BR-DEC-08: ExecutionCycle Event Registration

- **Rule**: Cada presentación de Top 3 se registra como evento en el ExecutionCycle activo.
- **Trigger**: Post-presentación exitosa del Top 3
- **Action**:
  - Actualizar `top3TaskIds` en ExecutionCycle con los IDs del Top 3 actual
  - Registrar evento `TOP3_PRESENTED` con timestamp y task IDs
- **Fallback (Q4 = C)**: Si no existe ExecutionCycle activo hoy, crear uno antes de registrar.
- **Constraint**: Best effort — si falla el registro, loggear warning pero no fallar la presentación.

---

## BR-DEC-09: Manual Reorder (S2.3)

- **Rule**: El usuario puede cambiar el orden del Top 3 sin resistencia del sistema.
- **Trigger**: Instrucción de reordenamiento por texto o comando
- **Action**:
  - Mover la tarea referenciada a posición #1
  - Incrementar `manualReorders` en ExecutionCycle
  - Registrar evento `MANUAL_REORDER` con posiciones y task_id
  - Confirmar nuevo orden sin preguntar por qué ni emitir juicio
- **Constraint**: El reordenamiento no cambia `totalScore`. Solo modifica la presentación.

---

## BR-DEC-10: Clarification Initiation (S2.2)

- **Rule**: El usuario inicia aclaración explícitamente via botón "? Aclarar".
- **Trigger**: Callback del botón "? Aclarar" sobre una tarea del Top 3
- **Action**:
  - Actualizar status: `prioritized → needs_clarification`
  - Enviar pregunta de aclaración (máx. 2 opciones o sí/no)
  - Registrar evento `CLARIFICATION_REQUESTED`
- **Constraint**: La tarea no vuelve al Top 3 hasta que su status regrese a `pending` (UOW-04).
- **Tone**: La pregunta de aclaración usa lenguaje neutro y curiosidad, no "¿por qué no está claro?".

---

## Rules Summary Table

| Rule ID | Nombre | Tipo | Blocking |
|---|---|---|---|
| BR-DEC-01 | Task Eligibility | Guard | Yes |
| BR-DEC-02 | Priority Scoring | Computation | No |
| BR-DEC-03 | Tie-Breaking | Ordering | No |
| BR-DEC-04 | Top 3 Selection | Selection + Transition | No |
| BR-DEC-05 | Score Explanation | Audit | No |
| BR-DEC-06 | Presentation Format | Output | No |
| BR-DEC-07 | Empty / Partial Top 3 | Output | No |
| BR-DEC-08 | ExecutionCycle Registration | Side-effect | No (best effort) |
| BR-DEC-09 | Manual Reorder | Interaction | No |
| BR-DEC-10 | Clarification Initiation | Transition | No |
