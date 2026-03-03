# Supuestos y Riesgos — PPAI

> Este documento registra los supuestos sobre los que se construye el sistema y los riesgos que podrían invalidarlo. Su función es obligar al equipo a tomar decisiones conscientes en lugar de avanzar con creencias no verificadas.

---

## Supuestos clave

Los supuestos están ordenados de mayor a menor impacto en la viabilidad del proyecto. Si los más críticos resultan ser falsos, el proyecto requiere un pivote.

### S1 — El usuario quiere ayuda externa para organizarse
**Supuesto:** Existe un segmento de personas que reconocen su problema de procrastinación y están dispuestas a delegar parte de su planificación a un sistema automatizado.

**Evidencia a buscar:** Entrevistas con al menos 5 usuarios en la primera semana donde expresen frustración activa con su organización actual.

**Señal de que es falso:** Los usuarios prefieren resolver el problema "a su manera" o ven el sistema como una amenaza a su autonomía.

---

### S2 — La entrada por lenguaje natural reduce la fricción de captura
**Supuesto:** Escribir `"Estudiar streams 30 min"` en un CLI o Telegram es suficientemente fácil como para que el usuario lo haga de forma habitual, sin necesitar una interfaz visual.

**Evidencia a buscar:** El usuario captura al menos 3 entradas por día durante la semana de prueba (Semana 4).

**Señal de que es falso:** El usuario olvida usar el sistema o lo usa menos de una vez al día porque "es un paso extra".

---

### S3 — La IA puede clasificar tareas con suficiente precisión
**Supuesto:** Un LLM como Claude o GPT puede clasificar correctamente el tipo, duración y nivel de energía de una tarea expresada en lenguaje coloquial en al menos el 80% de los casos.

**Evidencia a buscar:** Prueba de clasificación con 30 entradas reales del usuario antes de la Semana 3.

**Señal de que es falso:** Más del 30% de clasificaciones son incorrectas o requieren corrección manual constante, generando más fricción de la que resuelven.

---

### S4 — El plan de 3 tareas clave es aceptado por el usuario
**Supuesto:** El usuario acepta trabajar con un plan limitado (máximo 3 tareas prioritarias por día) y no siente que el sistema "le falta" al no incluir todas sus ideas.

**Evidencia a buscar:** El usuario ejecuta al menos 2 de las 3 tareas clave durante la semana de validación.

**Señal de que es falso:** El usuario sobreescribe el plan constantemente o siente que el sistema no refleja su realidad.

---

### S5 — El reporte nocturno genera valor percibido
**Supuesto:** Recibir un análisis automático al final del día de qué se hizo y qué se evitó es suficientemente valioso como para que el usuario lo lea y lo use para ajustar su comportamiento.

**Evidencia a buscar:** El usuario menciona espontáneamente el reporte como algo útil durante el feedback de la Semana 4.

**Señal de que es falso:** El usuario ignora o descarta el reporte nocturno sin leerlo.

---

### S6 — La detección de fricción es accionable
**Supuesto:** PPAI puede identificar patrones de procrastinación (tiempo muerto, tareas evitadas repetidamente) y ofrecer estrategias concretas que el usuario percibe como útiles, no como juicio.

**Evidencia a buscar:** Al menos 1 caso documentado donde la sugerencia del sistema llevó al usuario a retomar una tarea evitada.

**Señal de que es falso:** El usuario siente que el sistema "lo regaña" o las sugerencias son demasiado genéricas para ser útiles.

---

## Riesgos del proyecto

### R1 — Abandono temprano (riesgo de adopción)
**Descripción:** El usuario prueba el sistema los primeros días pero lo abandona antes de que se convierta en hábito.

**Probabilidad:** Alta — los hábitos digitales nuevos tardan entre 14 y 21 días en consolidarse.

**Impacto:** Crítico — sin uso continuo no hay datos, sin datos no hay aprendizaje, sin aprendizaje no hay valor.

**Mitigación:**
- Diseñar el onboarding para generar valor en el primer día de uso.
- El sistema debe ser útil desde la primera captura, sin necesidad de "entrenamiento previo".
- Recordatorios de reenganche si el usuario no interactúa en más de 24 horas.

---

### R2 — El sistema añade más fricción de la que quita (riesgo de UX)
**Descripción:** El proceso de captura, corrección de clasificaciones y lectura de reportes resulta más pesado que simplemente usar una nota mental o papel.

**Probabilidad:** Media — especialmente si la entrada por CLI resulta intimidante para perfiles no técnicos.

**Impacto:** Alto — invalida la propuesta de valor central.

**Mitigación:**
- Priorizar Telegram sobre CLI si el perfil de usuario no es técnico.
- Mantener el flujo de captura en máximo 2 pasos: escribir → confirmar.
- Eliminar cualquier configuración obligatoria antes del primer uso.

---

### R3 — Scope creep durante el MVP (riesgo de ejecución)
**Descripción:** El equipo intenta construir todas las funcionalidades de la visión completa en las 4 semanas, resultando en un sistema parcialmente funcional en todo en lugar de completamente funcional en lo esencial.

**Probabilidad:** Alta — la idea tiene muchas funcionalidades atractivas que compiten entre sí.

**Impacto:** Alto — un MVP incompleto no permite validar ningún supuesto con confianza.

**Mitigación:**
- El alcance del MVP está congelado en `00_resumen_idea.md`. Cualquier adición requiere aprobación explícita.
- Cada semana comienza con una revisión del backlog para confirmar prioridades.
- La regla: si no está en la tabla "Incluido en MVP", no se toca en estas 4 semanas.

---

### R4 — Privacidad y confianza (riesgo de adopción)
**Descripción:** El usuario no se siente cómodo enviando sus tareas, ideas y patrones de comportamiento a un sistema que las procesa con IA externa.

**Probabilidad:** Baja-Media — depende del perfil del usuario y del LLM usado.

**Impacto:** Medio — puede limitar el segmento de usuarios dispuestos a probarlo.

**Mitigación:**
- Ser transparente sobre qué datos se envían al LLM y cuáles se almacenan localmente.
- En el MVP, priorizar almacenamiento local (SQLite) sobre cloud.
- No recopilar datos sensibles (nombres de terceros, información financiera detallada).

---

### R5 — Fatiga de notificaciones (riesgo de producto)
**Descripción:** Los recordatorios inteligentes se perciben como interrupciones molestas, llevando al usuario a silenciarlos o desinstalar el bot.

**Probabilidad:** Media — es un error común en apps de productividad.

**Impacto:** Medio — degradaría la experiencia sin destruir el producto.

**Mitigación:**
- Regla de diseño: máximo 3 notificaciones activas por día en el MVP.
- El usuario puede configurar su ventana de silencio (ej. 22:00–08:00).
- El reporte nocturno es la única notificación no negociable; el resto son opt-in.

---

### R6 — Dependencia de APIs externas (riesgo técnico)
**Descripción:** El sistema depende de APIs de LLMs (OpenAI/Anthropic) y Telegram que pueden cambiar costos, políticas o disponibilidad sin previo aviso.

**Probabilidad:** Baja para el MVP de 4 semanas; mayor a largo plazo.

**Impacto:** Medio — un cambio de precios puede hacer inviable la operación a escala.

**Mitigación:**
- Diseñar la capa de IA como un módulo intercambiable (no acoplado al proveedor).
- Estimar costos de API para el volumen de uso esperado antes de la Semana 3.
- Tener un proveedor alternativo identificado (ej. si se usa Claude, tener GPT como fallback y viceversa).

---

## Matriz de prioridad

| ID | Supuesto/Riesgo | Probabilidad | Impacto | Prioridad de validación |
|----|---|---|---|---|
| S1 | Usuario quiere ayuda externa | Media | Crítico | Semana 1 |
| S2 | Lenguaje natural reduce fricción | Media | Crítico | Semana 2 |
| S3 | IA clasifica con precisión | Media | Alto | Semana 2 |
| R1 | Abandono temprano | Alta | Crítico | Semana 4 |
| R3 | Scope creep | Alta | Alto | Ongoing |
| S4 | Plan de 3 tareas es aceptado | Baja | Alto | Semana 4 |
| S5 | Reporte nocturno genera valor | Baja | Medio | Semana 4 |
| R2 | Sistema añade fricción | Media | Alto | Semana 2-3 |
| R5 | Fatiga de notificaciones | Media | Medio | Semana 3 |
| R4 | Privacidad y confianza | Baja | Medio | Semana 1 |
| R6 | Dependencia de APIs | Baja | Medio | Semana 3 |
| S6 | Detección de fricción es accionable | Baja | Medio | Semana 4 |

---

## Protocolo de revisión

- **Frecuencia:** Al inicio de cada semana se revisa este documento.
- **Acción si un supuesto se invalida:** Documentar el hallazgo, evaluar impacto en el plan y decidir explícitamente si se pivota o se continúa con la estrategia ajustada.
- **Responsable:** El equipo completo. No es un documento de un solo autor.
