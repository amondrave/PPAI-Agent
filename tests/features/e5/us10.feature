Feature: US-10 Activación de Rescue Mode
  As a usuario final
  I want recibir una salida empática cuando el día salió mal
  So that pueda retomar con una microacción concreta

  Background:
    Given el usuario "u1" tiene scheduler bot nativo activo

  Scenario: Recibo propuesta de rescate en día caído
    Given no completé tareas hoy y todavía tengo trabajo pendiente
    And la hora actual cae dentro de la ventana de cierre
    When el scheduler ejecuta el tick
    Then el resumen incluye una sugerencia de rescate empática
    And se registra el evento "RESCUE_TRIGGERED"

  Scenario: Activo modo zen y recibo nudges durante la sesión
    Given el usuario activa "/zen"
    And existe una tarea priorizada
    When el scheduler ejecuta el tick con zen activo
    Then se envía un nudge zen

  Scenario: El modo zen ignora la ventana de silencio
    Given el usuario tiene una ventana de silencio activa
    And el usuario activa "/zen"
    And existe una tarea priorizada
    When el scheduler ejecuta el tick dentro de la ventana de silencio
    Then el nudge zen sí se envía
