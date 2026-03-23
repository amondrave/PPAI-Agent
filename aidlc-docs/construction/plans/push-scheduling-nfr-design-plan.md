# NFR Design Plan — UOW-03 Push & Scheduling

**Fecha:** 2026-03-23
**Status:** Listo para review

## Unit Context
- **Unit**: UOW-03 Push & Scheduling
- **NFR Requirements**: Aprobados (`nfr-requirements.md`, `tech-stack-decisions.md`)
- **Stack**: Python 3.12 + DynamoDB + ECS Fargate + Terraform + CloudWatch
- **Design goal**: Traducir el scheduler lean y el dispatch con retries a patrones de diseño concretos y componentes lógicos simples.

## Plan Steps

- [x] Paso 1 — Resolver preguntas de patrones delta de UOW-03
- [x] Paso 2 — Generar `nfr-design-patterns.md` con resiliencia, performance, seguridad y observabilidad
- [x] Paso 3 — Generar `logical-components.md` con scheduler, evaluador, dispatcher y repositorios lógicos
- [x] Paso 4 — Validar compliance con baseline de seguridad para callbacks y preferencias

---

## Preguntas delta — UOW-03 NFR Design

### Patrones de ejecución del scheduler

**Q1.** El scheduler corre in-process. ¿Cómo prefieres modelar la responsabilidad interna?
```md
A) Un solo componente hace todo: tick, evaluacion y envio
B) Separar en 2 componentes: scheduler tick + nudge orchestrator
C) Separar en 3 componentes: scheduler tick + eligibility evaluator + dispatcher
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q2.** Para evitar duplicados dentro del mismo proceso, ¿qué patrón prefieres en MVP?
```md
A) Lock in-memory simple por userId/ventana durante el tick
B) Marcar en `ExecutionCycle` antes de enviar y verificar antes de cada intento
C) Ambas: lock in-memory + verificacion de estado persistido
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

### Tiempo, ventanas y timezone

**Q3.** La evaluacion depende de hora local del usuario. ¿Cómo quieres tratar el timezone cuando el usuario aun no configuró uno?
```md
A) Usar UTC como fallback
B) Usar una timezone default del producto (ej. America/Bogota)
C) No enviar nudges hasta tener timezone configurada
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

**Q4.** Para la ventana de silencio diaria, ¿quieres validación estricta del rango en diseño NFR?
```md
A) Si, `silenceStart < silenceEnd` en el mismo día y rechazar rangos inválidos
B) Si, pero permitiendo ventanas que crucen medianoche
C) No, mantener validacion básica y endurecer después
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

### Retry y fallos

**Q5.** La política de retry es 3 intentos. ¿Cómo prefieres modelar el backoff a nivel patrón?
```md
A) Backoff fijo corto
B) Backoff incremental simple
C) Backoff exponencial ligero
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q6.** Cuando un envío falla definitivamente, ¿qué patrón de error prefieres?
```md
A) Fail-soft: registrar, loggear y continuar sin romper el loop
B) Propagar error al scheduler para reintento global del tick
C) Circuit breaker simple si Telegram falla repetidamente
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

### Seguridad y observabilidad

**Q7.** La validación de owner en callbacks ya quedó obligatoria. ¿Dónde prefieres ubicarla lógicamente?
```md
A) En el adapter de Telegram antes de invocar aplicación
B) En el servicio de aplicación como guard principal
C) En ambos: chequeo temprano en adapter + validación defensiva en servicio
X) Other (please describe after [Answer]: tag below)

[Answer]: C
```

**Q8.** Para logs del scheduler, ¿quieres un patrón de correlación explícita?
```md
A) Si, usar `cycle_id` + `task_id` como claves de correlación
B) Si, además generar `dispatch_id` propio por intento
C) No, con `user_id` basta para MVP
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```
