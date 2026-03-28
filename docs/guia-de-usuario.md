# PPAI — Guia de Usuario

**Tu asistente de productividad personal en Telegram.**

PPAI observa, planifica, ejecuta y evalua tus actividades diarias. Usa inteligencia artificial para entender tus tareas, detectar cuando procrastinas, y ayudarte a ser mas productivo sin presionarte.

---

## Tabla de contenidos

0. [Requisitos previos](#0-requisitos-previos)
1. [Primeros pasos](#1-primeros-pasos)
2. [Capturar tareas](#2-capturar-tareas)
3. [Top 3 del dia](#3-top-3-del-dia)
4. [Gestionar tareas](#4-gestionar-tareas)
5. [Conectar Google Calendar](#5-conectar-google-calendar)
6. [Planificar tu dia](#6-planificar-tu-dia)
7. [Notificaciones inteligentes](#7-notificaciones-inteligentes)
8. [Modo Zen](#8-modo-zen)
9. [Configuracion avanzada](#9-configuracion-avanzada)
10. [Referencia rapida de comandos](#10-referencia-rapida-de-comandos)
11. [Tips para sacarle el maximo](#11-tips-para-sacarle-el-maximo)

---

## 0. Requisitos previos

### Que necesitas

- **Telegram** instalado en tu celular o computadora (iOS, Android, Windows, Mac, Linux o Web)
- Una **cuenta de Telegram** activa
- (Opcional) Una **cuenta de Google** si quieres conectar tu calendario

### Como encontrar el bot

1. Abre Telegram
2. Toca el icono de busqueda (lupa)
3. Busca: **`@PPAIDevBot`**
4. Toca el resultado para abrir el chat
5. Presiona **Iniciar** (o escribe `/start`)

> Si no encuentras el bot, usa el link directo:
> `https://t.me/PPAIDevBot`

### Importante antes de empezar

- PPAI se comunica en **espanol**
- Puedes escribirle tareas en cualquier idioma, pero los mensajes del bot son en espanol
- Todo lo que escribas se guarda de forma segura y encriptada
- Nadie mas puede ver tus tareas ni tu calendario

---

## 1. Primeros pasos

### Iniciar el bot

Al abrir el chat con PPAI, envia `/start`. El bot te guiara por un onboarding de 7 pasos:

| Paso | Pregunta | Ejemplo de respuesta |
|------|----------|---------------------|
| 1 | Tu nombre | `Angel` |
| 2 | A que te dedicas | `Ingeniero de software` |
| 3 | Hora de inicio de jornada | `08:00` |
| 4 | Hora de fin de jornada | `17:00` |
| 5 | Bloques protegidos (almuerzo, ejercicio) | `12:00-13:00 almuerzo` o `no` |
| 6 | Estilo de comunicacion | `1`, `2` o `3` (ver abajo) |
| 7 | Confirmacion | `Si` |

### Estilos de comunicacion

Elige como quieres que PPAI te hable. Esto afecta **todos** los mensajes del bot:

| Estilo | Descripcion | Ejemplo de nudge |
|--------|-------------|------------------|
| **1. Gentle** | Amable y comprensivo | "Tu siguiente paso podria ser: Revisar PR" |
| **2. Direct** | Al grano, sin rodeos | "Revisar PR — siguiente." |
| **3. Confrontational** | Retador, te empuja a actuar | "Esto va primero: Revisar PR. Arranca ya." |

Puedes cambiar tu estilo en cualquier momento con `/config estilo gentle`.

### Reconfigurar el perfil

- `/setup` — reinicia el onboarding completo
- `/perfil` — muestra tu perfil actual
- `/cancel` — cancela el onboarding si estas a mitad

---

## 2. Capturar tareas

**Simplemente escribe tu tarea como texto libre.** PPAI la captura automaticamente.

```
Revisar los PRs del equipo
```

PPAI responde: *"Capturado. Tu tarea ha sido registrada."*

### Capturar varias tareas a la vez

Escribe una tarea por linea:

```
Revisar PRs del equipo
Preparar presentacion del viernes
Comprar cafe
```

PPAI captura las 3 y te confirma cuantas registro.

### Clasificacion inteligente (IA)

Al capturar, PPAI usa inteligencia artificial para:

- **Categorizar** tu tarea (trabajo, personal, aprendizaje, salud, social, mandado)
- **Estimar** cuanto tiempo tomara (15, 30, 45, 60, 90 o 120 min)
- **Evaluar urgencia** (alta, media, baja)

La IA usa tu ocupacion para entender mejor el contexto. Si escribes "hacer deploy", y eres ingeniero de software, sabe que es trabajo y estima 30 min.

### Tags y fechas

Puedes agregar contexto extra:

| Formato | Ejemplo | Efecto |
|---------|---------|--------|
| `#tag` | `Revisar PRs #work` | Agrega etiqueta |
| `para hoy` | `Entregar reporte para hoy` | Deadline: hoy |
| `para manana` | `Llamar al banco para manana` | Deadline: manana |
| `urgente` | `Urgente: fix en produccion` | Deadline: hoy |
| `para 15/04` | `Preparar slides para 15/04` | Deadline: 15 de abril |

---

## 3. Top 3 del dia

Envia `/top3` para ver tus 3 tareas mas importantes del dia.

PPAI las prioriza automaticamente considerando:
- **Urgencia** — tareas con deadline cercano van primero
- **Antiguedad** — tareas que llevan dias pendientes suben
- **Posposiciones** — tareas pospuestas varias veces suben en prioridad

Cada tarea aparece con 3 botones:

| Boton | Accion |
|-------|--------|
| **[Hecho]** | Marcar como completada (pide confirmacion) |
| **[Posponer]** | Posponer 1 hora (max 3 veces) |
| **[Aclarar]** | Pedir mas informacion |

---

## 4. Gestionar tareas

### Completar una tarea

1. En `/top3`, presiona **[Hecho]**
2. PPAI pregunta: *"Confirmas?"* con botones **[Si]** / **[No]**
3. Al confirmar: *"Anotado."*

### Posponer una tarea

1. Presiona **[Posponer]**
2. La tarea se congela 1 hora y luego vuelve a PENDING
3. Puedes posponer maximo **3 veces** por tarea
4. Al tercer intento, PPAI activa automaticamente el flujo de aclaracion

### Aclarar una tarea

1. Presiona **[Aclarar]**
2. PPAI pregunta: *"Que necesitas saber sobre esta tarea?"*
3. Responde con texto libre (ej: "No tengo claro el alcance")
4. La tarea se actualiza y vuelve a PENDING con el snooze reseteado

---

## 5. Conectar Google Calendar

Conecta tu calendario para que PPAI vea tus eventos y planifique alrededor de ellos.

### Paso a paso

1. Envia `/calendar`
2. PPAI te muestra un link de **"Autorizar Google Calendar"**
3. Abre el link en tu navegador e inicia sesion con Google
4. Autoriza el acceso a tu calendario
5. Google te redirige a una pagina que **no carga** — eso es normal
6. En la barra de direccion veras algo como: `http://localhost/?code=4/0Aci98E-xxxx...`
7. Copia el valor despues de `code=` (o la URL completa, PPAI extrae el codigo solo)
8. Pega el codigo en el chat de Telegram
9. PPAI verifica la autorizacion y confirma la conexion mostrando tus proximos eventos

> **Nota:** Tienes 5 minutos para completar el proceso. Si se pasa el tiempo, envia `/calendar` de nuevo.
> Si algo falla, puedes pegar el codigo con o sin el prefijo `code=`.

### Que hace PPAI con tu calendario

- **Lee** tus eventos para detectar horarios ocupados
- **Planifica** bloques de trabajo en los huecos libres
- **Crea** eventos `[PPAI]` cuando confirmas un plan
- **Detecta** cambios (eventos cancelados/movidos) y te avisa
- **Nunca** modifica ni elimina tus eventos existentes

---

## 6. Planificar tu dia

### Generar el plan

```
/plan           → Plan de hoy
/plan tomorrow  → Plan de manana
```

PPAI analiza tus eventos de Google Calendar, encuentra huecos libres, y asigna tus tareas pendientes a esos huecos respetando:

- Tu horario laboral
- Tus bloques protegidos (almuerzo, ejercicio)
- La categoria y duracion estimada de cada tarea
- Un buffer de 10 min entre bloques

### Leer el plan

El plan muestra tus eventos y bloques con iconos de estado:

| Icono | Significado |
|-------|-------------|
| **Planned** | Bloque planificado, aun no empezado |
| **In progress** | Bloque en curso |
| **Completed** | Bloque completado |
| **Skipped** | Bloque omitido |

Y la categoria de cada bloque:

| Icono | Categoria |
|-------|-----------|
| Trabajo | work |
| Personal | personal |
| Aprendizaje | learning |
| Salud | health |
| Social | social |
| Mandado | errand |

### Gestionar bloques

Cada bloque tiene botones:
- **[Completado]** — marca el bloque como hecho
- **[Omitir]** — salta el bloque

---

## 7. Notificaciones inteligentes

PPAI te envia notificaciones proactivas en 6 momentos clave. **Todas respetan tu ventana de silencio y dias libres.**

### 7.1. Mensaje matutino

Al inicio de tu jornada, PPAI te saluda con tu Top 3 y contexto del dia. Si la IA esta activa, el mensaje es dinamico y personalizado a tu situacion.

### 7.2. Recordatorio de bloques

**5 minutos antes** de cada bloque planificado:

> *"Tu bloque 'Revisar PRs' empieza en 5 min."*

Botones:
| Boton | Accion |
|-------|--------|
| **[Empezar]** | Marca el bloque como en progreso |
| **[Retrasar 15min]** | Pospone el recordatorio |
| **[Omitir]** | Salta el bloque |

**Al terminar** el bloque:

> *"Bloque 'Revisar PRs' termino. Como fue?"*

Botones:
| Boton | Accion |
|-------|--------|
| **[Completado]** | Bloque exitoso |
| **[Necesito mas tiempo]** | Sigue trabajando |
| **[Sin progreso]** | Registra friccion |

### 7.3. Detector de friccion (tareas estancadas)

Si una tarea lleva **3 o mas dias** en tu Top 3 sin completarse, PPAI interviene:

**Sin IA (fallback):**
> *"'Refactorizar API' lleva 5 dias en tu Top 3. Que quieres hacer con ella?"*

**Con IA (ER4):**
> *"'Refactorizar API' lleva 5 dias en tu Top 3.*
>
> *La tarea parece demasiado ambigua — no tienes claro el primer paso.*
>
> *Estrategias:*
> *1. Dedica 15 min a leer solo la documentacion del endpoint*
> *2. Escribe el test antes que el codigo*
> *3. Pide pair programming a un companero*
>
> *Micro-accion (15 min): Abre el archivo y lee las primeras 20 lineas del endpoint."*

Botones:
| Boton | Accion |
|-------|--------|
| **[Dividir]** | PPAI te pide sub-tareas separadas por coma |
| **[Necesito info]** | Marca como "necesita informacion" |
| **[Eliminar]** | Elimina la tarea |
| **[Pomodoro 25min]** | Crea un bloque inmediato de 25 min |

### 7.4. Detector de huecos en calendario

Si un evento de Google Calendar se cancela o mueve, y queda un hueco de 15+ minutos:

> *"Se libero un espacio de 45 min. Que quieres hacer?"*

Botones:
| Boton | Accion |
|-------|--------|
| **[Reasignar tarea]** | Muestra tu Top 3 para elegir |
| **[Continuar]** | Sigue con lo que estabas |
| **[Descansar]** | Toma un break |

### 7.5. Check-in de medio dia

Si a mitad de tu jornada no completaste ningun bloque:

> *"Ya vamos a mitad de dia y no hay bloques completados. Como quieres seguir?"*

Botones:
| Boton | Accion |
|-------|--------|
| **[Tarde de recuperacion]** | PPAI te avisa del siguiente bloque |
| **[Surgio algo]** | Captura lo que surgio como tarea |
| **[Ayuda]** | Muestra tu Top 3 con opcion de dividir |
| **[Arrancar ya]** | Motivacion para empezar ahora |

### 7.6. Resumen de cierre

Al final de tu jornada, PPAI envia un resumen del dia:

- Tareas completadas, pendientes y pospuestas
- Si no completaste nada, incluye una sugerencia de "rescate" con una micro-accion

### 7.7. Reporte semanal

Cada **lunes por la manana** (o domingo si tu modo fin de semana no es descanso):

**Sin IA:**
- Tareas completadas, pospuestas, pendientes
- Bloques completados vs planificados
- Dia mas y menos productivo
- Patron detectado y sugerencia

**Con IA (ER4):**
- Todo lo anterior, mas:
- Que salio bien (con datos concretos, ej: "Completaste 12 tareas, 50% mas que la semana pasada")
- Patron problematico especifico (ej: "Los jueves no completaste ningun bloque por reuniones")
- Sugerencia concreta (ej: "Bloquea 2h sin reuniones los jueves")
- Pregunta reflexiva (ej: "Que reuniones del jueves podrias cancelar?")

---

## 8. Modo Zen

El modo zen activa nudges frecuentes para sesiones de trabajo enfocado.

### Activar

```
/zen
```

> *"Modo zen activado. Recibiras hasta 10 nudges cada 15 minutos."*

PPAI te recuerda tu tarea prioritaria cada N minutos (configurable). Util cuando necesitas concentracion extra.

### Desactivar

```
/zen off
```

> *"Modo zen desactivado. Enviaste 7 nudges en esta sesion."*

### Configurar

- `/config zen_intervalo 10` — cambia el intervalo a 10 minutos (5-60)
- `/config zen_max 20` — maximo de nudges antes de auto-desactivar (1-50)

---

## 9. Configuracion avanzada

### Ver configuracion actual

```
/config
```

Muestra: timezone, max nudges/dia, ventana de silencio, horarios, zen settings.

### Opciones disponibles

| Comando | Ejemplo | Descripcion |
|---------|---------|-------------|
| `/config nombre` | `/config nombre Angel` | Cambiar nombre |
| `/config estilo` | `/config estilo direct` | Cambiar estilo (gentle/direct/confrontational) |
| `/config horario` | `/config horario 09:00-18:00` | Cambiar horario laboral |
| `/config timezone` | `/config timezone America/Mexico_City` | Zona horaria |
| `/config inicio` | `/config inicio 08:30` | Hora del mensaje matutino |
| `/config cierre` | `/config cierre 17:30` | Hora del resumen de cierre |
| `/config silencio` | `/config silencio 22:00-07:00` | Ventana sin notificaciones |
| `/config nudges` | `/config nudges 5` | Max recordatorios por dia (1-10) |
| `/config pais` | `/config pais CO` | Pais para festivos automaticos |
| `/config finde` | `/config finde mixto` | Modo fin de semana (descanso/personal/mixto) |
| `/config motivacion` | `/config motivacion Hoy es un gran dia` | Mensaje motivacional matutino |
| `/config zen_intervalo` | `/config zen_intervalo 10` | Intervalo zen en minutos |
| `/config zen_max` | `/config zen_max 20` | Max nudges en modo zen |

### Dias libres

```
/libre 2026-04-15        → Agregar dia libre
/libre list               → Ver todos los dias libres
```

PPAI no te enviara notificaciones en dias libres ni en festivos de tu pais.

### Modo fin de semana

| Modo | Comportamiento |
|------|---------------|
| **descanso** | PPAI no te molesta sabado y domingo |
| **personal** | PPAI activo pero solo para tareas personales |
| **mixto** | PPAI activo normalmente |

---

## 10. Referencia rapida de comandos

| Comando | Que hace |
|---------|---------|
| `/start` | Iniciar onboarding |
| `/setup` | Reiniciar onboarding |
| `/top3` | Ver tus 3 tareas prioritarias |
| `/plan` | Generar plan del dia |
| `/plan tomorrow` | Generar plan de manana |
| `/calendar` | Conectar Google Calendar |
| `/perfil` | Ver tu perfil |
| `/config` | Ver/cambiar configuracion |
| `/zen` | Activar modo zen |
| `/zen off` | Desactivar modo zen |
| `/libre` | Gestionar dias libres |
| `/cancel` | Cancelar onboarding |
| *(texto libre)* | Capturar tarea(s) |

---

## 11. Tips para sacarle el maximo

### Captura todo, filtra despues

No te preocupes por redactar perfecto. Escribe lo que se te ocurra y PPAI lo clasifica. Puedes eliminar tareas irrelevantes despues.

### Usa /top3 cada manana

Empieza el dia con `/top3` para ver que es lo mas importante. PPAI ya ordeno tus tareas por urgencia y antiguedad.

### Conecta Google Calendar

Sin calendario, PPAI trabaja con tareas sueltas. Con calendario, planifica bloques alrededor de tus reuniones y detecta huecos libres. Es donde PPAI brilla.

### Genera un /plan todos los dias

Despues de `/top3`, usa `/plan` para ver tus bloques del dia. PPAI asigna tus tareas a los huecos libres de tu calendario.

### Responde a los botones

Cuando PPAI te pregunta algo (bloque terminado, tarea estancada, check-in), responde. Esa informacion alimenta el analisis de friccion y el reporte semanal.

### Usa el Pomodoro cuando te bloquees

Si una tarea te tiene paralizado, presiona **[Pomodoro 25min]** en el detector de friccion. 25 minutos enfocados suelen romper el bloqueo.

### Configura tu ventana de silencio

`/config silencio 22:00-07:00` — PPAI no te molesta fuera de horario. Respeta tu descanso.

### Revisa el reporte semanal

Cada lunes recibes un analisis de tu semana. Leelo con calma: los patrones que PPAI detecta (como "los jueves no completaste nada") son oro para mejorar.

### Experimenta con estilos

Si sientes que PPAI es muy suave, prueba `/config estilo direct`. Si quieres que te empuje mas, prueba `confrontational`. Puedes cambiar cuando quieras.

---

## Preguntas frecuentes

**Puedo usar PPAI sin Google Calendar?**
Si. La captura de tareas, /top3, nudges y modo zen funcionan sin calendario. Pero /plan y las notificaciones de bloques requieren calendario conectado.

**Cuanto cuesta usar PPAI?**
El bot es gratuito. Los costos de infraestructura (AWS + IA) los asume el equipo de desarrollo.

**Mis datos estan seguros?**
Tus tareas se guardan en DynamoDB con cifrado en reposo. Los tokens de Google Calendar se encriptan con Fernet antes de guardarse. PPAI nunca comparte tus datos.

**Puedo desconectar Google Calendar?**
Revoca el acceso desde tu cuenta de Google en https://myaccount.google.com/permissions. PPAI detectara que los tokens ya no son validos.

**Que pasa si la IA falla?**
PPAI usa templates estaticos como fallback. Si la API de Anthropic falla o se alcanza el limite diario de llamadas, el bot sigue funcionando normalmente pero con mensajes pre-definidos en vez de generados por IA. Nunca lo notaras.

**En que idioma funciona?**
PPAI se comunica en espanol. Puedes capturar tareas en cualquier idioma, pero los mensajes del bot son en espanol.

**Como elimino una tarea que ya no quiero?**
Si una tarea lleva 3+ dias estancada, PPAI te ofrece un boton **[Eliminar]** en el detector de friccion. Tambien puedes marcarla como hecha si ya no es relevante.

**Que es el modo zen exactamente?**
Es un modo de enfoque temporal. PPAI te envia recordatorios cada N minutos (configurable) de tu tarea prioritaria hasta que desactives el modo o se alcance el maximo de nudges. Ideal para sesiones de deep work.

**Puedo usar PPAI en grupo o solo funciona en chat privado?**
PPAI esta disenado para chat privado 1:1 con el bot. No funciona en grupos.

**Que pasa si no respondo a los mensajes del bot?**
Nada malo. PPAI respeta tu silencio. Pero la informacion que le das (completar bloques, responder check-ins) mejora la calidad de los reportes y el analisis de friccion. Mientras mas interactues, mas inteligente se vuelve.

---

## Tu primer dia con PPAI (paso a paso)

Si acabas de instalar PPAI, sigue este flujo para tu primer dia:

```
1. /start                          → Configura tu perfil (5 min)
2. Escribe 5-10 tareas pendientes  → PPAI las captura y clasifica
3. /top3                           → Ve tus 3 prioridades del dia
4. /calendar                      → Conecta Google Calendar (abre el link y pega el codigo)
5. /plan                           → Genera tu plan con bloques de tiempo
6. Trabaja y responde a los botones cuando PPAI te avise
7. Al final del dia, lee tu resumen de cierre
8. El lunes, revisa tu reporte semanal
```

Despues del primer dia, tu rutina diaria se reduce a:

```
Manana:  Lee el mensaje matutino de PPAI → /top3 → /plan
Dia:     Responde a recordatorios de bloques cuando aparezcan
Noche:   Lee el resumen de cierre
```

PPAI hace el resto automaticamente.

---

*PPAI — Personal Productivity AI*
*Construido con Python, Telegram Bot API, AWS y Claude.*
