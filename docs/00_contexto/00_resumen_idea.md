# PPAI — Personal Productivity AI
## Resumen de Idea (Workflow-First Edition)

Versión: 2.0
Fecha: 2026-03-04
Estado: Estrategia activa

---

## ¿Qué es PPAI?

PPAI es un sistema de **workflow de productividad personal** que opera sobre un loop de estados explícito: captura la intención del usuario, decide la siguiente acción prioritaria, ejecuta el empuje (notificación, prompt, reporte), y aprende del comportamiento real de ejecución y bloqueo. No es un generador de planes — es un conductor de proceso. La diferencia crítica: un output wrapper te da un plan bonito una vez; un workflow loop te acompaña en el ciclo completo y acumula estado y contexto a lo largo del tiempo.

---

## El problema durable post-GPT-6

El problema que PPAI resuelve **no es de output, es de proceso**. GPT-6 puede generar un plan de productividad perfecto. Notion puede almacenarlo. Lo que ningún modelo de lenguaje puede hacer por sí solo es:

- **Mantener estado**: saber qué confirmaste ayer, qué pospusiste tres veces, qué nunca arrancas cuando hay baja energía.
- **Ejecutar el loop**: iniciar conversaciones en el momento correcto, registrar el resultado, actualizar el contexto.
- **Aprender del comportamiento real**: no de lo que el usuario dice que hará, sino de lo que realmente hace (o no hace) cuando recibe el nudge.

El valor de PPAI está en la **integración entre momentos**, no en la calidad de un solo mensaje. Eso sobrevive a cualquier mejora de modelo base porque los datos de comportamiento son propietarios, acumulativos y no replicables por un competidor que empiece mañana.

---

## Workflow Loop Central (MVP Telegram)

```
┌─────────────────────────────────────────────────────────┐
│              WORKFLOW LOOP CENTRAL — PPAI               │
│                                                         │
│   CAPTURE ──► DECIDE ──► EXECUTE ──► CONFIRM/UPDATE     │
│      ▲                                    │             │
│      │                                    ▼             │
│   NEXT TASK ◄────────────── LEARN ◄── REPORT            │
└─────────────────────────────────────────────────────────┘
```

### Estados del loop

| Estado | Qué ocurre | Comandos / Botones |
|--------|-----------|-------------------|
| **CAPTURE** | Usuario envía tarea en lenguaje natural | Mensaje libre en Telegram |
| **DECIDE** | Sistema clasifica, prioriza, asigna energía y hora sugerida | — (automático) |
| **EXECUTE** | Sistema envía el nudge en el momento correcto | — (automático, triggered) |
| **CONFIRM/UPDATE** | Usuario cierra el loop informando resultado | `/done` · `/snooze` · `/clarify` |
| **LEARN** | Sistema registra patrón: ¿completó? ¿posposó? ¿razón? | — (automático) |
| **REPORT** | Reporte nocturno: síntesis + hipótesis curiosa + 1 recomendación | Mensaje a las 21:00 |

### Comandos mínimos del MVP

```
/done      → Tarea completada. Cierra el estado, registra energía final.
/snooze    → Posponer. Pide razón (opcional). Registra patrón de bloqueo.
/clarify   → La tarea no es accionable. Reabre captura para refinar.
```

> Los botones inline de Telegram reemplazan los comandos cuando el sistema hace el nudge (el usuario ve [✓ Hecho] [⏸ Posponer] [? Aclarar] sin escribir nada).

### Scope del loop — qué NO entra en MVP

- No hay integración con Google Calendar ni calendarios externos.
- No hay dashboards ni reportes gráficos.
- No hay rutinas complejas (descansos, pomodoro, bloques temáticos avanzados).
- No hay detección de "huecos muertos" en agenda (no tenemos acceso al calendario).
- No hay múltiples canales simultáneos (CLI es Fase 2).

---

## Moat primario: Data Behavioral Moat

**Elección: Data Moat (único moat primario).** La distribución por Telegram es ventaja de tiempo-al-valor, no moat.

### ¿Qué datos exactos capturamos?

Cada ciclo del loop genera datos que ningún competidor que empiece mañana puede comprar:

| Dato capturado | Cómo se genera | Por qué es valioso |
|---------------|----------------|-------------------|
| Tasa de confirmación por tipo de tarea | `/done` vs ausencia de respuesta | Revela qué categorías el usuario realmente ejecuta |
| Razón de posposición | Respuesta libre al `/snooze` | Identifica patrones de bloqueo individuales |
| Hora real de ejecución vs hora sugerida | Timestamp de `/done` | Calibra el modelo de energía del usuario |
| Energía reportada al completar | Emoji / escala 1-3 al hacer `/done` | Construye perfil de energía circadiana |
| Latencia de respuesta al nudge | Tiempo entre nudge y acción | Mide fricción real del canal y del momento |
| Tasa de reactivación post-bloqueo | Si vuelve a capturar después de `/snooze` | Valida si el loop tiene enganche real |

**Flywheel:** más usuarios → más datos → clasificación más precisa → nudges mejor timed → mejor retención → más usuarios.

---

## MVP Scope — Telegram-only

| Incluido | Excluido |
|---------|---------|
| Captura en lenguaje natural vía Telegram | CLI (Fase 2) |
| Clasificación tipo / energía / urgencia | Integración con calendarios |
| Nudge en momento sugerido | Dashboard web / app móvil |
| Comandos `/done` `/snooze` `/clarify` + botones | Reportes gráficos |
| Reporte nocturno (texto, 21:00) | Aprendizaje automático avanzado |
| Registro de razones de bloqueo | Rutinas complejas (pomodoro, etc.) |
| Perfil de energía básico | Claims de salud mental / terapia |

### Anti-features explícitas

- El sistema **nunca usa lenguaje acusatorio** ("fallaste", "no cumpliste", "como siempre").
- Si el usuario expresa culpa o vergüenza, el sistema **reduce intensidad** del siguiente nudge.
- El reporte nocturno usa **hipótesis curiosas**, no evaluaciones de desempeño.
- PPAI **no es terapia, no es coaching de salud mental** y no debe presentarse como tal.

---

## Roadmap: Fase 2 — CLI

**Condición de activación:** Telegram MVP supera targets de retención (≥ 2/3 usuarios activos al Día 5) y utilidad (≥ 60% reporta el reporte nocturno como útil).

### Comandos CLI mínimos (Fase 2)

```bash
ppai add "terminar módulo 3 del curso"   # Captura rápida desde terminal
ppai now                                  # Muestra la tarea prioritaria del momento
ppai done                                 # Cierra la tarea activa
```

**Por qué CLI es Fase 2 y no parte del MVP:** El loop completo (capture → confirm → learn) requiere canal bidireccional con nudge proactivo. Un CLI sin daemon de notificaciones es solo captura — no completa el loop. Telegram lo resuelve de forma nativa.

---

## Riesgos principales y mitigación

### C1 — El usuario no mantiene el hábito de captura

**Riesgo:** Sin capturas, el loop no arranca. El sistema queda vacío y el usuario lo abandona.

**Señal temprana:** < 3 capturas/día en los primeros 3 días del MVP de papel.

**Mitigación:** Reducir la fricción de captura al mínimo absoluto (1 mensaje = 1 tarea). Enviar un mensaje de apertura de día con "¿qué tienes hoy?" si no hay capturas antes de las 10:00.

**Cómo medir en Semana 1:** Capturas/día/usuario. *HIPÓTESIS: el usuario técnico captura ≥ 3 tareas/día si el canal es Telegram.*

---

### C4 — El reporte nocturno genera culpa, no insight

**Riesgo:** El tono equivocado destruye la retención. El usuario siente que el sistema lo juzga.

**Señal temprana:** > 33% de usuarios reporta sentirse culpable o avergonzado tras leer el reporte.

**Mitigación:** Todo prompt del reporte nocturno usa framing de "¿qué pasó?" (curioso) nunca "no lo lograste" (acusatorio). Si el usuario reporta culpa, el siguiente reporte reduce detalles de tareas no completadas y amplifica lo que sí se hizo.

**Cómo medir en Semana 1:** Pregunta directa post-reporte: "¿Cómo te sentiste al leer esto? (útil / neutral / culpable)".

---

### C5 — El costo LLM por usuario activo hace el modelo inviable

**Riesgo:** Con uso real (captura + clasificación + reporte), el costo de tokens supera lo que el usuario pagaría.

**Señal temprana:** Costo > $1/usuario activo/mes con uso medido en el MVP de papel.

**Mitigación:** Clasificación con modelo pequeño (Haiku / GPT-4o-mini) para captura; modelo más capaz solo para el reporte nocturno. Cache de clasificaciones para tareas recurrentes.

**Cómo medir en Semana 1:** Instrumentar cada llamada LLM con costo estimado. Calcular costo por usuario al final del MVP de papel. *HIPÓTESIS: costo ≤ $0.50/usuario activo/mes con modelo pequeño para clasificación.*
