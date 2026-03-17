# Unit of Work Plan — PPAI v1

## Objective
Descomponer PPAI en unidades de trabajo ejecutables para construcción ordenada del MVP, con dependencias explícitas y mapeo trazable desde historias.

## Planning Checklist
- [x] Definir criterio de corte para unidades
- [x] Definir número y alcance de unidades
- [x] Definir dependencias entre unidades
- [x] Definir estrategia de secuenciación (secuencial/paralela/híbrida)
- [x] Definir mapeo story -> unit
- [x] Generar `aidlc-docs/inception/application-design/unit-of-work.md`
- [x] Generar `aidlc-docs/inception/application-design/unit-of-work-dependency.md`
- [x] Generar `aidlc-docs/inception/application-design/unit-of-work-story-map.md`
- [x] Validar cobertura total de historias MVP

## Decomposition Options

### Option A: By Journey Stages
- Capture, Decide, Push, Respond, Learn/Report.
- Ventaja: máximo alineamiento con loop de producto.
- Riesgo: infraestructura y concerns transversales quedan repartidos.

### Option B: By Technical Modules
- Adapter, Core Engine, Orchestration, Persistence, Observability/Security.
- Ventaja: implementación técnica clara por módulo.
- Riesgo: puede fragmentar el valor por journey.

### Option C: Hybrid (Journey + Technical Foundation)
- Base técnica transversal + unidades por etapa de loop.
- Ventaja: balance entrega incremental + robustez técnica.
- Riesgo: requiere reglas claras de dependencia.

## Planning Questions

## Question 1
¿Qué enfoque de descomposición prefieres para unidades de trabajo?

A) Journey stages
B) Technical modules
C) Hybrid (journey + technical foundation)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 2
¿Cuántas unidades de trabajo objetivo quieres para v1?

A) 3-4 unidades (compacto)
B) 5-6 unidades (balanceado)
C) 7+ unidades (más granular)
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 3
¿Qué estrategia de ejecución prefieres?

A) Mayormente secuencial
B) Híbrida (base secuencial + frentes paralelos)
C) Máxima paralelización posible
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 4
¿Cómo tratamos unidad de seguridad/observabilidad?

A) Integrada dentro de cada unidad funcional
B) Unidad transversal inicial obligatoria
C) Enfoque mixto (baseline transversal + integración por unidad)
X) Other (please describe after [Answer]: tag below)

[Answer]: A

## Question 5
¿Cómo priorizamos unidades?

A) Riesgo técnico primero
B) Valor usuario primero
C) Balanceado riesgo + valor
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Question 6
¿Incluimos una unidad explícita de infraestructura antes de codegen fuerte?

A) Sí, unidad de infraestructura temprana
B) No, infraestructura just-in-time por unidad
C) Mínima infraestructura temprana + expansión posterior
X) Other (please describe after [Answer]: tag below)

[Answer]: B

## Mandatory Artifacts (Generation Phase)
- [ ] `aidlc-docs/inception/application-design/unit-of-work.md`
- [ ] `aidlc-docs/inception/application-design/unit-of-work-dependency.md`
- [ ] `aidlc-docs/inception/application-design/unit-of-work-story-map.md`

## Approval Gate
No generation starts until all `[Answer]:` tags are completed, ambiguities are resolved, and this plan is explicitly approved.
