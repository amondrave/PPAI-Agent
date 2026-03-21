#!/usr/bin/env bash
# =============================================================================
# PPAI — Preflight Check for Infrastructure Deployment
# Verifica que todas las herramientas necesarias están instaladas y configuradas
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

PASS=0
FAIL=0
WARN=0

check_pass() {
  echo -e "  ${GREEN}✓${NC} $1"
  ((PASS++))
}

check_fail() {
  echo -e "  ${RED}✗${NC} $1"
  ((FAIL++))
}

check_warn() {
  echo -e "  ${YELLOW}⚠${NC} $1"
  ((WARN++))
}

echo ""
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  PPAI — Preflight Check de Infraestructura      ${NC}"
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
echo ""

# ---------------------------------------------------------------------------
# 1. Herramientas CLI
# ---------------------------------------------------------------------------
echo -e "${BLUE}1. Herramientas CLI${NC}"

if command -v aws &>/dev/null; then
  AWS_VERSION=$(aws --version 2>&1 | head -1)
  check_pass "AWS CLI instalado ($AWS_VERSION)"
else
  check_fail "AWS CLI no encontrado — instalar: brew install awscli"
fi

if command -v terraform &>/dev/null; then
  TF_VERSION=$(terraform version -json 2>/dev/null | python3 -c "import sys,json; print(json.load(sys.stdin)['terraform_version'])" 2>/dev/null || terraform version | head -1)
  check_pass "Terraform instalado ($TF_VERSION)"
else
  check_fail "Terraform no encontrado — instalar: brew install terraform"
fi

if command -v docker &>/dev/null; then
  DOCKER_VERSION=$(docker --version 2>&1)
  check_pass "Docker instalado ($DOCKER_VERSION)"

  if docker info &>/dev/null; then
    check_pass "Docker daemon está corriendo"
  else
    check_fail "Docker daemon no está corriendo — iniciar Docker Desktop"
  fi
else
  check_fail "Docker no encontrado — instalar Docker Desktop"
fi

if command -v git &>/dev/null; then
  check_pass "Git instalado ($(git --version))"
else
  check_warn "Git no encontrado — recomendado para versionamiento"
fi

echo ""

# ---------------------------------------------------------------------------
# 2. Credenciales AWS
# ---------------------------------------------------------------------------
echo -e "${BLUE}2. Credenciales AWS${NC}"

if aws sts get-caller-identity &>/dev/null; then
  CALLER=$(aws sts get-caller-identity --output json 2>/dev/null)
  ACCOUNT=$(echo "$CALLER" | python3 -c "import sys,json; print(json.load(sys.stdin)['Account'])" 2>/dev/null || echo "unknown")
  ARN=$(echo "$CALLER" | python3 -c "import sys,json; print(json.load(sys.stdin)['Arn'])" 2>/dev/null || echo "unknown")
  check_pass "Credenciales válidas (Account: $ACCOUNT)"

  # Verificar que NO es root
  if echo "$ARN" | grep -q ":root"; then
    check_warn "Usando credenciales ROOT — se recomienda crear usuario IAM dedicado"
  else
    check_pass "Usando usuario IAM: $(echo "$ARN" | awk -F'/' '{print $NF}')"
  fi
else
  check_fail "Credenciales AWS no configuradas — ejecutar: aws configure"
fi

echo ""

# ---------------------------------------------------------------------------
# 3. Estructura del proyecto PPAI
# ---------------------------------------------------------------------------
echo -e "${BLUE}3. Estructura del proyecto${NC}"

# Buscar el directorio terraform relativo al script o al cwd
TERRAFORM_DIR=""
if [ -d "./terraform" ]; then
  TERRAFORM_DIR="./terraform"
elif [ -d "../terraform" ]; then
  TERRAFORM_DIR="../terraform"
fi

if [ -n "$TERRAFORM_DIR" ]; then
  check_pass "Directorio terraform/ encontrado"

  EXPECTED_MODULES=("networking" "ecs" "ecr" "dynamodb" "iam" "api-gateway" "monitoring")
  for mod in "${EXPECTED_MODULES[@]}"; do
    if [ -d "$TERRAFORM_DIR/modules/$mod" ]; then
      check_pass "Módulo terraform: $mod"
    else
      check_fail "Módulo terraform faltante: $mod"
    fi
  done
else
  check_warn "Directorio terraform/ no encontrado en cwd — ejecutar desde la raíz del proyecto"
fi

if [ -f "./Dockerfile" ] || [ -f "../Dockerfile" ]; then
  check_pass "Dockerfile encontrado"
else
  check_warn "Dockerfile no encontrado en cwd"
fi

if [ -f "./.env" ] || [ -f "../.env" ]; then
  check_pass "Archivo .env encontrado"
else
  check_warn "Archivo .env no encontrado — necesario para el token de Telegram"
fi

echo ""

# ---------------------------------------------------------------------------
# 4. Backend de Terraform (S3 + DynamoDB)
# ---------------------------------------------------------------------------
echo -e "${BLUE}4. Backend de Terraform${NC}"

if aws sts get-caller-identity &>/dev/null; then
  if aws s3 ls s3://ppai-terraform-state &>/dev/null 2>&1; then
    check_pass "S3 bucket ppai-terraform-state existe"
  else
    check_warn "S3 bucket ppai-terraform-state NO existe — necesitas ejecutar bootstrap"
  fi

  if aws dynamodb describe-table --table-name ppai-terraform-lock &>/dev/null 2>&1; then
    check_pass "DynamoDB table ppai-terraform-lock existe"
  else
    check_warn "DynamoDB table ppai-terraform-lock NO existe — necesitas ejecutar bootstrap"
  fi
else
  check_warn "No se puede verificar backend sin credenciales AWS"
fi

echo ""

# ---------------------------------------------------------------------------
# Resumen
# ---------------------------------------------------------------------------
echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
TOTAL=$((PASS + FAIL + WARN))
echo -e "  Resultado: ${GREEN}$PASS passed${NC} · ${RED}$FAIL failed${NC} · ${YELLOW}$WARN warnings${NC}"

if [ $FAIL -eq 0 ]; then
  echo -e "  ${GREEN}Listo para desplegar.${NC}"
  echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
  exit 0
else
  echo -e "  ${RED}Hay $FAIL problemas que resolver antes de continuar.${NC}"
  echo -e "${BLUE}══════════════════════════════════════════════════${NC}"
  exit 1
fi
