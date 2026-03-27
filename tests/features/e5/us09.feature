Feature: US-09 Reporte diario no acusatorio
  As a usuario final
  I want recibir acompañamiento automático al inicio y al cierre del día
  So that mantenga continuidad sin sentir presión

  Background:
    Given el usuario "u1" tiene preferencias activas del scheduler bot nativo

  Scenario: Recibo mi Top 3 automáticamente cada mañana
    Given existe un Top 3 vigente para hoy
    And la hora actual cae dentro de la ventana de inicio
    When el scheduler ejecuta el tick
    Then se envía un mensaje matutino con el Top 3
    And se registra el evento "DAILY_START_SENT"

  Scenario: Recibo resumen de cierre con detalle del día
    Given el usuario completó tareas y dejó otras pendientes
    And la hora actual cae dentro de la ventana de cierre
    When el scheduler ejecuta el tick
    Then se envía un resumen con listas de completadas, pendientes y pospuestas
    And se registra el evento "DAILY_END_SENT"

  Scenario: Configuro horarios de inicio y cierre
    Given el usuario usa el comando "/config"
    When configura "inicio 09:15" y "cierre 19:30"
    Then las preferencias quedan persistidas con esos horarios
