# Skill: story-to-bdd

**Versión:** 1.0-draft (JavaScript / Jest)
**Proyecto:** PPAI (Personal Productivity AI)
**Autor:** Co-creado Angel Mondragon + Claude
**Última actualización:** 2026-03-09

> ⚠️ **Nota de migración pendiente:** PPAI está construido en Python.
> Esta versión del Skill genera skeletons en **Jest (JavaScript)** como prueba de concepto.
> Migrar a **v2.0 Python** cuando se defina la arquitectura de tests:
> - BDD runner: `behave` (Gherkin nativo en Python)
> - Unit tests: `pytest`
> - Archivos output: `.feature` (sin cambios) + `test_{story}.py` (en lugar de `.test.js`)
> - El Gherkin es agnóstico al lenguaje — los `.feature` no necesitan cambios.

---

## Propósito

Este Skill toma **una User Story** de `specs/backlog.md` y genera dos artefactos:

1. **Archivo `.feature`** — escenarios BDD en formato Gherkin (Given / When / Then)
2. **Archivo `.test.js`** — skeleton de tests unitarios/integración en Jest (vacío, listo para implementar)

Es el puente entre el backlog y el código. El Sub-Agente 2 (Quality Agent) usa este Skill.

---

## Cuándo usar este Skill

Activar cuando:
- Se va a implementar una story específica del backlog.
- Se necesita contrato de comportamiento antes de escribir código.
- El equipo quiere TDD/BDD: primero el test, luego la implementación.

**Input requerido:** ID de story (ej. `S1.1`, `S2.3`)

Si no se especifica una story, pedir cuál antes de proceder.

---

## Pre-requisitos

| Archivo | Rol |
|---------|-----|
| `specs/backlog.md` | Fuente de la story con sus ACs |
| `specs/prd.md` | Referencia de principios no negociables |
| `AGENTS.md` | Naming conventions y DDD vocabulary |

Si `specs/backlog.md` no existe, indicar al usuario que primero debe correr el Skill `prd-to-backlog`.

---

## Instrucciones de ejecución (paso a paso)

### PASO 1 — Identificar y leer la story

Leer `specs/backlog.md` y ubicar la story por ID.

Extraer:
- Enunciado completo: Como / Quiero / Para
- Lista de ACs (todos los ítems `- [ ] AC: ...`)
- Metadatos: Prioridad, MoSCoW, Épica, Módulo DB
- Tags especiales: `[TBD]`, guardrails de tono si aplican

### PASO 2 — Leer el contexto del dominio

Leer en `AGENTS.md`:
- DDD vocabulary (nombres de entidades y tablas)
- Naming conventions

Leer en `specs/prd.md`:
- Principios de diseño no negociables (Segmento 6) — en especial "Tono no acusatorio"
- El caso de uso relacionado con esta story (Segmento 5)

### PASO 3 — Definir la ubicación de los archivos output

**Convención de directorios:**

```
tests/
└── features/
│   └── {epica-id}/
│       └── {story-id}.feature          ← escenarios Gherkin
└── unit/
    └── {epica-id}/
        └── {story-id}.test.js          ← skeleton Jest
```

**Conversión de IDs a nombres de archivo:**
- `S1.1` → carpeta `e1/`, archivos `s1-1.feature` y `s1-1.test.js`
- `S3.2` → carpeta `e3/`, archivos `s3-2.feature` y `s3-2.test.js`

Verificar si el directorio existe; si no, crearlo.

### PASO 4 — Generar el archivo `.feature`

Generar escenarios Gherkin siguiendo estas reglas:

**Regla 1 — Escenarios mínimos requeridos:**
- 1 escenario de **Happy Path** por story (obligatorio)
- 1 escenario de **Edge Case** o caso inválido (obligatorio)
- 1 escenario de **Guardrail de tono** si la story involucra comunicación con usuario
- Escenarios adicionales solo si un AC lo requiere explícitamente

**Regla 2 — Formato Gherkin estricto:**
```gherkin
Feature: {nombre descriptivo de la épica}
  Como {actor}
  Quiero {acción}
  Para {beneficio}

  Background: (opcional, solo si hay precondiciones comunes)
    Given {estado inicial común}

  Scenario: {nombre descriptivo del escenario}
    Given {precondición}
    When {acción del actor}
    Then {resultado esperado y verificable}
    And {resultado adicional si aplica}

  Scenario: {siguiente escenario}
    ...
```

**Regla 3 — Calidad de los pasos Gherkin:**
- `Given` → estado del sistema antes de la acción (setup)
- `When` → acción concreta del actor (un solo evento)
- `Then` → resultado observable y verificable (sin lógica interna)
- No usar `And` como primer paso — solo como continuación
- Los pasos en español (negocio), sin términos técnicos de implementación

**Regla 4 — Tono en escenarios de guardrail:**
```gherkin
Scenario: El sistema responde sin lenguaje acusatorio
  Given el usuario no completó ninguna tarea hoy
  When el sistema genera el reporte nocturno
  Then el mensaje no debe contener palabras como "fallaste", "no cumpliste" o "fracasaste"
  And el mensaje debe usar un tono empático y neutral
```

**Regla 5 — Sin lógica de implementación:**
- ❌ `Then la función classify() retorna "ALTA"`
- ✅ `Then el sistema muestra la tarea con prioridad "Alta"`

### PASO 5 — Generar el archivo `.test.js` (skeleton)

Generar un archivo Jest con estructura base, **SIN implementación** — solo los `describe` / `it` blocks con nombres descriptivos y `// TODO`.

**Estructura base:**

```javascript
/**
 * Story: {ID} — {nombre de la story}
 * Épica: {nombre de la épica}
 * BDD feature: tests/features/{epica-id}/{story-id}.feature
 *
 * Convención de naming: inglés para código, español en comentarios de negocio
 */

// ============================================================
// DEPENDENCIAS — completar con los módulos reales al implementar
// ============================================================
// const { modulo } = require('../../src/modulo');

describe('{StoryId} — {nombre técnico del módulo}', () => {

  // Setup compartido (opcional)
  beforeEach(() => {
    // TODO: inicializar estado de test
  });

  afterEach(() => {
    // TODO: limpiar estado si aplica
  });

  // ----------------------------------------------------------
  // Happy Path
  // ----------------------------------------------------------
  describe('Happy path', () => {
    it('should {descripción técnica del comportamiento esperado}', async () => {
      // Arrange — {descripción del estado inicial en español}
      // TODO: configurar datos de entrada

      // Act — {descripción de la acción en español}
      // TODO: ejecutar la función bajo prueba

      // Assert — {descripción del resultado esperado en español}
      // TODO: verificar resultado
      expect(true).toBe(false); // reemplazar con assertion real
    });
  });

  // ----------------------------------------------------------
  // Edge Cases
  // ----------------------------------------------------------
  describe('Edge cases', () => {
    it('should handle {descripción del caso límite}', async () => {
      // Arrange
      // TODO

      // Act
      // TODO

      // Assert
      // TODO
      expect(true).toBe(false);
    });
  });

  // ----------------------------------------------------------
  // Guardrails (solo si la story involucra comunicación con usuario)
  // ----------------------------------------------------------
  describe('Guardrails de tono', () => {
    it('should not use accusatory language in output', async () => {
      // Arrange — {descripción del escenario adversarial}
      // TODO: preparar caso donde usuario tuvo bajo rendimiento

      // Act
      // TODO: ejecutar generación de mensaje

      // Assert — verificar ausencia de lenguaje prohibido
      const prohibitedWords = ['fallaste', 'no cumpliste', 'fracasaste', 'otra vez'];
      // TODO: obtener output real
      const output = '';
      prohibitedWords.forEach(word => {
        expect(output.toLowerCase()).not.toContain(word);
      });
    });
  });

});
```

**Reglas para el skeleton:**
- Todos los `it()` deben tener nombre descriptivo en inglés técnico
- Los comentarios de negocio en español (qué estamos probando conceptualmente)
- Incluir bloque `Guardrails` solo si la story tiene AC de tono
- Cada `it()` que salga del `.feature` debe tener su test correspondiente
- Cada `expect()` debe ser incorrecto (`false`/`toBe(false)`) para que el test falle hasta ser implementado — esto es TDD: red first

### PASO 6 — Verificar coherencia entre artefactos

Antes de finalizar, confirmar:

- [ ] Cada `Scenario:` en el `.feature` tiene al menos un `it()` en el `.test.js`
- [ ] Los nombres de scenarios y tests son trazables entre sí
- [ ] No hay AC en el backlog sin cobertura en algún escenario
- [ ] El nombre del `Feature:` coincide con el nombre de la épica en el backlog
- [ ] Los archivos están en los directorios correctos

---

## Formato de output

### Archivo 1: `tests/features/e{n}/s{n}-{m}.feature`

```gherkin
Feature: {Nombre de la épica}
  Como {actor}
  Quiero {acción de la story}
  Para {beneficio}

  Scenario: {Happy path — nombre descriptivo}
    Given ...
    When ...
    Then ...

  Scenario: {Edge case — nombre descriptivo}
    Given ...
    When ...
    Then ...

  Scenario: {Guardrail de tono — si aplica}
    Given ...
    When ...
    Then ...
    And ...
```

### Archivo 2: `tests/unit/e{n}/s{n}-{m}.test.js`

Ver estructura completa en PASO 5.

---

## Restricciones críticas

| ❌ Prohibido | ✅ Permitido |
|-------------|-------------|
| Implementar lógica real en el skeleton | Solo `// TODO` y `expect(false)` |
| Usar términos técnicos en pasos Gherkin | Lenguaje de negocio en Gherkin |
| Inventar escenarios fuera de los ACs | Derivar de ACs y principios del PRD |
| Omitir el escenario de guardrail si aplica | Siempre incluir cuando hay comunicación con usuario |
| Usar lenguaje acusatorio en nombres de test | Tono neutro y técnico en todo el archivo |
| Modificar `specs/backlog.md` o `specs/prd.md` | Solo leer esos archivos |

---

## DDD — Nombres técnicos en el skeleton

Usar estos nombres en el código del skeleton (no en los pasos Gherkin):

| Concepto | Nombre en código | Módulo esperado |
|----------|-----------------|-----------------|
| Tarea capturada | `Task` | `task-capture` |
| Ciclo de ejecución | `ExecutionCycle` | `execution-engine` |
| Patrón de bloqueo | `BlockingPattern` | `pattern-detector` |
| Nudge | `Nudge` | `nudge-orchestrator` |
| Reporte nocturno | `DailyReport` | `report-generator` |
| Guardrail de tono | `ToneGuardrail` | `guardrails` |

---

## Ejemplo de ejecución completa

**Input:** `S1.1 — Captura de tarea en lenguaje natural`

**Output esperado:**

```
tests/
└── features/
│   └── e1/
│       └── s1-1.feature
└── unit/
    └── e1/
        └── s1-1.test.js
```

Con:
- `s1-1.feature`: 3 escenarios (happy path: captura exitosa, edge case: texto vacío o ambiguo, guardrail: confirmación sin tono agresivo)
- `s1-1.test.js`: 3 `it()` blocks en red (failing), listos para implementar

---

## Resultado final

Al terminar, reportar al usuario:

```
✅ BDD generado para {Story ID} — {Nombre de la story}

Archivos creados:
- tests/features/e{n}/s{n}-{m}.feature  ({N} escenarios)
- tests/unit/e{n}/s{n}-{m}.test.js      ({N} tests en red)

Cobertura de ACs:
- AC 1: ✅ cubierto en Scenario "{nombre}"
- AC 2: ✅ cubierto en Scenario "{nombre}"
- AC 3: ✅ cubierto en Scenario "{nombre}"

Siguiente paso: implementar los módulos y hacer pasar los tests (green).
```
