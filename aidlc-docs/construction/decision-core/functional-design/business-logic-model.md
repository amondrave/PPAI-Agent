# Business Logic Model — UOW-02 Decision Core

## Modelo de Scoring (Q1 = C — definido en sesión)

El algoritmo de priorización es determinístico y se basa en tres factores aditivos:

```
totalScore = urgencyScore + ageScore + snoozeScore   (max: 27)
```

### Factor 1 — urgencyScore (0–10)

Basado en la urgencia extraída por UOW-01 (campo `deadline` de TaskState).

| Condición | Puntuación |
|---|---|
| deadline dentro de las próximas 24h | 10 |
| deadline dentro de las próximas 72h | 7 |
| deadline en más de 72h | 4 |
| Sin deadline (deadline = null) | 3 |

**Rationale:** Las tareas con deadline explícito y cercano son las más críticas.
Las tareas sin deadline reciben el mínimo (3) para no desaparecer del ranking.

### Factor 2 — ageScore (0–7)

Basado en los días transcurridos desde que la tarea entró en estado `pending`.

```
ageScore = min(days_since_pending, 7)
```

1 punto por día, techo en 7. Una tarea de 7+ días en pending recibe siempre 7.

**Rationale:** Las tareas más antiguas merecen atención creciente. El techo evita
que tareas muy viejas monopolicen el Top 3 indefinidamente.

### Factor 3 — snoozeScore (0–10)

Basado en el número de veces que la tarea ha sido pospuesta (snoozeCount).

```
snoozeScore = min(snoozeCount * 2, 10)
```

| snoozeCount | snoozeScore |
|---|---|
| 0 | 0 |
| 1 | 2 |
| 2 | 4 |
| 3 | 6 |
| 4 | 8 |
| 5+ | 10 (techo) |

**Rationale (Q3 = B — sube):** Más posposiciones = más urgente. Una tarea
pospuesta 3 veces lleva semanas sin atención — debe subir en el ranking, no bajar.

### Tie-breaking (Q2 = B)

Cuando dos o más tareas tienen el mismo `totalScore`:

1. **Primero:** deadline más cercano (tareas con deadline antes que tareas sin deadline)
2. **Segundo:** `createdAt` más antiguo (FIFO)

---

## Flujo principal: get_top3(user_id)

```
1. Obtener todas las TaskState del usuario con status = 'pending'
2. Computar PriorityScore para cada tarea elegible
3. Ordenar por totalScore DESC → deadline ASC → createdAt ASC
4. Seleccionar top min(3, len(elegibles)) → Top3Result
5. Actualizar status de esas tareas: pending → prioritized
6. Registrar top3TaskIds en ExecutionCycle activo
7. Emitir evento TOP3_PRESENTED en ExecutionCycle
8. Retornar Top3Result para presentación en Telegram
```

### Casos especiales

| Caso | Comportamiento |
|---|---|
| 0 tareas elegibles | Retornar Top3Result vacío. El adaptador muestra "bandeja vacía" |
| 1–2 tareas elegibles (Q7 = B) | Mostrar las disponibles + mensaje motivacional para capturar más |
| Ciclo activo no existe (Q4 = C, fallback) | Crear ExecutionCycle con status=active para hoy antes de continuar |

---

## Flujo: reordenamiento manual (S2.3)

El usuario indica que quiere empezar por una tarea diferente (texto o botón futuro).

```
1. Recibir instrucción de reordenamiento (texto natural o comando)
2. Identificar la tarea referenciada en el Top 3 actual
3. Moverla a posición #1 del Top3Result (sin cambiar scores)
4. Incrementar manualReorders en el ExecutionCycle activo
5. Registrar evento MANUAL_REORDER con {from_position, to_position, task_id}
6. Responder confirmación del nuevo orden sin juicio ni justificación
```

**Invariante:** El reordenamiento no modifica `totalScore` — solo reordena la presentación.
Los scores originales se preservan para trazabilidad (UOW-05 learning).

---

## Flujo: tarea ambigua (S2.2) — needs_clarification (Q8 = C)

En UOW-02 no hay inferencia automática de ambigüedad. La tarea entra en
`needs_clarification` únicamente por acción explícita del usuario (botón "? Aclarar").

```
1. Usuario pulsa "? Aclarar" sobre una tarea del Top 3
2. El adaptador invoca clarify(task_id, user_id)
3. El sistema actualiza status: prioritized → needs_clarification
4. El sistema envía pregunta de aclaración con máx. 2 opciones (plain text o sí/no)
5. La tarea desaparece del Top 3 actual hasta que se resuelva la aclaración
6. Registrar evento CLARIFICATION_REQUESTED en ExecutionCycle
```

**Nota:** La resolución de la aclaración (recibir respuesta del usuario y volver a `pending`)
es responsabilidad de UOW-04. UOW-02 solo gestiona el inicio del flujo.

---

## Reglas de priorización (hardcoded, Q9 = C)

Los pesos del algoritmo se definen como constantes en código, bajo
`ppai/decision/domain/scoring_rules.py`. Un cambio de pesos = nueva versión del código.

No existe entidad `PrioritizationRule` en DB (Q10 = B — YAGNI).

**Versión actual de reglas:** `v1.0` (definida en sesión 2026-03-18)
