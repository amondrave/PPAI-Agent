# Skill: story-to-bdd

**Versión:** 2.0 (Python / pytest + behave)
**Proyecto:** PPAI (Personal Productivity AI)
**Autor:** Co-creado Angel Mondragon + Claude
**Última actualización:** 2026-03-18

---

## Propósito

Este Skill toma **una User Story** de `specs/backlog.md` y genera dos artefactos:

1. **Archivo `.feature`** — escenarios BDD en formato Gherkin (Given / When / Then), para correr con `behave`
2. **Archivo `test_{story}.py`** — skeleton de tests unitarios en `pytest` (vacío, en RED, listo para implementar)

Es el puente entre el backlog y el código. Aplica el ciclo TDD: **Red → Green → Refactor**.

---

## Cuándo usar este Skill

Activar cuando:
- Se va a implementar una story específica del backlog.
- Se necesita contrato de comportamiento antes de escribir código.
- Se quiere TDD/BDD: primero el test, luego la implementación.

**Input requerido:** ID de story (ej. `S2.1`, `S2.3`)

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
- Principios de diseño no negociables — en especial "Tono no acusatorio"
- El caso de uso relacionado con esta story

### PASO 3 — Definir la ubicación de los archivos output

**Convención de directorios:**

```
tests/
├── features/
│   └── e{n}/
│       └── s{n}-{m}.feature          ← escenarios Gherkin (behave)
└── unit/
    └── e{n}/
        └── test_s{n}_{m}.py          ← skeleton pytest (RED)
```

**Conversión de IDs a nombres de archivo:**
- `S2.1` → carpeta `e2/`, archivos `s2-1.feature` y `test_s2_1.py`
- `S3.2` → carpeta `e3/`, archivos `s3-2.feature` y `test_s3_2.py`

Verificar si el directorio existe; si no, crearlo (con `__init__.py` vacío en carpetas de tests).

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

### PASO 5 — Generar el archivo `test_{story}.py` (skeleton pytest)

Generar un archivo pytest con estructura base, **SIN implementación** — solo `describe`-equivalentes con clases y métodos `test_*` con `pytest.fail("not implemented")`.

**Estructura base:**

```python
"""
Story: {ID} — {nombre de la story}
Épica: {nombre de la épica}
BDD feature: tests/features/e{n}/s{n}-{m}.feature

Convención: inglés para código, comentarios de negocio en español.
TDD: todos los tests empiezan en RED (pytest.fail). Implementar para pasar a GREEN.
"""
import pytest

# ============================================================
# DEPENDENCIAS — completar con los módulos reales al implementar
# ============================================================
# from ppai.{modulo}.application.{service} import {Service}


class Test{StoryId}HappyPath:
    """Happy path — {descripción del escenario principal en español}"""

    def test_{descripcion_tecnica}(self):
        # Arrange — {descripción del estado inicial en español}
        # TODO: configurar datos de entrada

        # Act — {descripción de la acción en español}
        # TODO: ejecutar el servicio/función bajo prueba

        # Assert — {descripción del resultado esperado en español}
        # TODO: verificar resultado
        pytest.fail("not implemented")


class Test{StoryId}EdgeCases:
    """Edge cases — {descripción del caso límite en español}"""

    def test_{descripcion_caso_limite}(self):
        # Arrange
        # TODO

        # Act
        # TODO

        # Assert
        pytest.fail("not implemented")


# Solo incluir si la story involucra comunicación con usuario
class Test{StoryId}ToneGuardrails:
    """Guardrails de tono — el sistema no debe usar lenguaje acusatorio"""

    PROHIBITED_WORDS = [
        "fallaste", "no cumpliste", "fracasaste", "otra vez", "como siempre",
        "deberías", "tenías que",
    ]

    def test_output_does_not_contain_accusatory_language(self):
        # Arrange — preparar escenario donde usuario tuvo bajo rendimiento
        # TODO: construir contexto con tareas no completadas

        # Act — generar mensaje del sistema
        # TODO: invocar generación de mensaje
        output = ""  # reemplazar con output real

        # Assert — verificar ausencia de lenguaje prohibido
        for word in self.PROHIBITED_WORDS:
            assert word not in output.lower(), f"Lenguaje prohibido encontrado: '{word}'"
        pytest.fail("not implemented — completar Arrange y Act")
```

**Reglas para el skeleton:**
- Clases como agrupadores (equivalente a `describe`): `Test{StoryId}HappyPath`, `Test{StoryId}EdgeCases`, `Test{StoryId}ToneGuardrails`
- Métodos `test_*` en snake_case, nombre descriptivo en inglés técnico
- Comentarios de negocio en español dentro de cada método
- Incluir clase `ToneGuardrails` solo si la story tiene AC de tono
- Cada método termina en `pytest.fail("not implemented")` — esto es TDD: **RED first**
- No implementar lógica real en el skeleton

### PASO 6 — Crear `__init__.py` si no existen

Para cada directorio nuevo creado bajo `tests/`:
- Crear `__init__.py` vacío para que pytest los descubra correctamente

### PASO 7 — Verificar coherencia entre artefactos

Antes de finalizar, confirmar:

- [ ] Cada `Scenario:` en el `.feature` tiene al menos un método `test_*` en el `.py`
- [ ] Los nombres de scenarios y tests son trazables entre sí
- [ ] No hay AC en el backlog sin cobertura en algún escenario
- [ ] El nombre del `Feature:` coincide con el nombre de la épica en el backlog
- [ ] Los archivos están en los directorios correctos
- [ ] Existen `__init__.py` en todos los directorios nuevos

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

### Archivo 2: `tests/unit/e{n}/test_s{n}_{m}.py`

Ver estructura completa en PASO 5.

---

## Restricciones críticas

| ❌ Prohibido | ✅ Permitido |
|-------------|-------------|
| Implementar lógica real en el skeleton | Solo `# TODO` y `pytest.fail()` |
| Usar términos técnicos en pasos Gherkin | Lenguaje de negocio en Gherkin |
| Inventar escenarios fuera de los ACs | Derivar de ACs y principios del PRD |
| Omitir el guardrail si la story tiene AC de tono | Siempre incluir `ToneGuardrails` cuando aplica |
| Usar lenguaje acusatorio en nombres de test | Tono neutro y técnico en todo el archivo |
| Modificar `specs/backlog.md` o `specs/prd.md` | Solo leer esos archivos |

---

## DDD — Nombres técnicos en el skeleton

Usar estos nombres en el código del skeleton (no en los pasos Gherkin):

| Concepto | Nombre en código | Módulo esperado |
|----------|-----------------|-----------------|
| Tarea capturada | `TaskState` | `ppai.capture` |
| Ciclo de ejecución | `ExecutionCycle` | `ppai.decision` |
| Motor de priorización | `PrioritizationEngine` | `ppai.decision` |
| Patrón de bloqueo | `BlockingPattern` | `ppai.learning` |
| Nudge | `Nudge` | `ppai.nudge` |
| Reporte nocturno | `DailyReport` | `ppai.report` |
| Guardrail de tono | `ToneGuardrail` | `ppai.shared.guardrails` |

---

## Ejemplo de ejecución completa

**Input:** `S2.1 — Priorización automática y presentación del Top 3`

**Output esperado:**

```
tests/
├── features/
│   └── e2/
│       └── s2-1.feature
└── unit/
    └── e2/
        ├── __init__.py
        └── test_s2_1.py
```

Con:
- `s2-1.feature`: 3 escenarios (happy path: Top 3 presentado, edge case: menos de 3 tareas, guardrail: tono no acusatorio)
- `test_s2_1.py`: 3 clases con métodos `test_*` en RED (`pytest.fail`), listos para implementar

---

## Resultado final

Al terminar, reportar al usuario:

```
✅ BDD generado para {Story ID} — {Nombre de la story}

Archivos creados:
- tests/features/e{n}/s{n}-{m}.feature  ({N} escenarios)
- tests/unit/e{n}/test_s{n}_{m}.py      ({N} tests en RED)

Cobertura de ACs:
- AC 1: ✅ cubierto en Scenario "{nombre}"
- AC 2: ✅ cubierto en Scenario "{nombre}"
- AC 3: ✅ cubierto en Scenario "{nombre}"

Siguiente paso: implementar los módulos y hacer pasar los tests (GREEN).
```
