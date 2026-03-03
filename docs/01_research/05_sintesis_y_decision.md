# Síntesis y Decisión — PPAI
Fecha: 2026-03-03
Versión: 1.0

---

## Top 5 argumentos PRO

| # | Argumento | Fuerza |
|---|---|---|
| P1 | **El gap es real y sin dueño.** Ningún competidor (Motion, Reclaim, Todoist) trabaja la capa de comportamiento — solo reorganizan lo que el usuario ya decidió hacer. La "fricción de ejecución" no tiene incumbente claro. | Alta |
| P2 | **El canal ya existe.** Telegram es el canal de comunicación habitual en el segmento técnico latinoamericano. PPAI no pide un cambio de herramienta — entra donde el usuario ya vive. | Alta |
| P3 | **El mercado ya paga por la categoría.** Motion, Reclaim y BeforeSunset demuestran WTP real por productividad con IA. PPAI no necesita crear el mercado, solo capturar el segmento insatisfecho. | Media-Alta |
| P4 | **Costo técnico de entrada es bajo.** LLMs como Claude Haiku o GPT-4o-mini permiten construir el motor de clasificación en días, no meses. El tiempo de ejecución técnica es favorable para el builder solo. | Media |
| P5 | **El reporte nocturno como ritual de cierre es un diferenciador emocional.** Ningún competidor ofrece un espejo de comportamiento diario. Si el tono es correcto, crea el único feature de retención que importa: el usuario espera el mensaje. | Media |

---

## Top 5 argumentos CON

| # | Argumento | Letalidad |
|---|---|---|
| C1 | **La paradoja del procrastinador.** El usuario con mayor dolor es el menos capaz de mantener el hábito de usar cualquier herramienta nueva. El sistema depende de la disciplina que promete reemplazar. | Crítica |
| C2 | **No hay moat.** Todo el sistema es un prompt y una integración de Telegram. Cualquier developer lo replica en un fin de semana. Sin retención alta que genere datos propietarios, no hay defensa ante competencia capitalizada. | Crítica |
| C3 | **La categoría tiene un problema estructural de abandono.** Productos con $10M+ de inversión no resolvieron la retención D30 > 25% en productividad personal. Un MVP de 4 semanas no tiene ventaja estructural para superar ese benchmark. | Alta |
| C4 | **El reporte de fricción puede hacer daño.** Señalar tareas evitadas repetidamente puede intensificar el ciclo de culpa-procrastinación en lugar de romperlo. Si el feature más diferenciador hace daño, el producto tiene un problema ético y de negocio simultáneo. | Alta |
| C5 | **El scope de 4 semanas es agresivo para 1 builder.** Telegram + LLM + persistencia + scheduling + reporte nocturno automático son 5 integraciones con sus propios casos borde. El riesgo real es llegar a Semana 4 con nada completamente funcional. | Alta |

---

## Supuestos críticos — los que, si son falsos, matan la idea

| ID | Supuesto | Estado | Cómo validar en Semana 1 |
|---|---|---|---|
| **SC1** | El usuario procrastinador puede mantener el hábito de capturar tareas en Telegram durante > 7 días | **No validado** — es la pregunta más importante | MVP de papel: el builder clasifica manualmente tareas de 3 usuarios durante 5 días. Si siguen usándolo, el hábito existe. |
| **SC2** | El Segmento A (freelancer técnico) declara WTP > $8/mes después de experimentar el valor | **No validado** | Mostrar el flujo en vivo a 5 personas y preguntar precio. No antes de que lo vean funcionar. |
| **SC3** | La IA clasifica correctamente > 75% de las tareas en lenguaje coloquial sin corrección manual | **No validado** | Correr 30 entradas reales por el LLM elegido y revisar manualmente antes de construir la automatización. |
| **SC4** | El reporte nocturno genera insight, no culpa | **No validado** — riesgo emocional real | Después de 3 días de uso, preguntar: "¿Cómo te hizo sentir el reporte?" Si > 1/3 dice culpa, rehacer el tono. |
| **SC5** | El builder puede entregar los 2 flujos core (sin integración de calendario) en < 3 semanas | **No validado** | Hacer un spike técnico en Día 1: bot de Telegram + clasificación LLM + respuesta. Si tarda > 2 días, ajustar el scope. |

---

## Decisión provisional

```
PIVOT — antes de construir, validar SC1 y SC3.
```

**Lógica:**

- Los argumentos PRO son reales y el gap de mercado existe.
- Los argumentos CON no matan la idea — matan el *approach* de construir primero y validar después.
- El error estratégico más probable es **escribir código durante 4 semanas para descubrir en la Semana 5 que el usuario usó el bot 2 días y lo olvidó**.

**El pivot no es de idea — es de método:**

| Lo que se planea hacer | Lo que se debe hacer primero |
|---|---|
| Construir bot de Telegram en Semana 2 | Hacer MVP de papel durante 5 días con 3 usuarios reales |
| Integrar LLM para clasificación | Clasificar manualmente y medir si el plan es útil |
| Construir reporte nocturno en Semana 3 | Enviar el reporte manualmente (texto en Telegram) y medir apertura + reacción |
| Validar en Semana 4 | Validar en Semana 1 — construir solo si hay señal positiva |

**Condición para GO completo:**
> Si después de 5 días de MVP de papel, ≥ 2 de 3 usuarios siguen enviando tareas y al menos 1 pregunta "¿cuándo se automatiza esto?", el supuesto de comportamiento está validado. Entonces construir.

**Condición para NO-GO:**
> Si ningún usuario mantiene el hábito más de 3 días en el MVP de papel, el problema no es de producto — es de comportamiento humano que ninguna herramienta resolverá en 4 semanas.
