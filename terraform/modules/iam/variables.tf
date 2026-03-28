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

variable "cycles_table_arn" {
  description = "ARN of the cycles DynamoDB table (UOW-02)"
  type        = string
}

variable "preferences_table_arn" {
  description = "ARN of the preferences DynamoDB table (UOW-03)"
  type        = string
}

variable "user_profiles_table_arn" {
  description = "ARN of the user-profiles DynamoDB table (ER1)"
  type        = string
}

variable "calendar_auth_table_arn" {
  description = "ARN of the calendar-auth DynamoDB table (ER2)"
  type        = string
}

variable "time_blocks_table_arn" {
  description = "ARN of the time-blocks DynamoDB table (ER2)"
  type        = string
}

variable "github_repo" {
  description = "GitHub repo en formato owner/repo — restringe el OIDC role a este repo"
  type        = string
  default     = "amondrave/PPAI-Agent"
}

variable "ecr_repository_arn" {
  description = "ARN of the ECR repository"
  type        = string
}

variable "log_group_bot_arn" {
  description = "ARN of the bot CloudWatch log group"
  type        = string
}

