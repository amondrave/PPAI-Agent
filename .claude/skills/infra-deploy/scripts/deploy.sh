#!/usr/bin/env bash
# =============================================================================
# PPAI — Deploy Pipeline
# Ejecuta el flujo completo: build → push → terraform apply → webhook
# Uso: ./deploy.sh <version> [telegram_bot_token]
# Ejemplo: ./deploy.sh v0.2.0 7123456789:AAH-xxxxx
# =============================================================================

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# Argumentos
# ---------------------------------------------------------------------------
VERSION="${1:-}"
BOT_TOKEN="${2:-}"

if [ -z "$VERSION" ]; then
  echo -e "${RED}Uso: $0 <version> [telegram_bot_token]${NC}"
  echo "  Ejemplo: $0 v0.2.0 7123456789:AAH-xxxxx"
  echo ""
  echo "  Si no pasas el token, se intentará leer de .env"
  exit 1
fi

# Intentar leer token de .env si no se pasó como argumento
if [ -z "$BOT_TOKEN" ]; then
  if [ -f ".env" ]; then
    BOT_TOKEN=$(grep -E "^TELEGRAM_BOT_TOKEN=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'" || true)
  elif [ -f "../.env" ]; then
    BOT_TOKEN=$(grep -E "^TELEGRAM_BOT_TOKEN=" ../.env | cut -d'=' -f2- | tr -d '"' | tr -d "'" || true)
  fi

  if [ -z "$BOT_TOKEN" ]; then
    echo -e "${RED}✗ No se encontró TELEGRAM_BOT_TOKEN.${NC}"
    echo "  Pásalo como segundo argumento o ponlo en .env"
    exit 1
  fi
fi

# Detectar directorio raíz del proyecto
PROJECT_ROOT=""
if [ -f "./Dockerfile" ] && [ -d "./terraform" ]; then
  PROJECT_ROOT="."
elif [ -f "../Dockerfile" ] && [ -d "../terraform" ]; then
  PROJECT_ROOT=".."
else
  echo -e "${RED}✗ No se encontró la raíz del proyecto PPAI.${NC}"
  echo "  Ejecuta este script desde la raíz del proyecto o desde terraform/"
  exit 1
fi

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PPAI — Deploy Pipeline                         ${NC}"
echo -e "${BLUE}  Versión: $VERSION                              ${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo ""

# ---------------------------------------------------------------------------
# Step 1: Obtener ECR URL
# ---------------------------------------------------------------------------
echo -e "${BLUE}[1/6] Obteniendo ECR URL...${NC}"
ECR_URL=$(cd "$PROJECT_ROOT/terraform" && terraform output -raw ecr_repository_url 2>/dev/null)
if [ -z "$ECR_URL" ]; then
  echo -e "${RED}✗ No se pudo obtener ECR URL. ¿Ya ejecutaste terraform apply?${NC}"
  exit 1
fi
echo -e "${GREEN}✓ ECR URL: $ECR_URL${NC}"
echo ""

# ---------------------------------------------------------------------------
# Step 2: Login a ECR
# ---------------------------------------------------------------------------
echo -e "${BLUE}[2/6] Autenticando con ECR...${NC}"
REGION=$(echo "$ECR_URL" | cut -d'.' -f4)
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "$(echo $ECR_URL | cut -d'/' -f1)" 2>/dev/null
echo -e "${GREEN}✓ Autenticado con ECR${NC}"
echo ""

# ---------------------------------------------------------------------------
# Step 3: Build Docker image
# ---------------------------------------------------------------------------
echo -e "${BLUE}[3/6] Construyendo imagen Docker...${NC}"
cd "$PROJECT_ROOT"
docker build -t ppai-bot . 2>&1 | tail -3
echo -e "${GREEN}✓ Imagen construida${NC}"
echo ""

# ---------------------------------------------------------------------------
# Step 4: Tag & Push
# ---------------------------------------------------------------------------
echo -e "${BLUE}[4/6] Push a ECR ($VERSION)...${NC}"
docker tag ppai-bot:latest "$ECR_URL:$VERSION"
docker push "$ECR_URL:$VERSION" 2>&1 | tail -5
echo -e "${GREEN}✓ Imagen pusheada: $ECR_URL:$VERSION${NC}"
echo ""

# ---------------------------------------------------------------------------
# Step 5: Terraform apply con nueva imagen
# ---------------------------------------------------------------------------
echo -e "${BLUE}[5/6] Actualizando ECS via Terraform...${NC}"
cd terraform
terraform apply -auto-approve \
  -var="telegram_bot_token=$BOT_TOKEN" \
  -var="image_tag=$VERSION" 2>&1 | tail -10
echo -e "${GREEN}✓ Terraform apply completado${NC}"
echo ""

# ---------------------------------------------------------------------------
# Step 6: Registrar webhook
# ---------------------------------------------------------------------------
echo -e "${BLUE}[6/6] Registrando webhook de Telegram...${NC}"
API_URL=$(terraform output -raw api_gateway_url)
WEBHOOK_RESULT=$(curl -s "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${API_URL}/webhook")
echo "  $WEBHOOK_RESULT"

if echo "$WEBHOOK_RESULT" | python3 -c "import sys,json; r=json.load(sys.stdin); exit(0 if r.get('ok') else 1)" 2>/dev/null; then
  echo -e "${GREEN}✓ Webhook registrado${NC}"
else
  echo -e "${YELLOW}⚠ Webhook podría no haberse registrado correctamente${NC}"
fi
echo ""

# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Deploy completado exitosamente                 ${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════${NC}"
echo ""
echo "  Versión:     $VERSION"
echo "  ECR Image:   $ECR_URL:$VERSION"
echo "  API Gateway: $API_URL"
echo "  Webhook:     ${API_URL}/webhook"
echo ""
echo "  Verificar:"
echo "    aws logs tail /ppai/bot --follow --since 2m"
echo "    Enviar un mensaje al bot en Telegram"
echo ""
