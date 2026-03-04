# AGENTS.md

This file provides guidance to Claude Code (claude.ai/code) and ChatGPT (chatGPT/Codex) when working with code in this repository.

## Project Overview

EntreVista AI is a **product specification project** (not a software codebase) for a Latin American SaaS platform that uses agentic AI to conduct screening interviews via Telegram with human-in-the-loop oversight.

**Target Market:** High-volume hiring companies (BPO, retail) and mid-market tech/SaaS firms in LATAM
**Core Value:** Agentic AI conducts dynamic screening interviews → generates structured evidence → human recruiter makes final decision

## Repository Structure

```

├── docs/       # Input: research and analysis documents
│   ├── 00_contexto/
│   │   ├── 00_resumen_idea.md  ← Document describing the core idea of the project
│   │   └── 01_supuestos_y_riesgos.md ← Document outlining the assumptions and risks being considered for the project    
│   │
│   ├── 01_research/
│   │   ├── 01_deep_research_pro.md ← Argue why the idea could work (thesis, market signals, and potential segments).
│   │   ├── 02_deep_research_con.md ← Red team analysis of the idea (strong objections, risks, and failure criteria).
│   │   ├── 05_sintesis_y_decision.md ← Integrate PRO/CON findings and define a provisional decision with GO/NO-GO conditions.
│   │   ├── template_pro.md
│   │   └── template_con.md
│   │
│   ├── 02_usuarios/            ← (content pending)
│   │
│   └── 03_producto/
│       └── 01_product_vision_board.md ← Consolidate the product vision, target audience, needs, and MVP design into an executive artifact.

specs/          # Output: generated product specifications
  prd.md        # Complete Product Requirements Document (v1.0)

prompts-especificacion.md  # Co-creation methodology (three sequential prompts)
```

## Co-Creation Methodology

This project uses iterative co-creation with Claude AI as defined in `prompts-especificacion.md`. Follow these principles:

1. **Analyze conflicts first** - Review input documents for contradictions before generating
2. **Segment-by-segment production** - Produce one section, pause, wait for approval
3. **Document rationale** - Explain decisions and cite source documents
4. **No data invention** - Use "TBD" when information is missing; propose 2-3 reasonable options
5. **Human-in-the-loop** - User reviews and approves each segment before proceeding

## Specification Prompts

Three prompts are available in `prompts-especificacion.md`:

| Prompt | Purpose | Output |
|--------|---------|--------|
| Prompt 1 (PRD) | Product requirements | `specs/prd.md` ✅ Complete |
| Prompt 2 (Arquitectura) | Technical architecture | `specs/arquitectura.md` (pending) |
| Prompt 3 (Backlog) | Engineering backlog | `specs/backlog.md` (pending) |

## Current Status

- **PRD:** Complete (v1.0, all 13 segments approved)
- **Architecture:** Not yet created
- **Backlog:** Not yet created
- **Source Code:** None (specification phase only)

## Key Design Principles (Non-Negotiable)

1. **HITL Explicit** - AI recommends, human decides. No auto-reject/auto-advance.
2. **Transparency** - Candidates always know they talk to AI. Consent required.
3. **Auditable** - Every score linked to transcript quote. No black box.
4. **Anti-Hallucination** - Confined to knowledge base. Escalates unknowns.
5. **Privacy** - No biometrics, no emotion recognition, data purge policy.

## Agent Behavior Rules

When generating documents in this repository:

1. Do not invent data or market numbers.
2. If information is missing, write **TBD** and suggest 2–3 possible options.
3. Always reference source documents in `docs/` when making claims.
4. Prefer structured tables and bullet points over long prose.
5. Keep sections concise and decision-oriented.
6. Stop after completing the requested segment and wait for user approval.

## Language

All documentation is in **Spanish** (targeting LATAM market).