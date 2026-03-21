# NFR Requirements Plan — UOW-02 Decision Core

**Fecha:** 2026-03-18
**Status:** Pendiente respuestas
**Nota:** Tech stack base heredado de UOW-01 (Python 3.12, DynamoDB, ECS Fargate, pytest).
         Solo se preguntan los delta NFR nuevos que introduce UOW-02.

## Checklist

- [x] Paso 1 — Resolver preguntas delta de UOW-02
- [x] Paso 2 — Generar nfr-requirements.md (heredando UOW-01 + delta)
- [x] Paso 3 — Generar tech-stack-decisions.md (actualizaciones)

---

## Preguntas delta — UOW-02

### DynamoDB Access Pattern

**Q1.** `get_top3` necesita consultar todas las tareas `pending` de un usuario.
El schema actual de UOW-01 indexa `ppai-tasks` por `taskId` (PK).
Para buscar por `userId + status` sin hacer un Scan necesitamos un GSI.
```
A) Añadir GSI: PK=userId, SK=status — permite Query(userId, status="pending")
B) Añadir GSI: PK=userId, SK=createdAt — y filtrar por status en la aplicación (FilterExpression)
C) Scan con FilterExpression por ahora (volumen MVP es pequeño, optimizar después)
[Answer]: B
```

**Q2.** El scoring necesita `snoozeCount` en `TaskState`. ¿Cómo manejamos este campo nuevo?
```
A) Añadirlo como campo en DynamoDB con default=0 (sin migración — DynamoDB es schemaless)
B) Calcularlo on-the-fly desde CaptureEvents (contar eventos de tipo SNOOZED por taskId)
[Answer]: A
```

---

### Seguridad de Inline Keyboards

**Q3.** Los botones inline (✓ Hecho, ⏸ Posponer, ? Aclarar) tienen `callback_data` con el `taskId`.
Si el bot está en un grupo o alguien reenvía el mensaje, otro usuario podría pulsar el botón.
```
A) Validar en el handler que callback.from_user.id == tarea.userId antes de procesar
B) No validar — es un bot personal, solo el dueño lo usa, YAGNI para MVP
[Answer]: B
```

---

### Performance del Scoring

**Q4.** El scoring es computación pura en memoria (sin I/O). ¿Cacheamos el Top 3 calculado?
```
A) No cache — recalcular en cada llamada (simple, siempre fresco, volumen MVP es bajo)
B) Cache en memoria con TTL de 60s por usuario (evita recalcular si el usuario pide /top3 rápido)
[Answer]: B
```
