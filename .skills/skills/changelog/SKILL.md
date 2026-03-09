# Skill: changelog

**Versión:** 1.0
**Proyecto:** PPAI (Personal Productivity AI)
**Autor:** Co-creado Angel Mondragon + Claude
**Última actualización:** 2026-03-09

---

## Propósito

Este Skill analiza el historial de commits y Pull Requests del repositorio para generar o actualizar `CHANGELOG.md` con entradas estructuradas por versión y categoría.

El changelog es el registro público de evolución del producto: qué cambió, por qué, y en qué versión. Útil para el equipo, para el demo, y para auditar decisiones.

---

## Cuándo usar este Skill

Activar cuando:
- Se va a cerrar un sprint o milestone y se necesita documentar qué se hizo.
- Se lanza una nueva versión del MVP (v0.1, v0.2…).
- El `CHANGELOG.md` no existe o está desactualizado.
- Se quiere un resumen de cambios para compartir con usuarios o stakeholders.

---

## Pre-requisitos

| Recurso | Cómo acceder |
|---------|-------------|
| Historial de commits | MCP GitHub (`list_commits`) o `git log` por Filesystem MCP |
| Pull Requests cerrados | MCP GitHub (`list_pull_requests` con `state=closed`) |
| `CHANGELOG.md` actual | Filesystem MCP — si no existe, se crea desde cero |
| `AGENTS.md` | Para leer la versión actual del proyecto |

Si el MCP de GitHub no está disponible, usar `git log --oneline --no-merges` vía Filesystem MCP como fallback.

---

## Instrucciones de ejecución (paso a paso)

### PASO 1 — Determinar el rango de cambios

Antes de generar nada, clarificar el rango:

**Opción A — Desde el último tag:**
Buscar el tag más reciente con `git tag --sort=-version:refname | head -1`.
Tomar todos los commits desde ese tag hasta `HEAD`.

**Opción B — Rango manual:**
Si el usuario especifica un rango (ej. "los últimos 10 commits" o "desde el 2026-03-01"), usar ese rango.

**Opción C — Todo el historial (primera vez):**
Si `CHANGELOG.md` no existe, tomar todos los commits del repositorio.

Documentar el rango usado al inicio del proceso.

### PASO 2 — Recopilar commits y PRs

**Via MCP GitHub (preferido):**
1. Listar commits del rango con autor, fecha, mensaje completo.
2. Listar PRs cerrados en el período con título, descripción y labels.

**Via git log (fallback):**
```
git log {desde}..HEAD --pretty=format:"%h|%ad|%an|%s" --date=short --no-merges
```

Construir internamente una lista de cambios con:
- Hash corto
- Fecha
- Autor
- Mensaje del commit / título del PR
- Labels del PR (si aplica)

### PASO 3 — Clasificar los cambios

Asignar cada commit/PR a UNA de estas categorías usando el mensaje como señal:

| Categoría | Señales en el mensaje | Emoji |
|-----------|----------------------|-------|
| `Added` | feat, add, nuevo, agrega, implementa, crea | ✨ |
| `Changed` | refactor, update, mejora, modifica, cambia | 🔄 |
| `Fixed` | fix, bug, error, corrige, resuelve, patch | 🐛 |
| `Removed` | remove, delete, elimina, borra, deprecate | 🗑️ |
| `Security` | security, token, auth, guardrail, sanitize | 🔒 |
| `Docs` | docs, readme, changelog, skill, agents | 📝 |
| `Infra` | config, mcp, db, schema, setup, ci, gitignore | ⚙️ |
| `Performance` | perf, optimize, cache, speed, costo LLM | ⚡ |

Si un commit no encaja en ninguna categoría, usar `Changed` como fallback.

Omitir commits triviales:
- Merges automáticos sin contenido propio (`Merge branch...`)
- Commits de solo whitespace o typos menores sin impacto funcional

### PASO 4 — Determinar la versión

Si ya existe `CHANGELOG.md`:
- Leer la versión más reciente registrada.
- Proponer la siguiente versión usando **Semver**:
  - Cambios que rompen compatibilidad → mayor (1.0.0 → 2.0.0)
  - Features nuevas → minor (0.1.0 → 0.2.0)
  - Solo fixes/docs/infra → patch (0.1.0 → 0.1.1)
- Mostrar la propuesta al usuario antes de escribir.

Si NO existe `CHANGELOG.md`:
- Usar `v0.1.0` como versión inicial.
- Indicar al usuario que puede ajustarla.

### PASO 5 — Escribir la entrada del changelog

Agregar la nueva entrada al **tope** del archivo `CHANGELOG.md` (las versiones más recientes van primero).

Si el archivo no existe, crearlo completo con header y primera entrada.

### PASO 6 — Verificar el resultado

Antes de finalizar, confirmar:
- [ ] La versión nueva es mayor que la anterior
- [ ] Todas las categorías usadas tienen al menos 1 ítem
- [ ] No hay commits duplicados
- [ ] El formato Keep a Changelog es correcto (fechas ISO, links si aplica)
- [ ] Los items están en español de negocio (no mensajes crudos de commit)

---

## Formato de output: `CHANGELOG.md`

Seguir el estándar [Keep a Changelog](https://keepachangelog.com/es/1.0.0/) con adaptaciones para PPAI:

```markdown
# Changelog — PPAI (Personal Productivity AI)

Formato: [Keep a Changelog](https://keepachangelog.com/es/1.0.0/)
Versionado: [Semantic Versioning](https://semver.org/)

---

## [Unreleased]

> Cambios en progreso que aún no tienen versión asignada.

---

## [v0.2.0] — 2026-03-09

### ✨ Added
- Skill `prd-to-backlog`: convierte el PRD en backlog estructurado con épicas y stories.
- Skill `story-to-bdd`: genera escenarios Gherkin y skeleton de tests desde una story.
- Skill `changelog`: genera y actualiza CHANGELOG.md desde historial de commits.

### ⚙️ Infra
- MCPs configurados: `filesystem`, `github`, `sqlite` (3/3 operativos).
- Schema SQLite con 6 tablas del data moat (`tasks`, `execution_cycles`, etc.).
- `.gitignore` protege `mcp.json` y credenciales.

### 📝 Docs
- `AGENTS.md` reescrito como contrato del repositorio (model-agnostic).
- `README.md` creado con estructura del proyecto y workflow loop.
- `docs/00_contexto/guia-mcp-skills-dummies.md` — guía para principiantes.

---

## [v0.1.0] — 2026-{MES}-{DIA}

### ✨ Added
- PRD v1.0 consolidado (`specs/prd.md`).
- Product Vision Board v2.0 (`docs/03_producto/01_product_vision_board.md`).
- Resumen idea v2.0 workflow-first (`docs/00_contexto/00_resumen_idea.md`).

---

[Unreleased]: https://github.com/amondrave/PPAI-Agent/compare/v0.2.0...HEAD
[v0.2.0]: https://github.com/amondrave/PPAI-Agent/compare/v0.1.0...v0.2.0
[v0.1.0]: https://github.com/amondrave/PPAI-Agent/releases/tag/v0.1.0
```

---

## Reglas de escritura de items

Cada ítem del changelog debe:

1. **Empezar con verbo en pasado** en español: "Agregado", "Corregido", "Eliminado"… o en infinitivo si es más natural: "Agregar soporte para…"
2. **Describir el impacto de negocio**, no el detalle técnico:
   - ❌ `fix: null pointer exception in task_classifier.py line 42`
   - ✅ `Corregido error que impedía clasificar tareas con texto vacío`
3. **Referenciar el ID de story o PR** si está disponible: `(S1.1)`, `(#12)`
4. **Máximo 1 línea por ítem** — si necesita más, agregar como sub-ítem con `-` indentado
5. **Sin mensajes crudos de commit** — siempre reescribir en lenguaje de producto

---

## Restricciones críticas

| ❌ Prohibido | ✅ Permitido |
|-------------|-------------|
| Copiar mensajes crudos de commit como items | Reescribir en lenguaje de producto |
| Incluir merges automáticos | Solo commits con contenido real |
| Bajar la versión respecto a la anterior | Semver siempre ascendente |
| Modificar entradas de versiones ya publicadas | Solo agregar entradas nuevas al tope |
| Inventar cambios que no están en el historial | Solo lo que está en commits/PRs |
| Usar inglés en los items del changelog | Español en los items (nombres técnicos en código sí) |

---

## Fallback sin MCP GitHub

Si el MCP de GitHub no está disponible, usar:

```bash
git log --oneline --no-merges --since="2026-03-01" --pretty=format:"%h %ad %s" --date=short
```

Ejecutar vía Filesystem MCP o terminal. El resultado puede ser menos detallado pero funcional.

---

## Output final al usuario

Al terminar, reportar:

```
✅ CHANGELOG.md actualizado

Nueva versión registrada: v{X.Y.Z} — {fecha}
Commits procesados: {N}
Categorías incluidas: Added ({n}) · Fixed ({n}) · Docs ({n}) · Infra ({n})
Commits omitidos (triviales): {n}

Archivo: CHANGELOG.md
```
