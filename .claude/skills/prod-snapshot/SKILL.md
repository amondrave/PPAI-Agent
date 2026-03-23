---
name: prod-snapshot
description: >
  Documenta el estado actual de la infraestructura de producción de PPAI en AWS.
  Consulta los recursos reales via AWS CLI (ECS, DynamoDB, ECR, VPC, IAM, CloudWatch)
  y crea o actualiza docs/infra-snapshot.md con qué está corriendo, IDs, ARNs y
  comandos de verificación desde consola. Usar cuando el usuario confirme un deploy
  exitoso a prod, diga "actualiza el snapshot", "documenta la infra", "qué tenemos
  en prod", "crea el snapshot de infra" o pida trazabilidad del estado de AWS.
---

# Skill: prod-snapshot

**Proyecto:** PPAI (Personal Productivity AI)
**Versión:** 1.0
**Última actualización:** 2026-03-23

---

## Propósito

Al confirmar un deploy exitoso a producción, este Skill consulta el estado real de AWS
y genera o actualiza `docs/infra-snapshot.md` con una radiografía completa de la infra:
qué existe, con qué IDs/ARNs, cuándo fue desplegado, y cómo verificarlo desde consola
o CLI.

El objetivo es tener trazabilidad permanente: en cualquier momento se puede abrir el
archivo y saber exactamente qué hay en prod y cómo comprobarlo.

---

## Cuándo usar este Skill

Activar cuando el usuario:
- Confirme que un deploy a prod fue exitoso
- Diga "actualiza el snapshot de infra"
- Pida saber "qué tenemos en prod"
- Quiera documentar el estado actual de AWS
- Necesite los IDs/ARNs para debugging o auditoría

---

## Instrucciones de ejecución

### PASO 1 — Recopilar estado real de AWS

Ejecutar los siguientes comandos via Bash tool para obtener datos en vivo.
Si algún comando falla (recurso no existe aún), continuar con los demás y marcar como `⚠️ no encontrado`.

```bash
# ECS — cluster y servicio
aws ecs describe-clusters --clusters ppai-cluster \
  --query 'clusters[0].{status:status,runningTasks:runningTasksCount,pendingTasks:pendingTasksCount}' \
  --output json

aws ecs describe-services \
  --cluster ppai-cluster --services ppai-bot-service \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount,taskDef:taskDefinition,createdAt:createdAt}' \
  --output json

# Task definition activa
aws ecs describe-services \
  --cluster ppai-cluster --services ppai-bot-service \
  --query 'services[0].taskDefinition' --output text | xargs \
  aws ecs describe-task-definition --task-definition \
  --query 'taskDefinition.{family:family,revision:revision,image:containerDefinitions[0].image,cpu:cpu,memory:memory}' \
  --output json 2>/dev/null

# ECR — imagen desplegada
aws ecr describe-repositories --repository-names ppai-bot \
  --query 'repositories[0].{uri:repositoryUri,mutability:imageTagMutability}' --output json
aws ecr list-images --repository-name ppai-bot --filter tagStatus=TAGGED \
  --query 'imageIds[*].imageTag' --output json

# DynamoDB — tablas
aws dynamodb list-tables --query 'TableNames' --output json
for TABLE in ppai-tasks ppai-events ppai-dedup ppai-cycles; do
  aws dynamodb describe-table --table-name $TABLE \
    --query 'Table.{name:TableName,status:TableStatus,items:ItemCount,arn:TableArn}' \
    --output json 2>/dev/null
done

# VPC y networking
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ppai-vpc" \
  --query 'Vpcs[0].{vpcId:VpcId,cidr:CidrBlock,state:State}' --output json
aws ec2 describe-subnets --filters "Name=tag:Project,Values=ppai" \
  --query 'Subnets[*].{id:SubnetId,name:Tags[?Key==`Name`]|[0].Value,az:AvailabilityZone,public:MapPublicIpOnLaunch}' \
  --output json
aws ec2 describe-internet-gateways --filters "Name=tag:Name,Values=ppai-igw" \
  --query 'InternetGateways[0].{id:InternetGatewayId,state:Attachments[0].State}' --output json

# IAM roles
aws iam get-role --role-name ppai-task-execution-role \
  --query 'Role.{name:RoleName,arn:Arn,created:CreateDate}' --output json 2>/dev/null
aws iam get-role --role-name ppai-task-role \
  --query 'Role.{name:RoleName,arn:Arn,created:CreateDate}' --output json 2>/dev/null
aws iam get-role --role-name ppai-github-deploy \
  --query 'Role.{name:RoleName,arn:Arn,created:CreateDate}' --output json 2>/dev/null

# CloudWatch
aws logs describe-log-groups --log-group-name-prefix /ppai \
  --query 'logGroups[*].{name:logGroupName,retention:retentionInDays,stored:storedBytes}' \
  --output json

# Terraform state backend
aws s3 ls s3://ppai-terraform-state/ --recursive 2>/dev/null
aws dynamodb describe-table --table-name ppai-terraform-lock \
  --query 'Table.{name:TableName,status:TableStatus}' --output json 2>/dev/null
```

### PASO 2 — Obtener versión desplegada

```bash
# SHA del último push a main
git log main --pretty=format:"%H|%s|%ad" --date=short -1

# Tag en ECR que corresponde al SHA
aws ecr describe-images --repository-name ppai-bot \
  --query 'sort_by(imageDetails, &imagePushedAt)[-1].{tags:imageTags,digest:imageDigest,pushedAt:imagePushedAt}' \
  --output json
```

### PASO 3 — Obtener outputs de Terraform (si hay state)

```bash
cd terraform && terraform output -json 2>/dev/null || echo "No terraform state available"
```

### PASO 4 — Generar o actualizar `docs/infra-snapshot.md`

Escribir el archivo con todos los datos recopilados en el formato especificado abajo.
Si el archivo ya existe, **reemplazar completamente** con los datos más recientes (es un snapshot, no un log acumulativo).

---

## Formato de `docs/infra-snapshot.md`

```markdown
# Infra Snapshot — PPAI en Producción

**Región:** us-east-1
**Última actualización:** {FECHA ISO}
**Deploy commit:** `{SHA}` — {mensaje del commit}
**Estado general:** ✅ Operativo | ⚠️ Degradado | ❌ Down

---

## ECS — Bot en ejecución

| Campo | Valor |
|-------|-------|
| Cluster | `ppai-cluster` |
| Servicio | `ppai-bot-service` |
| Estado | {status} |
| Tasks corriendo | {runningCount} / {desiredCount} |
| Task Definition | `{family}:{revision}` |
| Imagen desplegada | `{ecr-url}:{sha-tag}` |
| CPU / Memoria | 256 CPU / 512 MB |

### Verificar desde CLI
```bash
# Estado del servicio
aws ecs describe-services \
  --cluster ppai-cluster \
  --services ppai-bot-service \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'

# Logs en tiempo real
aws logs tail /ppai/bot --follow --since 5m
```

---

## ECR — Imágenes Docker

| Campo | Valor |
|-------|-------|
| Repositorio | `{ecr-url}` |
| Mutabilidad | MUTABLE |
| Tags presentes | {lista de tags} |
| Imagen activa | `{sha-del-deploy}` |

### Verificar desde CLI
```bash
# Listar imágenes
aws ecr list-images --repository-name ppai-bot --filter tagStatus=TAGGED

# Imagen activa en el servicio
aws ecs describe-services --cluster ppai-cluster --services ppai-bot-service \
  --query 'services[0].taskDefinition' --output text | xargs \
  aws ecs describe-task-definition --task-definition \
  --query 'taskDefinition.containerDefinitions[0].image'
```

---

## DynamoDB — Persistencia

| Tabla | ARN | Estado | Items |
|-------|-----|--------|-------|
| `ppai-tasks` | `{arn}` | {status} | {count} |
| `ppai-events` | `{arn}` | {status} | {count} |
| `ppai-dedup` | `{arn}` | {status} | {count} |
| `ppai-cycles` | `{arn}` | {status} | {count} |

### Verificar desde CLI
```bash
# Estado de todas las tablas
for TABLE in ppai-tasks ppai-events ppai-dedup ppai-cycles; do
  aws dynamodb describe-table --table-name $TABLE \
    --query 'Table.{name:TableName,status:TableStatus,items:ItemCount}'
done

# Contar items en tasks
aws dynamodb scan --table-name ppai-tasks --select COUNT
```

---

## Networking — VPC

| Recurso | ID | Estado |
|---------|-----|--------|
| VPC | `{vpc-id}` | {state} |
| Subnet pública A | `{subnet-id}` | us-east-1a |
| Subnet pública B | `{subnet-id}` | us-east-1b |
| Internet Gateway | `{igw-id}` | {state} |
| DynamoDB VPC Endpoint | `{endpoint-id}` | available |

### Verificar desde CLI
```bash
# VPC
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ppai-vpc" \
  --query 'Vpcs[0].{id:VpcId,state:State}'

# Endpoint DynamoDB
aws ec2 describe-vpc-endpoints --filters "Name=tag:Name,Values=ppai-dynamodb-endpoint" \
  --query 'VpcEndpoints[0].{id:VpcEndpointId,state:State}'
```

---

## IAM — Roles

| Role | ARN | Propósito |
|------|-----|-----------|
| `ppai-task-execution-role` | `{arn}` | ECS pull de imagen + CloudWatch |
| `ppai-task-role` | `{arn}` | Permisos DynamoDB del bot |
| `ppai-github-deploy` | `{arn}` | GitHub Actions OIDC deploy |

### Verificar desde CLI
```bash
# Listar roles del proyecto
aws iam list-roles --query 'Roles[?starts_with(RoleName, `ppai`)].{name:RoleName,arn:Arn}'

# Policies del task role
aws iam get-role-policy --role-name ppai-task-role --policy-name ppai-task-policy
```

---

## CloudWatch — Logs

| Log Group | Retención | Bytes almacenados |
|-----------|-----------|-------------------|
| `/ppai/bot` | 90 días | {bytes} |

### Verificar desde CLI
```bash
# Ver logs del bot (últimos 10 minutos)
aws logs tail /ppai/bot --since 10m

# Buscar errores
aws logs filter-log-events \
  --log-group-name /ppai/bot \
  --filter-pattern "ERROR" \
  --start-time $(date -d '1 hour ago' +%s000)
```

---

## Terraform State Backend

| Recurso | Valor | Estado |
|---------|-------|--------|
| S3 Bucket | `ppai-terraform-state` | {versioning} |
| DynamoDB Lock | `ppai-terraform-lock` | {status} |
| State file | `ppai/terraform.tfstate` | {size/last-modified} |

### Verificar desde CLI
```bash
# Último state
aws s3 ls s3://ppai-terraform-state/ppai/ --human-readable

# Ver si hay lock activo
aws dynamodb scan --table-name ppai-terraform-lock \
  --query 'Items[*].LockID'
```

---

## Costos estimados (mensuales)

| Servicio | Costo estimado |
|----------|---------------|
| ECS Fargate (256 CPU, 512 MB, 24/7) | ~$8.50 |
| DynamoDB (On-Demand, bajo volumen) | ~$0.50 |
| CloudWatch Logs (90 días retención) | ~$1.00 |
| ECR (imágenes almacenadas) | ~$0.10 |
| VPC + Internet Gateway | $0.00 |
| **Total** | **~$10.10/mes** |

*NAT Gateway eliminado — ahorro de ~$32/mes respecto al diseño original.*

---

## Historial de snapshots

| Fecha | Commit | Cambios principales |
|-------|--------|---------------------|
| {FECHA} | `{SHA}` | {descripción} |
```

---

## Reglas de escritura

1. **Siempre datos reales** — nunca inventar IDs, ARNs o estados. Si un recurso no existe, marcarlo como `⚠️ no encontrado`.
2. **Fecha ISO** en el header (`2026-03-23T14:00:00Z`).
3. **Historial acumulativo** — la tabla de historial al final se extiende con cada snapshot, el resto del archivo se sobreescribe.
4. **Archivo único** — siempre `docs/infra-snapshot.md`, no versionar el nombre.
5. Si `terraform output` devuelve valores, preferirlos sobre los de la CLI (son la fuente de verdad del state).

---

## Output final al usuario

Al terminar, reportar:

```
✅ docs/infra-snapshot.md actualizado

Deploy: {SHA} — {fecha}
Recursos documentados: ECS ✅ | ECR ✅ | DynamoDB ✅ | VPC ✅ | IAM ✅ | CloudWatch ✅
Estado general: ✅ Operativo

Archivo: docs/infra-snapshot.md
```
