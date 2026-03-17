# Estructura Completa del Proyecto PPAI

> Mapa de navegación para humanos y agentes AI. Cubre los dos repositorios activos:
> `ppai/` (producto) y `ppai-ssd-aidlc/` (metodología de desarrollo).

---

## Contexto general

El proyecto se organiza en dos capas complementarias:

| Capa | Carpeta | Propósito |
|------|---------|-----------|
| **Producto** | `ppai/` | Toda la estrategia, research, specs y código de PPAI |
| **Metodología** | `ppai-ssd-aidlc/` | AI Development Lifecycle (AIDLC) que guía cómo se construye |

PPAI es un agente conversacional de productividad personal (Telegram-first) que opera un loop continuo: `CAPTURE → DECIDE → EXECUTE → CONFIRM/UPDATE → LEARN`. El moat del producto es el **Data Behavioral Moat**: el estado acumulado de patrones de comportamiento del usuario, que ningún competidor puede replicar desde cero.

---

## 1. Repositorio `ppai/` — El producto

```text
ppai/
│
│  ── Archivos raíz ──
├── README.md                         ← Vista general, loop central y roadmap de canales
├── AGENTS.md                         ← Reglas de trabajo para agentes AI dentro del repo
├── estructura.md                     ← Mapa del repositorio (versión anterior)
├── estructura-completa.md            ← Este archivo
├── ai-product-base.md                ← Framework: paradigma AI, moats, trampas y lenses
├── prompts-especificacion.md         ← Metodología de co-creación (3 prompts secuenciales)
│
│  ── Archivos ocultos (no editar a mano) ──
├── .git/                             ← Control de versiones Git
├── .gitignore                        ← Excluye DB locales, credenciales, .DS_Store
├── .claude/                          ← Config local del agente Claude (mcp.json excluido de git)
├── .skills/                          ← Skills del agente AI para este repo
│   └── skills/
│       ├── changelog/SKILL.md        ← Skill para generar changelogs
│       ├── prd-to-backlog/SKILL.md   ← Skill: convierte PRD en backlog de ingeniería
│       └── story-to-bdd/SKILL.md     ← Skill: convierte user stories en escenarios BDD
│
├── docs/                             ← Inputs estratégicos y research
│   ├── 00_contexto/
│   │   ├── 00_resumen_idea.md        ← Idea central, workflow loop, moat, MVP y riesgos
│   │   ├── 01_supuestos_y_riesgos.md ← Supuestos críticos SC1–SC5 y condiciones go/no-go
│   │   └── guia-mcp-skills-dummies.md ← Material complementario: cómo funcionan MCP y skills
│   │
│   ├── 01_research/
│   │   ├── 01_deep_research_pro.md   ← Tesis: por qué PPAI puede funcionar
│   │   ├── 02_deep_research_con.md   ← Red team: objeciones, riesgos y kill criteria
│   │   ├── 05_sintesis_y_decision.md ← Integración PRO/CON y decisión provisional GO/NO-GO
│   │   ├── template_pro.md           ← Plantilla reutilizable para análisis PRO
│   │   └── template_con.md           ← Plantilla reutilizable para análisis CON
│   │
│   ├── 02_usuarios/                  ← ⚠️ VACÍO — pendiente de entrevistas con ICP
│   │
│   └── 03_producto/
│       └── 01_product_vision_board.md ← Vision board + AI product canvas completo
│
├── specs/                            ← Outputs de especificación generados
│   ├── prd.md                        ← PRD consolidado v1.0 (13 segmentos) ✅
│   └── backlog.md                    ← Backlog draft generado desde el PRD ⏳
│
├── agents/                           ← Sub-agentes especializados
│   ├── specification-agent.md        ← Convierte specs/prd.md en specs/backlog.md
│   └── quality-agent.md              ← Convierte stories en escenarios BDD/tests
│
├── db/                               ← Base de datos local y bootstrap
│   ├── schema.sql                    ← Esquema SQLite del sistema
│   └── init_db.py                    ← Script para inicializar la base local
│
├── ppai.db                           ← Base SQLite local (excluida de git)
├── ppai.db-shm                       ← Archivo auxiliar SQLite — shared memory (excluido)
└── ppai.db-wal                       ← Archivo auxiliar SQLite — write-ahead log (excluido)
```

### Estado actual de artefactos — `ppai/`

| Artefacto | Estado | Descripción |
|-----------|--------|-------------|
| `docs/00_contexto/00_resumen_idea.md` | ✅ v2.0 | Workflow-first, loop central, moat, riesgos |
| `docs/00_contexto/01_supuestos_y_riesgos.md` | ✅ | Supuestos críticos SC1–SC5 |
| `docs/01_research/01_deep_research_pro.md` | ✅ | Análisis PRO |
| `docs/01_research/02_deep_research_con.md` | ✅ | Red team CON |
| `docs/01_research/05_sintesis_y_decision.md` | ✅ | Síntesis GO/NO-GO |
| `docs/02_usuarios/` | ⚠️ Vacío | Requiere entrevistas con usuarios reales |
| `docs/03_producto/01_product_vision_board.md` | ✅ v2.0 | AI product canvas completo |
| `specs/prd.md` | ✅ v1.0 | PRD consolidado, 13 segmentos aprobados |
| `specs/arquitectura.md` | ⏳ No existe | Requiere ejecutar Prompt 2 |
| `specs/backlog.md` | ⏳ Draft | Generado, pendiente de refinamiento |
| `db/schema.sql` + `db/init_db.py` | ✅ | Capa técnica operativa inicial |

---

## 2. Repositorio `ppai-ssd-aidlc/` — La metodología

Este repositorio contiene el **AI Development Lifecycle (AIDLC)**: el workflow adaptativo que gobierna cómo se construye cualquier software con AI. El `CLAUDE.md` de esta carpeta indica que cualquier agente que opere aquí debe seguir `AI_DLC_WORKFLOW.md`.

```text
ppai-ssd-aidlc/
│
│  ── Archivos raíz ──
├── CLAUDE.md                         ← Instrucción principal: "Follow AI_DLC_WORKFLOW.md"
├── AGENTS.md                         ← Reglas para agentes AI en este repo
├── AI_DLC_WORKFLOW.md                ← Workflow maestro: fases, etapas y reglas de ejecución
├── ppai-prd.md                       ← PRD del producto PPAI (copia de referencia)
│
├── .aidlc-rule-details/              ← Reglas detalladas por fase (AIDLC internals)
│   ├── common/                       ← Reglas transversales (siempre se cargan)
│   │   ├── ascii-diagram-standards.md
│   │   ├── content-validation.md
│   │   ├── depth-levels.md
│   │   ├── error-handling.md
│   │   ├── overconfidence-prevention.md
│   │   ├── process-overview.md
│   │   ├── question-format-guide.md
│   │   ├── session-continuity.md
│   │   ├── terminology.md
│   │   ├── welcome-message.md
│   │   └── workflow-changes.md
│   │
│   ├── inception/                    ← Reglas de la fase de Inception
│   │   ├── application-design.md
│   │   ├── requirements-analysis.md
│   │   ├── reverse-engineering.md
│   │   ├── units-generation.md
│   │   ├── user-stories.md
│   │   ├── workflow-planning.md
│   │   └── workspace-detection.md
│   │
│   ├── construction/                 ← Reglas de la fase de Construction
│   │   ├── build-and-test.md
│   │   ├── code-generation.md
│   │   ├── functional-design.md
│   │   ├── infrastructure-design.md
│   │   ├── nfr-design.md
│   │   └── nfr-requirements.md
│   │
│   ├── operations/
│   │   └── operations.md             ← Placeholder para fase futura de Operations
│   │
│   └── extensions/                   ← Restricciones transversales (hard constraints)
│       └── security/
│           ├── baseline/
│           │   └── security-baseline.md ← Baseline de seguridad siempre aplicado
│           └── compliance/
│               ├── hipaa/            ← (vacío — placeholder)
│               ├── pci-dss/          ← (vacío — placeholder)
│               └── soc2/             ← (vacío — placeholder)
│
└── aidlc-docs/                       ← Artefactos generados por el AIDLC para PPAI
    ├── aidlc-state.md                ← Estado actual del workflow (qué fases están completas)
    ├── audit.md                      ← Log completo de todas las interacciones (raw input)
    │
    ├── inception/                    ← Artefactos de la fase Inception
    │   ├── plans/
    │   │   ├── application-design-plan.md
    │   │   ├── execution-plan.md
    │   │   ├── story-generation-plan.md
    │   │   ├── unit-of-work-plan.md
    │   │   └── user-stories-assessment.md
    │   ├── requirements/
    │   │   ├── requirement-verification-questions.md
    │   │   └── requirements.md
    │   ├── user-stories/
    │   │   ├── personas.md
    │   │   └── stories.md
    │   └── application-design/
    │       ├── component-dependency.md
    │       ├── component-methods.md
    │       ├── components.md
    │       ├── services.md
    │       ├── unit-of-work-dependency.md
    │       ├── unit-of-work-story-map.md
    │       └── unit-of-work.md
    │
    └── construction/                 ← Artefactos de la fase Construction
        ├── plans/
        │   ├── capture-foundation-code-generation-plan.md
        │   ├── capture-foundation-functional-design-plan.md
        │   ├── capture-foundation-infrastructure-design-plan.md
        │   ├── capture-foundation-nfr-design-plan.md
        │   └── capture-foundation-nfr-requirements-plan.md
        └── capture-foundation/
            ├── functional-design/
            │   ├── business-logic-model.md
            │   ├── business-rules.md
            │   └── domain-entities.md
            ├── nfr-requirements/
            │   ├── nfr-requirements-questions.md
            │   ├── nfr-requirements.md
            │   └── tech-stack-decisions.md
            ├── nfr-design/
            │   ├── logical-components.md
            │   ├── nfr-design-patterns.md
            │   └── nfr-design-questions.md
            └── infrastructure-design/
                ├── deployment-architecture.md
                ├── infrastructure-design-questions.md
                └── infrastructure-design.md
```

---

## 3. Cómo se relacionan ambos repositorios

```
ppai-ssd-aidlc/                    ppai/
AI_DLC_WORKFLOW.md  ──governa──►  specs/prd.md
                                   specs/backlog.md
                                   specs/arquitectura.md (pendiente)

aidlc-docs/        ──produce──►   (artefactos intermedios de diseño)
  inception/                       docs/ (inputs estratégicos)
  construction/                    db/ (capa técnica)
```

El flujo de trabajo completo sigue estas fases del AIDLC:

**INCEPTION** → Workspace Detection → Requirements Analysis → User Stories → Workflow Planning → Application Design → Units Generation

**CONSTRUCTION** → (por cada unidad): Functional Design → NFR Requirements → NFR Design → Infrastructure Design → Code Generation → Build and Test

**OPERATIONS** → (placeholder, expansión futura)

---

## 4. Orden de lectura recomendado

Para entender el proyecto de principio a fin, seguir este orden:

**Capa 1 — Visión del producto**
- `ppai/ai-product-base.md` — framework para pensar productos agenticos
- `ppai/docs/00_contexto/00_resumen_idea.md` — qué es PPAI y por qué existe

**Capa 2 — Validación estratégica**
- `ppai/docs/01_research/01_deep_research_pro.md` — tesis
- `ppai/docs/01_research/02_deep_research_con.md` — red team
- `ppai/docs/01_research/05_sintesis_y_decision.md` — decisión GO/NO-GO

**Capa 3 — Especificación ejecutable**
- `ppai/specs/prd.md` — PRD completo (13 segmentos)
- `ppai/specs/backlog.md` — backlog de ingeniería

**Capa 4 — Diseño técnico (AIDLC)**
- `ppai-ssd-aidlc/aidlc-docs/aidlc-state.md` — estado del workflow
- `ppai-ssd-aidlc/aidlc-docs/inception/requirements/requirements.md`
- `ppai-ssd-aidlc/aidlc-docs/inception/application-design/components.md`
- `ppai-ssd-aidlc/aidlc-docs/construction/capture-foundation/`

**Capa 5 — Automatización**
- `ppai/agents/specification-agent.md`
- `ppai/agents/quality-agent.md`

**Capa 6 — Operativa local**
- `ppai/db/schema.sql`
- `ppai/db/init_db.py`

---

## 5. Vacíos y pendientes críticos

| Pendiente | Ubicación | Impacto |
|-----------|-----------|---------|
| Entrevistas con usuarios ICP | `ppai/docs/02_usuarios/` | Bloquea validación de KPIs reales |
| `specs/arquitectura.md` | `ppai/specs/` | Requiere Prompt 2 de prompts-especificacion.md |
| Code Generation (AIDLC) | `ppai-ssd-aidlc/aidlc-docs/construction/` | Siguiente fase del AIDLC |
| Compliance HIPAA / PCI-DSS / SOC2 | `ppai-ssd-aidlc/.aidlc-rule-details/extensions/security/compliance/` | Evaluación pendiente |

---

*Última actualización: 2026-03-16*
