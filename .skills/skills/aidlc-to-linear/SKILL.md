# Skill: aidlc-to-linear

**Versión:** 1.3
**Proyecto:** PPAI
**Compatibilidad:** Cualquier modelo con acceso a filesystem + MCP Linear

---

## Propósito

Leer todos los archivos en `aidlc-docs/construction/`, agruparlos por el
identificador `UOW-XX` que aparece en el heading `#` de cada archivo,
y crear o actualizar issues en Linear por unidad de trabajo.

---

## Cuándo usar este Skill

- Al terminar el diseño de una unidad y querer registrar sus tareas en Linear.
- Al avanzar pasos de Code Generation y querer reflejar el progreso.
- Para sincronizar sin duplicar issues ya existentes.

**Input requerido:** nombre del proyecto en Linear (ej. `ppai-mcp`)
Si no se proporciona, preguntar antes de continuar.

---

## Pre-requisitos

| Recurso | Verificar antes de empezar |
|---------|---------------------------|
| MCP Linear activo | Hacer una query de prueba; si falla, detener y avisar al usuario |
| `aidlc-docs/construction/` | Debe existir y tener al menos un archivo `.md` |
| `aidlc-docs/aidlc-state.md` | Leer para saber qué fases están `[x]` completas |

---

## PASO 1 — Descubrir y agrupar archivos por UOW

1. Leer **todos** los archivos `.md` dentro de `aidlc-docs/construction/`
   de forma recursiva (incluyendo subcarpetas).

2. En cada archivo, leer la **primera línea que empiece con `# `** (heading H1).

3. Buscar el patrón `UOW-XX` dentro de ese heading.
   - Si lo encuentra → registrar ese archivo bajo ese `UOW-XX`.
   - Si no lo encuentra → ignorar ese archivo (no pertenece a ninguna unidad).

4. El nombre completo de la unidad viene del mismo heading:
   todo lo que sigue al guión después de `UOW-XX`.
   Ejemplo: `# Domain Entities — UOW-01 Capture Foundation`
   → ID: `UOW-01`, Nombre: `Capture Foundation`

5. Resultado esperado: un mapa `UOW-XX → lista de archivos`.

---

## PASO 2 — Leer el estado del AIDLC

Leer `aidlc-docs/aidlc-state.md`.

Registrar qué fases están `[x]` (completas) y cuáles `[ ]` (pendientes)
en la sección `### 🟢 CONSTRUCTION PHASE`.

---

## PASO 3 — Para cada UOW encontrado

Con la lista de archivos de ese UOW, identificar cuáles son útiles
buscando su nombre de archivo (no necesitas leer el contenido completo
para identificarlos — el nombre del archivo es suficiente):

| Si el filename contiene... | Usar para... |
|---|---|
| `domain-entities` | Entidades del dominio → cuerpo del Epic |
| `business-rules` | Reglas de negocio → ACs del Epic |
| `tech-stack-decisions` | Stack técnico → labels del issue |
| `code-generation-plan` | Checkboxes → sub-issues con estado |

Leer solo esos 4 archivos. Los demás son de contexto interno del AIDLC
y no necesitan procesarse para crear issues en Linear.

**Del archivo `code-generation-plan`**, extraer:
- Sección `## Unit Context` → Stories, Stack (para el cuerpo del Epic)
- Todos los checkboxes bajo `## Generation Steps`:
  - `- [ ] texto` → estado **Todo**
  - `- [x] texto` → estado **Done**
  - Agrupar por sección: `### Step 1`, `### Step 2`, etc.

**Del archivo `domain-entities`**, extraer:
- Cada `## Entity: Nombre` y su primer párrafo de descripción.

**Del archivo `business-rules`**, extraer:
- Cada `## BR-XXX: Nombre` y la línea `- **Rule**:` correspondiente.

**Del archivo `tech-stack-decisions`**, extraer:
- Los valores clave de la primera columna de cada tabla del documento.

---

## PASO 4 — Crear o actualizar en Linear

**4.1 — Verificar si el Epic ya existe:**

Buscar en el proyecto Linear un issue cuyo título contenga el ID `UOW-XX`.
- Si existe → modo actualización (paso 4.3).
- Si no existe → crear (paso 4.2).

**4.2 — Crear el Epic:**
```
Título:  [UOW-XX] {Nombre de la unidad}
         Ej: [UOW-01] Capture Foundation

Descripción:
## Entidades del dominio
{Nombre entidad — descripción 1 línea}
{...}

## Reglas de negocio
{BR-XXX — descripción 1 línea}
{...}

## Stack
{Tecnologías clave del tech-stack-decisions}

## Estado AIDLC
| Fase                  | Estado |
|-----------------------|--------|
| Functional Design     | ✅ / ⏳ |
| NFR Requirements      | ✅ / ⏳ |
| NFR Design            | ✅ / ⏳ |
| Infrastructure Design | ✅ / ⏳ |
| Code Generation       | ✅ / ⏳ |

Labels:    aidlc-unit
Priority:  UOW-01 → Urgent · UOW-02/03 → High · UOW-04+ → Medium
```

**4.3 — Crear sub-issues por cada checkbox del plan:**

Para cada checkbox de `## Generation Steps`:
```
Título:  [Step N] {texto exacto del checkbox}
Parent:  Epic creado en 4.2
Estado:  [ ] → Todo  |  [x] → Done
Labels:  step-N
```

**4.4 — Modo actualización (Epic ya existe):**

1. Releer checkboxes del `code-generation-plan`.
2. Para cada sub-issue existente cuyo checkbox ahora es `[x]`:
   - Cambiar estado a Done.
   - Agregar comentario: `Completado · {fecha ISO} · AIDLC Code Generation`
3. Actualizar la tabla `## Estado AIDLC` del Epic.

---

## PASO 5 — Reportar al usuario
```
✅ AIDLC → Linear completado

Proyecto: {nombre}

{UOW-XX} {Nombre}
  Epic: #{id Linear} — {creado / actualizado}
  Sub-issues: {N} Todo · {N} Done

Próximo paso:
  Retomar Code Generation en Claude Code, luego volver a correr
  este Skill para sincronizar el avance.
```

---

## Restricciones

| ❌ Prohibido | ✅ Permitido |
|---|---|
| Asumir el ID UOW desde el nombre de carpeta o archivo | Solo leer el heading `#` del archivo |
| Procesar archivos sin `UOW-XX` en el heading | Ignorarlos |
| Modificar cualquier archivo en `aidlc-docs/` | Solo lectura |
| Crear duplicados si el Epic ya existe | Buscar primero, actualizar si existe |
| Inventar tareas fuera de los checkboxes del plan | El plan es la única fuente de tareas |
| Crear sub-issues sin Epic padre | Siempre encontrar o crear el Epic primero |

---

## Compatibilidad

Solo requiere:
- Lectura de archivos `.md` en `aidlc-docs/construction/`
- MCP de Linear activo

Funciona con Claude, GPT-4o, Gemini, Codex o cualquier modelo
que tenga estas dos herramientas disponibles.