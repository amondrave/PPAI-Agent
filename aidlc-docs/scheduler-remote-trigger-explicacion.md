# Scheduler Remoto — ¿Qué es y por qué pide GitHub?

## ¿Qué quieres lograr?

Que todas las mañanas (ej. 8:00 AM Colombia, lunes a viernes) recibas un resumen automático de:
1. Tus issues abiertos en Linear
2. En qué fase va el AIDLC (leyendo `aidlc-state.md`)
3. Si hay PRs pendientes de merge

Sin que tú tengas que abrir nada ni escribir ningún comando.

---

## ¿Qué es un Remote Trigger?

Es un **agente de Claude Code que corre en la nube de Anthropic** de forma programada (tipo cron job). No corre en tu máquina — corre en un servidor remoto.

```
Tu máquina (local)              Anthropic Cloud
┌──────────────┐               ┌─────────────────────────┐
│              │               │  Remote Trigger (cron)   │
│  Tú duermes  │               │  ┌───────────────────┐   │
│  o trabajas  │               │  │ Claude Code Agent  │   │
│              │               │  │ - clona tu repo    │   │
│              │               │  │ - lee aidlc-state  │   │
│              │               │  │ - consulta Linear  │   │
│              │               │  │ - genera resumen   │   │
│              │               │  └───────────────────┘   │
│              │               │  Se ejecuta a las 8am    │
│              │               │  cada día laborable      │
└──────────────┘               └─────────────────────────┘
```

### Diferencia con el NudgeScheduler del bot

| | NudgeScheduler (bot) | Remote Trigger (scheduler) |
|---|---|---|
| **Dónde corre** | Dentro del contenedor ECS del bot | En la nube de Anthropic |
| **Qué hace** | Envía nudges de tareas por Telegram | Ejecuta un agente Claude que analiza estado del proyecto |
| **Trigger** | Cada 15 min automáticamente | Cron programado (ej. 8am L-V) |
| **Acceso** | DynamoDB (tareas del bot) | Tu repo en GitHub + MCPs conectados |
| **Output** | Mensaje de Telegram al usuario | Resultado en Claude Code (web/CLI) |

---

## ¿Por qué pide conectar GitHub?

El agente remoto **no tiene acceso a tu máquina**. Cuando arranca, necesita clonar tu repositorio para poder leer archivos como `aidlc-state.md`. Para eso necesita permiso de lectura sobre `amondrave/PPAI-Agent`.

Hay dos formas de dárselo:

### Opción 1: Claude GitHub App (recomendada)
- Instalas la app de Claude en tu repo de GitHub
- El agente remoto puede clonar y leer el repo
- Setup: https://claude.ai/code/onboarding?magic=github-app-setup

### Opción 2: `/web-setup` desde Claude Code
- Sincroniza tus credenciales de GitHub con claude.ai
- Misma funcionalidad

**Sin esto**, el agente arranca pero no puede leer tu código → el resumen estaría incompleto (solo podría consultar Linear si conectas ese MCP).

---

## ¿Y Linear?

Linear tampoco está conectado como MCP remoto. Solo tienes **Gmail** conectado en claude.ai.

Para que el agente pueda consultar issues de Linear, necesitas conectar el MCP de Linear en: https://claude.ai/settings/connectors

**Sin Linear**, el agente solo podría leer el repo (aidlc-state.md + PRs de GitHub).

---

## Resumen de lo que necesitas conectar

| Servicio | Para qué | Cómo conectar | ¿Obligatorio? |
|----------|----------|---------------|----------------|
| **GitHub** | Clonar repo, leer aidlc-state.md, ver PRs | https://claude.ai/code/onboarding?magic=github-app-setup | Sí |
| **Linear** | Consultar issues abiertos/en progreso | https://claude.ai/settings/connectors | Opcional (nice to have) |

---

## Alternativa: Sin Remote Trigger

Si prefieres no conectar nada por ahora, podemos:

1. **Usar el NudgeScheduler del bot** — ya funciona y te manda nudges de tareas por Telegram. Con el deploy de v0.7.0 + `/config`, ya tendrías recordatorios automáticos.

2. **Crear un comando `/status` en el bot** — que te muestre un resumen del estado del proyecto directo en Telegram, sin necesidad de agente remoto.

3. **Dejarlo para después** — cuando tengas un momento para hacer el setup de GitHub/Linear en claude.ai.

---

## Mi recomendación

El **NudgeScheduler del bot** (que acabamos de activar) ya cubre el caso de "recuérdame mis tareas". El Remote Trigger sería un extra para tener un briefing de proyecto más completo.

Si te interesa el briefing completo → conecta GitHub y creamos el trigger.
Si con los nudges del bot es suficiente por ahora → lo dejamos para después y seguimos con UOW-04.
