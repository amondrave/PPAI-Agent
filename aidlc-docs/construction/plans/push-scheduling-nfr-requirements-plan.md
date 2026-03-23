# NFR Requirements Plan — UOW-03 Push & Scheduling

**Fecha:** 2026-03-23
**Status:** Listo para review
**Nota:** Tech stack base heredado de UOW-01/UOW-02 (Python 3.12, DynamoDB, ECS Fargate, pytest, Telegram Bot).
         Solo se preguntan los delta NFR que introduce UOW-03.

## Unit Context
- **Unit**: UOW-03 Push & Scheduling
- **Goal**: Programar y despachar nudges accionables por Telegram con control de frecuencia, ventana y reintentos.
- **Stories**: US-05, US-06
- **Backlog relacionado**: S3.1, S3.2, S3.3, S3.4
- **Functional Design**: Aprobado (`business-logic-model.md`, `business-rules.md`, `domain-entities.md`)

## Checklist

- [x] Paso 1 — Resolver preguntas delta de UOW-03
- [x] Paso 2 — Generar `nfr-requirements.md` (heredando UOW-01/UOW-02 + delta)
- [x] Paso 3 — Generar `tech-stack-decisions.md` (actualizaciones)
- [x] Paso 4 — Validar compliance con seguridad baseline para el dispatch

---

## Preguntas delta — UOW-03

### Scheduler Runtime

**Q1.** UOW-03 necesita ejecutar evaluaciones de ventana (scheduler tick). ¿Qué estrategia prefieres para MVP?
```md
A) Scheduler in-process dentro del mismo contenedor del bot (simple, 1 servicio)
B) Job/worker separado dedicado al scheduler (mas limpio, mas complejidad)
C) Cron externo / EventBridge / servicio administrado desde el inicio
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q2.** Si usamos scheduler in-process, ¿cada cuánto debe correr el tick para revisar si hay que disparar un nudge?
```md
A) Cada 1 minuto
B) Cada 5 minutos
C) Cada 15 minutos
X) Other (please describe after [Answer]: tag below)

[Answer]: C
```

### Persistencia de preferencias y estado de dispatch

**Q3.** `UserNudgePreferences` necesita persistirse. ¿Dónde prefieres modelarlo en MVP?
```md
A) Nueva tabla DynamoDB dedicada (ej. `ppai-preferences`)
B) Reusar una tabla existente con item especializado
C) Mantenerlo temporalmente en memoria/config hasta tener mas historias
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q4.** `NudgeDispatch` funcionalmente existe. Para MVP, ¿cómo prefieres persistir la trazabilidad?
```md
A) Como eventos/metadata dentro de `ExecutionCycle` y event log existente
B) Tabla DynamoDB nueva dedicada a dispatches
C) Solo logs estructurados en CloudWatch
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

### Performance y experiencia de usuario

**Q5.** ¿Cuál es tu expectativa operacional para el envio de un nudge una vez que el scheduler detecta una ventana valida?
```md
A) Mejor esfuerzo dentro del mismo minuto
B) Debe salir idealmente en menos de 30 segundos
C) Puede tardar hasta 5 minutos y sigue siendo aceptable para MVP
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q6.** Los botones inline de un nudge deben sentirse rapidos. ¿Cuál target quieres asumir para callback response?
```md
A) < 2 segundos
B) < 5 segundos
C) Mejor esfuerzo sin target formal en MVP
X) Other (please describe after [Answer]: tag below)

[Answer]: C
```

### Reliability y retries

**Q7.** La politica funcional de retry ya esta definida en 3 intentos. ¿Quieres que el fallo del scheduler o dispatch sea idempotente frente a reinicios del contenedor?
```md
A) Si, evitar duplicados aunque el contenedor reinicie entre intentos
B) Mejor esfuerzo basta para MVP; aceptar riesgo bajo de duplicado
C) Solo proteger contra duplicados dentro del mismo proceso
X) Other (please describe after [Answer]: tag below)

[Answer]: C
```

**Q8.** Si el contenedor cae durante una ventana de envio, ¿cómo quieres tratar el nudge perdido?
```md
A) No recuperar la ventana perdida; seguir con la siguiente
B) Intentar recuperarlo si el proceso vuelve dentro de un margen corto
C) Requiere cola persistente desde el inicio
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

### Seguridad y control de acceso

**Q9.** En UOW-02 se aceptó no validar `callback.from_user.id` por ser bot personal. ¿Para nudges quieres mantener esa decisión o endurecerla ya?
```md
A) Mantener YAGNI del MVP personal
B) Validar userId en callbacks de nudge desde ahora
C) Validar solo en prod, no en local
X) Other (please describe after [Answer]: tag below)

[Answer]: B
```

**Q10.** `/config` aparece como posible override futuro para intensidad. ¿Quieres tratarlo en NFR como interfaz prevista pero no obligatoria en esta unidad?
```md
A) Si, documentarlo como extension futura sin implementacion obligatoria ahora
B) No, considerar que UOW-03 ya debe dejar esa interfaz lista
C) Mantenerlo fuera del alcance por completo en esta etapa
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

### Observabilidad y costo

**Q11.** El scheduler agregará ruido en logs/metricas. ¿Qué granularidad prefieres para MVP?
```md
A) Loggear solo decisiones relevantes: sent, skipped, failed
B) Loggear cada tick del scheduler para debugging
C) Loggear ticks solo en debug local; en prod solo eventos relevantes
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```

**Q12.** Para mantener costo/control simples en prod, ¿quieres evitar nueva infraestructura pesada (colas, redis, workers separados) salvo que sea estrictamente necesaria?
```md
A) Si, mantener UOW-03 lo mas lean posible
B) No, prefiero robustez desde ahora aunque suba complejidad/costo
C) Depende de si rompe mucho la confiabilidad del MVP
X) Other (please describe after [Answer]: tag below)

[Answer]: A
```
