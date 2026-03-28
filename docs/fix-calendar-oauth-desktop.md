# Fix Calendar OAuth — Migrar de Device Flow a Desktop App

**Fecha:** 2026-03-28
**Estado:** Completado — migrado a Desktop App OAuth flow

---

## El problema

El OAuth client tipo **"TV y entrada limitada"** (device flow) no permite el scope `calendar.events` (escritura). Solo permite `calendar.readonly`.

Error confirmado con test directo al endpoint de Google:

```
POST https://oauth2.googleapis.com/device/code
Status: 400
Response: {
  "error": "invalid_scope",
  "error_description": "Invalid device flow scope: https://www.googleapis.com/auth/calendar.events"
}
```

Sin `calendar.events`, PPAI no puede crear eventos `[PPAI]` en el calendario del usuario — que es el plus principal de la integración.

---

## La solución

Crear un nuevo OAuth client tipo **"Aplicación de escritorio" (Desktop app)**. Este tipo sí permite todos los scopes de Calendar, incluyendo `calendar.events`.

### Flujo para el usuario

1. `/calendar` → bot genera un link de Google
2. Usuario abre el link → autoriza en Google
3. Google redirige a `http://localhost?code=XXXXX` → el browser muestra "no se puede conectar" pero **el código está en la barra de dirección**
4. Usuario copia el código de la URL y lo pega en Telegram
5. Bot intercambia el código por tokens

---

## Paso a paso en Google Cloud Console

1. Ve a **Google Cloud Console** → APIs & Services → **Credentials**
2. Click **"+ CREATE CREDENTIALS"** → **OAuth client ID**
3. Application type: **"Desktop app"** (Aplicación de escritorio)
4. Nombre: `PPAI Bot Desktop` (o lo que quieras)
5. Click **Create**
6. Copia el **Client ID** y **Client Secret** nuevos
7. (Opcional) Puedes eliminar o desactivar el client viejo de TV/limited input

---

## Paso a paso para probar en local

Una vez que tengas las credenciales nuevas:

1. Actualiza tu `.env` con el nuevo `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET`
2. Actualizar el código de `google_oauth_service.py` para usar el flujo Desktop (auth URL + code exchange en vez de device flow)
3. Correr un test local directo contra el endpoint de Google para verificar que funciona
4. Levantar el bot en local con `python -m ppai.main` y probar `/calendar` desde Telegram
5. Si todo funciona, commit, PR y deploy

---

## Qué cambia en el código

| Archivo | Cambio |
|---------|--------|
| `ppai/calendar/application/google_oauth_service.py` | Reemplazar `start_device_flow()` + `poll_device_token()` por `generate_auth_url()` (con `redirect_uri=http://localhost`) + `exchange_code()` (POST directo a token endpoint con `requests`) |
| `ppai/calendar/infrastructure/calendar_telegram_adapter.py` | Volver al flujo "abre este link → pega el código" en vez de "ingresa código en google.com/device → escribe listo" |
| `ppai/calendar/application/calendar_service.py` | `connect()` vuelve a recibir `auth_code` en vez de `device_code` |
| GitHub Secrets (`prod` environment) | Actualizar `GOOGLE_CLIENT_ID` y `GOOGLE_CLIENT_SECRET` con los nuevos valores |

---

## Notas técnicas

- **No usar `InstalledAppFlow`** — requiere la librería `google_auth_oauthlib` y el OOB flow está deprecado. Usar `requests.post` directo al token endpoint es más simple y controlable.
- **`redirect_uri=http://localhost`** — los Desktop app clients permiten localhost por defecto sin configuración adicional.
- **Scopes**: `calendar.readonly` + `calendar.events` — ambos necesarios para leer eventos y crear bloques `[PPAI]`.
- **Token refresh** — no cambia, funciona igual para cualquier tipo de OAuth client.
