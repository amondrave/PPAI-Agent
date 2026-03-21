# Troubleshooting — Despliegue de PPAI

## Índice

1. Credenciales y permisos
2. Terraform
3. Docker y ECR
4. ECS y deployment
5. Telegram webhook
6. Costos inesperados

---

## 1. Credenciales y permisos

### `aws sts get-caller-identity` → "Unable to locate credentials"

**Causa:** AWS CLI no tiene credenciales configuradas.

**Solución:**
```bash
aws configure
# Ingresar Access Key ID y Secret Access Key
```

O verifica que exista `~/.aws/credentials`:
```bash
cat ~/.aws/credentials
```

### `An error occurred (AccessDenied)` en terraform

**Causa:** El usuario IAM no tiene los permisos necesarios.

**Diagnóstico:**
```bash
# Ver qué usuario estás usando
aws sts get-caller-identity

# Ver qué políticas tiene
aws iam list-attached-user-policies --user-name terraform-deployer
aws iam list-user-policies --user-name terraform-deployer
```

**Solución:** Adjuntar los permisos faltantes según `aws-iam-setup.md`.

### "SignatureDoesNotMatch" al ejecutar comandos AWS

**Causa:** La Secret Access Key está mal copiada (espacios extra, caracteres truncados).

**Solución:** Regenerar las access keys desde IAM console y volver a configurar:
```bash
aws configure
```

---

## 2. Terraform

### `terraform init` → "Failed to get existing workspaces: S3 bucket does not exist"

**Causa:** El bucket S3 para el state no fue creado.

**Solución:** Ejecutar el bootstrap:
```bash
bash .claude/skills/infra-deploy/scripts/bootstrap-backend.sh
```

### `terraform init` → "Error configuring S3 Backend: no valid credential sources"

**Causa:** Las credenciales no están configuradas o son incorrectas.

**Solución:**
```bash
aws sts get-caller-identity  # Verificar que funciona
terraform init               # Reintentar
```

### `terraform plan` falla con "Error: Reference to undeclared resource"

**Causa:** Los módulos no están bien conectados.

**Solución:** Asegúrate de estar en el directorio correcto:
```bash
cd terraform
terraform init  # Re-init si moviste archivos
terraform plan -var="telegram_bot_token=TU_TOKEN"
```

### `terraform apply` → "Error creating IAM Role: AccessDenied"

**Causa:** El usuario `terraform-deployer` no tiene permisos para crear roles IAM.

**Solución:** Si usas la política personalizada, verifica que la sección `IAMRoleManagement`
incluye `iam:CreateRole` y que el Resource permite `arn:aws:iam::*:role/ppai-*`.

### `terraform destroy` falla con "DeletionProtectionEnabled"

**Causa:** Las tablas DynamoDB tienen protección contra borrado (diseñado así).

**Solución:** Deshabilitar la protección primero:
```bash
aws dynamodb update-table \
  --table-name ppai-tasks \
  --no-deletion-protection-enabled

# Repetir para ppai-events y ppai-dedup
# Luego re-ejecutar terraform destroy
```

### State lock: "Error acquiring the state lock"

**Causa:** Un `terraform apply` anterior falló y dejó el lock activo.

**Solución:**
```bash
# Ver quién tiene el lock
terraform force-unlock LOCK_ID
```

El `LOCK_ID` aparece en el mensaje de error. Solo usa `force-unlock` si estás seguro
de que no hay otro proceso ejecutando terraform.

---

## 3. Docker y ECR

### `docker build` falla con "failed to solve: python:3.12.8-slim: not found"

**Causa:** Docker no puede descargar la imagen base (red o Docker daemon).

**Solución:**
```bash
docker pull python:3.12.8-slim  # Probar manualmente
docker build -t ppai-bot .
```

### ECR login falla con "no basic auth credentials"

**Causa:** El token de ECR expiró (duran 12 horas) o el login no se ejecutó.

**Solución:**
```bash
ECR_URL=$(cd terraform && terraform output -raw ecr_repository_url)
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin $(echo $ECR_URL | cut -d'/' -f1)
```

### `docker push` → "denied: Your authorization token has expired"

**Causa:** Token de ECR expirado.

**Solución:** Re-ejecutar el login (paso anterior).

### `docker push` → "tag invalid: The image tag 'v0.1.0' already exists"

**Causa:** ECR tiene image tag mutability = IMMUTABLE (diseño correcto).

**Solución:** Usa un nuevo tag de versión:
```bash
docker tag ppai-bot:latest $ECR_URL:v0.1.1
docker push $ECR_URL:v0.1.1
```

---

## 4. ECS y deployment

### ECS task se reinicia en loop (CrashLoopBackOff)

**Diagnóstico:**
```bash
# Ver estado del servicio
aws ecs describe-services --cluster ppai-cluster --services ppai-bot-service \
  --query "services[0].{running:runningCount,desired:desiredCount}"

# Ver logs de la última tarea
aws logs tail /ppai/bot --since 10m
```

**Causas comunes:**
- `TELEGRAM_BOT_TOKEN` incorrecto o vacío → verificar en `terraform.tfvars`
- El bot no puede conectar a DynamoDB → verificar VPC endpoint
- Error de código en `ppai/main.py` → ver logs

### ECS service stuck en "DRAINING"

**Causa:** El servicio está intentando detener tasks viejas pero algo lo bloquea.

**Solución:**
```bash
# Forzar nuevo deployment
aws ecs update-service --cluster ppai-cluster --services ppai-bot-service --force-new-deployment
```

### "CannotPullContainerError: pull image manifest has been retried"

**Causa:** ECS no puede descargar la imagen del ECR (permisos o imagen no existe).

**Diagnóstico:**
```bash
# Verificar que la imagen existe
aws ecr list-images --repository-name ppai-bot

# Verificar el task execution role
aws iam get-role-policy --role-name ppai-task-execution-role --policy-name ppai-task-execution-policy
```

---

## 5. Telegram webhook

### Webhook no responde (bot no contesta mensajes)

**Diagnóstico paso a paso:**

```bash
# 1. Verificar que el webhook está registrado
curl -s "https://api.telegram.org/bot$TOKEN/getWebhookInfo" | python3 -m json.tool

# 2. Verificar que ECS tiene tasks corriendo
aws ecs describe-services --cluster ppai-cluster --services ppai-bot-service \
  --query "services[0].runningCount"

# 3. Ver logs recientes
aws logs tail /ppai/bot --since 5m

# 4. Ver logs del API Gateway
aws logs tail /ppai/apigw --since 5m
```

### "Webhook was set" pero `getWebhookInfo` muestra errores

**Revisar:**
- `last_error_message`: indica qué falla
- `last_error_date`: cuándo fue el último error
- `pending_update_count`: updates acumulados sin procesar

**Errores comunes en `last_error_message`:**
- "Wrong response from the webhook: 502 Bad Gateway" → ECS task no está corriendo
- "Connection timed out" → Security group no permite tráfico en port 8443
- "SSL handshake failed" → API Gateway URL incorrecta

### Limpiar updates pendientes

Si el bot acumuló muchos updates mientras estaba caído:
```bash
# Eliminar webhook, limpiar updates, re-registrar
curl -s "https://api.telegram.org/bot$TOKEN/deleteWebhook?drop_pending_updates=true"
curl -s "https://api.telegram.org/bot$TOKEN/setWebhook?url=$API_URL/webhook"
```

---

## 6. Costos inesperados

### NAT Gateway genera costos altos

El NAT Gateway cobra ~$0.045/hora (~$32/mes) solo por existir, más ~$0.045/GB de datos.

**Para desarrollo:** Destruir la infra cuando no la estés usando:
```bash
cd terraform && terraform destroy -var="telegram_bot_token=TU_TOKEN"
```

**Para producción con bajo presupuesto:** Considerar reemplazar NAT Gateway por:
- NAT Instance (EC2 t4g.nano ~$3/mes)
- O mover ECS a public subnet con assign_public_ip=true (menos seguro)

### Cómo ver el gasto actual

```bash
# Requiere permisos de Cost Explorer
aws ce get-cost-and-usage \
  --time-period Start=2026-03-01,End=2026-03-31 \
  --granularity MONTHLY \
  --metrics BlendedCost \
  --filter '{"Tags":{"Key":"Project","Values":["ppai"]}}'
```
