# Product Vision Board — PPAI
Fecha: 2026-03-04
Versión: 2.0
Estado: Estrategia activa
Author: Angel Yesid Mondragon

---

## 1) Vision

> **¿Por qué existe PPAI y a qué aspira?**

PPAI existe porque el problema de la ejecución no es de organización ni de output — es de **proceso continuo**. Las herramientas actuales te dan un plan. PPAI conduce el ciclo completo: captura la intención, empuja en el momento correcto, registra el resultado real y aprende del patrón.

**Aspiración:** Ser el workflow loop de productividad personal más confiable para trabajadores autónomos — el sistema que convierte intenciones dispersas en ciclos de ejecución medibles, sin apps nuevas, sin dashboards, sin culpa.

**Por qué sobrevive a GPT-6:** PPAI no es un generador de outputs — es un conductor de estados. Cualquier LLM puede escribir un plan. Ningún LLM puede, por sí solo, mantener estado de lo que pospusiste tres veces, saber tu patrón de bloqueo del martes a las 3pm y ajustar el nudge del miércoles en consecuencia. Eso es proceso + datos propietarios.

---

## 2) Target Group

### Primario — Freelancer / Developer solopreneur

- **Quién es:** Desarrollador, diseñador o consultor independiente. 25–38 años. Trabaja desde casa o en espacios cowork.
- **Contexto:** Sin estructura laboral externa que defina qué hacer ni cuándo. Mezcla proyectos de clientes con aprendizaje personal. Su tiempo es su único activo — la procrastinación tiene costo directo en ingresos.
- **Dolor principal:** No es que no sepa qué hacer — sabe exactamente qué debería hacer y aun así no arranca. La fricción de ejecución es diaria, repetitiva y genera culpa acumulada.
- **Canal natural:** Telegram para comunicación + CLI para trabajo técnico. No abre apps de productividad nuevas.
- **Trigger de mayor dolor:** Lunes por la mañana o después de un día improductivo. Abre Notion, ve la lista, se paraliza.

### Secundario — Estudiante autodidacta intensivo

- **Quién es:** 18–26 años. Alta carga cognitiva, bajo presupuesto.
- **Rol en el producto:** Canal de distribución orgánica (comparte con su red). Valida el tono del reporte nocturno.
- **Canal preferido:** Telegram principalmente.

---

## 3) Needs — validables en 7 días

**Need #1 — Claridad de próxima acción, ahora, en el canal donde ya está**
- Medición (Semana 1): % de usuarios que ejecutan ≥ 1 tarea en la primera hora post-plan.
- Supuesto vinculado: C1 — el usuario mantiene el hábito de captura.

**Need #2 — Captura sin fricción ni cambio de contexto**
- Medición (Semana 1): Capturas/día/usuario activo. Target: ≥ 3/día.
- Supuesto vinculado: C1, C3.

**Need #3 — Cierre del día con insight, no con culpa**
- Medición (Semana 1): ≤ 33% reporta culpa / ≥ 60% lo califica como útil.
- Supuesto vinculado: C4 — el tono del reporte funciona.

**Need #4 — Plan que respeta la energía disponible**
- Medición (Semana 1): % de usuarios que ejecutan ≥ 2 de las 3 tareas clave. Target: > 60%.
- Supuesto vinculado: C3 — clasificación de energía/tipo funciona.

---

## 4) Product — MVP Telegram (Workflow Loop)

### 4.1 El Workflow Loop Central

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

Este loop es el producto. No los mensajes individuales, no el plan diario — el **ciclo completo** de captura a confirmación a aprendizaje es lo que genera valor y genera datos.

**Comandos mínimos del MVP:**

```
/done      → Cierra tarea. Registra energía y hora real.
/snooze    → Posponer + razón opcional. Registra patrón de bloqueo.
/clarify   → Tarea no accionable. Reabre captura para refinar.
```

> Botones inline de Telegram: [✓ Hecho] [⏸ Posponer] [? Aclarar] — equivalentes a los comandos, sin escribir.

### 4.2 Value Proposition

> **"PPAI conduce el ciclo completo entre intención y ejecución — desde Telegram, sin instalar nada, sin migrar tareas, sin dashboards."**

| Alternativa | Qué resuelve | Gap que PPAI cubre |
|---|---|---|
| Motion / Reclaim | Reorganiza el calendario si fallas | No trabaja la fricción de ejecución ni captura estado de bloqueo |
| Todoist / Notion | Registra lo que decidiste hacer | No actúa si no ejecutas; no aprende del patrón |
| ChatGPT / Claude | Genera un plan de productividad | No mantiene estado, no conduce el ciclo, no acumula contexto |
| Papel / notas | Cero fricción de captura | Las notas nunca se convierten en ciclo de ejecución |

### 4.3 Flujos Core del MVP

**Flujo 1 — Captura → Plan del día**

1. Usuario envía texto libre en Telegram en cualquier momento.
2. LLM clasifica: tipo / energía requerida / duración estimada / urgencia.
3. Sistema responde con plan: 3 tareas clave ordenadas por energía + N backlog.
4. En el momento sugerido, sistema envía nudge con botones inline.

**Momento wow:** El usuario recibe su plan en < 30 segundos. Siente que alguien tomó el caos y lo organizó.

**Flujo 2 — Ritual de cierre (Reporte nocturno)**

1. Trigger automático a las 21:00 hora local.
2. Sistema compila: tareas confirmadas, posposiciones, razones registradas.
3. LLM genera: síntesis de qué se hizo + hipótesis curiosa de por qué se pospuso lo que se pospuso + 1 recomendación suave.
4. Mensaje breve en Telegram. Tono: compañero que cierra contigo, no jefe que evalúa.

**Momento wow:** El usuario lee la hipótesis de por qué pospuso algo y piensa "exactamente eso era". El sistema lo conoce.

### 4.4 Anti-features — lo que PPAI no hace en el MVP

- No integra con Google Calendar ni calendarios externos.
- No genera dashboards ni reportes gráficos.
- No usa lenguaje acusatorio ni de evaluación de desempeño.
- No tiene interfaz web visual ni app móvil.
- No promete resolver TDAH, ansiedad ni salud mental.
- No procesa datos sensibles (finanzas, médicos, terceros identificables).
- No opera en CLI en MVP (es Fase 2).
- No implementa rutinas complejas (pomodoro, bloques temáticos, etc.).

---

## 5) Moat Primario — Data Behavioral Moat

**Elección: Data Moat.** Es el único moat que se acumula con el uso y que ningún competidor puede comprar.

La distribución por Telegram es ventaja táctica de tiempo-al-valor. Es lo que permite validar rápido. No es el moat.

### ¿Qué datos genera el loop, semana a semana?

| Semana | Dato acumulado | Por qué importa |
|--------|---------------|-----------------|
| 1 | Primeras confirmaciones y posposiciones por tipo de tarea | Baseline de patrón de ejecución |
| 2 | Razones de bloqueo recurrentes (3+ registros) | Permite hipótesis personalizadas en el reporte |
| 3 | Patrón de energía por hora del día | Calibra cuándo enviar el nudge para máximo impacto |
| 4 | Tasa de reactivación post-snooze | Valida si el loop tiene enganche real o es abandono silencioso |
| 8+ | Perfil de bloqueo individual maduro | Clasificación más precisa, menor necesidad de LLM costoso |

**Flywheel:**
```
Más usuarios activos
       ↓
Más datos de confirmación / bloqueo / energía
       ↓
Clasificación más precisa → nudges mejor timed
       ↓
Mejor retención → más datos → más usuarios
```

---

## 6) UX Paradigm — Assistant con Workflow y Estado

**Paradigma elegido:** Conversational assistant con estado persistente, operando sobre un loop explícito.

**Por qué no "chat libre":** El chat libre (tipo ChatGPT) no mantiene estado entre sesiones ni conduce el ciclo. El usuario tiene que recordar dónde quedó. PPAI sabe exactamente en qué estado está cada tarea.

**Por qué no "app con UI":** El segmento primario no abre apps de productividad. La fricción de cambio de contexto mata el hábito. Telegram intercepta el comportamiento instintivo de captura donde ya ocurre.

**Por qué Telegram específicamente:**
- Cero instalación / onboarding para el usuario.
- Notificaciones push nativas sin configuración.
- Botones inline para `done / snooze / clarify` sin escribir.
- El MVP vive en infraestructura del usuario (no requiere app store approval ni web hosting complejo).

---

## 7) AI Decision Triangle — Trade-offs

```
           CAPABILITY
              /\
             /  \
            /    \
           /      \
          /________\
        COST      SPEED
```

**Trade-off del MVP:**

| Decisión | Elección | Justificación |
|---------|---------|---------------|
| Modelo para clasificación | Pequeño (Haiku / GPT-4o-mini) | Costo < $0.01/tarea. C3 exige accuracy ≥ 75%, no perfección. |
| Modelo para reporte nocturno | Mediano (Sonnet / GPT-4o) | El reporte es el momento de mayor valor percibido; vale más tokens. |
| Latencia de respuesta | < 5 segundos para clasificación | El usuario espera en tiempo real; más lento rompe el feeling de "alguien tomó el caos". |
| Prompt engineering | Prompts cortos y determinísticos | Reduce varianza de output; más fácil auditar el tono del reporte. |

**Hipótesis de costo:** ≤ $0.50/usuario activo/mes con esta arquitectura. *Medir en Semana 1 con uso real.*

---

## 8) Métricas — User Metrics + AI Metrics + Kill Criteria

### User Metrics (comportamiento)

| Métrica | Target | Kill criteria |
|---------|--------|---------------|
| Usuarios activos al Día 5 del MVP de papel | ≥ 2 de 3 | < 2/3 → no construir el bot aún |
| Capturas/día/usuario activo | ≥ 3/día | < 2/día → revisar fricción de captura |
| % tareas con `/done` registrado | ≥ 40% | < 25% → el loop no está cerrando |
| % usuarios que reportan culpa post-reporte | ≤ 33% | > 33% → rediseñar tono del reporte |
| % que califica el reporte como útil | ≥ 60% | < 40% → pivote completo en el flujo de cierre |
| WTP > $8/mes declarado | ≥ 3 de 5 entrevistados | < 3/5 → revisar segmento o modelo de precio |

### AI Metrics (calidad del sistema)

| Métrica | Target | Kill criteria |
|---------|--------|---------------|
| Accuracy de clasificación (tipo/energía) | ≥ 75% sin corrección manual | < 70% → ajustar prompt antes de automatizar |
| Costo LLM / usuario activo / mes | ≤ $1 | > $2 → cambiar modelo o reducir features |
| Latencia de respuesta a captura | < 5 segundos | > 10 segundos → revisar arquitectura |
| Tasa de respuestas con tono acusatorio detectado | 0% | > 0% → audit inmediato de prompt del reporte |

### Métricas de Semana 1 (MVP de papel — antes de código)

- [ ] Día 1–2: Entrevistar 5 personas del Segmento A. Pregunta clave: "¿Cómo resolviste hoy el problema de saber qué hacer primero?"
- [ ] Día 2: Spike técnico — integración LLM + respuesta en Telegram. Si tarda > 2 días, ajustar scope.
- [ ] Día 3–7: MVP de papel — clasificar manualmente tareas de 3 usuarios por 5 días. Medir si siguen al Día 5.
- [ ] Día 3: Correr 30 entradas reales por el LLM elegido. Medir accuracy e instrumentar costo.
- [ ] Día 5: Mostrar Flujo 1 a 5 personas. Preguntar WTP después de verlo funcionar.

**Condición de GO para Semana 2 (construcción):**
> ≥ 2 de 3 usuarios del MVP de papel siguen enviando tareas al Día 5 **Y** al menos 1 pregunta espontáneamente "¿cuándo se automatiza esto?"

---

## 9) Riesgos y Trust Guardrails

### Riesgos principales

| ID | Riesgo | Probabilidad | Impacto | Mitigación |
|----|--------|-------------|---------|-----------|
| C1 | Usuario no mantiene hábito de captura | Alta | Existencial | Mensaje de apertura de día si no hay capturas antes de las 10:00. Fricción mínima (1 mensaje = 1 tarea). |
| C3 | Clasificación IA inexacta (< 75%) | Media | Alto | Ajustar prompt antes de automatizar. Medir en 30 entradas reales en Semana 1. |
| C4 | Reporte nocturno genera culpa | Media | Alto | Prompt audit. Reducir intensidad si usuario reporta culpa. Ver guardrails abajo. |
| C5 | Costo LLM > $2/usuario/mes | Baja-Media | Alto | Modelo pequeño para clasificación. Cache para tareas recurrentes. Medir desde Semana 1. |
| C6 | Competidor clona loop en Telegram | Media | Medio | El moat es el dato acumulado, no el bot. Un clon arranca desde cero en datos. |

### Trust Guardrails — reglas no negociables

**Lenguaje del sistema:**
- Nunca: "fallaste", "no cumpliste", "como siempre", "otra vez", "deberías".
- Siempre: "¿qué pasó?", "parece que hubo algo que lo dificultó", "mañana es otro ciclo".
- El reporte nocturno usa hipótesis curiosas, no evaluaciones.

**Si el usuario expresa culpa o vergüenza:**
- El sistema reconoce sin amplificar ("entendido, fue un día difícil").
- El siguiente nudge reduce intensidad (solo 1 tarea, no 3).
- El siguiente reporte amplifica lo que sí se hizo, minimiza lo que no.

**Claims prohibidos:**
- PPAI no es terapia.
- PPAI no trata TDAH, ansiedad ni ninguna condición de salud mental.
- PPAI no hace promesas de resultado ("serás más productivo en X días").

---

## 10) Canales — Roadmap por fases

### Fase 1 (MVP actual) — Telegram Bot

- **Por qué:** máximo time-to-value, mínimo esfuerzo de integración, canal bidireccional nativo con notificaciones push.
- **Objetivo:** validar el loop completo (capture → confirm → learn → report).
- **Condición de GO a Fase 2:** targets de retención y utilidad de Semana 1 cumplidos.

### Fase 2 — CLI (siguiente integración)

**Condición:** Telegram MVP supera ≥ 2/3 usuarios activos al Día 5 y ≥ 60% utilidad en reporte.

**Por qué CLI es Fase 2 y no parte del MVP:** Un CLI sin daemon de notificaciones es solo captura — no completa el loop. El valor de PPAI está en el ciclo bidireccional. Telegram lo resuelve nativamente; CLI requiere infraestructura adicional (daemon, notificaciones del sistema) que añade complejidad sin validar primero el loop.

**Comandos mínimos (Fase 2):**
```bash
ppai add "terminar módulo 3 del curso"   # Captura desde terminal
ppai now                                  # Muestra tarea prioritaria del momento
ppai done                                 # Cierra tarea activa, registra en el loop
```

El estado del loop se comparte entre Telegram y CLI — el usuario puede capturar en CLI y confirmar en Telegram (o viceversa). Un sistema, un estado.

### Fase 3 — API Web (integraciones)

- Webhooks para automatizaciones y conexiones con flujos externos.
- Solo si Fase 2 CLI valida que el segmento técnico necesita integración profunda.

---

## 11) Business Goals

| Goal | Métrica | Target MVP | Kill criteria |
|------|---------|-----------|---------------|
| Retención de hábito (C1) | Usuarios activos al Día 5 del MVP de papel | ≥ 2 de 3 | < 2/3 → no construir bot; revisar flujo |
| Calidad de clasificación IA (C3) | % correctamente clasificadas sin corrección | ≥ 75% en 30 entradas | < 70% → ajustar prompt primero |
| Impacto del reporte (C4) | Culpa ≤ 33% / Útil ≥ 60% | Ver targets arriba | > 33% culpa → rediseñar tono |
| Señal de demanda / WTP (C2) | WTP > $8/mes tras ver el flujo | ≥ 3 de 5 entrevistados | < 3/5 → pivotar precio o segmento |
| Costo operativo (C5) | Costo LLM real / usuario activo / mes | ≤ $1 | > $2 → cambiar modelo o reducir features |
