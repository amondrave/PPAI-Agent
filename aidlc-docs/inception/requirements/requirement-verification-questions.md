# Requirements Clarification Questions — PPAI

Por favor responde cada pregunta llenando la etiqueta `[Answer]:` con la letra elegida.

## Question 1
¿Cuál es el canal inicial obligatorio para MVP v1?

A) Solo Telegram (bot)
B) Telegram + CLI desde el inicio
C) Web app desde el inicio
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
¿Cuál es el alcance funcional mínimo del loop en v1 (antes de ampliar features)?

A) Captura -> priorización Top 3 -> nudge -> done/snooze/clarify -> reporte diario
B) Igual que A + rescue mode de día caído
C) Igual que A + resumen semanal
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3
¿Qué nivel de autonomía debe tener el motor para decidir la "siguiente acción" en v1?

A) Regla determinística simple (sin LLM en decisión final)
B) Híbrido (reglas + LLM con guardrails)
C) Mayoritariamente LLM con fallback a reglas
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 4
¿Qué estrategia de estado persistente prefieres para v1?

A) Event log first (eventos del loop como fuente de verdad)
B) Estado materializado first (tabla estado actual) + eventos mínimos
C) Híbrido (event log + proyecciones/materialized views)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 5
¿Cuál es el objetivo primario de esta iteración de construcción?

A) MVP funcional end-to-end deployable
B) Vertical slice ejecutable en local con métricas clave
C) Solo arquitectura + contratos + scaffolding
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 6
Should security extension rules be enforced for this project?

A) Yes — enforce all SECURITY rules as blocking constraints (recommended for production-grade applications)
B) No — skip all SECURITY rules (suitable for PoCs, prototypes, and experimental projects)
X) Other (please describe after [Answer]: tag below)

[Answer]: A
