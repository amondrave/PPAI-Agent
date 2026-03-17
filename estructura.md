# Estructura del Proyecto

Estado actual del repositorio: PPAI ya no es solo una carpeta de research. Hoy combina documentacion estrategica, especificaciones generadas, sub-agentes de trabajo y una capa operativa minima para datos locales.

```text
ppai/
│
│  ── Archivos ocultos (gestionados automaticamente, no editar a mano) ──
├── .git/                             ← Repositorio Git local (control de versiones)
├── .gitignore                        ← Excluye credenciales, DB locales, .DS_Store y node_modules
├── .claude/                          ← Configuracion local del agente Claude (ej: mcp.json excluido de git)
├── .skills/                          ← Skills instalados para uso del agente AI en este repo
│
│  ── Archivos raiz ──
├── README.md                         ← Vista general del proyecto, loop central y roadmap
├── AGENTS.md                         ← Reglas de trabajo para agentes AI dentro del repo
├── estructura.md                     ← Este mapa del repositorio
├── ai-product-base.md                ← Framework base para pensar productos agenticos
├── prompts-especificacion.md         ← Metodo de co-creacion para PRD, arquitectura y backlog
│
├── docs/                             ← Inputs estrategicos y research
│   ├── 00_contexto/
│   │   ├── 00_resumen_idea.md        ← Idea central, workflow loop, moat, MVP y riesgos
│   │   ├── 01_supuestos_y_riesgos.md ← Supuestos criticos y condiciones de validacion
│   │   └── guia-mcp-skills-dummies.md ← Material complementario de contexto operativo
│   │
│   ├── 01_research/
│   │   ├── 01_deep_research_pro.md   ← Tesis de por que PPAI podria funcionar
│   │   ├── 02_deep_research_con.md   ← Red team: objeciones, riesgos y kill criteria
│   │   ├── 05_sintesis_y_decision.md ← Integracion PRO/CON y decision metodologica
│   │   ├── template_pro.md           ← Plantilla reusable para research PRO
│   │   └── template_con.md           ← Plantilla reusable para research CON
│   │
│   ├── 02_usuarios/                  ← [CARPETA CREADA — pendiente de contenido]
│   │
│   └── 03_producto/
│       └── 01_product_vision_board.md ← Vision board consolidado del producto
│
├── specs/                            ← Outputs de especificacion
│   ├── prd.md                        ← PRD consolidado v1.0 con Paso 0 + Segmentos 1–13
│   └── backlog.md                    ← Backlog draft generado desde el PRD
│
├── agents/                           ← Sub-agentes especializados para producir artefactos
│   ├── specification-agent.md        ← Convierte `specs/prd.md` en `specs/backlog.md`
│   └── quality-agent.md              ← Convierte stories del backlog en escenarios BDD/tests
│
├── db/                               ← Base de datos local y bootstrap
│   ├── schema.sql                    ← Esquema SQLite del sistema
│   └── init_db.py                    ← Script para inicializar la base local
│
├── ppai.db                           ← Base SQLite local del proyecto (excluida de git)
├── ppai.db-shm                       ← Archivo auxiliar de SQLite — shared memory (excluida de git)
└── ppai.db-wal                       ← Archivo auxiliar de SQLite — write-ahead log (excluida de git)
```

## Lectura recomendada por capas

1. Base conceptual
   - `ai-product-base.md`
   - `docs/00_contexto/00_resumen_idea.md`

2. Validacion estrategica
   - `docs/01_research/01_deep_research_pro.md`
   - `docs/01_research/02_deep_research_con.md`
   - `docs/01_research/05_sintesis_y_decision.md`

3. Especificacion ejecutable
   - `specs/prd.md`
   - `specs/backlog.md`

4. Automatizacion del trabajo
   - `agents/specification-agent.md`
   - `agents/quality-agent.md`

5. Capa operativa
   - `db/schema.sql`
   - `db/init_db.py`
   - `ppai.db*`

## Vacios y pendientes visibles

- `docs/02_usuarios/` ya existe como carpeta, pero esta vacia — el PRD sigue marcando esa evidencia como critica y pendiente de poblarse.
- `specs/arquitectura.md` todavia no existe.
- Hay una capa de datos local (`db/` y `ppai.db`) que ya sugiere transicion desde pura especificacion hacia implementacion/prototipo.

## Archivos ocultos y su rol

| Archivo / Carpeta | Razon de existencia | Trackeado en git |
|---|---|---|
| `.git/` | Control de versiones del repo | No (es el repo mismo) |
| `.gitignore` | Define que NO sube a GitHub (DB, credenciales, `.DS_Store`) | Si |
| `.claude/` | Config local del agente AI — incluye `mcp.json` con credenciales | No (`mcp.json` excluido) |
| `.skills/` | Skills del agente instalados localmente para este proyecto | No (uso local) |

## Lectura rapida del estado del proyecto

- `docs/` define la tesis de producto y la validacion estrategica.
- `specs/` ya contiene el PRD consolidado y un backlog draft.
- `agents/` formaliza un flujo de trabajo por sub-agentes para seguir bajando especificacion a ejecucion.
- `db/` y `ppai.db` indican que el repositorio ya empezo a incorporar piezas tecnicas concretas.
