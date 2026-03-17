# Requirements — PPAI v1 (Workflow Loop de Productividad Personal)

## Intent Analysis Summary
- **User request**: Construir PPAI como sistema de productividad personal que opera un loop explícito de estados: captura intención, decide siguiente acción prioritaria, ejecuta empuje (notificación/prompt/reporte), aprende de ejecución y bloqueo.
- **Request type**: New Project
- **Initial scope estimate**: System-wide (producto completo MVP)
- **Initial complexity estimate**: Complex (motor de decisión + estado persistente + nudges + aprendizaje conductual)

## Product Positioning Constraints (No Negociables)
- PPAI **no es** un generador de planes estáticos.
- PPAI **sí es** un conductor de proceso continuo con estado acumulado.
- El loop operativo v1 debe permanecer explícito y trazable: `capture -> decide -> push -> user response -> learn`.
- El tono del sistema debe ser no acusatorio y orientado a reenganche.

## Scope Definition (MVP v1)

### In Scope
- Canal inicial único: **Telegram Bot**.
- Loop mínimo + rescate:
  - Captura en lenguaje natural.
  - Priorización Top 3.
  - Nudge/Push accionable.
  - Respuestas: `done`, `snooze`, `clarify`.
  - Reporte diario textual.
  - **Rescue mode** para día caído.
- Motor de decisión v1: **reglas determinísticas** (sin LLM en decisión final).
- Persistencia v1: **estado materializado first** + eventos mínimos de auditoría.
- Entregable de iteración: **MVP end-to-end deployable**.

### Out of Scope (v1)
- Web app propia.
- CLI inicial.
- Integraciones de calendario.
- Dashboard visual completo.
- Modo equipo/multiplayer.

## Functional Requirements

### FR-01 Captura de Intención
- El sistema debe aceptar entrada libre por Telegram.
- Debe normalizar la entrada a una estructura interna de tarea/intención.
- Debe soportar captura incremental (una o múltiples tareas en una sesión).

### FR-02 Motor de Priorización Determinístico
- El sistema debe calcular un Top 3 accionable usando reglas explícitas.
- Debe permitir incorporar señales mínimas de contexto (urgencia declarada, vencimiento, arrastre, esfuerzo estimado simple).
- Debe registrar la razón de priorización para trazabilidad.

### FR-03 Orquestación de Nudges
- Debe emitir nudges accionables en Telegram con opciones directas.
- Debe soportar al menos respuestas: `✓ done`, `⏸ snooze`, `? clarify`.
- Debe permitir frecuencia/intensidad mínima configurable.

### FR-04 Cierre de Loop
- Al recibir respuesta del usuario, el sistema debe actualizar el estado materializado inmediatamente.
- Debe guardar eventos mínimos para análisis posterior (ej. decisión, envío de nudge, interacción de usuario).
- Debe cerrar cada ciclo con estado verificable del ítem (`pending`, `in_progress`, `done`, `blocked/snoozed`).

### FR-05 Reporte Diario
- Debe generar un reporte textual diario con foco en ejecución real del día.
- Debe incluir síntesis de avance, bloqueos y recomendación breve para el siguiente ciclo.
- Debe evitar lenguaje acusatorio.

### FR-06 Rescue Mode
- Debe detectar patrón de “día caído” (sin cierres efectivos dentro de ventana definida).
- Debe activar reenganche de baja fricción con 1 tarea clave + 1 microacción.
- Debe registrar activaciones y efectividad del rescue mode.

### FR-07 Aprendizaje Conductual Básico
- Debe ajustar reglas simples de empuje/prioridad con base en comportamiento observado (ej. latencia de respuesta, tasa done/snooze).
- Debe versionar/configurar reglas de forma auditable.

### FR-08 Observabilidad de Loop
- Debe capturar métricas base del ciclo: capturas, tiempo a primer done, done rate, snooze rate, latencia nudge->acción, uso rescue mode.
- Debe exponer estas métricas para operación del producto (aunque la visualización sea mínima en v1).

## Non-Functional Requirements

### NFR-01 Seguridad (Extension Enabled)
- Las reglas de seguridad baseline quedan **habilitadas** como restricciones bloqueantes para diseño e implementación.
- Deben aplicarse según aplicabilidad en cada etapa (N/A cuando corresponda).

### NFR-02 Confiabilidad
- El loop debe tolerar fallos transitorios de mensajería y reintentos controlados.
- El estado materializado no debe quedar inconsistente ante reintentos.

### NFR-03 Rendimiento
- Respuesta operacional percibida en Telegram debe ser rápida para mantener momentum del usuario (objetivo operacional a definir en diseño/técnico).

### NFR-04 Auditabilidad
- Toda decisión principal del loop y transición de estado debe ser trazable.

### NFR-05 Mantenibilidad
- Reglas determinísticas deben estar desacopladas y versionables para iteración rápida sin reescritura extensa.

### NFR-06 Privacidad y Alcance
- Minimización de datos: capturar solo lo necesario para el loop de ejecución.
- Evitar claims de terapia/salud y mantener límites explícitos del producto.

## Key User Scenarios
- Inicio de día sin claridad -> captura rápida -> Top 3 -> primer nudge -> primer done.
- Usuario en bloqueo -> `clarify` sobre tarea prioritaria -> reformulación accionable.
- Usuario posterga repetidamente -> `snooze` recurrente -> rescue mode.
- Cierre diario -> reporte útil sin culpa + siguiente mejor acción.

## Success Criteria for MVP Iteration
- MVP deployable end-to-end en Telegram.
- Loop completo funcional con estado persistente y trazabilidad.
- Instrumentación base de métricas críticas operativa.
- Guardrails de tono y seguridad incorporados.

## Open Decisions Deferred to Next Stages
- Diseño detallado de componentes y contratos internos.
- Modelo exacto de reglas de priorización (fórmula, pesos y umbrales).
- Estrategia de despliegue concreta y stack de infraestructura.
- Umbrales numéricos de SLO/SLA y alertamiento.
