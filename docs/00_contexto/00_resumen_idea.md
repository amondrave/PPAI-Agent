# PPAI — Sistema Personal de Productividad Automatizado con IA

## ¿Qué es?

PPAI es un agente de productividad personal que **observa, planifica, ejecuta y evalúa** las actividades diarias del usuario usando automatización e IA. Su objetivo es eliminar la fricción que genera procrastinación y convertir las intenciones del usuario en acciones concretas y calendarizadas.

---

## Problema que resuelve

| # | Síntoma del usuario | Cómo PPAI responde |
|---|---|---|
| 1 | "No sé qué hacer ahora" | El sistema prioriza y te dice exactamente qué es lo siguiente |
| 2 | "Sé qué hacer pero lo postergo" | Detecta tiempo muerto y fricción, activa al usuario con estrategias |
| 3 | "Tengo ideas dispersas" | Las captura en lenguaje natural y las convierte en tareas accionables |
| 4 | "No veo mi progreso" | Genera reportes simples y visuales al final del día |
| 5 | "Algo me genera fricción y no sé cómo salir" | Propone actividades y herramientas concretas para superarla |
| 6 | "Quiero rutinas que realmente funcionen" | Aprende del usuario y define su rutina matutina/nocturna ideal |

---

## Cómo funciona (flujo general)

### 1. Entrada — Lenguaje natural
El usuario captura ideas y tareas en cualquier momento vía:
- **CLI** (texto rápido desde terminal)
- **Telegram** (bot conversacional)
- **API Web** (integración futura)

```
"Estudiar streams 30 min"
"Pagar factura mañana"
"Idea: app de recordatorios con voz"
```

### 2. Procesamiento — Motor de IA
La IA clasifica cada entrada según:
- **Tipo:** estudio / trabajo / personal / idea / compromiso
- **Duración:** tiempo estimado y en qué bloques ejecutarla
- **Energía:** nivel de esfuerzo cognitivo requerido (alto / medio / bajo)

Y decide:
- ¿Es para hoy o para después?
- ¿Ahora o en qué momento del día tiene más sentido?
- ¿Cómo activar al usuario si detecta resistencia?

### 3. Automatización
- Agenda bloques automáticamente en el calendario del usuario
- Genera recordatorios inteligentes (no spam, sino en el momento correcto)
- Detecta huecos muertos en el día y los clasifica: ¿ocio necesario o trabajo ligero?
- Construye rutinas matutinas y nocturnas aprendiendo de los patrones del usuario

### 4. Salida
- **Plan diario concreto:** máximo 3 tareas clave (inamovibles) + N tareas secundarias opcionales
- **Reporte nocturno automático:**
  - Qué se cumplió
  - Qué se evitó y por qué (análisis de fricción)
  - Sugerencias para el día siguiente
  - *(Informe gráfico — fuera del MVP inicial)*

---

## Plan de trabajo — 4 semanas

### Semana 1 — Definición y arquitectura base
**Objetivo:** Tener claridad total del sistema antes de escribir código.

- [ ] Definir persona objetivo (usuario primario)
- [ ] Mapear el JTBD (Job to be Done) principal
- [ ] Diseñar el modelo de datos: tarea, sesión, reporte
- [ ] Elegir stack técnico (CLI, bot de Telegram, LLM)
- [ ] Definir el alcance del MVP: qué entra y qué se deja fuera
- [ ] Documentar supuestos y riesgos (`01_supuestos_y_riesgos.md`)

**Entregable:** Documento de arquitectura + backlog priorizado

---

### Semana 2 — MVP Core: captura + clasificación IA
**Objetivo:** El sistema puede recibir una tarea en lenguaje natural y devolver una clasificación útil.

- [ ] Implementar CLI o bot de Telegram funcional
- [ ] Conectar con LLM (Claude / GPT) para clasificación de tareas
- [ ] Persistir tareas en base de datos simple (SQLite o JSON local)
- [ ] Mostrar lista de tareas del día con prioridad sugerida
- [ ] Validar clasificaciones con al menos 1 usuario real (puede ser uno mismo)

**Entregable:** CLI/bot que captura, clasifica y lista tareas del día

---

### Semana 3 — Automatización y reporte nocturno
**Objetivo:** El sistema actúa, no solo registra.

- [ ] Implementar agendado de bloques de trabajo (integración básica con calendario o recordatorios)
- [ ] Generar recordatorios inteligentes basados en la clasificación de energía
- [ ] Implementar detección de huecos muertos (comparar agenda vs tiempo real)
- [ ] Construir reporte nocturno automático (texto por ahora, sin gráficas)
- [ ] Lógica de activación ante señales de procrastinación

**Entregable:** Sistema que agenda, recuerda y reporta automáticamente

---

### Semana 4 — Validación e iteración
**Objetivo:** Aprender si el sistema resuelve el problema real.

- [ ] Prueba de uso durante 5 días seguidos (usuario real)
- [ ] Recopilar feedback cualitativo: ¿qué fricción generó el propio sistema?
- [ ] Ajustar clasificación de IA según casos de error encontrados
- [ ] Definir qué características pasan a la siguiente iteración
- [ ] Documentar aprendizajes y decisiones (`02_aprendizajes.md`)

**Entregable:** Reporte de validación + decisión de qué construir en la v2

---

## Alcance del MVP (qué sí y qué no)

| Incluido en MVP | Excluido del MVP |
|---|---|
| Captura por CLI o Telegram | Interfaz web / app móvil |
| Clasificación con IA | Aprendizaje automático avanzado |
| Lista diaria priorizada (3+N) | Informe gráfico |
| Reporte nocturno en texto | Integración con múltiples calendarios |
| Recordatorios básicos | Análisis de productividad histórico |
| Detección de huecos muertos | Coaching conversacional complejo |

---

## Visión a futuro (fuera del MVP)

- Modo "coach de procrastinación": el sistema conversa y ayuda a desbloquear resistencia
- Reportes visuales semanales y mensuales
- Aprendizaje continuo del perfil de energía del usuario
- Integración con Google Calendar, Notion, Obsidian
- API pública para que otros sistemas envíen tareas a PPAI
