# Guía de Teardown — Destruir infraestructura PPAI

## Antes de destruir

Asegúrate de:

1. **Desregistrar el webhook de Telegram** (el bot dejará de responder):
   ```bash
   curl -s "https://api.telegram.org/bot$TOKEN/deleteWebhook"
   ```

2. **Exportar datos si los necesitas** (las tablas DynamoDB tienen deletion protection):
   ```bash
   # Exportar tareas
   aws dynamodb scan --table-name ppai-tasks --output json > backup-tasks.json

   # Exportar eventos
   aws dynamodb scan --table-name ppai-events --output json > backup-events.json
   ```

3. **Confirmar con el usuario** — esta acción es irreversible.

---

## Paso 1: Deshabilitar deletion protection en DynamoDB

Las tablas tienen protección contra borrado activada por diseño:

```bash
for table in ppai-tasks ppai-events ppai-dedup; do
  aws dynamodb update-table \
    --table-name $table \
    --no-deletion-protection-enabled \
    --region us-east-1
  echo "Deletion protection deshabilitada para $table"
done
```

## Paso 2: Terraform destroy

```bash
cd terraform
terraform destroy -var="telegram_bot_token=TU_TOKEN"
```

Revisa el plan de destrucción y confirma con `yes` solo si estás seguro.

Esto elimina: VPC, subnets, NAT Gateway, ECS cluster, servicio, task definitions,
DynamoDB tablas, API Gateway, ECR repository, IAM roles, CloudWatch log groups.

## Paso 3: Limpiar recursos de bootstrap (opcional)

Si no planeas volver a usar Terraform con este proyecto:

```bash
# Vaciar y eliminar el bucket S3
aws s3 rb s3://ppai-terraform-state --force

# Eliminar la tabla de lock
aws dynamodb delete-table --table-name ppai-terraform-lock
```

## Paso 4: Limpiar imágenes Docker locales (opcional)

```bash
docker rmi ppai-bot:latest
docker image prune -f
```

---

## Qué NO se destruye

- La cuenta AWS sigue existiendo
- El usuario IAM `terraform-deployer` sigue existiendo
- Las access keys siguen activas
- El bot de Telegram sigue existiendo (pero sin webhook no recibe mensajes)

Para eliminar todo rastro, también necesitas:
1. Eliminar el usuario IAM manualmente desde la consola
2. Hablar con BotFather y usar `/deletebot` para eliminar el bot de Telegram
