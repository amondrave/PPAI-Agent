# Product Vision Board — PPAI
Fecha: 2026-03-03
Versión: 1.1
Estado: Draft
Author: Angel Yesid Mondragon

---

## 1) Vision

> **¿Por qué existe PPAI y a qué aspira?**

PPAI existe porque el problema de la procrastinación no es de organización — es de ejecución.
Las herramientas actuales te ayudan a registrar lo que ya decidiste hacer. PPAI trabaja sobre por qué no lo estás haciendo.

**Aspiración:** Ser el sistema que convierte intenciones dispersas en acciones concretas, usando el canal que el usuario prefiera — sin apps nuevas, sin configuración, sin culpa.

---

## 2) Target Group

### Primario — Freelancer / Developer solopreneur
- **Quién es:** Desarrollador, diseñador o consultor independiente. 25–38 años.
- **Contexto:** Trabaja desde casa. Sin estructura laboral externa que le diga qué hacer ni cuándo. Mezcla proyectos de clientes con aprendizaje y proyectos personales. Su tiempo es su único activo — la procrastinación tiene costo directo en ingresos.
- **Herramientas actuales:** Según perfil: CLI o Telegram para comunicación diaria + Notion o Todoist (abandonado en < 30 días) + notas de voz o mensajes a sí mismo (captura instintiva).
- **Dolor principal:** No es que no sepa qué hacer — sabe exactamente qué debería hacer y aun así no arranca. La fricción de ejecución es diaria, repetitiva y genera culpa acumulada.
- **Trigger de mayor dolor:** Lunes por la mañana o después de un día improductivo. El usuario abre Notion, ve la lista, se paraliza, y termina haciendo algo que no estaba en ninguna lista.
- **Canal preferido:** Usuario técnico → CLI; usuario conversacional → Telegram; integración con sistema propio → API Web.

### Secundario — Estudiante universitario / autodidacta intensivo
- **Quién es:** 18–26 años. Estudia una carrera + aprende por cuenta propia. Alta carga cognitiva, bajos ingresos.
- **Diferencia vs primario:** No paga (o paga muy poco). Es el canal de distribución orgánica — comparte en su grupo y trae usuarios del Segmento A.
- **Canal preferido:** Telegram principalmente; adopta CLI si tiene perfil técnico.
- **Por qué podría pagar:** Si hay tier gratuita funcional y la tier de pago desbloquea el reporte nocturno + análisis de fricción.

---

## 3) Needs — validables en 7 días

> Formato: Need + cómo medirlo + supuesto crítico vinculado

**Need #1 — Claridad de próxima acción inmediata**
> "No sé por dónde empezar" es el estado más frecuente y más paralizante.
- El usuario necesita que algo le diga qué es lo siguiente, ahora, en el canal donde ya está trabajando.
- **Medición (7 días):** % de usuarios que ejecutan ≥ 1 tarea en la primera hora después de recibir el plan.
- **Supuesto vinculado:** SC1 — el usuario puede mantener el hábito de capturar tareas.

**Need #2 — Captura sin fricción ni cambio de contexto**
> El usuario ya captura en notas de voz, stickies o mensajes a sí mismo. El problema es que esas capturas nunca se convierten en plan.
- PPAI debe interceptar ese comportamiento instintivo — desde CLI, bot conversacional o API — y convertirlo en acción, no añadir un paso más.
- **Medición (7 días):** Promedio de capturas/día/usuario activo. Target: ≥ 3/día.
- **Supuesto vinculado:** SC1, SC3 — el canal reduce fricción y la IA clasifica bien.

**Need #3 — Cierre del día con insight, no con culpa**
> El usuario que tuvo un día malo no quiere un resumen de sus fracasos. Quiere entender qué pasó y cómo hacerlo diferente mañana.
- El reporte nocturno debe funcionar como un espejo curioso, no como un juez — independientemente del canal por el que llegue.
- **Medición (7 días):** ≤ 1 de cada 3 usuarios reporta sentir culpa o vergüenza. ≥ 60% lo califica como útil.
- **Supuesto vinculado:** SC4 — el reporte genera insight, no culpa.

**Need #4 — Plan que respeta la energía disponible**
> No todas las tareas son iguales. El usuario necesita un plan que reconozca cuándo tiene energía para qué tipo de trabajo.
- **Medición (7 días):** % de usuarios que ejecutan ≥ 2 de las 3 tareas clave del plan diario. Target: > 60%.
- **Supuesto vinculado:** SC3 — clasificación de energía/tipo funciona correctamente.

---

## 4) Product

### 4.1 Value Proposition

> **"PPAI convierte mensajes sueltos en un plan ejecutable y un ritual de cierre útil — desde el canal que prefieras, sin instalar nada, sin migrar tareas."**

Lo que nos diferencia de cada alternativa:

| Alternativa | Qué resuelve | Qué no resuelve | Gap que PPAI cubre |
|---|---|---|---|
| Motion / Reclaim | Reorganiza el calendario si fallas | No trabaja la fricción de ejecución | La capa de comportamiento |
| Todoist / Notion | Registra lo que decidiste hacer | No actúa si no ejecutas | La conversión de lista a acción |
| Papel / notas | Cero fricción de captura | No genera plan ni análisis | Automatización del paso "captura → plan" |
| Mensajes a sí mismo | Captura instintiva natural | Las notas nunca se convierten en acciones | El ritual de cierre y el análisis |

### 4.2 Canales (roadmap por fases)

#### Fase 1 (MVP) — Telegram Bot (único canal)
- **Por qué:** máximo “time-to-value” y mínimo esfuerzo de integración.
- **Caso de uso:** captura en lenguaje natural + respuesta inmediata + reporte nocturno.
- **Objetivo:** validar hábito (SC1), clasificación (SC3) y tono del reporte (SC4).

#### Fase 2 (Post-MVP) — CLI (siguiente integración)
- **Por qué:** el segmento primario técnico vive en terminal; reduce aún más el cambio de contexto.
- **Caso de uso:** captura ultra-rápida (`ppai add "..."`) + consulta de “top 3” del día.
- **Dependencia:** solo se implementa si el MVP en Telegram supera los targets de retención y utilidad.

#### Fase 3 (Futuro) — API Web (integraciones)
- **Por qué:** habilita automatizaciones e integraciones con flujos externos.
- **Caso de uso:** webhooks, scripts, conexiones con herramientas existentes.

### 4.3 MVP — 2 Flujos Core

#### Flujo Core #1 — Captura → Plan del día
- **Disparador:** El usuario envía una o varias tareas en lenguaje libre — por CLI, bot o API — en cualquier momento del día.
- **Entrada:** Texto coloquial. Sin formato. Sin categorías.
  ```
  "Terminar módulo 3 del curso"
  "Llamar al banco"
  "Idea: app de notas con voz"
  ```
- **Transformación:** LLM clasifica tipo / energía requerida / duración estimada. Decide qué es para hoy y qué va al backlog. Prioriza las 3 tareas clave del día.
- **Salida:** Respuesta en el canal usado con el plan del día: 3 tareas clave ordenadas por energía + bloque horario sugerido + N tareas secundarias opcionales.
- **Momento wow:** El usuario recibe su plan en < 30 segundos. Siente que alguien tomó el caos de su cabeza y lo organizó.
- **Métrica de éxito:** ≥ 60% de usuarios ejecutan ≥ 2 de las 3 tareas clave ese mismo día.

#### Flujo Core #2 — Ritual de cierre (Reporte nocturno)
- **Disparador:** Trigger automático a las 21:00 hora local del usuario.
- **Entrada:** Historial del día — tareas capturadas, confirmaciones de completado, ausencias de confirmación.
- **Transformación:** LLM genera resumen de qué se hizo, qué se pospuso, y una hipótesis curiosa (no acusatoria) de por qué. Incluye 1 recomendación suave para mañana.
- **Salida:** Mensaje breve en el canal preferido del usuario. Tono: compañero que hace el cierre contigo, no jefe que evalúa tu desempeño.
- **Momento wow:** El usuario lee la hipótesis de por qué pospuso algo y piensa "exactamente eso era". El sistema lo conoce.
- **Métrica de éxito:** ≥ 70% de apertura / lectura en D1–D7. ≥ 60% lo califica como útil en feedback de Semana 4.

### 4.4 Anti-features — lo que PPAI no hace en el MVP

- No integra con Google Calendar ni calendarios externos.
- No "regaña" al usuario ni usa lenguaje de fracaso.
- No requiere migrar tareas desde otras apps.
- No tiene interfaz web visual ni app móvil.
- No genera reportes gráficos ni dashboards.
- No promete resolver TDAH, ansiedad o salud mental.
- No procesa datos sensibles (finanzas detalladas, nombres de terceros, información médica).
- En el MVP solo hay 1 canal: Telegram (CLI es post-MVP).

---

## 5) Business Goals — medibles en 7–14 días

> Estos son los números mínimos para decidir si se avanza, se pivota o se detiene. Sin números, no hay decisión.

| Goal | Métrica | Target MVP | Kill criteria si no se alcanza |
|---|---|---|---|
| **Retención de hábito** (SC1) | Usuarios que siguen enviando tareas al Día 5 del MVP de papel | ≥ 2 de 3 usuarios | Si < 2/3 → no construir el bot aún; revisar el flujo |
| **Calidad de clasificación IA** (SC3) | % de tareas clasificadas correctamente sin corrección | ≥ 75% en 30 entradas reales | Si < 70% → ajustar prompt antes de automatizar |
| **Impacto del reporte nocturno** (SC4) | % que reporta culpa / % que lo encuentra útil | ≤ 33% culpa / ≥ 60% útil | Si > 33% culpa → rediseñar tono del reporte |
| **Señal de demanda / WTP** (SC2) | Usuarios que declaran WTP > $8/mes tras ver el flujo en vivo | ≥ 3 de 5 entrevistados | Si < 3/5 → pivotar modelo de precio o segmento |
| **Costo operativo** (SC5) | Costo LLM real por usuario activo/mes con uso real medido | ≤ $1/usuario/mes | Si > $2 → cambiar modelo de LLM o reducir features |

---

## 6) Próximos pasos — Semana 1

> Antes de escribir una línea de código.

- [ ] **Día 1–2:** Entrevistar 5 personas del Segmento A. Pregunta clave: "¿Cómo resolviste hoy el problema de saber qué hacer primero?" y "¿Qué canal usarías: CLI, Telegram o algo más?"
- [ ] **Día 2:** Spike técnico — integración LLM + respuesta en el canal más rápido de implementar. Si tarda > 2 días, ajustar el scope.
- [ ] **Día 3–7:** MVP de papel — clasificar manualmente tareas de 3 usuarios durante 5 días (por el canal que cada uno prefiera). Medir si siguen usándolo al Día 5.
- [ ] **Día 3:** Correr 30 entradas reales por el LLM elegido. Medir accuracy antes de automatizar.
- [ ] **Día 5:** Mostrar el Flujo #1 (mockup o versión manual) a 5 personas del Segmento A. Preguntar WTP después de verlo funcionar.

**Condición de GO para Semana 2 (construcción):**
> ≥ 2 de 3 usuarios del MVP de papel siguen enviando tareas al Día 5 **Y** al menos 1 pregunta espontáneamente "¿cuándo se automatiza esto?"
