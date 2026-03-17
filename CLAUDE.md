Follow AI_DLC_WORKFLOW.md
PRD source: specs/prd.md

## Configuración del entorno

**MCPs** — configurados en `.mcp.json` (raíz del proyecto):
- `filesystem` — lectura/escritura de archivos del repo
- `github` — issues y PRs en `amondrave/PPAI-Agent`
- `sqlite` — persistencia del workflow loop (`ppai.db`)
- `linear` — gestión de issues en Linear (`https://mcp.linear.app/mcp`)

**Skills** — disponibles en `.claude/skills/`:
- `prd-to-backlog` — convierte `specs/prd.md` en `specs/backlog.md`
- `story-to-bdd` — convierte stories en escenarios BDD + skeleton de tests
- `changelog` — genera `CHANGELOG.md` desde commits/PRs

**AIDLC** — workflow de desarrollo en `AI_DLC_WORKFLOW.md`:
- Reglas por fase: `.aidlc-rule-details/`
- Artefactos generados: `aidlc-docs/`
- Estado actual: `aidlc-docs/aidlc-state.md`
