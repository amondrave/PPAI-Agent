# GitHub Actions OIDC — permite a GitHub Actions asumir roles IAM sin credenciales de larga duración
# Docs: https://docs.github.com/en/actions/security-for-github-actions/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services

# OIDC Provider para GitHub Actions (uno por cuenta AWS, idempotente)
resource "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"

  client_id_list = ["sts.amazonaws.com"]

  # Thumbprint de GitHub Actions (estable — GitHub publica actualizaciones con aviso)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]

  tags = { Project = "ppai", Purpose = "github-actions-oidc" }
}

# IAM Role que GitHub Actions asume via OIDC
resource "aws_iam_role" "github_deploy" {
  name = "ppai-github-deploy-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringLike = {
          # Solo permite el repo específico de PPAI — no cualquier repo
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:*"
        }
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })

  tags = { Project = "ppai", Purpose = "github-actions-deploy" }
}

# Permisos del role de deploy — ECR, ECS, Terraform state, y lo necesario para apply
resource "aws_iam_role_policy" "github_deploy" {
  name = "ppai-github-deploy-policy"
  role = aws_iam_role.github_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR — build y push de imágenes
      {
        Effect = "Allow"
        Action = [
          "ecr:GetAuthorizationToken",
        ]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchGetImage",
          "ecr:BatchCheckLayerAvailability",
          "ecr:CompleteLayerUpload",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = var.ecr_repository_arn
      },
      # ECS — force-new-deployment y describe
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:RegisterTaskDefinition",
          "ecs:DescribeTaskDefinition",
        ]
        Resource = "*"
      },
      # Terraform state backend — S3 + DynamoDB lock
      {
        Effect = "Allow"
        Action = ["s3:GetObject", "s3:PutObject", "s3:DeleteObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::ppai-terraform-state",
          "arn:aws:s3:::ppai-terraform-state/*",
        ]
      },
      {
        Effect = "Allow"
        Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:DeleteItem"]
        Resource = "arn:aws:dynamodb:*:*:table/ppai-terraform-lock"
      },
      # IAM — Terraform necesita leer/crear/actualizar roles y policies
      {
        Effect = "Allow"
        Action = [
          "iam:GetRole", "iam:GetRolePolicy", "iam:GetOpenIDConnectProvider",
          "iam:CreateRole", "iam:UpdateRole", "iam:DeleteRole",
          "iam:PutRolePolicy", "iam:DeleteRolePolicy",
          "iam:AttachRolePolicy", "iam:DetachRolePolicy",
          "iam:PassRole", "iam:TagRole", "iam:UntagRole",
          "iam:CreateOpenIDConnectProvider", "iam:UpdateOpenIDConnectProvider",
          "iam:ListRolePolicies", "iam:ListAttachedRolePolicies",
        ]
        Resource = "*"
      },
      # DynamoDB — Terraform crea/actualiza tablas
      {
        Effect = "Allow"
        Action = [
          "dynamodb:CreateTable", "dynamodb:DescribeTable", "dynamodb:DeleteTable",
          "dynamodb:UpdateTable", "dynamodb:TagResource", "dynamodb:UntagResource",
          "dynamodb:DescribeContinuousBackups", "dynamodb:DescribeTimeToLive",
          "dynamodb:UpdateTimeToLive", "dynamodb:ListTagsOfResource",
        ]
        Resource = "*"
      },
      # CloudWatch Logs
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:DescribeLogGroups", "logs:DeleteLogGroup", "logs:TagLogGroup", "logs:ListTagsLogGroup", "logs:PutRetentionPolicy"]
        Resource = "*"
      },
    ]
  })
}

output "github_deploy_role_arn" {
  value       = aws_iam_role.github_deploy.arn
  description = "ARN del role que GitHub Actions asume via OIDC — copiar a GitHub Secret AWS_DEPLOY_ROLE_ARN"
}
