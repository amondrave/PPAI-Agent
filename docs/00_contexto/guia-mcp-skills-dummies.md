# Guía para Dummies: MCP + Skills + Sub-Agentes en PPAI

Versión: 1.0
Fecha: 2026-03-04
Audiencia: Alguien que entiende el producto pero nunca configuró MCPs ni Skills

---

## La analogía que lo explica todo

Imaginate que el modelo de AI (Claude, GPT-4o, Gemini) es un cerebro muy capaz encerrado en un cuarto sin ventanas. Por defecto solo puede leer lo que vos le pegás en el chat.

- **MCPs** = puertas al mundo exterior. Le das llaves al cerebro para que pueda abrir el filesystem, hablar con GitHub, consultar una base de datos.
- **Skills** = manuales de procedimiento. En vez de explicarle cada vez cómo hacer algo, dejás el manual en el cuarto y cualquier cerebro que entre puede seguirlo.
- **Sub-agentes** = empleados con tarea específica. En vez de un solo cerebro haciendo todo, tenés uno que solo genera el backlog y otro que solo escribe tests.
- **AGENTS.md** = el contrato de la oficina. Cualquier cerebro nuevo que entre lee ese archivo y sabe cómo funciona el proyecto, qué herramientas tiene disponibles y qué reglas debe seguir.

---

## Parte 1 — Qué es un MCP

### Definición simple

MCP (Model Context Protocol) es un protocolo abierto de Anthropic que define cómo un modelo de AI puede conectarse a herramientas externas de forma estándar. Es el "USB-C para AI": una vez que algo habla MCP, cualquier modelo compatible puede usarlo.

### Cómo funciona en la práctica

```
Tu prompt
    ↓
Modelo (Claude / GPT / Gemini)
    ↓  ← el modelo decide qué herramienta usar
MCP Client (intermediario)
    ↓
MCP Server (el que tiene acceso real)
    ↓
Filesystem / GitHub / SQLite / lo que sea
```

### Los 3 MCPs que vamos a usar en PPAI

| MCP | Qué hace | Por qué lo necesita PPAI |
|-----|----------|--------------------------|
| **Filesystem** | Lee y escribe archivos en el repo | Permite al agente leer el PRD y escribir el backlog |
| **GitHub** | Gestiona issues, PRs, commits | Permite crear issues desde historias, trackear progreso |
| **SQLite** | Consulta y escribe en base de datos local | Persiste el estado del workflow loop (tareas, confirmaciones, patrones) |

### Dónde se configura

Los MCPs se configuran en un archivo JSON que el modelo lee al arrancar. La ubicación depende del modelo:

```
Para Claude Code:
  ~/.claude/mcp.json              ← configuración global (todos los proyectos)
  .claude/mcp.json                ← configuración solo para este repo ← USAREMOS ESTA

Para ChatGPT / Codex:
  Se configura en la plataforma de OpenAI o via Codex CLI config
  Pero el AGENTS.md documenta qué MCPs están disponibles → cualquier modelo sabe qué herramientas hay
```

### La clave model-agnostic

El archivo de configuración es model-specific. **Lo que hacemos model-agnostic es el AGENTS.md**: ahí documentamos qué MCPs están configurados, qué hacen y cómo usarlos. Así cualquier modelo que lea AGENTS.md sabe con qué herramientas cuenta aunque no tenga la configuración nativa.

---

## Parte 2 — Qué es un Skill

### Definición simple

Un Skill es un archivo markdown (SKILL.md) que contiene instrucciones específicas para que un agente complete una tarea recurrente bien definida. No es código — es un prompt estructurado con contexto, reglas y ejemplos.

### Por qué es model-agnostic por naturaleza

Un Skill es solo texto markdown. Claude lo puede seguir, GPT-4o lo puede seguir, Gemini lo puede seguir. El mismo SKILL.md funciona en cualquier modelo que pueda leer archivos.

### Estructura de un Skill

```
.skills/
└── skills/
    └── nombre-del-skill/
        └── SKILL.md          ← instrucciones completas del skill
```

### Los 3 Skills que vamos a crear para PPAI

```
.skills/skills/
├── prd-to-backlog/
│   └── SKILL.md      ← lee specs/prd.md → genera specs/backlog.md con épicas, stories, ACs
│
├── story-to-bdd/
│   └── SKILL.md      ← toma 1 story → genera escenarios BDD (Given/When/Then) + skeleton de tests
│
└── changelog/
    └── SKILL.md      ← analiza commits/PRs → actualiza CHANGELOG.md
```

### Diferencia entre Skill y MCP

| | MCP | Skill |
|---|---|---|
| **Qué es** | Herramienta externa (acceso a datos/sistemas) | Instrucciones de procedimiento |
| **Ejemplo** | "Puedo leer el filesystem" | "Cuando leas el PRD, hazlo así: …" |
| **Lo escribe** | El desarrollador o usa uno pre-hecho | Vos o el AI con guía |
| **Dónde vive** | Configuración (JSON) | Archivo markdown en el repo |
| **Model-agnostic** | No nativo (requiere config por modelo) | Sí, es solo texto |

---

## Parte 3 — Qué es un Sub-Agente

### Definición simple

Un sub-agente es una instancia del modelo con un propósito acotado y específico. En vez de pedirle a un solo agente "hacé todo", tenés agentes especializados que hacen una cosa muy bien.

### Por qué sub-agentes para PPAI

El workflow loop de PPAI tiene partes muy distintas. Un agente que hace todo termina siendo poco confiable. Dos agentes especializados son más predecibles.

### Los 2 sub-agentes que vamos a implementar

**Sub-Agente 1: Specification Agent**
- Propósito: transforma artefactos de especificación
- Entrada: `specs/prd.md`
- Salida: `specs/backlog.md` (épicas + stories + ACs)
- Usa: Filesystem MCP + Skill `prd-to-backlog`

**Sub-Agente 2: Quality Agent**
- Propósito: genera tests y scenarios de calidad
- Entrada: 1 story del backlog
- Salida: escenarios BDD + skeleton de tests en `/tests/`
- Usa: Filesystem MCP + Skill `story-to-bdd`

### Cómo se definen (model-agnostic)

En AGENTS.md agregamos una sección de sub-agentes con:
- Nombre y propósito
- Input/output esperado
- Skill que debe usar
- Reglas de comportamiento

Cualquier modelo que lea AGENTS.md puede actuar como cualquiera de los dos sub-agentes simplemente siguiendo esas instrucciones.

---

## Parte 4 — TDD, DDD y BDD: repaso rápido

### TDD — Test Driven Development

**La idea en una frase:** escribís el test ANTES de escribir el código.

```
Red   → escribís el test que falla (porque el código no existe)
Green → escribís el mínimo código para que el test pase
Refactor → mejorás el código sin romper el test
```

**Para PPAI significa:** antes de implementar el motor de priorización, escribís un test que diga "dado este input de tarea, espero este output de prioridad".

### DDD — Domain Driven Design

**La idea en una frase:** el código habla el mismo idioma que el negocio.

En DDD el modelo del dominio (las entidades, sus reglas, su lenguaje) es el centro de todo. No hay "User" y "Item" genéricos — hay "Tarea", "CicloDeEjecucion", "PatronDeBloqueo".

**Para PPAI significa:** el código usa los términos del PRD directamente. Una tarea no es un "record" — es una `Tarea` con estados `Pendiente`, `Confirmada`, `Pospuesta`. El loop no es un "cron" — es un `CicloDeEjecucion`.

### BDD — Behavior Driven Development

**La idea en una frase:** los tests se escriben en lenguaje de negocio, no en código técnico.

```gherkin
Feature: Captura de tarea

  Scenario: Usuario captura una tarea en lenguaje natural
    Given el usuario envía "terminar módulo 3 del curso" por Telegram
    When el motor de priorización procesa la entrada
    Then la tarea se clasifica como tipo "estudio"
    And la energía requerida se marca como "media"
    And la tarea aparece en el plan del día
```

**Para PPAI significa:** los scenarios BDD son literalmente el vocabulario del PRD traducido a tests verificables. Y sirven como documentación viva.

### Cómo se relacionan los tres

```
DDD define el lenguaje del dominio
    ↓
BDD escribe los comportamientos esperados en ese lenguaje
    ↓
TDD implementa ciclo a ciclo hasta que los tests pasan
```

---

## Parte 5 — El plan de 7 pasos (lo hacemos juntos)

```
Paso 1: Preparar la estructura de carpetas para MCPs y Skills
         → Crear .claude/ con mcp.json vacío y documentar en AGENTS.md

Paso 2: Configurar Filesystem MCP
         → Instalar, configurar, probar que el agente puede leer el repo

Paso 3: Configurar GitHub MCP
         → Instalar, configurar con token, probar que puede listar issues

Paso 4: Configurar SQLite MCP
         → Instalar, crear ppai.db con schema mínimo, probar query

Paso 5: Crear Skill prd-to-backlog
         → Escribir SKILL.md + ejecutar → genera specs/backlog.md

Paso 6: Crear Skill story-to-bdd
         → Escribir SKILL.md + ejecutar con 1 story del backlog

Paso 7: Actualizar AGENTS.md con sub-agentes y todo el contexto
         → El proyecto queda agnostico al modelo
```

**Cada paso tiene:**
- ¿Qué hacemos?
- Comando o archivo concreto
- Cómo verificar que funcionó
- Qué pasa si falla

---

## Preguntas frecuentes

**¿Necesito instalar algo primero?**
Para los MCPs: necesitás `node` y `npm` instalados (para correr los servers con `npx`). Para los Skills: nada, son archivos markdown.

**¿El MCP funciona igual en Claude y en ChatGPT?**
El protocolo es el mismo pero la configuración cambia. Claude Code usa `.claude/mcp.json`. ChatGPT/Codex tiene su propia forma de agregar herramientas. Por eso documentamos todo en AGENTS.md — ese archivo es el contrato que cualquier modelo puede leer.

**¿Puedo usar los Skills sin MCPs?**
Sí. Los Skills son solo instrucciones. Si el modelo puede leer archivos por sus propios medios (como Claude en este modo), funciona igual. Los MCPs amplían lo que el modelo puede hacer, pero no son prerequisito para los Skills.

**¿Qué va primero: MCPs o Skills?**
MCPs primero, porque los Skills van a necesitar leer y escribir archivos. Sin Filesystem MCP, el Skill `prd-to-backlog` no puede leer el PRD ni escribir el backlog automáticamente.

**¿Cómo sé si mi MCP está funcionando?**
Cada MCP tiene un comando de test. Por ejemplo, para Filesystem: pedirle al modelo "listá los archivos de `/docs`" — si lo hace sin que vos le hayas pegado el contenido, el MCP está funcionando.
