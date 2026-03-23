# Infra Snapshot — PPAI en Producción

**Región:** us-east-1
**Última actualización:** 2026-03-23T12:51:00Z
**Deploy commit:** `af69f6a5` — Fix: 7 issues in pipeline + terraform for reliable continuous deploy
**Estado general:** ✅ Operativo

---

## ECS — Bot en ejecución

| Campo | Valor |
|-------|-------|
| Cluster | `ppai-cluster` |
| Servicio | `ppai-bot-service` |
| Estado | ACTIVE |
| Tasks corriendo | 1 / 1 |
| Task Definition | `ppai-bot-task:1` |
| Imagen desplegada | `198860290243.dkr.ecr.us-east-1.amazonaws.com/ppai-bot:af69f6a587326eac26a1b9c38b0b8d82a53969a9` |
| CPU / Memoria | 256 CPU / 512 MB |
| Modo | Polling (sin webhook, sin puerto expuesto) |
| Creado | 2026-03-23 |

### Verificar desde CLI
```bash
# Estado del servicio
aws ecs describe-services \
  --cluster ppai-cluster \
  --services ppai-bot-service \
  --query 'services[0].{status:status,running:runningCount,desired:desiredCount}'

# Task corriendo y su IP pública
aws ecs list-tasks --cluster ppai-cluster --service-name ppai-bot-service
aws ecs describe-tasks --cluster ppai-cluster \
  --tasks $(aws ecs list-tasks --cluster ppai-cluster --service-name ppai-bot-service --query 'taskArns[0]' --output text) \
  --query 'tasks[0].{status:lastStatus,health:healthStatus,startedAt:startedAt}'

# Logs en tiempo real
aws logs tail /ppai/bot --follow --since 5m
```

---

## ECR — Imágenes Docker

| Campo | Valor |
|-------|-------|
| Repositorio | `198860290243.dkr.ecr.us-east-1.amazonaws.com/ppai-bot` |
| Mutabilidad | MUTABLE |
| Imagen activa (SHA) | `af69f6a587326eac26a1b9c38b0b8d82a53969a9` |
| Tag `latest` apunta a | `af69f6a5` |
| Imágenes almacenadas | 3 (b499f83c, 5296740d, af69f6a5/latest) |

### Verificar desde CLI
```bash
# Listar todas las imágenes con fecha
aws ecr describe-images --repository-name ppai-bot \
  --query 'sort_by(imageDetails, &imagePushedAt)[*].{tags:imageTags,pushed:imagePushedAt}' \
  --output table

# Imagen activa en el servicio ECS
aws ecs describe-services --cluster ppai-cluster --services ppai-bot-service \
  --query 'services[0].taskDefinition' --output text | xargs \
  aws ecs describe-task-definition --task-definition \
  --query 'taskDefinition.containerDefinitions[0].image' --output text
```

---

## DynamoDB — Persistencia

| Tabla | ARN | Estado | Items |
|-------|-----|--------|-------|
| `ppai-tasks` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-tasks` | ACTIVE | 0 |
| `ppai-events` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-events` | ACTIVE | 0 |
| `ppai-dedup` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-dedup` | ACTIVE | 0 |
| `ppai-cycles` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-cycles` | ACTIVE | 0 |

Todas con `deletion_protection = true` y billing `PAY_PER_REQUEST`.

### Verificar desde CLI
```bash
# Estado de todas las tablas de un vistazo
for TABLE in ppai-tasks ppai-events ppai-dedup ppai-cycles; do
  echo -n "$TABLE: "
  aws dynamodb describe-table --table-name $TABLE \
    --query 'Table.{status:TableStatus,items:ItemCount}' --output text
done

# Contar items en tasks (cuando haya datos)
aws dynamodb scan --table-name ppai-tasks --select COUNT --output text
```

---

## Networking — VPC

| Recurso | ID | Estado |
|---------|-----|--------|
| VPC (`10.0.0.0/16`) | `vpc-0cf93e598f59df491` | available |
| Subnet pública A | `subnet-03d19cda064456e32` | us-east-1a |
| Subnet pública B | `subnet-022789a4aabc02774` | us-east-1b |
| Internet Gateway | `igw-05d33fa9098f16f0f` | available |
| DynamoDB VPC Endpoint | `vpce-0f369f01df69672c5` | available |

> ECS corre en subnets **públicas** con `assign_public_ip = true`. Sin NAT Gateway.
> DynamoDB usa el VPC Endpoint — tráfico interno, sin salir a internet.

### Verificar desde CLI
```bash
# VPC y subnets
aws ec2 describe-vpcs --filters "Name=tag:Name,Values=ppai-vpc" \
  --query 'Vpcs[0].{id:VpcId,state:State,cidr:CidrBlock}'

# VPC Endpoint para DynamoDB
aws ec2 describe-vpc-endpoints --filters "Name=tag:Name,Values=ppai-dynamodb-endpoint" \
  --query 'VpcEndpoints[0].{id:VpcEndpointId,state:State,service:ServiceName}'

# Security group de ECS
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=ppai-ecs-sg" \
  --query 'SecurityGroups[0].{id:GroupId,egress:IpPermissionsEgress}'
```

---

## IAM — Roles

| Role | ARN | Propósito |
|------|-----|-----------|
| `ppai-task-execution-role` | `arn:aws:iam::198860290243:role/ppai-task-execution-role` | ECS pull de imagen ECR + escribir CloudWatch |
| `ppai-task-role` | `arn:aws:iam::198860290243:role/ppai-task-role` | Permisos DynamoDB del bot (least privilege) |
| `ppai-github-deploy` | `arn:aws:iam::198860290243:role/ppai-github-deploy` | GitHub Actions OIDC — deploy sin access keys |

### Verificar desde CLI
```bash
# Todos los roles del proyecto
aws iam list-roles \
  --query 'Roles[?starts_with(RoleName, `ppai`)].{name:RoleName,arn:Arn}' \
  --output table

# Policies inline del task role (permisos DynamoDB)
aws iam get-role-policy \
  --role-name ppai-task-role \
  --policy-name ppai-task-policy \
  --query 'PolicyDocument.Statement[*].{effect:Effect,actions:Action,resources:Resource}'

# OIDC provider para GitHub Actions
aws iam list-open-id-connect-providers --query 'OpenIDConnectProviderList[*].Arn'
```

---

## CloudWatch — Logs

| Log Group | Retención | Bytes almacenados |
|-----------|-----------|-------------------|
| `/ppai/bot` | 90 días | 0 (bot recién iniciado) |

### Verificar desde CLI
```bash
# Ver logs del bot (últimos 10 minutos)
aws logs tail /ppai/bot --since 10m

# Buscar errores en la última hora
aws logs filter-log-events \
  --log-group-name /ppai/bot \
  --filter-pattern "ERROR" \
  --start-time $(python3 -c "import time; print(int((time.time()-3600)*1000))")

# Buscar arranque del bot
aws logs filter-log-events \
  --log-group-name /ppai/bot \
  --filter-pattern "Starting PPAI"
```

---

## Terraform State Backend

| Recurso | Valor | Estado |
|---------|-------|--------|
| S3 Bucket | `ppai-terraform-state` | ACTIVE (versioning + AES256) |
| DynamoDB Lock | `ppai-terraform-lock` | ACTIVE |
| State file | `ppai/terraform.tfstate` | 59.2 KiB — 2026-03-23 |

### Verificar desde CLI
```bash
# Ver state file en S3
aws s3 ls s3://ppai-terraform-state/ppai/ --human-readable

# Verificar que no hay lock activo (debería estar vacío en reposo)
aws dynamodb scan --table-name ppai-terraform-lock \
  --query 'Items[*].LockID' --output text

# Outputs del last apply
cd terraform && terraform output
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

> NAT Gateway eliminado — ahorro de ~$32/mes respecto al diseño original.

---

## Historial de snapshots

| Fecha | Commit | Estado | Cambios principales |
|-------|--------|--------|---------------------|
| 2026-03-23 | `af69f6a5` | ✅ Operativo | Primer deploy exitoso a prod — polling mode, ECS 1/1, 4 tablas DynamoDB activas |
