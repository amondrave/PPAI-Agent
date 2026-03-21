---
name: infra-deploy
description: >
  AWS infrastructure deployment skill for PPAI. Handles the full lifecycle of deploying
  the PPAI Telegram bot to AWS: IAM user setup, credential configuration, Terraform
  bootstrap, infrastructure provisioning (VPC, ECS Fargate, DynamoDB, API Gateway, ECR),
  Docker image build & push, ECS deployment, Telegram webhook registration, health checks,
  cost monitoring, and teardown. Use this skill whenever the user mentions deploying to AWS,
  running Terraform, pushing Docker images to ECR, configuring IAM credentials, setting up
  the webhook, checking infrastructure status, estimating AWS costs, or destroying/tearing
  down cloud resources. Also trigger when the user says things like "deploy", "levantar la
  infra", "subir a AWS", "terraform plan", "terraform apply", "push to ECR", "registrar
  webhook", "destruir infra", or asks about AWS setup, credentials, or access keys.
---

# Skill: infra-deploy

**Proyecto:** PPAI (Personal Productivity AI)
**Versión:** 1.0
**Última actualización:** 2026-03-21

---

## Propósito

Este skill guía y ejecuta el despliegue completo de la infraestructura de PPAI en AWS.
Cubre desde la preparación de la cuenta AWS (IAM, credenciales) hasta la verificación
del bot corriendo en producción, pasando por Terraform, Docker y Telegram webhook.

El objetivo es que el usuario pueda desplegar, actualizar y destruir su infraestructura
con confianza, entendiendo cada paso sin necesidad de memorizar comandos.

---

## Cuándo usar este Skill

Activar cuando el usuario quiera:

- Crear un usuario IAM para Terraform o deployment
- Configurar credenciales de AWS (`aws configure`, access keys)
- Crear los recursos base para Terraform state (S3 bucket, DynamoDB lock)
- Ejecutar `terraform init`, `plan`, `apply` o `destroy`
- Construir y subir la imagen Docker al ECR
- Desplegar o actualizar el servicio ECS
- Registrar o verificar el webhook de Telegram
- Verificar que la infraestructura está sana (health checks, logs)
- Estimar costos de AWS
- Destruir la infraestructura (teardown)
- Cualquier pregunta sobre el flujo de deployment de PPAI

---

## Contexto del proyecto

PPAI es un bot de Telegram que opera un loop de productividad personal. La infraestructura
se gestiona con Terraform y consiste en:

| Componente | Servicio AWS | Módulo Terraform |
|------------|-------------|------------------|
| Red privada | VPC + subnets + NAT | `modules/networking` |
| Bot container | ECS Fargate (256 CPU, 512 MB) | `modules/ecs` |
| Registro de imágenes | ECR | `modules/ecr` |
| Persistencia | DynamoDB (3 tablas) | `modules/dynamodb` |
| Webhook ingress | API Gateway v2 HTTP | `modules/api-gateway` |
| Permisos | IAM roles | `modules/iam` |
| Logs | CloudWatch (90 días) | `modules/monitoring` |

**Archivos Terraform:** `terraform/` (raíz del proyecto PPAI)
**Guía de setup existente:** `docs/setup-guide.md`
**Dockerfile:** raíz del proyecto

---

## Flujo de trabajo

El deployment tiene un orden lógico. Cada paso depende del anterior. Cuando el usuario
pide ayuda, determina en qué punto del flujo se encuentra y guíalo desde ahí.

```
┌─────────────────────────────────────────────────────────────┐
│  FASE 0: PREPARACIÓN (una sola vez)                         │
│  ┌───────────┐  ┌──────────────┐  ┌───────────────────┐    │
│  │ Preflight │→ │ IAM User +   │→ │ AWS CLI configure │    │
│  │ Check     │  │ Access Keys  │  │                   │    │
│  └───────────┘  └──────────────┘  └───────────────────┘    │
├─────────────────────────────────────────────────────────────┤
│  FASE 1: BOOTSTRAP (una sola vez)                           │
│  ┌────────────────────┐  ┌──────────────────────────┐      │
│  │ S3 Bucket (state)  │→ │ DynamoDB Table (lock)    │      │
│  └────────────────────┘  └──────────────────────────┘      │
├─────────────────────────────────────────────────────────────┤
│  FASE 2: INFRAESTRUCTURA (terraform)                        │
│  ┌────────┐  ┌──────────────┐  ┌───────────────────┐      │
│  │ init   │→ │ plan         │→ │ apply             │      │
│  └────────┘  └──────────────┘  └───────────────────┘      │
├─────────────────────────────────────────────────────────────┤
│  FASE 3: DEPLOYMENT (docker + ecs)                          │
│  ┌───────────┐  ┌──────────┐  ┌─────────┐  ┌───────────┐ │
│  │ ECR login │→ │ build    │→ │ push    │→ │ tf apply  │ │
│  └───────────┘  └──────────┘  └─────────┘  └───────────┘ │
├─────────────────────────────────────────────────────────────┤
│  FASE 4: ACTIVACIÓN                                         │
│  ┌──────────────────┐  ┌──────────────────────────────┐   │
│  │ Telegram webhook  │→ │ Health check + verificación │   │
│  └──────────────────┘  └──────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## FASE 0: Preparación del entorno

### Paso 0.1 — Preflight check

Antes de cualquier cosa, verifica que el usuario tiene las herramientas necesarias.
Ejecuta el script `scripts/preflight-check.sh` que está junto a este SKILL.md:

```bash
bash <SKILL_DIR>/scripts/preflight-check.sh
```

Esto valida: AWS CLI, Terraform, Docker y la estructura del proyecto.

Si algo falta, guía al usuario para instalarlo. Referencias de instalación:

| Herramienta | macOS | Linux |
|-------------|-------|-------|
| AWS CLI | `brew install awscli` | `curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip && unzip awscliv2.zip && sudo ./aws/install` |
| Terraform | `brew install terraform` | Descargar de [terraform.io/downloads](https://terraform.io/downloads) |
| Docker | Docker Desktop | `sudo apt install docker.io` |

### Paso 0.2 — Crear usuario IAM para Terraform

El usuario **nunca** debe usar credenciales root para Terraform. Se necesita un usuario
IAM programático dedicado. Para la guía detallada paso a paso con capturas mentales de
cada pantalla de la consola AWS, lee `references/aws-iam-setup.md`.

**Resumen rápido:**

1. En la consola AWS → IAM → Usuarios → "Crear usuario"
2. Nombre: `terraform-deployer`
3. **No** habilitar acceso a la consola (solo programático)
4. Adjuntar permisos — dos opciones:
   - **MVP (rápido):** Política `AdministratorAccess`
   - **Producción (seguro):** Política personalizada (ver `references/aws-iam-setup.md`)
5. Crear el usuario
6. Ir a la pestaña "Credenciales de seguridad" del usuario creado
7. "Crear clave de acceso" → caso de uso "CLI"
8. Copiar `Access Key ID` y `Secret Access Key` (el Secret solo se muestra una vez)

### Paso 0.3 — Configurar AWS CLI

```bash
aws configure
```

Ingresa:
- **AWS Access Key ID:** la que obtuviste en el paso anterior
- **AWS Secret Access Key:** la que obtuviste en el paso anterior
- **Default region name:** `us-east-1`
- **Default output format:** `json`

**Verificar que funciona:**

```bash
aws sts get-caller-identity
```

Debe mostrar el Account ID y el ARN del usuario `terraform-deployer`.

---

## FASE 1: Bootstrap del backend de Terraform

Terraform necesita un lugar remoto donde guardar su estado. Estos recursos se crean
**una sola vez** y no son gestionados por Terraform (chicken-and-egg problem).

Ejecuta el script de bootstrap:

```bash
bash <SKILL_DIR>/scripts/bootstrap-backend.sh
```

O manualmente:

```bash
# Bucket S3 para Terraform state
aws s3 mb s3://ppai-terraform-state --region us-east-1

# Tabla DynamoDB para state locking
aws dynamodb create-table \
  --table-name ppai-terraform-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region us-east-1
```

**Verificar:**

```bash
aws s3 ls | grep ppai-terraform-state
aws dynamodb describe-table --table-name ppai-terraform-lock --query "Table.TableStatus"
```

---

## FASE 2: Provisionar infraestructura con Terraform

### Paso 2.1 — Inicializar Terraform

```bash
cd terraform
terraform init
```

Esto descarga los providers (AWS ~5.40) y conecta con el backend S3.
Si falla con "access denied", las credenciales no están bien configuradas.

### Paso 2.2 — Plan (preview de cambios)

```bash
terraform plan -var="telegram_bot_token=TU_TOKEN_AQUI"
```

Esto muestra qué recursos va a crear sin ejecutar nada. Revisa el output con el
usuario antes de proceder. Resalta los componentes principales que va a crear.

Para el token de Telegram, el usuario debe obtenerlo de BotFather en Telegram.
Si no lo tiene, referirlo a `docs/setup-guide.md` Paso 1.

### Paso 2.3 — Apply (crear recursos)

```bash
terraform apply -var="telegram_bot_token=TU_TOKEN_AQUI"
```

Terraform pide confirmación (`yes`). Los recursos se crean en ~3-5 minutos.

**Outputs importantes que se generan:**

| Output | Uso |
|--------|-----|
| `api_gateway_url` | URL base para registrar el webhook de Telegram |
| `ecr_repository_url` | URL del ECR para push de imágenes Docker |
| `ecs_cluster_name` | Nombre del cluster para monitoreo |
| `ecs_service_name` | Nombre del servicio para actualizaciones |

Guarda estos valores — se necesitan en las fases siguientes.

Para verlos después:

```bash
terraform output
```

---

## FASE 3: Build y deploy de la imagen Docker

### Paso 3.1 — Login al ECR

```bash
ECR_URL=$(cd terraform && terraform output -raw ecr_repository_url)
ACCOUNT_ID=$(echo $ECR_URL | cut -d'.' -f1)
REGION=$(cd terraform && terraform output -raw ecr_repository_url | cut -d'.' -f4)

aws ecr get-login-password --region $REGION | \
  docker login --username AWS --password-stdin $ECR_URL
```

### Paso 3.2 — Build de la imagen

```bash
# Desde la raíz del proyecto (donde está el Dockerfile)
docker build -t ppai-bot .
```

### Paso 3.3 — Tag y push

```bash
VERSION="v0.1.0"  # Incrementar en cada deploy
ECR_URL=$(cd terraform && terraform output -raw ecr_repository_url)

docker tag ppai-bot:latest $ECR_URL:$VERSION
docker push $ECR_URL:$VERSION
```

### Paso 3.4 — Desplegar nueva imagen en ECS

```bash
cd terraform
terraform apply \
  -var="telegram_bot_token=TU_TOKEN" \
  -var="image_tag=$VERSION"
```

Esto actualiza el task definition de ECS con la nueva imagen. El deployment circuit
breaker se encarga de rollback automático si la nueva versión falla.

---

## FASE 4: Activación y verificación

### Paso 4.1 — Registrar webhook de Telegram

```bash
API_URL=$(cd terraform && terraform output -raw api_gateway_url)
BOT_TOKEN="TU_TOKEN"

curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${API_URL}/webhook" | python -m json.tool
```

Respuesta esperada: `{"ok": true, "result": true, "description": "Webhook was set"}`

### Paso 4.2 — Verificar estado del servicio ECS

```bash
CLUSTER=$(cd terraform && terraform output -raw ecs_cluster_name)
SERVICE=$(cd terraform && terraform output -raw ecs_service_name)

aws ecs describe-services \
  --cluster $CLUSTER \
  --services $SERVICE \
  --query "services[0].{status:status,running:runningCount,desired:desiredCount,deployments:deployments[*].{status:status,running:runningCount}}"
```

### Paso 4.3 — Ver logs del bot

```bash
aws logs tail /ppai/bot --follow --since 5m
```

### Paso 4.4 — Test funcional

Enviar un mensaje al bot en Telegram (ej: "test de deploy") y verificar que responde.

---

## Operaciones adicionales

### Actualizar solo la imagen (sin cambiar infra)

```bash
NEW_VERSION="v0.2.0"
ECR_URL=$(cd terraform && terraform output -raw ecr_repository_url)

docker build -t ppai-bot .
docker tag ppai-bot:latest $ECR_URL:$NEW_VERSION
docker push $ECR_URL:$NEW_VERSION

cd terraform
terraform apply -var="telegram_bot_token=TU_TOKEN" -var="image_tag=$NEW_VERSION"
```

### Ver costos estimados

| Servicio | Costo mensual estimado |
|----------|----------------------|
| ECS Fargate (0.25 vCPU, 512MB, 24/7) | ~$9.50 |
| NAT Gateway (fijo + data) | ~$32.00 |
| DynamoDB (On-Demand, bajo volumen) | ~$0.50 |
| API Gateway (< 100K requests) | ~$0.10 |
| ECR + CloudWatch + S3 | ~$1.00 |
| **Total** | **~$43/mes** |

El NAT Gateway es el mayor costo. Para reducirlo, se podría usar un NAT Instance
(EC2 t4g.nano ~$3/mes) pero requiere más mantenimiento.

### Teardown (destruir todo)

Lee `references/teardown-guide.md` antes de ejecutar. Esto es irreversible.

```bash
cd terraform
terraform destroy -var="telegram_bot_token=TU_TOKEN"
```

Después, limpiar los recursos de bootstrap (manual):

```bash
aws s3 rb s3://ppai-terraform-state --force
aws dynamodb delete-table --table-name ppai-terraform-lock
```

---

## Troubleshooting

Para problemas comunes y sus soluciones, consultar `references/troubleshooting.md`.

Los más frecuentes:

| Problema | Causa probable | Solución rápida |
|----------|---------------|-----------------|
| `terraform init` falla con "access denied" | Credenciales incorrectas o permisos insuficientes | `aws sts get-caller-identity` para verificar |
| `terraform apply` falla en IAM | El usuario no tiene permisos para crear IAM roles | Agregar permisos IAM al usuario deployer |
| ECS task se reinicia en loop | Error en la app, no en infra | Revisar logs: `aws logs tail /ppai/bot` |
| Webhook no responde | ECS task no está healthy o API Gateway mal configurado | Verificar ECS running count y logs |
| "Image not found" en ECS | Image tag no existe en ECR | Verificar push exitoso con `aws ecr list-images` |
| NAT Gateway billed without use | NAT tiene costo fijo por hora | Solo destruir cuando no se use |

---

## Restricciones de seguridad

| ❌ Nunca | ✅ Siempre |
|---------|-----------|
| Usar credenciales root para Terraform | Crear usuario IAM dedicado |
| Commitear tokens o secrets a git | Usar `-var` o `terraform.tfvars` (gitignored) |
| Hardcodear access keys en código | Usar `aws configure` o variables de entorno |
| Desplegar sin revisar el plan | Ejecutar `terraform plan` antes de `apply` |
| Destruir sin confirmar con el usuario | Pedir confirmación explícita antes de `destroy` |
