# PPAI — Personal Productivity AI

> **Un sistema de workflow de productividad personal, no un generador de outputs.**

---

## ¿Qué es PPAI?

PPAI es un agente conversacional que opera un **loop de ejecución continua** para trabajadores autónomos (freelancers, developers solopreneurs) que saben qué hacer pero no logran arrancar.

La diferencia con cualquier otra herramienta de productividad: PPAI no te da un plan bonito y te deja solo. Opera el ciclo completo — captura la intención, decide la prioridad, empuja en el momento correcto, registra el resultado real y aprende del patrón de comportamiento con cada ciclo.

```
CAPTURE ──► DECIDE ──► EXECUTE ──► CONFIRM/UPDATE
   ▲                                     │
   │                                     ▼
NEXT TASK ◄────────────── LEARN ◄── REPORT
```

**Canal del MVP:** Telegram-first. Sin instalar nada, sin migrar tareas, sin dashboards.

**Por qué sobrevive a GPT-6:** El valor no está en la calidad del output — está en el estado acumulado. Cualquier LLM puede escribir un plan. Ningún LLM puede, por sí solo, saber que pospusiste la misma tarea tres martes seguidos y ajustar el nudge del miércoles en consecuencia.

---

## Workflow Loop — Comandos mínimos del MVP

| Acción | Comando / Botón | Qué registra |
|--------|----------------|-------------|
| Capturar tarea | Mensaje libre en Telegram | Intención + timestamp |
| Confirmar completado | `/done` · `[✓ Hecho]` | Hora real, energía final |
| Posponer | `/snooze` · `[⏸ Posponer]` | Razón de bloqueo (opcional) |
| Aclarar tarea ambigua | `/clarify` · `[? Aclarar]` | Reabre captura para refinar |

---

## Estructura del proyecto

```
ppai/
├── README.md                       ← Este archivo
├── AGENTS.md                       ← Instrucciones para agentes AI que trabajen en el repo
├── ai-product-base.md              ← Framework base: paradigma AI, moats, trampas, lenses
├── prompts-especificacion.md       ← Metodología de co-creación (3 prompts secuenciales)
├── estructura.md                   ← Mapa visual del repositorio
│
├── docs/                           ← Documentos de entrada y research
│   ├── 00_contexto/
│   │   ├── 00_resumen_idea.md      ← Qué es PPAI, workflow loop, moat, roadmap, riesgos
│   │   └── 01_supuestos_y_riesgos.md ← Supuestos críticos SC1–SC5 y condiciones de go/no-go
│   │
│   ├── 01_research/
│   │   ├── 01_deep_research_pro.md ← Tesis: por qué la idea puede funcionar
│   │   ├── 02_deep_research_con.md ← Red team: objeciones fuertes y criterios de fallo
│   │   ├── 05_sintesis_y_decision.md ← Integración PRO/CON + decisión provisional GO/NO-GO
│   │   ├── template_pro.md         ← Plantilla para análisis PRO
│   │   └── template_con.md         ← Plantilla para análisis CON (red team)
│   │
│   ├── 02_usuarios/                ← ⚠️ Pendiente: entrevistas, verbatims, ICP validado
│   │
│   └── 03_producto/
│       └── 01_product_vision_board.md ← Vision board + AI product canvas completo
│
└── specs/                          ← Especificaciones generadas (outputs de los prompts)
    ├── prd.md                      ← PRD completo v1.0 (13 segmentos) ✅
    ├── arquitectura.md             ← Arquitectura técnica (pendiente) ⏳
    └── backlog.md                  ← Backlog de ingeniería (pendiente) ⏳
```

---

## Estado del proyecto

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
| `specs/arquitectura.md` | ⏳ Pendiente | Requiere ejecutar Prompt 2 |
| `specs/backlog.md` | ⏳ Pendiente | Requiere ejecutar Prompt 3 |

---

## Cómo usar este repositorio

Este proyecto sigue una **metodología de co-creación iterativa** con AI definida en `prompts-especificacion.md`. Los documentos de `docs/` son los inputs; los de `specs/` son los outputs.

### Paso 1 — Leer el contexto base

Empieza por estos dos documentos en orden:

1. `ai-product-base.md` — el framework completo: paradigma AI, moats, trampas mortales, lenses estratégicos.
2. `docs/00_contexto/00_resumen_idea.md` — qué es PPAI, el workflow loop y el moat primario.

### Paso 2 — Revisar el research

Los tres documentos de `docs/01_research/` forman el análisis estratégico base:

- `01_deep_research_pro.md` — la tesis de por qué puede funcionar.
- `02_deep_research_con.md` — el red team que busca razones para fallar.
- `05_sintesis_y_decision.md` — la decisión provisional con condiciones GO/NO-GO.

### Paso 3 — Revisar las specs generadas

- `specs/prd.md` — el PRD completo. Contiene el one-liner, JTBD, ICP, UVP, casos de uso, MoSCoW, métricas, riesgos y plan 30/60/90.

### Paso 4 — Generar las specs pendientes

Usar los Prompts 2 y 3 de `prompts-especificacion.md` adjuntando todos los docs de `docs/` para generar:

- `specs/arquitectura.md` — arquitectura técnica del agente.
- `specs/backlog.md` — backlog de ingeniería priorizado.

### Paso 5 — Completar `docs/02_usuarios/`

Antes de construir, ejecutar al menos 5 entrevistas con el ICP primario y depositar los resultados aquí. Los baselines reales de KPIs dependen de este paso.

---

## Moat primario — Data Behavioral Moat

Cada ciclo del loop genera datos propietarios que ningún competidor que empiece mañana puede comprar:

| Dato | Cómo se genera |
|------|----------------|
| Tasa de confirmación por tipo de tarea | `/done` vs ausencia de respuesta |
| Razón de posposición | Respuesta libre al `/snooze` |
| Hora real de ejecución vs hora sugerida | Timestamp del `/done` |
| Energía reportada al completar | Escala 1-3 al cerrar tarea |
| Latencia de respuesta al nudge | Tiempo entre nudge y acción |

---

## Trust Guardrails — no negociables

- El sistema **nunca usa** lenguaje acusatorio: "fallaste", "no cumpliste", "otra vez", "deberías".
- Si el usuario expresa culpa, el sistema **reduce intensidad** del siguiente nudge.
- El reporte nocturno usa **hipótesis curiosas**, no evaluaciones de desempeño.
- PPAI **no es terapia**, no trata condiciones de salud mental, no hace promesas de resultado.

---

## Roadmap de canales

| Fase | Canal | Condición |
|------|-------|-----------|
| **MVP (ahora)** | Telegram Bot | — |
| **Fase 2** | CLI (`ppai add`, `ppai now`, `ppai done`) | ≥ 2/3 usuarios activos al D5 **y** ≥ 60% reporte útil |
| **Fase 3** | API Web (webhooks, integraciones) | A definir según señales de Fase 2 |
