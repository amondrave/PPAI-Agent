variable "tasks_table_arn" {
  description = "ARN of the tasks DynamoDB table"
  type        = string
}

variable "events_table_arn" {
  description = "ARN of the events DynamoDB table"
  type        = string
}

variable "dedup_table_arn" {
  description = "ARN of the dedup DynamoDB table"
  type        = string
}

variable "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  type        = string
}

variable "log_group_bot_arn" {
  description = "ARN of the bot CloudWatch log group"
  type        = string
}

variable "log_group_apigw_arn" {
  description = "ARN of the API Gateway CloudWatch log group"
  type        = string
}
