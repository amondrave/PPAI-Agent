# Backlog — PPAI (Personal Productivity AI)

Generado desde: `specs/prd.md` v1.0
Fecha de generación: 2026-03-09
Estado: Draft v1.0
Generado por: Specification Agent (agents/specification-agent.md + skill prd-to-backlog)

> Convenciones:
> - Idioma: español para negocio, inglés para nombres técnicos y código
> - Prioridad: P1-crítico · P2-importante · P3-deseable
> - Tags: [MUST] [SHOULD] [COULD] [TBD]
> - Won't Have del PRD no aparecen en este backlog

---

## Índice de épicas

| ID | Épica | Stories | Prioridad |
|----|-------|---------|-----------|
| E1 | Captura y Normalización | S1.1 · S1.2 · S1.3 | P1 |
| E2 | Motor de Priorización y Decisión | S2.1 · S2.2 · S2.3 | P1 |
| E3 | Orquestador de Nudges | S3.1 · S3.2 · S3.3 · S3.4 | P1 |
| E4 | Cierre de Loop y Aprendizaje | S4.1 · S4.2 · S4.3 · S4.4 | P1 |
| E5 | Reporte Diario e Insights | S5.1 · S5.2 | P1 |
| E6 | Guardrails, Seguridad y Cumplimiento | S6.1 · S6.2 · S6.3 | P1 |
| E7 | Observabilidad y Métricas | S7.1 · S7.2 | P1 |

---

## E1 — Captura y Normalización

> Módulo responsable de recibir el texto libre del usuario por Telegram, extraer la intención de tarea y confirmar la captura. Es el punto de entrada del workflow loop. Sin captura confiable y de baja fricción, no hay loop.

### S1.1 — Captura de tarea en lenguaje natural

**Como** usuario freelancer/solopreneur
**Quiero** enviar un mensaje de texto libre por Telegram describiendo lo que tengo que hacer
**Para** que el sistema lo registre como tarea sin obligarme a usar formatos ni comandos especiales

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `tasks`

**Acceptance Criteria:**
- [ ] AC: El usuario puede enviar cualquier texto en Telegram y el sistema lo reconoce como una tarea a capturar, sin requerir prefijos, comandos ni formato especial.
- [ ] AC: El sistema responde con una confirmación de recepción en menos de 3 segundos, mostrando el texto interpretado.
- [ ] AC: Si el texto está vacío o contiene solo espacios, el sistema solicita aclaración en lugar de crear una tarea vacía.
- [ ] AC: El mensaje de confirmación usa tono empático y no acusatorio, sin lenguaje de juicio sobre la tarea enviada.

---

### S1.2 — Normalización y deduplicación de tarea capturada

**Como** sistema PPAI
**Quiero** procesar el texto libre del usuario y normalizarlo en una tarea estructurada con título, contexto y urgencia inferida
**Para** que el motor de priorización pueda clasificarla correctamente sin requerir información adicional del usuario

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `tasks`

**Acceptance Criteria:**
- [ ] AC: El sistema extrae un título corto (máx. 80 caracteres) de cada tarea a partir del texto libre.
- [ ] AC: Si el sistema detecta una tarea muy similar a una ya registrada y pendiente, notifica al usuario y pregunta si es la misma antes de crear un duplicado.
- [ ] AC: El sistema infiere nivel de urgencia (alta/media/baja) a partir de palabras clave del mensaje (ej. "urgente", "para hoy", "cuando pueda") y lo almacena en la tabla `tasks`.
- [ ] AC: Si la urgencia no puede inferirse con confianza, se asigna "media" como valor por defecto y se registra la ambigüedad.

---

### S1.3 — Captura de múltiples tareas en un solo mensaje

**Como** usuario freelancer/solopreneur
**Quiero** poder enviar varias tareas en un mismo mensaje separadas por saltos de línea o numeración
**Para** no tener que enviar un mensaje por cada tarea cuando quiero hacer un dump rápido de pendientes

**MoSCoW:** [SHOULD]
**Prioridad:** P2-importante
**Módulo DB:** `tasks`

**Acceptance Criteria:**
- [ ] AC: El sistema detecta correctamente cuando un mensaje contiene más de una tarea (por salto de línea, numeración o puntuación).
- [ ] AC: Cada tarea identificada se registra como una entrada independiente en la tabla `tasks`.
- [ ] AC: El sistema confirma cuántas tareas detectó y lista los títulos normalizados para validación del usuario.
- [ ] AC: Si el sistema tiene baja confianza sobre la separación de tareas, pregunta al usuario antes de dividir, en lugar de adivinar.

---

## E2 — Motor de Priorización y Decisión

> Módulo responsable de clasificar las tareas capturadas y seleccionar el Top 3 para presentar al usuario al inicio del día o bajo demanda. Es el cerebro del workflow loop: sin buena priorización, el usuario sigue paralizado.

### S2.1 — Priorización automática y presentación del Top 3

**Como** usuario freelancer/solopreneur
**Quiero** recibir las 3 tareas más importantes de mi lista en orden de prioridad
**Para** saber exactamente por dónde empezar sin tener que revisar toda mi lista

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `tasks`, `execution_cycles`

**Acceptance Criteria:**
- [ ] AC: El sistema presenta exactamente 3 tareas priorizadas (o todas las disponibles si hay menos de 3) al inicio de cada ciclo de ejecución.
- [ ] AC: El criterio de priorización considera al menos: urgencia inferida, fecha de captura y patrones de posposición previos del usuario.
- [ ] AC: Cada tarea en el Top 3 se muestra con su título y un botón inline de acción ("✓ Hecho", "⏸ Posponer", "? Aclarar").
- [ ] AC: El mensaje de presentación del Top 3 no contiene lenguaje de presión, culpa ni urgencia artificial.

---

### S2.2 — Manejo de tarea ambigua o sin suficiente contexto

**Como** sistema PPAI
**Quiero** detectar cuando una tarea tiene contexto insuficiente para priorizarla correctamente
**Para** solicitar una aclaración mínima al usuario antes de incluirla en el Top 3

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `tasks`

**Acceptance Criteria:**
- [ ] AC: Si una tarea no tiene título interpretable o tiene urgencia no inferible, el sistema la marca con estado `needs_clarification` en la tabla `tasks`.
- [ ] AC: El sistema envía una pregunta de aclaración concreta con máximo 2 opciones o una pregunta de sí/no para resolver la ambigüedad.
- [ ] AC: La tarea ambigua no aparece en el Top 3 hasta que se resuelva la aclaración.
- [ ] AC: Si el usuario no responde la aclaración en el ciclo actual, la tarea se mantiene pendiente sin ser descartada y sin enviar recordatorios en ese mismo ciclo.

---

### S2.3 — Reordenamiento manual del Top 3 por el usuario

**Como** usuario freelancer/solopreneur
**Quiero** poder indicarle al sistema que quiero empezar por una tarea diferente a la que él priorizó
**Para** mantener el control sobre mi propia agenda cuando el contexto lo requiere

**MoSCoW:** [SHOULD]
**Prioridad:** P2-importante
**Módulo DB:** `tasks`, `execution_cycles`

**Acceptance Criteria:**
- [ ] AC: El usuario puede indicar por texto o botón que quiere cambiar el orden del Top 3, y el sistema acepta la instrucción sin resistencia ni justificación adicional.
- [ ] AC: El sistema registra el cambio manual como un evento en `execution_cycles` para aprendizaje futuro del patrón.
- [ ] AC: Tras el reordenamiento, el sistema confirma el nuevo orden sin reprochar la decisión del usuario.

---

## E3 — Orquestador de Nudges

> Módulo responsable de enviar recordatorios proactivos al usuario en ventanas de tiempo óptimas para mantener el loop activo. El nudge es el mecanismo de reenganche: sin él, la captura queda sin cierre.

### S3.1 — Envío de nudge en ventana de actividad óptima

**Como** sistema PPAI
**Quiero** enviar un recordatorio proactivo al usuario cuando hay tareas pendientes en su Top 3 y no ha registrado actividad en un período definido
**Para** ayudarlo a retomar la ejecución sin esperar a que él recuerde activamente

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `execution_cycles`

**Acceptance Criteria:**
- [ ] AC: El sistema envía un máximo de 3 nudges por día por usuario, en franjas horarias configurables.
- [ ] AC: El nudge incluye la tarea más prioritaria del Top 3 actual y los botones de acción inline.
- [ ] AC: El texto del nudge usa tono de acompañamiento, no de presión: no contiene palabras como "debías", "no hiciste", "ya es tarde".
- [ ] AC: Si el usuario ya registró actividad en los últimos 30 minutos, el sistema no envía el nudge programado.

---

### S3.2 — Respuesta a nudge con botones inline

**Como** usuario freelancer/solopreneur
**Quiero** poder responder a un nudge de PPAI directamente con botones sin tener que escribir
**Para** cerrar o posponer una tarea con mínima fricción desde cualquier contexto

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `execution_cycles`, `tasks`

**Acceptance Criteria:**
- [ ] AC: Cada nudge muestra exactamente 3 botones inline: "✓ Hecho", "⏸ Posponer" y "? Aclarar".
- [ ] AC: Al presionar "✓ Hecho", el sistema registra el cierre de la tarea y responde con confirmación positiva sin exagerar el elogio.
- [ ] AC: Al presionar "⏸ Posponer", el sistema pospone la tarea al siguiente ciclo y confirma sin cuestionamiento.
- [ ] AC: Al presionar "? Aclarar", el sistema inicia el flujo de aclaración de tarea ambigua (ver S2.2).
- [ ] AC: Los botones responden en menos de 2 segundos y el estado se actualiza correctamente en la base de datos.

---

### S3.3 — Ventana de silencio configurable por el usuario

**Como** usuario freelancer/solopreneur
**Quiero** poder indicarle al sistema un rango horario en el que no quiero recibir nudges
**Para** proteger mis bloques de trabajo profundo o tiempo personal sin apagar el sistema completamente

**MoSCoW:** [SHOULD]
**Prioridad:** P2-importante
**Módulo DB:** `energy_profiles`

**Acceptance Criteria:**
- [ ] AC: El usuario puede configurar una ventana de silencio enviando un comando o mensaje natural (ej. "No me molestes entre 9am y 12pm").
- [ ] AC: El sistema confirma la ventana configurada mostrando el rango horario interpretado para validación del usuario.
- [ ] AC: El sistema no envía ningún nudge dentro de la ventana de silencio configurada.
- [ ] AC: La configuración se persiste en la tabla `energy_profiles` y se aplica a todos los días hasta que el usuario la modifique.

---

### S3.4 — Reenganche por inactividad prolongada

**Como** sistema PPAI
**Quiero** detectar cuando un usuario lleva más de 24 horas sin registrar ninguna actividad
**Para** enviar un reenganche de baja intensidad que lo invite a volver sin hacerlo sentir mal

**MoSCoW:** [SHOULD]
**Prioridad:** P2-importante
**Módulo DB:** `execution_cycles`, `tasks`

**Acceptance Criteria:**
- [ ] AC: El sistema detecta usuarios inactivos (sin eventos en `execution_cycles`) por más de 24 horas.
- [ ] AC: El mensaje de reenganche es de baja intensidad: propone retomar con una sola tarea pequeña, no con todo el backlog.
- [ ] AC: El texto del reenganche no usa lenguaje acusatorio ni menciona la inactividad de forma negativa.
- [ ] AC: Si el usuario no responde al reenganche en 48 horas adicionales, el sistema no envía más mensajes automáticos hasta que el usuario interactúe.

---

## E4 — Cierre de Loop y Aprendizaje

> Módulo responsable de registrar los eventos de cierre del ciclo (hecho, pospuesto, aclarado) y actualizar los patrones de comportamiento del usuario para mejorar la priorización futura. Es el motor del data behavioral moat.

### S4.1 — Registro de cierre de tarea completada

**Como** usuario freelancer/solopreneur
**Quiero** marcar una tarea como completada con el menor esfuerzo posible
**Para** cerrar el loop de ejecución y que el sistema aprenda que pude hacerla

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `tasks`, `execution_cycles`

**Acceptance Criteria:**
- [ ] AC: El usuario puede marcar una tarea como completada usando el botón "✓ Hecho", el comando `/done` o una respuesta de texto natural equivalente.
- [ ] AC: Al registrar el cierre, el sistema actualiza el campo `status` de la tarea en `tasks` a `completed` y registra el timestamp en `execution_cycles`.
- [ ] AC: El sistema responde con una confirmación breve y empática, sin elogios exagerados ni felicitaciones vacías.
- [ ] AC: Si el usuario intenta marcar como completada una tarea que ya está cerrada, el sistema lo informa sin error ni confusión.

---

### S4.2 — Registro de posposición de tarea

**Como** usuario freelancer/solopreneur
**Quiero** posponer una tarea para el siguiente ciclo cuando no puedo o no quiero hacerla ahora
**Para** mantenerla en el sistema sin que desaparezca ni me genere culpa por no haberla hecho

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `tasks`, `execution_cycles`

**Acceptance Criteria:**
- [ ] AC: El usuario puede posponer una tarea usando el botón "⏸ Posponer", el comando `/snooze` o texto natural equivalente.
- [ ] AC: El sistema actualiza el campo `status` de la tarea a `snoozed` y registra el evento con timestamp en `execution_cycles`.
- [ ] AC: El sistema confirma la posposición sin preguntar por qué ni emitir juicio sobre la decisión.
- [ ] AC: La tarea pospuesta vuelve al pool de priorización en el siguiente ciclo sin perder su historial de posposiciones.

---

### S4.3 — Detección de patrón de posposición repetida

**Como** sistema PPAI
**Quiero** identificar tareas que el usuario ha pospuesto 3 o más veces consecutivas
**Para** preguntarle si sigue siendo relevante o si hay un bloqueo que puedo ayudarle a resolver

**MoSCoW:** [SHOULD]
**Prioridad:** P2-importante
**Módulo DB:** `tasks`, `blocking_patterns`

**Acceptance Criteria:**
- [ ] AC: El sistema detecta automáticamente cuando una tarea acumula 3 o más posposiciones consecutivas y la marca en `blocking_patterns`.
- [ ] AC: El sistema envía un mensaje empático preguntando si la tarea sigue siendo relevante, ofreciendo opciones: mantenerla, descartarla o aclarar el bloqueo.
- [ ] AC: El texto del mensaje no usa framing de fracaso ni pregunta "¿por qué no la hiciste?"; usa curiosidad neutral.
- [ ] AC: La respuesta del usuario se registra en `blocking_patterns` para enriquecer su perfil de comportamiento.

---

### S4.4 — Actualización del perfil de comportamiento del usuario

**Como** sistema PPAI
**Quiero** aprender de cada evento del loop (hecho, pospuesto, aclarado, tiempo de respuesta)
**Para** mejorar progresivamente la priorización y el timing de nudges para ese usuario específico

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `execution_cycles`, `energy_profiles`, `blocking_patterns`

**Acceptance Criteria:**
- [ ] AC: Cada evento del loop (cierre, posposición, aclaración, respuesta a nudge) se registra en `execution_cycles` con actor, timestamp y metadata del evento.
- [ ] AC: El sistema actualiza `energy_profiles` con las franjas horarias donde el usuario históricamente completa más tareas.
- [ ] AC: El sistema actualiza `blocking_patterns` con los tipos de tarea que se posponen con más frecuencia.
- [ ] AC: El perfil actualizado se usa en la siguiente sesión de priorización sin requerir acción del usuario.

---

## E5 — Reporte Diario e Insights

> Módulo responsable de generar el cierre diario con un resumen de lo logrado, el patrón del día y la sugerencia para el día siguiente. El tono es la variable crítica: mal tono = churn.

### S5.1 — Generación del reporte nocturno

**Como** usuario freelancer/solopreneur
**Quiero** recibir un resumen del día al cierre de mi jornada que me muestre qué hice, qué quedó pendiente y una sugerencia para mañana
**Para** cerrar el día con claridad sin culpa y arrancar el siguiente con contexto

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `daily_reports`, `tasks`, `execution_cycles`

**Acceptance Criteria:**
- [ ] AC: El sistema envía el reporte nocturno a la hora configurada por el usuario (default: 21:00) o al detectar cierre de sesión.
- [ ] AC: El reporte incluye: número de tareas completadas, tareas que quedan pendientes para mañana, y una sugerencia de arranque para el día siguiente.
- [ ] AC: El tono del reporte es neutro y empático en cualquier escenario, incluso si el usuario no completó ninguna tarea: no menciona "fallaste", "no cumpliste" ni señala el número de pendientes como algo negativo.
- [ ] AC: El reporte se persiste en la tabla `daily_reports` con el contenido generado y el timestamp de envío.
- [ ] AC: El reporte no contiene claims de salud mental, terapia ni promesas de transformación personal.

---

### S5.2 — Encuesta de utilidad del reporte

**Como** sistema PPAI
**Quiero** saber si el reporte fue útil o generó culpa en el usuario
**Para** ajustar el tono y el contenido en reportes futuros y detectar si hay un problema de diseño

**MoSCoW:** [SHOULD]
**Prioridad:** P2-importante
**Módulo DB:** `daily_reports`

**Acceptance Criteria:**
- [ ] AC: Después del reporte, el sistema envía 2 botones de respuesta rápida: "👍 Útil" y "😕 No me ayudó".
- [ ] AC: Si el usuario responde, el feedback se registra en `daily_reports` en el campo correspondiente.
- [ ] AC: Si el % de respuestas "No me ayudó" supera el 33% en 7 días consecutivos, el sistema genera una alerta interna para el operador/admin.
- [ ] AC: No se reintenta pedir feedback si el usuario ignoró la encuesta en el ciclo actual.

---

## E6 — Guardrails, Seguridad y Cumplimiento

> Módulo responsable de garantizar que todos los outputs del sistema cumplen los principios de diseño no negociables: tono no acusatorio, sin claims prohibidos, alcance restringido a productividad. Es la red de seguridad del producto.

### S6.1 — Validación de tono no acusatorio en todos los outputs

**Como** sistema PPAI
**Quiero** verificar que ningún mensaje enviado al usuario contiene lenguaje de juicio, culpa o presión
**Para** cumplir el principio de diseño más crítico del producto y evitar churn por mala experiencia

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** *(capa transversal — no una tabla específica)*

**Acceptance Criteria:**
- [ ] AC: Antes de enviar cualquier mensaje al usuario, el sistema pasa el texto por una capa de validación de tono.
- [ ] AC: La lista de términos prohibidos incluye al menos: "fallaste", "no cumpliste", "otra vez", "fracasaste", "como siempre", "deberías", "tenías que".
- [ ] AC: Si el texto generado contiene un término prohibido, el sistema lo reformula o usa un fallback seguro antes de enviarlo.
- [ ] AC: El sistema registra cada intervención del guardrail de tono para auditoría posterior.

---

### S6.2 — Bloqueo de claims prohibidos de salud mental y terapia

**Como** sistema PPAI
**Quiero** garantizar que el sistema nunca haga afirmaciones de tipo terapéutico, de salud mental o de transformación personal
**Para** cumplir los límites legales y éticos del producto y no crear falsas expectativas

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** *(capa transversal)*

**Acceptance Criteria:**
- [ ] AC: El sistema detecta y bloquea cualquier generación de texto que incluya claims como "te va a ayudar con tu ansiedad", "mejora tu salud mental" o "terapia de productividad".
- [ ] AC: Si el usuario pregunta algo relacionado con salud mental o bienestar emocional, el sistema responde con un mensaje de límites claros y no entra en ese territorio.
- [ ] AC: Los claims bloqueados se registran para auditoría y revisión periódica del modelo.

---

### S6.3 — Detección y manejo de solicitudes fuera de alcance

**Como** sistema PPAI
**Quiero** detectar cuando el usuario pide algo que está fuera del alcance del sistema (ej. gestión de calendario, consejos médicos, tareas de equipo)
**Para** responder con transparencia sobre los límites sin dejar al usuario sin salida

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** *(capa transversal)*

**Acceptance Criteria:**
- [ ] AC: El sistema identifica solicitudes fuera de alcance (calendario, salud, finanzas personales, tareas de terceros) y responde indicando el límite de forma clara y amigable.
- [ ] AC: El mensaje de límite no deja al usuario sin alternativa: sugiere cómo puede continuar dentro del scope del sistema.
- [ ] AC: El escalamiento humano [TBD] se activa cuando el sistema detecta una situación que no puede resolver y que requiere intervención humana.
- [ ] AC: El sistema registra los tipos de solicitudes fuera de alcance para informar decisiones de roadmap futuras.

---

## E7 — Observabilidad y Métricas

> Módulo responsable de capturar todos los eventos del sistema y exponer las métricas críticas para medir el North Star Metric y detectar alertas operativas. Sin datos, no hay aprendizaje ni moat.

### S7.1 — Instrumentación de eventos del loop

**Como** sistema PPAI
**Quiero** registrar cada evento significativo del workflow loop con timestamp, actor y metadata
**Para** tener el dataset que alimenta el aprendizaje del sistema y permite medir el NSM

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `execution_cycles`, `tasks`, `daily_reports`

**Acceptance Criteria:**
- [ ] AC: El sistema registra en `execution_cycles` los siguientes eventos: captura, priorización, nudge enviado, nudge respondido, tarea completada, tarea pospuesta, tarea aclarada, reporte enviado.
- [ ] AC: Cada evento incluye: user_id, event_type, task_id (si aplica), timestamp, latencia desde el evento anterior.
- [ ] AC: Los eventos se persisten de forma atómica: si el registro falla, el sistema reintenta sin duplicar el evento en la base de datos.
- [ ] AC: Los datos de eventos son suficientes para calcular el NSM (% usuarios activos >= 1 tarea/día por 5 días consecutivos) sin consultas adicionales al modelo.

---

### S7.2 — Consola operativa mínima para el operador/admin

**Como** operador/admin
**Quiero** tener acceso a un panel mínimo con las métricas críticas del sistema
**Para** monitorear el estado del producto, detectar alertas y tomar decisiones de ajuste

**MoSCoW:** [SHOULD]
**Prioridad:** P2-importante
**Módulo DB:** `execution_cycles`, `daily_reports`, `tasks`

**Acceptance Criteria:**
- [ ] AC: La consola expone al menos: NSM actual, D1/D7, % tareas completadas, % reporte útil, costo LLM estimado por usuario/mes.
- [ ] AC: Si el costo LLM supera $1/usuario/mes, la consola genera una alerta visible. Si supera $2, genera alerta crítica.
- [ ] AC: Si el % de reportes "No me ayudó" supera 33% en 7 días, la consola genera una alerta de tono.
- [ ] AC: La consola es de solo lectura para el MVP — no permite modificar configuraciones directamente desde ella. [TBD: canal de acceso — web mínima, Telegram bot admin, CLI]

---

## Preguntas abiertas [TBD]

> Ambigüedades encontradas durante la generación del backlog. Requieren decisión antes de implementar las stories marcadas.

| # | Story | Pregunta | Opciones sugeridas |
|---|-------|----------|--------------------|
| 1 | S3.1 | ¿Cuál es la franja horaria default para nudges si el usuario no configuró nada? | A) 9am · 1pm · 6pm · B) Solo por la mañana · C) Configurable antes de primer uso |
| 2 | S3.4 | ¿Qué pasa si el usuario no responde al reenganche en 48h? ¿Se archiva, se mantiene activo o se escala? | A) Se mantiene activo sin mensajes · B) Se archiva con opción de recuperar · C) Se escala a operador |
| 3 | S5.1 | ¿La hora del reporte (default 21:00) es configurable desde el primer mensaje o solo después de un ciclo completo? | A) Configurable desde el onboarding · B) Fixed en MVP, configurable en v2 |
| 4 | S6.3 | ¿Cuál es el canal y SLA del escalamiento humano cuando el sistema detecta una solicitud fuera de alcance crítica? | A) Notificación al operador por Telegram · B) Email admin · C) Log interno sin acción — TBD legal |
| 5 | S7.2 | ¿Por qué canal se expone la consola operativa? | A) Mini web dashboard · B) Bot de Telegram separado para admin · C) CLI con output en terminal |
| 6 | S4.3 | ¿A partir de cuántas posposiciones se activa la detección? El PRD dice "repetida" sin número exacto | A) 3 consecutivas · B) 3 en la semana · C) Configurable por operador |

---

## Checklist de calidad (verificación post-generación)

- [x] El índice lista TODAS las épicas (E1–E7)
- [x] Cada épica tiene al menos 2 stories
- [x] Cada story tiene al menos 2 ACs verificables
- [x] No hay funcionalidad inventada fuera del PRD
- [x] Todas las stories de Must Have están presentes
- [x] Los Won't Have del PRD no aparecen (Calendar, Dashboard, App móvil, Modo equipo, Salud mental, Pomodoro avanzado)
- [x] Las ambigüedades están en la sección TBD con opciones sugeridas
- [x] Nombres de tablas/módulos en inglés snake_case
- [x] ACs en español de negocio
- [x] Stories que tocan comunicación con usuario tienen AC de tono (S1.1, S3.1, S3.2, S3.4, S4.1, S4.2, S4.3, S5.1, S6.1)
