# AGENTS.md — PPAI (Personal Productivity AI)

Este archivo es el contrato del repositorio para cualquier agente AI (Claude Code, Codex, ChatGPT,
Gemini, o cualquier modelo futuro). Si sos un agente trabajando en este repo, leé esto primero.

---

## Qué es este proyecto

PPAI es un sistema de **workflow loop de productividad personal** que opera en Telegram.
No es un generador de planes — es un conductor de ciclos de ejecución con estado persistente.

El loop central:
```
CAPTURE → DECIDE → EXECUTE → CONFIRM/UPDATE → LEARN → REPORT → (next cycle)
```

Comandos del MVP: `/done` · `/snooze` · `/clarify`
Canal del MVP: Telegram Bot (CLI es Fase 2)
Moat primario: Data behavioral (patrones de ejecución acumulados por usuario)

---

## Estructura del repositorio

```
ppai/
├── AGENTS.md                          ← este archivo (leelo primero)
├── README.md                          ← overview para humanos
├── ai-product-base.md                 ← framework AI: moats, lenses, trampas
├── prompts-especificacion.md          ← metodología de co-creación (3 prompts)
│
├── .claude/
│   └── mcp.json                       ← configuración de MCPs para Claude Code
│
├── docs/                              ← inputs: research y contexto
│   ├── 00_contexto/
│   │   ├── 00_resumen_idea.md         ← qué es PPAI, workflow loop, moat, roadmap
│   │   ├── 01_supuestos_y_riesgos.md  ← supuestos SC1–SC5 y condiciones GO/NO-GO
│   │   └── guia-mcp-skills-dummies.md ← guía de configuración MCP + Skills
│   │
│   ├── 01_research/
│   │   ├── 01_deep_research_pro.md    ← tesis: por qué puede funcionar
│   │   ├── 02_deep_research_con.md    ← red team: riesgos y criterios de fallo
│   │   ├── 05_sintesis_y_decision.md  ← síntesis GO/NO-GO
│   │   ├── template_pro.md
│   │   └── template_con.md
│   │
│   ├── 02_usuarios/                   ← ⚠️ pendiente: entrevistas con usuarios reales
│   │
│   └── 03_producto/
│       └── 01_product_vision_board.md ← AI product canvas completo
│
├── specs/                             ← outputs: especificaciones generadas
│   ├── prd.md                         ← PRD completo v1.0 ✅
│   ├── backlog.md                     ← backlog de épicas/stories ⏳ (pendiente)
│   └── arquitectura.md                ← arquitectura técnica ⏳ (pendiente)
│
└── tests/                             ← ⏳ pendiente: BDD scenarios + test skeletons
```

---

## Repositorio GitHub

- **URL:** https://github.com/amondrave/PPAI-Agent
- **Clone SSH:** `git@github.com:amondrave/PPAI-Agent.git`
- **Clone HTTPS:** `https://github.com/amondrave/PPAI-Agent.git`

---

## MCPs disponibles

Los MCPs amplían lo que el agente puede hacer. Están configurados en `.claude/mcp.json`
para Claude Code. Para otros modelos, usar las herramientas equivalentes del entorno.

> ⚠️ **Seguridad:** `.claude/mcp.json` está en `.gitignore` porque contiene credenciales.
> Usar `.claude/mcp.example.json` como plantilla para configurar el entorno local.

| MCP | Estado | Para qué se usa en PPAI |
|-----|--------|-------------------------|
| `filesystem` | ✅ Paso 2 | Leer/escribir archivos del repo (PRD → backlog, stories → tests) |
| `github` | ✅ Paso 3 | Crear issues desde stories, trackear PRs, listar commits — repo: `amondrave/PPAI-Agent` |
| `sqlite` | ✅ Paso 4 | Persistir estado del workflow loop — DB: `ppai.db` · Schema: `db/schema.sql` |

---

## Skills disponibles

Los Skills son instrucciones en markdown que cualquier modelo puede seguir.
Están en `.skills/skills/<nombre>/SKILL.md`.

| Skill | Estado | Qué hace |
|-------|--------|----------|
| `prd-to-backlog` | ✅ Paso 5 | Lee `specs/prd.md` → genera `specs/backlog.md` con épicas, stories y ACs |
| `story-to-bdd` | ✅ Paso 6 (draft JS → migrar a Python/behave) | Toma 1 story → genera escenarios BDD (Given/When/Then) + skeleton de tests |
| `changelog` | ✅ Paso 7 | Analiza commits/PRs → actualiza `CHANGELOG.md` |

---

## Sub-agentes definidos

> Los sub-agentes tienen sus propios archivos en `agents/`. Cada archivo es su prompt completo de activación.

### Sub-Agente 1: Specification Agent

**Archivo:** `agents/specification-agent.md`

**Propósito:** Transformar artefactos de especificación del producto.

**Cuándo activarlo:** Cuando el PRD se actualiza y hay que regenerar el backlog,
o cuando se necesita crear/actualizar `specs/backlog.md`.

**Input:** `specs/prd.md`
**Output:** `specs/backlog.md`

**Instrucciones:**
1. Leer `specs/prd.md` completo antes de generar nada.
2. Usar el Skill `prd-to-backlog` si está disponible.
3. Estructura del output: épicas numeradas → stories con formato estándar → ACs en lista.
4. No inventar funcionalidad que no esté en el PRD.
5. Si hay ambigüedad, marcá con `[TBD]` y anotá la pregunta al final del archivo.
6. Idioma: español (targeting LATAM).

**Formato de story:**
```
## E{n} — {Nombre de la Épica}

### S{n}.{m} — {Nombre de la Story}
**Como** {tipo de usuario}
**Quiero** {acción}
**Para** {beneficio}

**Acceptance Criteria:**
- [ ] AC1
- [ ] AC2
```

---

### Sub-Agente 2: Quality Agent

**Archivo:** `agents/quality-agent.md`

**Propósito:** Generar escenarios de calidad y tests para las stories del backlog.

**Cuándo activarlo:** Cuando una story del backlog está lista para ser implementada
y necesita tests BDD y skeleton de código de test.

**Input:** 1 story de `specs/backlog.md` (especificar ID: S{n}.{m})
**Output:** archivo en `tests/bdd/S{n}.{m}.feature` + `tests/unit/S{n}.{m}.test.js`

**Instrucciones:**
1. Leer la story completa incluyendo sus ACs.
2. Usar el Skill `story-to-bdd` si está disponible.
3. Generar escenarios BDD en formato Gherkin (Given/When/Then).
4. Generar 1 escenario por AC como mínimo.
5. Incluir al menos 1 escenario negativo (unhappy path).
6. El skeleton de test puede ser Jest o Pytest según el stack definido.
7. No implementar la lógica — solo el skeleton con `// TODO: implement`.
8. Idioma de los escenarios: español. Idioma del código: inglés.

**Formato de escenario BDD:**
```gherkin
Feature: {nombre del feature del PRD}

  Background:
    Given {contexto base que aplica a todos los scenarios}

  Scenario: {descripción del AC}
    Given {estado inicial}
    When {acción del usuario o sistema}
    Then {resultado esperado}
    And {condición adicional si aplica}
```

---

## Reglas para cualquier agente que trabaje en este repo

1. **No inventar datos.** Si falta información, escribir `[TBD]` y proponer 2-3 opciones.
2. **No tocar el PRD sin instrucción explícita.** Es el documento fuente de verdad.
3. **Citar fuente.** Si tomás una decisión basada en un doc, mencioná cuál.
4. **Idioma: español** para toda la documentación. Inglés para código y nombres técnicos.
5. **Trust guardrails.** Nunca generar mensajes con lenguaje acusatorio hacia el usuario.
6. **Scope discipline.** No agregar features fuera del MoSCoW del PRD sin aprobación.
7. **Un archivo a la vez.** Completar y verificar antes de pasar al siguiente.

---

## Estado actual del proyecto

| Fase | Estado |
|------|--------|
| PRD v1.0 | ✅ Completo |
| Product Vision Board v2.0 | ✅ Completo |
| Configuración MCPs | ✅ Completo (3/3 MCPs) |
| Skill prd-to-backlog | ✅ Completo |
| Skill story-to-bdd | ✅ Completo |
| Skill changelog | ✅ Completo |
| Sub-Agente 1: Specification Agent | ✅ Completo |
| Sub-Agente 2: Quality Agent | ✅ Completo |
| Backlog | ⏳ Pendiente (listo para generar — activar Specification Agent) |
| Arquitectura técnica | ⏳ Pendiente |
| Tests BDD skeleton | ⏳ Pendiente (requiere Skill story-to-bdd) |
| Implementación MVP | ⏳ Pendiente |

---

## Convenciones de naming — NO negociables

| Contexto | Idioma | Ejemplos |
|----------|--------|---------|
| Tablas SQL | inglés, snake_case | `tasks`, `execution_cycles`, `blocking_patterns` |
| Columnas SQL | inglés, snake_case | `user_id`, `energy_level`, `response_latency_sec` |
| Variables / funciones | inglés, camelCase o snake_case según lenguaje | `taskType`, `nudge_sent_at` |
| Clases / modelos | inglés, PascalCase | `Task`, `ExecutionCycle`, `BlockingPattern` |
| Archivos de código | inglés, kebab-case | `task-classifier.js`, `nudge-orchestrator.py` |
| Documentación / comentarios negocio | español | `-- tabla de patrones de bloqueo` |
| Escenarios BDD (Feature files) | español | `Scenario: Usuario captura una tarea` |

## Lenguaje del dominio (DDD)

El código habla el mismo idioma que el PRD, pero en inglés técnico:

| Término del negocio (español) | Nombre en código (inglés) | Tabla SQL |
|-------------------------------|--------------------------|-----------|
| Tarea | `Task` | `tasks` |
| Ciclo de Ejecución | `ExecutionCycle` | `execution_cycles` |
| Patrón de Bloqueo | `BlockingPattern` | `blocking_patterns` |
| Nudge Proactivo | `Nudge` | (columna en `execution_cycles`) |
| Reporte Nocturno | `DailyReport` | `daily_reports` |
| Perfil de Energía | `EnergyProfile` | `energy_profiles` |
| Estado del Loop | `LoopStatus` | (campo `status` en `tasks`) |
