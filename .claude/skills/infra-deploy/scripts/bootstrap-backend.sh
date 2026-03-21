#!/usr/bin/env bash
# =============================================================================
# PPAI — Bootstrap del Backend de Terraform
# Crea el S3 bucket y la tabla DynamoDB para el state remoto de Terraform.
# Solo se ejecuta UNA VEZ al inicio del proyecto.
# =============================================================================

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

BUCKET_NAME="ppai-terraform-state"
LOCK_TABLE="ppai-terraform-lock"
REGION="us-east-1"

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PPAI — Bootstrap Backend de Terraform           ${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo ""

# ---------------------------------------------------------------------------
# Verificar credenciales
# ---------------------------------------------------------------------------
echo -e "${BLUE}Verificando credenciales AWS...${NC}"
if ! aws sts get-caller-identity &>/dev/null; then
  echo -e "${RED}✗ No hay credenciales AWS configuradas.${NC}"
  echo "  Ejecuta: aws configure"
  exit 1
fi

ACCOUNT=$(aws sts get-caller-identity --query Account --output text)
echo -e "${GREEN}✓ Conectado a la cuenta: $ACCOUNT${NC}"
echo ""

# ---------------------------------------------------------------------------
# S3 Bucket
# ---------------------------------------------------------------------------
echo -e "${BLUE}1. Creando S3 bucket para Terraform state...${NC}"

if aws s3 ls "s3://$BUCKET_NAME" &>/dev/null 2>&1; then
  echo -e "${YELLOW}⚠ Bucket $BUCKET_NAME ya existe — saltando.${NC}"
else
  aws s3 mb "s3://$BUCKET_NAME" --region "$REGION"

  # Habilitar versionamiento (protección contra borrado accidental del state)
  aws s3api put-bucket-versioning \
    --bucket "$BUCKET_NAME" \
    --versioning-configuration Status=Enabled

  # Habilitar encriptación por defecto
  aws s3api put-bucket-encryption \
    --bucket "$BUCKET_NAME" \
    --server-side-encryption-configuration '{
      "Rules": [{"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
    }'

  # Bloquear acceso público
  aws s3api put-public-access-block \
    --bucket "$BUCKET_NAME" \
    --public-access-block-configuration '{
      "BlockPublicAcls": true,
      "IgnorePublicAcls": true,
      "BlockPublicPolicy": true,
      "RestrictPublicBuckets": true
    }'

  echo -e "${GREEN}✓ Bucket $BUCKET_NAME creado con versionamiento y encriptación.${NC}"
fi
echo ""

# ---------------------------------------------------------------------------
# DynamoDB Lock Table
# ---------------------------------------------------------------------------
echo -e "${BLUE}2. Creando DynamoDB table para state locking...${NC}"

if aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$REGION" &>/dev/null 2>&1; then
  echo -e "${YELLOW}⚠ Tabla $LOCK_TABLE ya existe — saltando.${NC}"
else
  aws dynamodb create-table \
    --table-name "$LOCK_TABLE" \
    --attribute-definitions AttributeName=LockID,AttributeType=S \
    --key-schema AttributeName=LockID,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --region "$REGION" \
    --tags Key=Project,Value=ppai Key=ManagedBy,Value=manual

  echo -e "  Esperando que la tabla esté activa..."
  aws dynamodb wait table-exists --table-name "$LOCK_TABLE" --region "$REGION"

  echo -e "${GREEN}✓ Tabla $LOCK_TABLE creada y activa.${NC}"
fi
echo ""

# ---------------------------------------------------------------------------
# Verificación
# ---------------------------------------------------------------------------
echo -e "${BLUE}3. Verificación final...${NC}"

S3_STATUS=$(aws s3 ls "s3://$BUCKET_NAME" &>/dev/null 2>&1 && echo "OK" || echo "FAIL")
DYNAMO_STATUS=$(aws dynamodb describe-table --table-name "$LOCK_TABLE" --region "$REGION" --query "Table.TableStatus" --output text 2>/dev/null || echo "FAIL")

echo -e "  S3 Bucket ($BUCKET_NAME): ${GREEN}$S3_STATUS${NC}"
echo -e "  DynamoDB ($LOCK_TABLE): ${GREEN}$DYNAMO_STATUS${NC}"
echo ""

if [ "$S3_STATUS" = "OK" ] && [ "$DYNAMO_STATUS" = "ACTIVE" ]; then
  echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
  echo -e "${GREEN}  Bootstrap completado. Puedes ejecutar:          ${NC}"
  echo -e "${GREEN}  cd terraform && terraform init                  ${NC}"
  echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
else
  echo -e "${RED}══════════════════════════════════════════════════${NC}"
  echo -e "${RED}  Bootstrap incompleto. Revisa los errores arriba.${NC}"
  echo -e "${RED}══════════════════════════════════════════════════${NC}"
  exit 1
fi
