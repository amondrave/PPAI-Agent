Feature: US-06 Control de intensidad y ventana de empuje
  As a operador/admin
  I want configurar intensidad mínima/frecuencia de nudges
  So that evite fatiga y mantenga efectividad

  Background:
    Given el usuario "u1" tiene preferencias de nudge configuradas

  Scenario: Nudge omitido durante ventana de silencio
    Given el usuario configuró ventana de silencio "22:00" - "08:00"
    And la hora actual es las 23:30 en la zona horaria del usuario
    When el scheduler evalúa el tick
    Then no se envía ningún nudge
    And se registra el motivo "skipped_activity" o equivalente de silencio

  Scenario: Ventana de silencio que cruza medianoche
    Given el usuario configuró ventana de silencio "23:00" - "07:00"
    And la hora actual es las 01:00 en la zona horaria del usuario
    When el scheduler evalúa el tick
    Then no se envía ningún nudge

  Scenario: Nudge omitido por actividad reciente menor a 60 minutos
    Given el usuario tuvo actividad hace 30 minutos (captura/top3/respuesta)
    When el scheduler evalúa el tick
    Then no se envía ningún nudge
    And se registra el motivo "skipped_activity"

  Scenario: Límite diario de nudges alcanzado
    Given el usuario ya recibió 3 nudges automáticos hoy
    When el scheduler evalúa el tick
    Then no se envía ningún nudge adicional
    And se registra el motivo de límite diario alcanzado

  Scenario: Nudge enviado cuando no hay bloqueadores activos
    Given el usuario no está en ventana de silencio
    And el usuario no tuvo actividad en los últimos 60 minutos
    And el usuario recibió menos de 3 nudges hoy
    When el scheduler evalúa el tick
    Then se envía el nudge normalmente

  Scenario: Cambio de configuración afecta solo futuros nudges
    Given el usuario actualiza su ventana de silencio
    Then los nudges ya enviados no se ven afectados
    And los próximos ticks respetan la nueva configuración
