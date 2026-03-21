# Guía: Crear usuario IAM para Terraform en PPAI

## Por qué un usuario dedicado

Terraform necesita credenciales programáticas para crear y gestionar recursos en AWS.
Usar la cuenta root es peligroso porque tiene acceso ilimitado y no se puede restringir.
Un usuario IAM dedicado:

- Tiene solo los permisos que necesita (principle of least privilege)
- Se puede revocar sin afectar tu acceso a la consola
- Genera access keys independientes del root
- Deja un audit trail claro en CloudTrail

---

## Paso a paso en la consola AWS

### 1. Navegar a IAM

1. Inicia sesión en la consola AWS (https://console.aws.amazon.com)
2. En la barra de búsqueda superior, escribe "IAM"
3. Selecciona "IAM" (Identity and Access Management)
4. En el menú izquierdo, haz clic en "Personas" (Users)

### 2. Crear el usuario

1. Clic en el botón **"Crear usuario"** (Create user)
2. **Nombre de usuario:** `terraform-deployer`
3. **Acceso a la consola:** NO marcar esta casilla (solo necesita acceso programático)
4. Clic en **"Siguiente"**

### 3. Asignar permisos

Tienes dos opciones:

#### Opción A: AdministratorAccess (rápida, para MVP)

1. Selecciona **"Adjuntar políticas directamente"**
2. En el buscador, escribe `AdministratorAccess`
3. Marca la casilla junto a **AdministratorAccess**
4. Clic en **"Siguiente"** → **"Crear usuario"**

Esta opción da acceso total a la cuenta. Es aceptable para un proyecto personal MVP
donde eres el único administrador. Para producción, usa la Opción B.

#### Opción B: Política personalizada (segura, para producción)

1. Selecciona **"Adjuntar políticas directamente"**
2. Clic en **"Crear política"** (se abre una nueva pestaña)
3. Selecciona la pestaña **"JSON"**
4. Pega la siguiente política:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "VPCAndNetworking",
      "Effect": "Allow",
      "Action": [
        "ec2:CreateVpc", "ec2:DeleteVpc", "ec2:DescribeVpcs", "ec2:ModifyVpcAttribute",
        "ec2:CreateSubnet", "ec2:DeleteSubnet", "ec2:DescribeSubnets",
        "ec2:CreateInternetGateway", "ec2:DeleteInternetGateway", "ec2:AttachInternetGateway",
        "ec2:DetachInternetGateway", "ec2:DescribeInternetGateways",
        "ec2:AllocateAddress", "ec2:ReleaseAddress", "ec2:DescribeAddresses",
        "ec2:CreateNatGateway", "ec2:DeleteNatGateway", "ec2:DescribeNatGateways",
        "ec2:CreateRouteTable", "ec2:DeleteRouteTable", "ec2:DescribeRouteTables",
        "ec2:CreateRoute", "ec2:DeleteRoute", "ec2:ReplaceRoute",
        "ec2:AssociateRouteTable", "ec2:DisassociateRouteTable",
        "ec2:CreateSecurityGroup", "ec2:DeleteSecurityGroup", "ec2:DescribeSecurityGroups",
        "ec2:AuthorizeSecurityGroupIngress", "ec2:RevokeSecurityGroupIngress",
        "ec2:AuthorizeSecurityGroupEgress", "ec2:RevokeSecurityGroupEgress",
        "ec2:CreateVpcEndpoint", "ec2:DeleteVpcEndpoints", "ec2:DescribeVpcEndpoints",
        "ec2:ModifyVpcEndpoint",
        "ec2:DescribeAvailabilityZones", "ec2:DescribeRegions",
        "ec2:DescribeNetworkInterfaces", "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface", "ec2:DescribeAccountAttributes",
        "ec2:CreateTags", "ec2:DeleteTags", "ec2:DescribeTags"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECSFullAccess",
      "Effect": "Allow",
      "Action": [
        "ecs:CreateCluster", "ecs:DeleteCluster", "ecs:DescribeClusters",
        "ecs:RegisterTaskDefinition", "ecs:DeregisterTaskDefinition",
        "ecs:DescribeTaskDefinition", "ecs:ListTaskDefinitions",
        "ecs:CreateService", "ecs:UpdateService", "ecs:DeleteService",
        "ecs:DescribeServices", "ecs:ListServices",
        "ecs:DescribeTasks", "ecs:ListTasks", "ecs:RunTask", "ecs:StopTask",
        "ecs:TagResource", "ecs:UntagResource",
        "ecs:PutClusterCapacityProviders", "ecs:UpdateClusterSettings"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ECRFullAccess",
      "Effect": "Allow",
      "Action": [
        "ecr:CreateRepository", "ecr:DeleteRepository", "ecr:DescribeRepositories",
        "ecr:GetAuthorizationToken",
        "ecr:BatchGetImage", "ecr:GetDownloadUrlForLayer",
        "ecr:BatchCheckLayerAvailability",
        "ecr:PutImage", "ecr:InitiateLayerUpload", "ecr:UploadLayerPart",
        "ecr:CompleteLayerUpload",
        "ecr:PutLifecyclePolicy", "ecr:GetLifecyclePolicy",
        "ecr:PutImageScanningConfiguration",
        "ecr:ListImages", "ecr:DescribeImages",
        "ecr:TagResource", "ecr:ListTagsForResource",
        "ecr:SetRepositoryPolicy", "ecr:GetRepositoryPolicy"
      ],
      "Resource": "*"
    },
    {
      "Sid": "DynamoDBFullAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:CreateTable", "dynamodb:DeleteTable", "dynamodb:DescribeTable",
        "dynamodb:UpdateTable", "dynamodb:ListTables",
        "dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:UpdateItem",
        "dynamodb:Query", "dynamodb:Scan", "dynamodb:DeleteItem",
        "dynamodb:DescribeContinuousBackups", "dynamodb:UpdateContinuousBackups",
        "dynamodb:DescribeTimeToLive", "dynamodb:UpdateTimeToLive",
        "dynamodb:TagResource", "dynamodb:UntagResource", "dynamodb:ListTagsOfResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "APIGatewayV2",
      "Effect": "Allow",
      "Action": [
        "apigateway:*"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CloudWatchLogs",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup", "logs:DeleteLogGroup", "logs:DescribeLogGroups",
        "logs:PutRetentionPolicy", "logs:DeleteRetentionPolicy",
        "logs:TagLogGroup", "logs:UntagLogGroup",
        "logs:ListTagsLogGroup", "logs:ListTagsForResource",
        "logs:CreateLogStream", "logs:PutLogEvents",
        "logs:GetLogEvents", "logs:FilterLogEvents",
        "logs:TagResource"
      ],
      "Resource": "*"
    },
    {
      "Sid": "IAMRoleManagement",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole", "iam:DeleteRole", "iam:GetRole",
        "iam:AttachRolePolicy", "iam:DetachRolePolicy",
        "iam:PutRolePolicy", "iam:GetRolePolicy", "iam:DeleteRolePolicy",
        "iam:ListRolePolicies", "iam:ListAttachedRolePolicies",
        "iam:ListInstanceProfilesForRole",
        "iam:TagRole", "iam:UntagRole",
        "iam:PassRole"
      ],
      "Resource": [
        "arn:aws:iam::*:role/ppai-*"
      ]
    },
    {
      "Sid": "TerraformStateBucket",
      "Effect": "Allow",
      "Action": [
        "s3:GetObject", "s3:PutObject", "s3:DeleteObject",
        "s3:ListBucket", "s3:GetBucketVersioning",
        "s3:GetEncryptionConfiguration"
      ],
      "Resource": [
        "arn:aws:s3:::ppai-terraform-state",
        "arn:aws:s3:::ppai-terraform-state/*"
      ]
    },
    {
      "Sid": "STSIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

5. Clic en **"Siguiente"**
6. **Nombre de la política:** `ppai-terraform-deployer-policy`
7. Clic en **"Crear política"**
8. Vuelve a la pestaña de creación de usuario
9. Refresca la lista de políticas y busca `ppai-terraform-deployer-policy`
10. Márcala y clic en **"Siguiente"** → **"Crear usuario"**

### 4. Crear Access Keys

1. En la lista de usuarios, haz clic en **`terraform-deployer`**
2. Ve a la pestaña **"Credenciales de seguridad"** (Security credentials)
3. En la sección **"Claves de acceso"** (Access keys), clic en **"Crear clave de acceso"**
4. **Caso de uso:** selecciona **"Interfaz de línea de comandos (CLI)"**
5. Marca la casilla de confirmación abajo
6. Clic en **"Siguiente"** → **"Crear clave de acceso"**
7. **COPIA AMBOS VALORES AHORA:**
   - `Access Key ID`: empieza con `AKIA...`
   - `Secret Access Key`: cadena larga alfanumérica

El Secret Access Key **solo se muestra una vez**. Si lo pierdes, debes crear una
nueva clave (puedes tener máximo 2 activas por usuario).

### 5. Configurar AWS CLI

```bash
aws configure
```

Responde a las preguntas:
- **AWS Access Key ID:** pega el que copiaste
- **AWS Secret Access Key:** pega el que copiaste
- **Default region name:** `us-east-1`
- **Default output format:** `json`

### 6. Verificar

```bash
aws sts get-caller-identity
```

Debe mostrar algo como:

```json
{
    "UserId": "AIDAXXXXXXXXXXXXXXXXX",
    "Account": "198860290243",
    "Arn": "arn:aws:iam::198860290243:user/terraform-deployer"
}
```

Si ves `:root` en el ARN, estás usando las credenciales root. Repite el proceso.

---

## Seguridad adicional (recomendada)

### Rotar access keys periódicamente

AWS recomienda rotar las keys cada 90 días:

```bash
# Crear nueva key
aws iam create-access-key --user-name terraform-deployer

# Configurar la nueva key
aws configure

# Eliminar la key vieja
aws iam delete-access-key --user-name terraform-deployer --access-key-id AKIAOLD...
```

### Habilitar MFA para el usuario (si tiene acceso a consola)

Para el usuario `terraform-deployer` no es necesario porque no tiene acceso a consola.
Pero si decides habilitarlo en el futuro, puedes hacerlo desde la pestaña de
credenciales de seguridad del usuario.
