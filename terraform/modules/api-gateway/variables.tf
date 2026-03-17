variable "private_subnet_ids" {
  description = "List of private subnet IDs for VPC Link"
  type        = list(string)
}

variable "ecs_security_group_id" {
  description = "Security group ID for ECS tasks"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "log_group_apigw_arn" {
  description = "CloudWatch log group ARN for API Gateway access logs"
  type        = string
}
