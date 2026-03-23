# Business Logic Model — UOW-03 Push & Scheduling

## Modelo funcional del empuje

UOW-03 introduce el primer flujo verdaderamente proactivo del loop: el sistema ya no
espera a que el usuario pida `/top3`, sino que evalua ventanas de envio y despacha un
nudge accionable por Telegram cuando el contexto lo justifica.

El objetivo funcional es mantener el loop activo sin generar fatiga:

```
capture -> decide -> push -> user response -> learn
```

UOW-03 cubre la parte `push` y deja preparada la trazabilidad para `user response`
y `learn`.

---

## Politica base de scheduling (Q1, Q2, Q3)

### Ventanas default del MVP

Si el usuario no configuro preferencia explicita, el sistema usa una sola ventana
diaria por defecto:

```text
09:00 hora local del usuario
```

Esto reduce complejidad operativa en la primera iteracion y evita fatiga temprana.

### Apertura de `ExecutionCycle`

UOW-03 no crea ciclos "vacíos" por calendario. El `ExecutionCycle` del dia se crea
solo cuando el scheduler detecta que existen condiciones reales para empujar:

1. llega una ventana de envio;
2. hay una tarea prioritaria elegible para nudge;
3. no existe ciclo activo para hoy;
4. se crea el ciclo antes del despacho.

### Cierre de `ExecutionCycle`

UOW-03 **no cierra** el ciclo. Solo lo abre cuando hace falta. El cierre queda
delegado a UOW-05, que tiene el contexto del dia completo (reporte, rescue, learn).

---

## Flujo principal: scheduler tick -> nudge

### Paso 1 — Evaluar ventana activa

En cada tick del scheduler, el sistema verifica:

1. si el usuario esta dentro de una ventana permitida;
2. si no esta dentro de una ventana de silencio;
3. si no excedio el maximo de nudges del dia;
4. si no tuvo actividad reciente en los ultimos 60 minutos;
5. si existe una tarea objetivo para empujar.

### Paso 2 — Resolver tarea objetivo (Q4, Q5)

La tarea objetivo del nudge es siempre:

```text
la tarea #1 del Top 3 actual
```

Si al momento de la ventana **no existe Top 3 vigente o cacheado**, el sistema **no**
recalcula ni envia mensaje generico. Simplemente:

1. omite el nudge de esa ventana;
2. registra el motivo;
3. espera la siguiente oportunidad.

Rationale: en este MVP el push depende de un estado previo de decision ya consolidado.

### Paso 3 — Construir el nudge

Formato funcional elegido (Q6 = B):

```text
{titulo de la tarea prioritaria}
{linea corta de razon de prioridad}
[✓ Hecho] [⏸ Posponer] [? Aclarar]
```

La explicacion de prioridad es breve, legible y operativa. No es un dump tecnico del
score ni una justificacion larga.

Ejemplos:

- "Tu siguiente foco: Enviar propuesta al cliente"
- "Va primero porque vence hoy"

### Paso 4 — Despachar por Telegram

Si Telegram responde OK:

1. el mensaje queda enviado;
2. la tarea objetivo transiciona a `nudged`;
3. se registra `NUDGE_SENT`;
4. el ciclo queda actualizado con metadata de ventana y `task_id`.

Si Telegram falla por error transitorio:

1. se ejecutan hasta 3 intentos;
2. se aplica backoff corto dentro de la misma ventana;
3. si todos fallan, se registra `NUDGE_FAILED`.

---

## Reglas de frecuencia e intensidad (Q7, Q8, Q9)

### Intensidad base del MVP

Para el MVP:

- el sistema usa un estandar de hasta **3 nudges por dia**;
- la intensidad es global por defecto;
- queda abierta una extension futura para override por usuario via `/config`.

Esta decision permite un MVP util sin exigir desde ya un sistema completo de
preferencias avanzadas.

### Silencio por actividad reciente

Si el usuario tuvo actividad dentro de los **ultimos 60 minutos**, el nudge
programado se omite.

Actividad relevante significa cualquier evento que indique engagement real del loop,
por ejemplo: captura, top 3, respuesta a nudge, done, snooze, clarify.

### Ventana de silencio configurable

El MVP modela una sola ventana persistida por usuario:

```text
un rango horario por dia que aplica a todos los dias
```

Ejemplo:

```text
09:00 -> 12:00
```

Durante esa ventana no se envia ningun nudge automatico.

---

## Retry y manejo de fallos (Q10, Q11)

### Politica de retry

Ante error transitorio de mensajeria:

```text
maximo 3 intentos dentro de la misma ventana
```

Backoff sugerido a nivel funcional:

```text
inmediato -> +30s -> +2m
```

La implementacion exacta puede variar, pero el comportamiento esperado es:

- no abandonar al primer fallo;
- no arrastrar reintentos a otra ventana;
- no generar tormenta de mensajes.

### Registro de fallo final

Si todos los intentos fallan, el sistema persiste:

- evento de fallo en `ExecutionCycle`;
- timestamp;
- motivo resumido del error;
- `task_id` objetivo;
- ventana evaluada.

---

## Reenganche por inactividad (Q12)

UOW-03 **si incluye** el flujo de reenganche por inactividad >24h.

### Regla funcional

Si un usuario lleva mas de 24 horas sin actividad relevante del loop:

1. el sistema no empuja el backlog completo;
2. envía un nudge de baja intensidad;
3. propone retomar con una sola tarea;
4. mantiene el mismo set de botones inline.

Esto permite que S3.4 quede dentro de la unidad, no como anexo futuro.

---

## Guardrails de tono (Q13)

Baseline de tono:

```text
motivacional suave, sin elogio exagerado
```

Principios funcionales:

- acompañar sin presionar;
- no usar culpa ni urgencia artificial;
- no sonar terapéutico;
- no felicitar de forma vacía.

### Ejemplos validos

- "Tu siguiente paso podria ser este."
- "Si te sirve, puedes retomar por aqui."
- "Esto va primero porque vence hoy."

### Ejemplos prohibidos

- "No lo has hecho todavia."
- "Ya vas tarde."
- "Debias haber avanzado."
- "Otra vez lo dejaste pasar."

---

## Telemetria minima del dispatch (Q14)

El ciclo debe registrar al menos:

- `NUDGE_SCHEDULED`
- `NUDGE_SENT`
- `NUDGE_SKIPPED_ACTIVITY`
- `NUDGE_FAILED`

Con metadata minima:

- `task_id`
- ventana usada
- timestamp
- motivo de skip/fallo si aplica

Esto deja a UOW-05 una base limpia para medir latencia nudge -> accion, efectividad
y fatiga.

---

## Flujo resumido

```text
1. Scheduler evalua ventana
2. Verifica silencio/configuracion/actividad reciente
3. Busca Top 3 vigente
4. Toma la tarea #1
5. Crea ExecutionCycle si hace falta
6. Registra NUDGE_SCHEDULED
7. Intenta envio por Telegram
8. Si envia: task -> nudged, registra NUDGE_SENT
9. Si falla: retry hasta 3 veces
10. Si agota retries: registra NUDGE_FAILED
```

---

## Limites conscientes de esta unidad

UOW-03 deja explicitamente fuera de su responsabilidad directa:

- procesar la accion final del usuario (`done`, `snooze`, `clarify`) como mutacion
  completa del estado de negocio;
- cerrar el `ExecutionCycle`;
- aprender de efectividad a nivel behavioral.

Esas piezas se apoyan en esta unidad, pero se consolidan en UOW-04 y UOW-05.
