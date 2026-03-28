variable "image_uri" {
  description = "Full ECR image URI with tag"
  type        = string
}

variable "task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  type        = string
}

variable "task_role_arn" {
  description = "ARN of the ECS task role"
  type        = string
}

variable "subnet_ids" {
  description = "List of subnet IDs for ECS tasks (public for polling mode)"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

variable "log_group_name" {
  description = "CloudWatch log group name"
  type        = string
}

variable "telegram_bot_token" {
  description = "Telegram bot token"
  type        = string
  sensitive   = true
}

variable "table_prefix" {
  description = "DynamoDB table prefix"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "google_client_id" {
  description = "Google OAuth 2.0 client ID"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth 2.0 client secret"
  type        = string
  sensitive   = true
}

variable "fernet_encryption_key" {
  description = "Fernet key for token encryption"
  type        = string
  sensitive   = true
}

variable "anthropic_api_key" {
  description = "Anthropic API key for Claude LLM (ER4)"
  type        = string
  sensitive   = true
}
