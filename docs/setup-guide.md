# PPAI — Guia de Setup y Despliegue

## Resumen

Esta guia cubre todo lo necesario para correr PPAI en local y eventualmente desplegarlo en AWS. Esta dividida en dos fases: **Local** (sin costos, sin cuenta AWS) y **Produccion** (AWS real).

---

## Fase 1: Setup Local

### Pre-requisitos locales

| Herramienta | Version | Verificar |
|-------------|---------|-----------|
| Python | 3.12+ | `python --version` |
| Docker + Docker Compose | 20+ | `docker --version` |
| Git | cualquiera | `git --version` |

### Paso 1: Crear el bot en Telegram

Telegram requiere que registres un bot para obtener un token de acceso. El proceso se hace desde la app de Telegram hablando con un bot oficial llamado **BotFather**.

#### 1.1 — Abrir BotFather

1. Abre Telegram (celular o desktop, ambos funcionan).
2. En la barra de busqueda escribe `@BotFather`.
3. Selecciona el resultado que tiene el check azul verificado.
4. Dale click en **Start** (o escribe `/start`) si es la primera vez.

#### 1.2 — Crear un nuevo bot

1. Escribe `/newbot` en el chat con BotFather.
2. BotFather te pregunta: **"Alright, a new bot. How are we going to call it? Please choose a name for your bot."**
   - Escribe un nombre descriptivo, por ejemplo: `PPAI Dev Bot`
   - Este nombre es lo que ven los usuarios en Telegram (se puede cambiar despues).
3. BotFather te pregunta: **"Good. Now let's choose a username for your bot..."**
   - Debe terminar en `bot` (regla de Telegram).
   - Ejemplo: `ppai_dev_bot`
   - Si ya esta tomado, prueba variaciones: `ppai_angel_bot`, `ppai_test_123_bot`, etc.

#### 1.3 — Guardar el token

BotFather responde con algo asi:

```
Done! Congratulations on your new bot. You will find it at t.me/ppai_dev_bot.

Use this token to access the HTTP API:
7123456789:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

Keep your token secure and store it safely.
```

**Copia el token completo** (la linea que empieza con numeros, incluye los dos puntos y todo lo que sigue). Lo vas a necesitar en el siguiente paso.

> **Importante**: No compartas este token. Quien lo tenga puede controlar tu bot.

#### 1.4 — Configuracion opcional del bot

Estos comandos son opcionales pero recomendados. Escribelos en el mismo chat con BotFather:

| Comando | Para que | Ejemplo |
|---------|----------|---------|
| `/setdescription` | Descripcion corta del bot | "Tu asistente de productividad personal" |
| `/setabouttext` | Texto en el perfil del bot | "Captura tareas desde Telegram" |
| `/setcommands` | Comandos visibles (menu) | Dejalo vacio por ahora |

#### 1.5 — Probar que el bot existe

1. En Telegram, busca el username que elegiste (ej: `@ppai_dev_bot`).
2. Abrelo y dale **Start**.
3. Escribe cualquier cosa. No recibiras respuesta aun — es normal, el bot no esta corriendo.

---

### Paso 2: Crear archivo .env

En la raiz del proyecto, crea un archivo `.env` con tu token:

```bash
# Desde la raiz del proyecto
cp .env.example .env
```

Luego edita `.env` y pega tu token:

```env
TELEGRAM_BOT_TOKEN=7123456789:AAH-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DYNAMODB_TABLE_PREFIX=ppai
AWS_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:4566
ACTIVE_TASK_LIMIT=50
DEDUP_WINDOW_SECONDS=300
RATE_LIMIT_PER_MINUTE=10
```

> `AWS_ENDPOINT_URL` apunta a LocalStack. Cuando despliegues en AWS real, se elimina esta variable.

---

### Paso 3: Levantar LocalStack

```bash
docker compose up -d
```

Esto levanta:
- LocalStack en `localhost:4566` (emula DynamoDB)
- Crea las 3 tablas automaticamente (ppai-tasks, ppai-events, ppai-dedup)

Verificar que las tablas existen:

```bash
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```

---

### Paso 4: Activar entorno virtual

```bash
source .venv/bin/activate
```

Si es la primera vez:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov "moto[dynamodb]"
```

---

### Paso 5: Correr los tests

```bash
# Todos los tests (no requiere LocalStack ni token)
python -m pytest tests/ -v

# Solo unit tests (mas rapido)
python -m pytest tests/unit/ -v
```

---

### Paso 6: Correr el bot en local

```bash
source .venv/bin/activate
python -m ppai.local
```

Esto arranca el bot en **modo polling** (no necesita webhook ni URL publica). Abre Telegram, busca tu bot y enviare un mensaje como:

- `comprar leche`
- `llamar al doctor #salud`
- `entregar reporte para mañana`
- Multiples lineas:
  ```
  tarea uno
  tarea dos
  tarea tres
  ```

Deberias recibir respuestas como: *"Capturado. Tu tarea ha sido registrada."*

Para detener: `Ctrl+C`

---

### Paso 7: Verificar datos en DynamoDB local

```bash
# Ver tareas creadas
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name ppai-tasks

# Ver eventos
aws --endpoint-url=http://localhost:4566 dynamodb scan --table-name ppai-events
```

---

## Fase 2: Despliegue en AWS (cuando estes listo)

### Pre-requisitos AWS

| Recurso | Como obtenerlo |
|---------|----------------|
| Cuenta AWS | [aws.amazon.com](https://aws.amazon.com) — free tier cubre mucho |
| AWS CLI instalado | `brew install awscli` (macOS) |
| AWS CLI configurado | `aws configure` → Access Key + Secret + region `us-east-1` |
| Terraform instalado | `brew install terraform` |

### Paso 8: Crear recursos base (manual, 1 sola vez)

Terraform necesita un lugar donde guardar su estado. Estos 2 recursos se crean manualmente:

```bash
# Bucket S3 para Terraform state
aws s3 mb s3://ppai-terraform-state --region us-east-1

# Tabla DynamoDB para Terraform lock
aws dynamodb create-table \
  --table-name ppai-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

### Paso 9: Desplegar infraestructura

```bash
cd terraform

# Inicializar (descarga providers, conecta con S3 backend)
terraform init

# Ver que va a crear (sin ejecutar)
terraform plan -var="telegram_bot_token=TU_TOKEN_AQUI"

# Crear todo
terraform apply -var="telegram_bot_token=TU_TOKEN_AQUI"
```

Terraform crea: VPC, subnets, NAT, API Gateway, ECS cluster, DynamoDB (3 tablas), ECR, IAM roles, CloudWatch logs.

Al terminar, muestra:

```
api_gateway_url = "https://xxxxx.execute-api.us-east-1.amazonaws.com"
ecr_repository_url = "123456789.dkr.ecr.us-east-1.amazonaws.com/ppai-bot"
```

### Paso 10: Build y push de la imagen Docker

```bash
# Login a ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 123456789.dkr.ecr.us-east-1.amazonaws.com

# Build
docker build -t ppai-bot .

# Tag
docker tag ppai-bot:latest 123456789.dkr.ecr.us-east-1.amazonaws.com/ppai-bot:v0.1.0

# Push
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/ppai-bot:v0.1.0
```

### Paso 11: Desplegar en ECS

```bash
cd terraform
terraform apply -var="telegram_bot_token=TU_TOKEN" -var="image_tag=v0.1.0"
```

### Paso 12: Configurar webhook de Telegram

Una vez que ECS este corriendo y API Gateway activo:

```bash
curl "https://api.telegram.org/botTU_TOKEN/setWebhook?url=https://xxxxx.execute-api.us-east-1.amazonaws.com/webhook"
```

Respuesta esperada: `{"ok":true,"result":true,"description":"Webhook was set"}`

A partir de aqui, el bot responde automaticamente sin necesidad de correr nada en tu maquina.

---

## Costos estimados (AWS, mensual)

| Servicio | Costo estimado |
|----------|---------------|
| ECS Fargate (0.25 vCPU, 512MB, 24/7) | ~$9.50 |
| NAT Gateway | ~$32.00 |
| DynamoDB (On-Demand, bajo volumen) | ~$0.50 |
| API Gateway (< 100K req) | ~$0.10 |
| ECR + CloudWatch + S3 | ~$1.00 |
| **Total** | **~$43/mes** |

---

## Referencia rapida

| Quiero... | Comando |
|-----------|---------|
| Correr tests | `source .venv/bin/activate && pytest tests/ -v` |
| Levantar LocalStack | `docker compose up -d` |
| Correr bot local | `source .venv/bin/activate && python -m ppai.local` |
| Parar LocalStack | `docker compose down` |
| Ver tablas locales | `aws --endpoint-url=http://localhost:4566 dynamodb list-tables` |
| Desplegar infra | `cd terraform && terraform apply` |
