# Functional Design Plan — UOW-02 Decision Core

**Fecha:** 2026-03-18
**Status:** Pendiente respuestas

## Checklist de ejecución

- [x] Paso 1 — Definir entidades del dominio (ExecutionCycle, PriorityScore, Top3Result)
- [x] Paso 2 — Diseñar algoritmo de priorización determinístico
- [x] Paso 3 — Diseñar reglas de negocio (BR-DEC-01..10)
- [x] Paso 4 — Diseñar flujo de tarea ambigua (S2.2)
- [x] Paso 5 — Diseñar flujo de reordenamiento manual (S2.3)
- [x] Paso 6 — Diseñar presentación del Top 3 en Telegram
- [x] Paso 7 — Generar artefactos (domain-entities.md, business-rules.md, business-logic-model.md)

---

## Preguntas para Functional Design

### Grupo 1 — Algoritmo de Priorización

**Q1.** El Top 3 debe ser determinístico. ¿Cuáles son los factores de scoring y su peso relativo?
```
A) Urgencia (del texto) + Antigüedad (cuánto tiempo lleva pending) + Snooze count (veces pospuesta)
B) Solo urgencia + antigüedad (sin penalizar por snooze)
C) Quiero definirlos contigo ahora
[Answer]: C
```

**Q2.** ¿Cómo se resuelven los empates (mismo score)?
```
A) Por orden de creación (FIFO — la más antigua gana)
B) Por deadline más cercano
C) Aleatorio (no importa el orden en empates)
[Answer]: B
```

**Q3.** ¿Tiene "recencia negativa"? ¿Una tarea pospuesta muchas veces baja, sube, o no cambia en el ranking?
```
A) Baja (más snoozes = menos prioridad — el usuario claramente no quiere hacerla)
B) Sube (más snoozes = más urgente — lleva mucho tiempo sin hacerse)
C) No cambia (snooze_count no afecta el ranking en UOW-02, se usa en UOW-05)
[Answer]: B
```

---

### Grupo 2 — Ciclo de Ejecución

**Q4.** `ExecutionCycle` representa un ciclo de trabajo del usuario. ¿Qué lo inicia?
```
A) El usuario escribe cualquier mensaje (lazy init — se crea si no hay ciclo activo hoy)
B) El usuario envía un comando explícito como /start o /top3
C) El sistema lo crea automáticamente al inicio del día (scheduled — se implementa en UOW-03)
[Answer]: C
```

**Q5.** ¿Un usuario puede tener más de un ciclo activo al mismo tiempo?
```
A) No — máximo 1 ciclo activo por usuario (el anterior se cierra al abrir uno nuevo)
B) Sí — puede haber ciclos solapados (mañana, tarde, noche)
[Answer]: A
```

---

### Grupo 3 — Presentación del Top 3 (S2.1)

**Q6.** ¿Cómo se presentan las 3 tareas en Telegram?
```
A) Mensaje de texto numerado (1. tarea, 2. tarea, 3. tarea) — sin botones por ahora
B) Cada tarea con botones inline: ✓ Hecho · ⏸ Posponer · ? Aclarar
C) Un mensaje por tarea, con sus propios botones
[Answer]: B
```

**Q7.** Cuando hay menos de 3 tareas pendientes, ¿qué hace el sistema?
```
A) Presenta las que haya (1 o 2) con el mismo formato, sin mencionar que "faltan"
B) Presenta las que haya + un mensaje motivacional para capturar más
C) Si hay 0 tareas presenta "bandeja vacía" — de lo contrario muestra todas
[Answer]: B
```

---

### Grupo 4 — Tarea Ambigua (S2.2)

**Q8.** ¿Cuándo se marca una tarea como `needs_clarification`?
```
A) Cuando el título normalizado tiene menos de 3 palabras (muy corto para entender qué es)
B) Cuando el sistema no pudo inferir urgencia Y el texto es menor de 5 palabras
C) Solo cuando el usuario explícitamente pulsa "? Aclarar" — en UOW-02 no hay inferencia automática
[Answer]: C
```

---

### Grupo 5 — Gestión de Reglas (US-04)

**Q9.** ¿Las reglas de priorización son configurables o hardcoded?
```
A) Hardcoded — los pesos se definen en config/env vars, no en DB
B) Almacenadas en DynamoDB, modificables via comando Telegram de admin
C) Hardcoded pero versionadas en código (cambio = deploy) — suficiente para MVP
[Answer]: C
```

**Q10.** ¿Existe un concepto de "regla activa/inactiva" que modelar ahora?
```
A) Sí — una regla puede estar activa o desactivada sin borrarla
B) No — para el MVP es suficiente con que existan o no (YAGNI)
[Answer]: B
```
