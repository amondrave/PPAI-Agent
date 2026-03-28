# Infra Snapshot — PPAI en Producción

**Región:** us-east-1
**Última actualización:** 2026-03-28T13:00:00Z
**Deploy commit:** `a7ba1639` — Merge pull request #14 (ER1 profile/onboarding + ER2 Google Calendar)
**Estado general:** ✅ Operativo

---

## ECS — Bot en ejecución

| Campo | Valor |
|-------|-------|
| Cluster | `ppai-cluster` |
| Servicio | `ppai-bot-service` |
| Estado | ACTIVE |
| Tasks corriendo | 1 / 1 |
| Task Definition | `ppai-bot-task:14` |
| Imagen desplegada | `198860290243.dkr.ecr.us-east-1.amazonaws.com/ppai-bot:a7ba16399aa3354eb0a149f50b289bd663af2fe5` |
| CPU / Memoria | 256 CPU / 512 MB |
| Env vars nuevas | `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `FERNET_ENCRYPTION_KEY` |

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
| Repositorio | `198860290243.dkr.ecr.us-east-1.amazonaws.com/ppai-bot` |
| Mutabilidad | MUTABLE |
| Imagen activa | `a7ba16399aa3354eb0a149f50b289bd663af2fe5` |

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

| Tabla | ARN | Estado | Items | Módulo |
|-------|-----|--------|-------|--------|
| `ppai-tasks` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-tasks` | ACTIVE | 4 | UOW-01 |
| `ppai-events` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-events` | ACTIVE | 9 | UOW-01 |
| `ppai-dedup` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-dedup` | ACTIVE | 0 | UOW-01 |
| `ppai-cycles` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-cycles` | ACTIVE | 5 | UOW-02 |
| `ppai-preferences` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-preferences` | ACTIVE | 1 | UOW-03 |
| `ppai-user-profiles` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-user-profiles` | ACTIVE | 0 | ER1 |
| `ppai-calendar-auth` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-calendar-auth` | ACTIVE | 0 | ER2 |
| `ppai-time-blocks` | `arn:aws:dynamodb:us-east-1:198860290243:table/ppai-time-blocks` | ACTIVE | 0 | ER2 |

### Verificar desde CLI
```bash
# Estado de todas las tablas
for TABLE in ppai-tasks ppai-events ppai-dedup ppai-cycles ppai-preferences ppai-user-profiles ppai-calendar-auth ppai-time-blocks; do
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
| VPC | `vpc-0cf93e598f59df491` | available |
| Subnet pública A | `subnet-03d19cda064456e32` | us-east-1a |
| Subnet pública B | `subnet-022789a4aabc02774` | us-east-1b |
| Subnet privada A | `subnet-05cb3536c9592345e` | us-east-1a |
| Subnet privada B | `subnet-08d184f1312bce86b` | us-east-1b |
| Internet Gateway | `igw-05d33fa9098f16f0f` | available |
| DynamoDB VPC Endpoint | `vpce-0f369f01df69672c5` | available |

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
| `ppai-task-execution-role` | `arn:aws:iam::198860290243:role/ppai-task-execution-role` | ECS pull de imagen + CloudWatch |
| `ppai-task-role` | `arn:aws:iam::198860290243:role/ppai-task-role` | Permisos DynamoDB del bot (8 tablas) |
| `ppai-github-deploy` | `arn:aws:iam::198860290243:role/ppai-github-deploy` | GitHub Actions OIDC deploy |

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
| `/ppai/bot` | 90 días | 7,693,775 |

### Verificar desde CLI
```bash
# Ver logs del bot (últimos 10 minutos)
aws logs tail /ppai/bot --since 10m

# Buscar errores
aws logs filter-log-events \
  --log-group-name /ppai/bot \
  --filter-pattern "ERROR" \
  --start-time $(date -v-1H +%s000)
```

---

## Terraform State Backend

| Recurso | Valor | Estado |
|---------|-------|--------|
| S3 Bucket | `ppai-terraform-state` | versioning enabled |
| DynamoDB Lock | `ppai-terraform-lock` | ACTIVE |
| State file | `ppai/terraform.tfstate` | 72.4 KiB — 2026-03-28 |

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
| ECS Fargate (256 CPU, 512 MB, 24/7) | ~$9.50 |
| DynamoDB (On-Demand, 8 tablas, bajo volumen) | ~$2.00 |
| CloudWatch Logs (90 días retención) | ~$1.00 |
| ECR (imágenes almacenadas) | ~$0.10 |
| VPC + Internet Gateway | $0.00 |
| **Total** | **~$12.60/mes** |

*NAT Gateway eliminado — ahorro de ~$32/mes respecto al diseño original.*

---

## Historial de snapshots

| Fecha | Commit | Estado | Cambios principales |
|-------|--------|--------|---------------------|
| 2026-03-23 | `af69f6a5` | ✅ Operativo | Primer deploy exitoso — polling mode, ECS 1/1, 4 tablas DynamoDB |
| 2026-03-25 | `baafa2b2` | ✅ Operativo | UOW-03: tabla ppai-preferences ACTIVE, task def :5 creada, rolling update pendiente |
| 2026-03-25 | `dc1f81da` | ✅ Operativo | Fix #8: /top3 bandeja vacía + requests dep — task def :7, 5 tablas DynamoDB, 1/1 running |
| 2026-03-28 | `a7ba1639` | ✅ Operativo | ER1+ER2: 3 tablas nuevas (user-profiles, calendar-auth, time-blocks), task def :14, env vars Google/Fernet, 8 tablas total |
