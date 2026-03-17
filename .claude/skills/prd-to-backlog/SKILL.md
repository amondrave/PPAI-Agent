# Skill: prd-to-backlog

**Versión:** 1.0
**Proyecto:** PPAI (Personal Productivity AI)
**Autor:** Co-creado Angel Mondragon + Claude
**Última actualización:** 2026-03-09

---

## Propósito

Este Skill convierte el PRD de PPAI (`specs/prd.md`) en un backlog estructurado (`specs/backlog.md`) con épicas, user stories y acceptance criteria (ACs) listos para implementar.

Es la puerta de entrada al ciclo de desarrollo: sin backlog bien estructurado, no hay stories para implementar, ni BDD para testear.

---

## Cuándo usar este Skill

Activar cuando:
- El PRD (`specs/prd.md`) tiene cambios y hay que regenerar el backlog.
- `specs/backlog.md` no existe o está desactualizado.
- Se necesita priorización explícita de épicas para una fase de desarrollo.

---

## Pre-requisitos

Antes de ejecutar este Skill, verificar que existen:

| Archivo | Rol |
|---------|-----|
| `specs/prd.md` | Fuente única de verdad — NO modificar durante este proceso |
| `AGENTS.md` | Contrato del repositorio — contiene naming conventions y DDD |

Si alguno no existe, detener y notificar al usuario.

---

## Instrucciones de ejecución (paso a paso)

### PASO 1 — Leer el PRD completo

Leer `specs/prd.md` en su totalidad antes de generar nada.

Extraer y registrar internamente:
- One-liner del producto
- JTBD principal
- MoSCoW completo (Must/Should/Could/Won't Have)
- Los 7 módulos funcionales (Segmento 9)
- Los 5 casos de uso top (Segmento 5)
- Principios de diseño no negociables (Segmento 6)
- Métricas de éxito (Segmento 10)

### PASO 2 — Leer AGENTS.md

Leer `AGENTS.md` para confirmar:
- Naming conventions (tablas SQL en inglés snake_case, código en inglés, docs en español)
- DDD domain vocabulary (Task, ExecutionCycle, BlockingPattern, etc.)
- Story format definido en Sub-Agente 1

### PASO 3 — Derivar las épicas desde el PRD

Cada épica corresponde a un módulo funcional del PRD (Segmento 9). Usar exactamente estos módulos como base:

| Épica | Nombre | Fuente en PRD |
|-------|--------|---------------|
| E1 | Captura y Normalización | Segmento 9, Módulo 1 |
| E2 | Motor de Priorización y Decisión | Segmento 9, Módulo 2 |
| E3 | Orquestador de Nudges | Segmento 9, Módulo 3 |
| E4 | Cierre de Loop y Aprendizaje | Segmento 9, Módulo 4 |
| E5 | Reporte Diario e Insights | Segmento 9, Módulo 5 |
| E6 | Guardrails, Seguridad y Cumplimiento | Segmento 9, Módulo 6 |
| E7 | Observabilidad y Métricas | Segmento 9, Módulo 7 |

### PASO 4 — Generar stories por épica

Para cada épica, generar entre 2 y 5 stories. Reglas:

1. **Solo funcionalidad del MoSCoW** — priorizar Must Have. Should Have se incluye con tag `[SHOULD]`. Could Have se incluye con tag `[COULD]`. Won't Have NO se incluye.
2. **Actor correcto** — usar los actores definidos en el PRD: `usuario freelancer/solopreneur`, `sistema PPAI`, `operador/admin`.
3. **JTBD como norte** — cada story debe contribuir a resolver el JTBD principal.
4. **Sin inventar funcionalidad** — si el PRD es ambiguo, marcar con `[TBD]` y anotar la pregunta al final del backlog.
5. **Principios no negociables** — toda story que involucre comunicación con el usuario DEBE incluir un AC de tono no acusatorio.

### PASO 5 — Escribir ACs para cada story

Cada story debe tener mínimo 2 y máximo 5 ACs. Reglas para los ACs:

- Escribir en formato: verificable, concreto, sin ambigüedad.
- Usar lenguaje de negocio (español), no lenguaje técnico en los ACs.
- Incluir al menos 1 AC de **happy path** y 1 AC de **edge case o validación**.
- Si la story involucra guardrails, incluir AC de verificación de tono.
- Formato de AC: checklist Markdown `- [ ] AC: {descripción concreta y verificable}`.

### PASO 6 — Asignar prioridad y etiquetas

Para cada story, asignar:

| Campo | Valores posibles |
|-------|-----------------|
| `Prioridad` | `P1-crítico`, `P2-importante`, `P3-deseable` |
| `MoSCoW` | `MUST`, `SHOULD`, `COULD` |
| `Épica` | ID de la épica (E1–E7) |
| `Módulo DB` | tabla SQLite relacionada (si aplica) |

Regla de prioridad:
- `P1-crítico` → Must Have + impacta NSM o guardrail
- `P2-importante` → Must Have sin impacto directo en NSM, o Should Have crítico
- `P3-deseable` → Should Have / Could Have

### PASO 7 — Escribir el archivo backlog.md

Usar exactamente la estructura definida a continuación.

---

## Formato de output: `specs/backlog.md`

```markdown
# Backlog — PPAI (Personal Productivity AI)

Generado desde: `specs/prd.md` v1.0
Fecha de generación: {FECHA}
Estado: Draft v1.0

> Convenciones:
> - Idioma: español para negocio, inglés para nombres técnicos y código
> - Prioridad: P1-crítico · P2-importante · P3-deseable
> - Tags: [MUST] [SHOULD] [COULD] [TBD]

---

## Índice de épicas

| ID | Épica | Stories | Prioridad |
|----|-------|---------|-----------|
| E1 | Captura y Normalización | S1.1 · S1.2 · ... | P1 |
| E2 | Motor de Priorización y Decisión | S2.1 · S2.2 · ... | P1 |
| ...| ... | ... | ... |

---

## E1 — Captura y Normalización

> Descripción: {descripción breve de la épica extraída del PRD}

### S1.1 — {Nombre de la Story}

**Como** {tipo de usuario}
**Quiero** {acción concreta}
**Para** {beneficio medible o resultado esperado}

**MoSCoW:** [MUST]
**Prioridad:** P1-crítico
**Módulo DB:** `tasks`

**Acceptance Criteria:**
- [ ] AC: {descripción verificable — happy path}
- [ ] AC: {descripción verificable — edge case o validación}
- [ ] AC: {descripción verificable — tono no acusatorio si aplica}

---

{repetir para cada story de la épica}

---

## E2 — Motor de Priorización y Decisión

{repetir estructura...}

---

## Preguntas abiertas [TBD]

> Anotar aquí todas las ambigüedades encontradas durante la generación.

| # | Story | Pregunta | Opciones sugeridas |
|---|-------|----------|--------------------|
| 1 | S{n}.{m} | {pregunta} | A) ... · B) ... · C) ... |
```

---

## Restricciones críticas

| ❌ Prohibido | ✅ Permitido |
|-------------|-------------|
| Inventar features fuera del PRD | Interpretar features ambiguos con `[TBD]` |
| Modificar `specs/prd.md` | Solo leer el PRD |
| Generar stories para Won't Have | Solo Must/Should/Could Have |
| Usar lenguaje acusatorio en ACs | Tono neutro y empático siempre |
| Ignorar principios de diseño del PRD | Incluir AC de tono cuando aplica |
| Omitir el índice de épicas | El índice es obligatorio |

---

## Convenciones de naming a respetar

| Contexto | Idioma | Ejemplo |
|----------|--------|---------|
| Nombres de stories y épicas | Español | "Captura de tarea en lenguaje natural" |
| Nombres técnicos en metadatos | Inglés | `tasks`, `execution_cycles` |
| ACs (acceptance criteria) | Español | "El usuario recibe confirmación en menos de 2s" |
| Tags de prioridad y MoSCoW | Inglés | `[MUST]`, `P1-crítico` |
| Nombres de módulos de código | Inglés | `task-classifier`, `nudge-orchestrator` |

---

## DDD — Vocabulario del dominio

Usar estos términos consistentemente en todo el backlog:

| Término de negocio (español) | En código (inglés) | Tabla SQLite |
|------------------------------|--------------------|--------------|
| Tarea | `Task` | `tasks` |
| Ciclo de Ejecución | `ExecutionCycle` | `execution_cycles` |
| Patrón de Bloqueo | `BlockingPattern` | `blocking_patterns` |
| Nudge Proactivo | `Nudge` | columna en `execution_cycles` |
| Reporte Nocturno | `DailyReport` | `daily_reports` |
| Perfil de Energía | `EnergyProfile` | `energy_profiles` |
| Estado del Loop | `LoopStatus` | campo `status` en `tasks` |

---

## Verificación de calidad antes de finalizar

Antes de guardar `specs/backlog.md`, verificar cada punto:

- [ ] El índice de épicas lista TODAS las épicas (E1–E7)
- [ ] Cada épica tiene al menos 2 stories
- [ ] Cada story tiene al menos 2 ACs verificables
- [ ] No hay funcionalidad inventada fuera del PRD
- [ ] Todas las stories de Must Have están presentes
- [ ] Los Won't Have del PRD NO aparecen como stories
- [ ] Las ambigüedades están en la sección `[TBD]` con opciones sugeridas
- [ ] El naming de tablas/módulos sigue las convenciones (inglés snake_case)
- [ ] Los ACs usan lenguaje de negocio (español), no lenguaje técnico
- [ ] Las stories que tocan comunicación con usuario tienen AC de tono

---

## Output esperado

Un único archivo: `specs/backlog.md`

Ubicación: raíz del directorio `specs/` (junto a `prd.md`)

El archivo debe poder ser leído directamente por el **Sub-Agente 2 (Quality Agent)** para generar escenarios BDD story por story.
