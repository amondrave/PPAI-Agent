# User Stories — PPAI v1

## Story Strategy
- Breakdown approach: **User Journey-Based**
- Prioritization rule: **Risk first**
- Story size target: **Small (1-2 days ideal)**
- Acceptance criteria style: **Functional + critical edge cases**
- Security/compliance: **Integrated in relevant functional stories**

## Journey 1: Capture

### US-01 Capture de intención en lenguaje natural
**Persona**: Executor Freelancer  
**As a** usuario final  
**I want** capturar tareas en texto libre por Telegram  
**So that** pueda iniciar el loop sin fricción.

**Acceptance Criteria**
- El bot acepta mensajes de texto libre y confirma recepción.
- Cada entrada se transforma a una entidad interna de intención/tarea.
- Soporta múltiples capturas en una misma sesión conversacional.
- Edge: si el mensaje está vacío/no interpretable, solicita reformulación sin perder contexto.

**Traceability**: FR-01

### US-02 Normalización mínima de captura
**Persona**: Loop Operator  
**As a** operador/admin  
**I want** que cada captura quede normalizada en formato consistente  
**So that** la priorización y trazabilidad sean confiables.

**Acceptance Criteria**
- Cada intención almacena ID, texto original, timestamp y estado inicial.
- La normalización no elimina información crítica del texto original.
- Edge: mensajes duplicados cercanos en tiempo se marcan para deduplicación simple.

**Traceability**: FR-01, NFR-04

## Journey 2: Decide

### US-03 Top 3 determinístico y trazable
**Persona**: Executor Freelancer  
**As a** usuario final  
**I want** recibir Top 3 priorizado por reglas claras  
**So that** sepa exactamente con qué arrancar.

**Acceptance Criteria**
- El sistema genera Top 3 usando reglas determinísticas configuradas.
- Cada elemento priorizado incluye razón resumida de decisión.
- Edge: si hay menos de 3 tareas válidas, devuelve lista parcial sin error.

**Traceability**: FR-02

### US-04 Gestión segura de reglas de priorización
**Persona**: Loop Operator  
**As a** operador/admin  
**I want** ajustar reglas de priorización de forma controlada  
**So that** pueda mejorar resultados sin romper el loop.

**Acceptance Criteria**
- Reglas se almacenan de forma versionada y auditada.
- Cambios quedan trazados con quién/cuándo/qué cambió.
- Edge: ante configuración inválida, se rechaza cambio y se mantiene versión previa.
- Seguridad integrada: acceso restringido a operación administrativa.

**Traceability**: FR-02, FR-07, NFR-01, NFR-04, NFR-05

## Journey 3: Push

### US-05 Nudge accionable en Telegram
**Persona**: Executor Freelancer  
**As a** usuario final  
**I want** recibir nudges con opciones directas (`done`, `snooze`, `clarify`)  
**So that** pueda responder rápido sin fricción cognitiva.

**Acceptance Criteria**
- El nudge contiene tarea prioritaria y opciones de acción inmediata.
- El usuario puede responder desde botones o comandos equivalentes.
- Edge: si falla entrega del nudge, se ejecuta reintento controlado.

**Traceability**: FR-03, NFR-02

### US-06 Control de intensidad y ventana de empuje
**Persona**: Loop Operator  
**As a** operador/admin  
**I want** configurar intensidad mínima/frecuencia de nudges  
**So that** evite fatiga y mantenga efectividad.

**Acceptance Criteria**
- Existe configuración de frecuencia/ventana de envío.
- Cambios de configuración impactan solo nuevos nudges, no eventos históricos.
- Edge: si la ventana es inválida, se rechaza con error claro.

**Traceability**: FR-03, FR-07

## Journey 4: Respond

### US-07 Cierre inmediato de estado por respuesta de usuario
**Persona**: Executor Freelancer  
**As a** usuario final  
**I want** que mi respuesta actualice estado de inmediato  
**So that** el sistema refleje mi ejecución real.

**Acceptance Criteria**
- `done` actualiza estado a completado y registra timestamp.
- `snooze` actualiza estado de posposición con siguiente intento.
- `clarify` activa flujo de aclaración sobre tarea objetivo.
- Edge: respuestas duplicadas no deben corromper el estado final.

**Traceability**: FR-04

### US-08 Registro mínimo de eventos del loop
**Persona**: Loop Operator  
**As a** operador/admin  
**I want** conservar eventos clave del loop  
**So that** pueda auditar y analizar comportamiento.

**Acceptance Criteria**
- Se registran eventos de decisión, envío nudge e interacción.
- Cada evento contiene correlación con tarea/intención correspondiente.
- Edge: ante error de escritura de evento, el sistema reporta fallo y aplica estrategia de recuperación.
- Seguridad integrada: datos sensibles no se exponen en logs/eventos.

**Traceability**: FR-04, FR-08, NFR-01, NFR-04

## Journey 5: Learn

### US-09 Reporte diario no acusatorio
**Persona**: Executor Freelancer  
**As a** usuario final  
**I want** recibir un reporte diario útil y neutral  
**So that** ajuste mi siguiente ciclo sin culpa.

**Acceptance Criteria**
- Reporte incluye avances, bloqueos y recomendación breve.
- Lenguaje evita tono acusatorio o punitivo.
- Edge: si hay cero avances, el mensaje propone reenganche práctico.

**Traceability**: FR-05

### US-10 Activación de Rescue Mode
**Persona**: Executor Freelancer  
**As a** usuario final  
**I want** que el sistema detecte “día caído” y me proponga rescate  
**So that** recupere tracción con baja fricción.

**Acceptance Criteria**
- El sistema detecta condición de baja ejecución según regla definida.
- Activa propuesta de 1 tarea clave + 1 microacción.
- Registra activación y resultado del rescate.
- Edge: evita múltiples activaciones redundantes en la misma ventana.

**Traceability**: FR-06

### US-11 Aprendizaje conductual básico por reglas
**Persona**: Loop Operator  
**As a** operador/admin  
**I want** ajustar el sistema con base en señales reales de uso  
**So that** mejore efectividad de priorización y nudges.

**Acceptance Criteria**
- Se calculan señales mínimas: done rate, snooze rate, latencia nudge->acción.
- Ajustes de reglas se aplican de manera auditable y reversible.
- Edge: si no hay datos suficientes, no se aplica ajuste automático.

**Traceability**: FR-07, FR-08, NFR-04, NFR-05

### US-12 Observabilidad base del loop
**Persona**: Loop Operator  
**As a** operador/admin  
**I want** consultar métricas críticas del ciclo  
**So that** tome decisiones de mejora en operación.

**Acceptance Criteria**
- Se exponen métricas: capturas, primer done, done/snooze rate, latencia, uso rescue.
- Las métricas son consistentes con el registro de eventos.
- Edge: si falta data en un periodo, el sistema lo reporta explícitamente.

**Traceability**: FR-08

## Integrated Security and Compliance Notes
- Historias con controles de acceso/auditoría: US-04, US-08.
- Historias con resiliencia operativa: US-05, US-07, US-08.
- Controles de seguridad detallados (SECURITY-01..15) se verifican en diseño y construcción.

## INVEST Validation Summary
- **Independent**: historias desacopladas por etapa del journey.
- **Negotiable**: reglas/umbrales ajustables en diseño técnico.
- **Valuable**: cada historia aporta valor directo de ejecución o control operativo.
- **Estimable**: tamaño pequeño/mediano con criterios verificables.
- **Small**: objetivo 1-2 días por historia (algunas técnicas podrían dividirse más en construcción).
- **Testable**: todas incluyen acceptance criteria funcionales y borde crítico.

## Persona Mapping
- Executor Freelancer: US-01, US-03, US-05, US-07, US-09, US-10
- Loop Operator: US-02, US-04, US-06, US-08, US-11, US-12

## Future Stories (Out of Scope v1)
- FS-01 Integración con calendario externo (sync y conflictos)
- FS-02 CLI companion para captura y estado rápido
- FS-03 Resumen semanal avanzado con tendencias
